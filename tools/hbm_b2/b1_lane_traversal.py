#!/usr/bin/env python3
"""HBM B1: operation/record -> traversed-lane map from the real edge ledger, and the S2 price of a plan pair.

Why: stages_arch.py prices a per-class BIT-WEIGHTED MEAN lane latency (an aggregate); it cannot price one lane's
cycle change on the records that actually cross it (COORD/Codex OWNER? 10-26: "operation/record -> traversed-lane map
missing; no aggregate station-count shortcut; never substitute B2/generic stage prices").

Edge ledger (per plan, nothing defaulted):
  lane cycles     tools/die_plan/schema.Plan.lane_latency (2 boundary flops + faces + ft stations + pads), per lane id
  lane endpoints  core_conns.json of the SAME plan: every hard-core port wired to the lane's src bus / dst bus
  internal legs   partition_types[*].internal_stations with conn 'bus:<lane bus>' (core-internal relay legs)
Traversal: a lane belongs to FAMILY F when an F core port sits on its src bus or its dst bus (an end with no hard-core
port = soft partition / pass-through, accepted from the other end).  A lane with NO hard-core port at either end is
UNBOUND: no record of this die's core graph crosses it (listed, priced 0, flagged).
Record latency per family (static schedule => a coherent broadcast is padded to its longest member):
  legs = for every ordered (src role, dst role) group of the family's cross-role lanes: max lane cycles (+ internal leg)
  chain = longest directed path through the family's same-role lanes (e.g. HC bank sum chain b000->b001->b002->b003)
  family latency = sum(legs) + chain.   op delta = family latency(candidate) - family latency(baseline), summed over
  the families the op uses (OP_FAMILIES, crossing classes of hgi_sim.ds_relay_latency.crossings).
SM/ATT: the x leg (hub<->SM) runs in parallel with the weight/KV fetch through HBM; 'lower' charges an SM-leg growth
only when it exceeds the fetch-leg growth (ds_relay_latency nominal rule), 'upper' charges it serially.

    python3 b1_lane_traversal.py map  --plan DIR [--plan DIR ...] --out MAP.json
    python3 b1_lane_traversal.py price --baseline DIR --candidate DIR --out PRICE.json [--no-schedule]
"""
import argparse, collections, hashlib, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(os.environ.get("OT_ROOT") or Path(__file__).resolve().parents[2])
sys.path.insert(0, str(ROOT / 'tools'))

# hard-core instance prefix -> functional family (from core_conns instance names of the B1 die)
FAMILY_RULES = [
    (r'^u_(su|sucore|pgp|calendar|cxij)', 'SU'),
    (r'^u_vmb', 'SU_BANK'),
    (r'^u_sfu', 'SFU'),
    (r'^u_(hcb|hc|hc_eng)', 'HC'),
    (r'^u_hb_idx|^u_col_idx', 'IDX'),
    (r'^u_hb_argmax', 'ARGMAX'),
    (r'^u_cij', 'COLL_INJ'),
    (r'^u_(hb_coll|hcollgi|hcollgl|ep|lk|vmdel)', 'COLL'),
    (r'^u_(tkm|tkx)', 'TOPK'),
    (r'^u_(smw|svg|xq|xc|xl|vmks)', 'SM'),
    (r'^u_(hb_vms|hb_dbk|wbk)', 'VM'),
    (r'^u_hb_quant', 'QUANT'),
    (r'^u_host', 'HOST'),
    (r'^u_ctl', 'CTL'),
]
# S2 record op pattern -> families it crosses (ds_relay_latency.crossings classes, made lane-explicit)
OP_FAMILIES = [
    ('SU.*', ['SU', 'SU_BANK']),
    ('ARGMAX.*', ['SU', 'ARGMAX']),
    ('SFU.*', ['SFU']),
    ('HC.*|FUSED.HC_*', ['HC']),
    ('FUSED.QDQ*', ['QUANT']),
    ('FUSED.*', ['SU']),
    ('IDX.TOPK', ['IDX', 'TOPK']),
    ('IDX.*', ['IDX', 'COLL_INJ']),
    ('COLL.TOPK_MERGE', ['COLL', 'TOPK']),
    ('COLL.*', ['COLL', 'COLL_INJ']),
    ('SM.*|ATT.*', ['SM']),
    ('DMA.*', ['VM']),
]
PARALLEL_FAMILIES = {'SM'}
STATUS = re.compile(r'\.(fault|fault_cause|phy_up)$')     # x leg || HBM fetch leg (see doc)


def family(inst):
    for rx, f in FAMILY_RULES:
        if re.match(rx, inst):
            return f
    return 'OTHER'


def port_family(port):
    # a SerDes endpoint's rx_block_ready goes to the host command processor (host interface, not the on-die COLL record)
    if re.match(r'^u_ep_[NS]\d+\.rx_block_ready$', port):
        return 'HOST'
    return family(port.split('.')[0])


