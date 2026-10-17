#!/usr/bin/env python3
"""HBM die -> opentallas.die_relay_stages.v1 (ROOT RELAY-SCHEMA 10-16; additive post-processor, no placement change).

    relay_stages_export.py CASE_DIR --contract C.json --plan-id ID [--stations STATIONS.json[.gz]]
        [--clock-manifest M.json] [--commit SHA] [--reach UM] [--clock-period-ps 833.333] --out FILE.json[.gz]

Reads a die case exactly as die_relay_pass / die_relay_stations do (manifest placement, view LEF pins, die.v nets,
typed clocks excluded) and gives every die data bus  origin (inst, port) -> terminal sink (inst, port)  its relay
stage count, per bit, walked back through the hbfd_rly_* relay instances already in the netlist (1 stage each):
  * die run  (no --stations): stages = relay instances in the netlist  -- what the die actually contains;
  * die plan (--stations, the station list planned on THIS case): + the planned station depth of every hop
    (equal_age_pad: the bus max depth at every sink; p2p / cfg_no_pad: the sink's own depth) -- what the relay
    contract will instantiate.  A relayed die run of that plan must export the same table (tools/die_relay_check.py).
A bus whose bits disagree takes the max and is listed in 'problems'.  Nets from die ports (reset/por, refclk) and
reset-forest nets are excluded (not data).  coverage = complete (0-stage buses included).
"""
import argparse, collections, gzip, hashlib, json, math, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent))
import die_relay_pass as RP  # noqa: E402
import die_relay_stages as DRS  # noqa: E402

RESET = re.compile(r'^(por_|rst|reset)|_rst_n$|_rst$')
BIT = re.compile(r'\[(\d+)\]$')


def _read(p):
    return json.loads(gzip.open(p).read() if str(p).endswith('.gz') else Path(p).read_text())


def planned_depths(stations):
    """(driver inst, sorted sink-inst tuple) -> (row, {sink: depth seen by that sink}, eq group or None)"""
    out = {}
    for r in stations['rows']:
        di = r['driver'].split('.')[0]
        key = (di, tuple(sorted(r['sinks'])))
        dmax = r['depth']
        dep = {s: (dmax if r['cls'] == 'equal_age_pad' else d) for s, d in zip(r['sinks'], r['sink_depths'])}
        grp = None
        if r['cls'] == 'equal_age_pad':
            grp = f"{r['driver']}#{hashlib.sha1(','.join(sorted(r['sinks'])).encode()).hexdigest()[:8]}"
        out[key] = (r, dep, grp)
    return out


