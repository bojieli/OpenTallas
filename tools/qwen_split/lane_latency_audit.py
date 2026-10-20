#!/usr/bin/env python3
"""Q-COLLCAL 10-18: lane audit of a Qwen compute die netlist (part of the strict bind gate, port_bind_compute.sh).

From die.v ALONE (the GEN's records are only cross-checked) it derives, per die bus, the stages the netlist really has:
  forwarded lane   rly_<bid>_0 .. rly_<bid>_<n-1> (qfd_rlyh0 / qfd_rlyh / qfd_landh / qfd_landh0), K = the landing's k2..k0
                   straps (each k pin on the instance's tie_hi or tie_lo net), which must equal (total E + calendar
                   G - R0) mod 8 of case/fwd_lanes.json; lane cycles = E + 1
  plain relays     rly_<bid>_0 .. (qfd_rly* masters): n cycles
and FAILS when
  (a) the bits of one bus group (a valid bus + its data buses, tools/qwen_split/lane_groups.py) carry different stage
      counts (forwarded: different E or K; plain: different n; or a mix of forwarded and plain);
  (b) a landing's K straps disagree with fwd_lanes.json (GEN drift), or a lane's frame count does;
  (c) the collective calendar does not absorb the SerDes lanes: io_collective's elaboration LX0..2 (die.v.params.json,
      the parameters the strict bind elaborates it with; missing = 0) != TX(peer port) + RX(own) from the netlist lanes,
      or a UCIe FDI lane has cycles (no UCIe calendar knob);
  (d) Q-COLLCAL3 10-18: the collective calendar PERIOD does not cover the lanes: the elaborated LS (die.v.params.json
      LS; missing = the master's RTL default 376) < lane_groups.collective_calendar(LX as built).LS = max_j KC + KW + 17 +
      PS + LX_j + R_j + R_peer(j) (dv2f14bq LX 10/0/9 needs 377: the real-lane TP8 bench FAILS at 376, PASSES at 377).

    lane_latency_audit.py DIE_V [--lanes fwd_lanes.json] [--params die.v.params.json] --out audit.json
(defaults: fwd_lanes.json / die.v.params.json beside DIE_V).  Exit 0 = PASS, 1 = FAIL, 2 = cannot audit.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lane_groups as LG  # noqa: E402

INST = re.compile(r'^\s*(qfd_\w+)\s+(rly_\w+?)_(\d+)\s*\((.*)\);\s*$', re.M)
CONN = re.compile(r'\.(\w+)\(([^()]*)\)')


def parse(die_v):
    lanes = {}
    for m in INST.finditer(Path(die_v).read_text()):
        mst, bid, k, body = m.group(1), m.group(2)[4:], int(m.group(3)), m.group(4)
        c = dict(CONN.findall(body))
        kind = re.match(r'qfd_(rlyh0|rlyh|landh0|landh|rlyr0|rlyr|rlyrl|rlyf|rlyp|rly)_', mst)
        kind = kind.group(1) if kind else mst
        L = lanes.setdefault(bid, dict(frames={}, K=None, kind=set()))
        L['frames'][k] = kind
        L['kind'].add('fwd' if kind in ('rlyh0', 'rlyh', 'landh0', 'landh') else
                      'reset' if kind.startswith('rlyr') else 'plain')
        if kind in ('landh', 'landh0'):
            hi, lo = c.get('tie_hi'), c.get('tie_lo')
            kb = []
            for b in range(3):
                n = c.get(f'k{b}')
                kb.append(1 if n is not None and n == hi else 0 if n is not None and n == lo else None)
            L['K'] = None if None in kb else kb[0] + 2 * kb[1] + 4 * kb[2]
            L['k_bits'] = kb
    for L in lanes.values():
        L['n'] = max(L['frames']) + 1
        L['contiguous'] = sorted(L['frames']) == list(range(L['n']))
        L['kind'] = sorted(L['kind'])
    return lanes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('die_v', type=Path)
    ap.add_argument('--lanes', type=Path)
    ap.add_argument('--params', type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    lanes_p = a.lanes or a.die_v.parent / 'fwd_lanes.json'
    params_p = a.params or Path(str(a.die_v) + '.params.json')
    net = parse(a.die_v)
    fl = json.loads(lanes_p.read_text()) if lanes_p.exists() else None
    rows = {r['bid']: r for r in (fl or {}).get('lanes', [])}
    fails = []
    # (b) netlist vs GEN record; the per-bus netlist latency
    bus = []
    for bid, L in sorted(net.items()):
        r = rows.get(bid, {})
        if not L['contiguous']:
            fails.append(f'{bid}: relay frames {sorted(L["frames"])} not contiguous')
        if 'reset' in L['kind']:
            continue
        if len(L['kind']) > 1:
            fails.append(f'{bid}: mixed relay kinds {L["kind"]}')
        if 'fwd' in L['kind']:
            if L['K'] is None:
                fails.append(f'{bid}: landing K straps not all on tie_hi / tie_lo ({L.get("k_bits")})'); continue
            if not r or r.get('E') is None:
                fails.append(f'{bid}: forwarded lane in die.v but not in {lanes_p.name}'); continue
            if r.get('n') != L['n']:
                fails.append(f'{bid}: {L["n"]} frames in die.v vs n {r.get("n")} in {lanes_p.name}')
            E, cal = int(r['E']), int(r.get('cal', 0))
            if L['K'] != (E + cal) % 8:
                fails.append(f'{bid}: die.v K {L["K"]} != (total E {E} + calendar {cal}) mod 8 = {(E + cal) % 8} '
                             f'(record K {r.get("K")}; a K from the residual E_sta reads the wrong ring slot)')
            bus.append(dict(bid=bid, src=r.get('src'), dst=r.get('dst'), n=L['n'], E=E, K=L['K'], kind='fwd'))
        else:
            bus.append(dict(bid=bid, src=rows.get(bid, {}).get('src'), dst=rows.get(bid, {}).get('dst'), n=L['n'],
                            E=None, kind='plain'))
    # (a) one latency per bus group (QXF-SEAMC: record bundles by the GEN's 'bundle' field or the bus name)
    import record_bundles as RB
    for b in bus:
        b['bundle'] = rows.get(b['bid'], {}).get('bundle') or RB.bundle_of_bid(b['bid'], b.get('src'), b.get('dst'))
    gid = LG.group_of(bus)
    groups = {}
    for b in bus:
        groups.setdefault(gid[b['bid']], []).append(b)
    gl = {}
    for g, mem in sorted(groups.items()):
        if len(mem) < 2:
            continue
        lat = {b['bid']: (LG.lane_cycles(b), b['kind']) for b in mem}
        gl[g] = {k: v[0] for k, v in lat.items()}
        if len({v for v in lat.values()}) > 1 or len({b.get('K') for b in mem}) > 1:
            fails.append(f'bus group {g}: stage counts differ {gl[g]} ({sorted({v[1] for v in lat.values()})})')
    # (c) the collective calendar
    cll = LG.coll_lane_latency([b for b in bus if b['kind'] == 'fwd'], [b for b in bus if b['kind'] == 'plain'],
                               source=f'{a.die_v} (netlist lanes)')
    fails += [f'collective: {x}' for x in cll['fails']]
    prm = (json.loads(params_p.read_text()).get('masters', {}) if params_p.exists() else {}).get(LG.COLL_MASTER, {})
    has_coll = re.search(r'^\s*' + LG.COLL_MASTER + r'\s+' + LG.COLL_INST + r'\b', a.die_v.read_text(), re.M) is not None
    got = [int(prm.get(f'LX{j}', 0)) for j in range(3)]
    if has_coll and got != cll['LX']:
        fails.append(f'collective calendar LX {got} ({params_p.name if params_p.exists() else "no params sidecar"}) != '
                     f'SerDes lane cycles TX(peer) + RX(own) {cll["LX"]}: every die would fault its static schedule')
    # (d) the calendar period (Q-COLLCAL3): the elaborated LS must absorb the netlist lanes
    cal = LG.collective_calendar(cll['LX'], {k: v for k, v in prm.items() if k != 'LS'})
    ls_got = int(prm['LS']) if 'LS' in prm else cal['rtl_default_LS']
    if has_coll and ls_got < cal['LS']:
        fails.append(f'collective calendar period LS {ls_got} ({"die.v.params.json" if "LS" in prm else "RTL default"}) < '
                     f'{cal["LS"]} needed by the SerDes lanes as built (port {cal["binding_port"]}: '
                     f'{cal["ports"][cal["binding_port"]]}; {cal["rule"]}): the face reads its RX slot before the peer frame lands')
    rec = dict(schema='opentallas.qwen_split.lane_latency_audit.v1', die_v=str(a.die_v), lanes=str(lanes_p) if fl else None,
               params=str(params_p) if params_p.exists() else None, buses=len(bus),
               forwarded=sum(b['kind'] == 'fwd' for b in bus), plain=sum(b['kind'] == 'plain' for b in bus),
               groups=gl, collective=dict(has_instance=has_coll, LX_params=got, LX_lanes=cll['LX'], ports=cll['ports'],
                                          LS_params=ls_got, LS_need=cal['LS'], calendar=cal),
               verdict='FAIL' if fails else 'PASS', fails=fails)
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(f"LANE_LATENCY_AUDIT {rec['verdict']} buses={rec['buses']} fwd={rec['forwarded']} plain={rec['plain']} "
          f"groups={len(gl)} LX_params={got} LX_lanes={cll['LX']} LS={ls_got} LS_need={cal['LS']} fails={len(fails)}" + (f' first: {fails[0]}' if fails else ''))
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