def role(p):
    if p.startswith('PHY'): return 'PHY'
    if p == 'root': return 'root'
    loc = re.sub(r'^(NW|NE|SW|SE)_', '', p)
    for rx, r in ((r'sm\d', 'sm'), (r'su\d', 'su'), (r'sp', 'spine'), (r'hub$', 'hub'), (r'b0', 'hcb'), (r'b10', 'idx'),
                  (r'b11', 'sfuc'), (r'io$', 'io'), (r'mc', 'mc')):
        if re.match(rx, loc): return r
    return 'seam'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def ledger(pdir, conns=None):
    from die_plan.schema import Plan
    pdir = Path(pdir); pp = pdir / 'die_plan.json'; cp = Path(conns) if conns else pdir / 'core_conns.json'
    plan = json.loads(pp.read_text()); cc = json.loads(cp.read_text())
    P = Plan(plan, str(pp))
    pt = {p['name']: p['type'] for p in plan['partitions']}
    ports = {q['id']: q for q in plan['ports']}
    rev = collections.defaultdict(set)
    for tn, cores in cc.items():
        for core, cps in (cores.items() if isinstance(cores, dict) else ()):
            for port, tg in (cps.items() if isinstance(cps, dict) else ()):
                for t in (tg if isinstance(tg, list) else [tg]):
                    if isinstance(t, str) and t.startswith('bus:'):
                        rev[(tn, t[4:])].add(f'{core}.{port}')
    hard_types = {tn for tn, cores in cc.items() if isinstance(cores, dict) and cores}
    internal = collections.defaultdict(int)          # (type, bus) -> max internal relay stations on that bus
    for tn, ty in plan['partition_types'].items():
        for e in ty.get('internal_stations', []):
            for part in str(e.get('conn', '')).split('|'):
                if part.startswith('bus:'):
                    internal[(tn, part[4:])] = max(internal[(tn, part[4:])], len(e['regs_um']))
    lanes = {}
    for ln in plan['lanes']:
        s = ports[ln['ports'][0]]['src']; d = ports[ln['ports'][-1]]['dst']
        sp = sorted(rev.get((pt[s['part']], s['bus']), ())); dp = sorted(rev.get((pt[d['part']], d['bus']), ()))
        # status / observability ports (fault, fault_cause, phy_up) are on no record's data path
        fs = {port_family(x) for x in sp if not STATUS.search(x)}
        fd = {port_family(x) for x in dp if not STATUS.search(x)}
        hard_s, hard_d = pt[s['part']] in hard_types, pt[d['part']] in hard_types
        if fs and fd:
            fam = sorted(fs & fd)
        else:
            fam = sorted(fs | fd)
        L = P.lane_latency(ln['id'])
        extra = internal.get((pt[s['part']], s['bus']), 0) + internal.get((pt[d['part']], d['bus']), 0)
        lanes[ln['id']] = dict(src=s['part'], src_bus=s['bus'], dst=d['part'], dst_bus=d['bus'],
                               width=ports[ln['ports'][0]]['width'], cycles=L['cycles'], internal_stations=extra,
                               total=L['cycles'] + extra, roles=[role(s['part']), role(d['part'])],
                               families=fam, src_ports=len(sp), dst_ports=len(dp),
                               bound='BOTH' if sp and dp else ('ONE_SIDE' if sp or dp else 'UNBOUND'),
                               traversed=bool(fam),
                               ft_slots=[x for x in ln['ports'][1:-1]])
    return dict(plan=str(pp), plan_sha256=sha(pp), core_conns=str(cp), core_conns_sha256=sha(cp), lanes=lanes)


def family_latency(led, fam):
    """-> (total, legs{(rs,rd): (cycles, lane)}, chain(cycles, path))"""
    legs = {}; chain_edges = collections.defaultdict(list)
    for lid, x in led['lanes'].items():
        if fam not in x['families']:
            continue
        rs, rd = x['roles']
        if rs == rd and x['src'][:2] == x['dst'][:2] and rs not in ('hub', 'root'):
            chain_edges[x['src']].append((x['dst'], x['total'], lid))
        else:
            k = f'{rs}->{rd}'
            if k not in legs or x['total'] > legs[k][0]:
                legs[k] = (x['total'], lid)
    memo = {}

    def longest(n, seen):
        best = (0, [])
        for m, c, lid in chain_edges.get(n, ()):
            if m in seen: continue
            t, p = longest(m, seen | {m})
            if c + t > best[0]: best = (c + t, [lid] + p)
        return best
    chain = (0, [])
    for n in list(chain_edges):
        c = longest(n, {n})
        if c[0] > chain[0]: chain = c
    return sum(v[0] for v in legs.values()) + chain[0], legs, chain