def export(case, contract, plan_id, stations=None, clock_manifest=None, commit=None, reach=None,
           clock_period_ps=833.333, sources=()):
    c = Path(case)
    pl, nets, directions, top_inputs = RP.load_case(c, contract)
    isrly = lambda inst: (pl[inst].get('master') or '').startswith('hbfd_rly_')
    dom_of = {}
    cm = clock_manifest or json.loads((c / 'manifest.json').read_text())
    for dom, m in cm.get('clock_entry_map', {}).items():
        for inst in m:
            dom_of.setdefault(inst, dom)
    plan = planned_depths(stations) if stations else {}
    net_drv, net_loads, rly_in, excluded = {}, {}, {}, collections.Counter()
    for n, ends in nets.items():
        if n in top_inputs:
            excluded['die_port_driven'] += 1; continue
        if len(ends) < 2:
            continue
        drv = [e for e in ends if directions.get(e[:2]) == 'OUTPUT']
        lds = [e for e in ends if directions.get(e[:2]) == 'INPUT']
        if len(drv) != 1 or len(drv) + len(lds) != len(ends):
            excluded['ambiguous'] += 1; continue
        net_drv[n], net_loads[n] = drv[0], lds
        for l in lds:
            if isrly(l[0]):
                k = BIT.search(l[1]); rly_in[(l[0], k.group(1) if k else '')] = n
    used_rows = set()

    def hop(n, sink_inst):
        if not plan:
            return 0, None, None
        key = (net_drv[n][0], tuple(sorted({l[0] for l in net_loads[n]})))
        p = plan.get(key)
        if p is None:
            return 0, None, None
        used_rows.add(key)
        return p[1].get(sink_inst, 0), p[2], p[0].get('domain')

    bits = collections.defaultdict(lambda: dict(st=[], drv_pins=set(), grp=set(), dom=set(), o=None, s=None, sp=[]))
    for n, loads in net_loads.items():
        for l in loads:
            if isrly(l[0]):
                continue
            st, grp, rdom = hop(n, l[0])
            relays, cur, seen = 0, n, set()
            while isrly(net_drv[cur][0]) and cur not in seen:
                seen.add(cur)
                k = BIT.search(net_drv[cur][1]); prev = rly_in.get((net_drv[cur][0], k.group(1) if k else ''))
                relays += 1
                if prev is None:
                    break
                s2, g2, d2 = hop(prev, net_drv[cur][0]); st += s2; cur = prev
                grp = grp or g2; rdom = rdom or d2
            o = net_drv[cur]
            op, sp = RP.base(o[1]), RP.base(l[1])
            if RESET.search(op) or RESET.search(sp):
                excluded['reset_forest_bits'] += 1; continue
            b = bits[(o[0], op, l[0], sp)]
            b['st'].append(st + relays); b['drv_pins'].add(o[1]); b['o'] = o; b['sp'].append(l[2])
            if grp:
                b['grp'].add(grp)
            b['dom'].add(dom_of.get(o[0]) or rdom)
    buses, problems = [], []
    for (oi, op, si, sp), b in sorted(bits.items()):
        smax, smin = max(b['st']), min(b['st'])
        bid = DRS.bus_id(oi, op, si, sp)
        if smax != smin:
            problems.append(f'{bid}: non-uniform bit stages {smin}..{smax} (max taken)')
        if len(b['grp']) > 1:
            problems.append(f'{bid}: bits in {len(b["grp"])} equal-age groups')
        doms = sorted(d for d in b['dom'] if d)
        cx = sum(p[0] for p in b['sp']) / len(b['sp']); cy = sum(p[1] for p in b['sp']) / len(b['sp'])
        buses.append(dict(id=bid, src=dict(inst=oi, port=op, master=pl[oi].get('master')),
                          dst=dict(inst=si, port=sp, master=pl[si].get('master')), width=len(b['drv_pins']),
                          stages=smax, domain=doms[0] if len(doms) == 1 else (None if not doms else 'multi:' + '+'.join(doms)),
                          eq_age_group=sorted(b['grp'])[0] if b['grp'] else None,
                          span_um=round(abs(b['o'][2][0] - cx) + abs(b['o'][2][1] - cy), 1)))
    if plan:
        unused = [k for k in plan if k not in used_rows]
        for k in unused[:50]:
            problems.append(f'station row {plan[k][0]["driver"]} -> {len(k[1])} sinks not matched in the case nets')
        if unused:
            problems.append(f'{len(unused)} station rows unmatched in total')
    if reach is None:
        import die_reach
        reach = die_reach.reach_um('hbm')
    kind = 'die plan (netlist relays + planned stations)' if stations else 'die run (netlist relays only)'
    return DRS.make_doc('hbm', dict(id=plan_id, commit=commit, generator='tools/hbm_die_v15/relay_stages_export.py',
                                    sources=[str(c)] + list(sources), kind=kind),
                        clock_period_ps, reach, buses, coverage='complete', reach_source='results/arch/die_reach_1016.json',
                        excluded=dict(excluded), problems=problems,
                        existing_relay_instances=sum(1 for i in pl if isrly(i)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('case'); ap.add_argument('--contract', required=True); ap.add_argument('--plan-id', required=True)
    ap.add_argument('--stations'); ap.add_argument('--clock-manifest'); ap.add_argument('--commit')
    ap.add_argument('--reach', type=float); ap.add_argument('--clock-period-ps', type=float, default=833.333)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    doc = export(a.case, _read(a.contract), a.plan_id, _read(a.stations) if a.stations else None,
                 _read(a.clock_manifest) if a.clock_manifest else None, a.commit, a.reach, a.clock_period_ps,
                 sources=[a.contract] + ([a.stations] if a.stations else []))
    DRS.write(a.out, doc)
    st = collections.Counter(b['stages'] for b in doc['buses'])
    print(f"{a.out}: {doc['bus_count']} buses, stages max {max(st) if st else 0}, relayed buses "
          f"{sum(v for k, v in st.items() if k)}, problems {len(doc['problems'])}, {doc['digest']}")
    for p in doc['problems'][:10]:
        print('  problem:', p)


if __name__ == '__main__':
    main()