def op_deltas(base, cand, exclude=()):
    fams = sorted({f for _, fs in OP_FAMILIES for f in fs})
    fl = {f: dict(baseline=family_latency(base, f), candidate=family_latency(cand, f)) for f in fams}
    rows = []
    for op, fs in OP_FAMILIES:
        d = 0; det = {}
        for f in fs:
            b, c = fl[f]['baseline'], fl[f]['candidate']
            det[f] = dict(baseline=b[0], candidate=c[0], delta=c[0] - b[0],
                          legs_changed={k: [b[1].get(k), c[1].get(k)] for k in set(b[1]) | set(c[1])
                                        if b[1].get(k, (None,))[0] != c[1].get(k, (None,))[0]},
                          chain=[b[2], c[2]])
            if f in exclude:
                det[f]['excluded'] = 'priced by an existing ledger row; not double-charged'
            else:
                d += c[0] - b[0]
        rows.append(dict(op=op, families=fs, delta_cycles=d, parallel=bool(set(fs) & PARALLEL_FAMILIES), detail=det))
    return rows, fl


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('map'); m.add_argument('--plan', action='append', required=True); m.add_argument('--out', required=True)
    p = sub.add_parser('price'); p.add_argument('--baseline', required=True); p.add_argument('--candidate', required=True)
    p.add_argument('--out', required=True); p.add_argument('--no-schedule', action='store_true')
    p.add_argument('--core-conns', help='one core graph for BOTH plans (default: each plan its own core_conns.json)')
    p.add_argument('--exclude-family', action='append', help='family already priced by an existing ledger row')
    p.add_argument('--host-per-token', action='store_true', help='charge HOST-family leg growth once per token')
    a = ap.parse_args()
    src = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    if a.cmd == 'map':
        out = dict(schema='opentallas.hbm_b1_lane_traversal_map.v1', source_commit=src, family_rules=FAMILY_RULES,
                   op_families=OP_FAMILIES, plans=[ledger(x) for x in a.plan])
        Path(a.out).write_text(json.dumps(out, indent=1) + '\n'); return
    base, cand = ledger(a.baseline, a.core_conns), ledger(a.candidate, a.core_conns)
    rows, fl = op_deltas(base, cand, set(a.exclude_family or ()))
    changed = {l: dict(baseline=base['lanes'][l]['total'], candidate=cand['lanes'][l]['total'],
                       families=cand['lanes'][l]['families'], bound=cand['lanes'][l]['bound'],
                       src=cand['lanes'][l]['src'], dst=cand['lanes'][l]['dst'], width=cand['lanes'][l]['width'],
                       on_critical_leg=sorted({f for f in cand['lanes'][l]['families'] if f in fl and (
                           any(v[1] == l for v in fl[f]['candidate'][1].values()) or l in fl[f]['candidate'][2][1])}))
               for l in sorted(set(base['lanes']) | set(cand['lanes']))
               if base['lanes'].get(l, {}).get('total') != cand['lanes'].get(l, {}).get('total')}
    res = dict(schema='opentallas.hbm_b1_lane_price.v1', status='CONDITIONAL_MODEL_NOT_ADOPTED', source_commit=src,
               baseline=dict(plan=base['plan'], sha256=base['plan_sha256'], core_conns_sha256=base['core_conns_sha256']),
               candidate=dict(plan=cand['plan'], sha256=cand['plan_sha256'], core_conns_sha256=cand['core_conns_sha256']),
               changed_lanes=changed, op_deltas=rows, excluded_families=sorted(a.exclude_family or ()),
               unbound_changed=[l for l, x in changed.items() if not x['families']],
               family_latency={f: dict(baseline=v['baseline'][0], candidate=v['candidate'][0]) for f, v in fl.items()})
    hostd = fl.get('HOST') and fl['HOST']['candidate'][0] - fl['HOST']['baseline'][0]
    if not a.no_schedule:
        sys.path.insert(0, str(ROOT / 'tools/throughput'))
        import accepted_cost as A
        CLK = 1.2e9
        res['schedule'] = {}
        for wl, name in A.DESIGNS['r25gq']['workloads'].items():
            run, count = A.hbm_schedule(name)
            b = run(); w = dict(base_cycles=round(b, 1), base_tok_s=round(CLK / b, 2), records={})
            first = {}
            for k in count:
                for r in rows:
                    if A.op_match(k, r['op']):
                        first[k] = r; break
            for mode in ('lower', 'upper'):
                ex = [(k, None, float(r['delta_cycles'])) for k, r in sorted(first.items())
                      if r['delta_cycles'] and not (r['parallel'] and mode == 'lower')]
                new = run(extra=tuple(ex))
                if a.host_per_token and hostd:
                    new += hostd
                w[mode] = dict(terms=[[o, d] for o, f, d in ex], cycles=round(new, 1), added_cycles=round(new - b, 1),
                               tok_s=round(CLK / new, 2), e2e_loss_pct=round(A.loss_pct(b, new), 4))
            w['op_rows'] = {k: r['op'] for k, r in sorted(first.items())}
            w['unmapped_ops'] = sorted(k for k in count if k not in first)
            for k, r in first.items():
                w['records'][r['op']] = w['records'].get(r['op'], 0) + count[k]
            res['schedule'][wl] = w
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    print(json.dumps(dict(changed=len(changed), unbound=res['unbound_changed'],
                          ops={r['op']: r['delta_cycles'] for r in rows if r['delta_cycles']},
                          schedule={k: {m: v[m]['e2e_loss_pct'] for m in ('lower', 'upper')} for k, v in res.get('schedule', {}).items()})))


if __name__ == '__main__':
    main()
