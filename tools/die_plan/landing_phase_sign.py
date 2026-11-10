#!/usr/bin/env python3
"""landing_phase_sign.py -- signed phase class of every mesochronous clock landing of a bind (TOK-VERIFY-1, COORD 11-10).

Why: a falling-edge-write ring (ot_dp_clk_landing WNEG=1 / ot_meso_ring TNEG=1) has its late/early flip at ZERO phase
(measured, TOK-VERIFY-1 S1 sweep: +3 cycles when the local read clock rises at or before the forwarded write clock,
+2 when it rises later by any amount in (0, P/2)).  A WNEG=0 ring is +3 over the whole |phase| < P/2 window.  The bind
counts added_cycles_per_crossing (3) for every crossing, and landed_phase_ocv bounds |d| but not its sign.

Per landing and corner, with the signed delta d = t_local - t_fwd at the RING (local rclk pin minus forwarded tclk pin
arrival, ps) and its OCV/droop pessimism p_up (local late / fwd early) and p_dn (fwd late / local early):
    hi = d + p_up, lo = d - p_dn
    LEAD   hi <= -margin          ring counts 3 (what the bind assumes)
    LAG    lo >= +margin          ring counts 2: bind and programme must use 2 there, deterministically
    NEAR   otherwise              non-deterministic per reset: not fixable by counting; structural fix at THIS landing
                                  only (WNEG=0 form or count-aligned ring) with ring hold re-checked
A landing whose corners disagree (LEAD in one, LAG in another) is NEAR.  WNEG=0 rings are FIXED3 (the existing |d|
gate covers them).  No arrivals for a landing -> UNMEASURED.  ADVISORY gate (targets, not gates): the result is
reported in the bind record and the sign-off record; it does not stop a bind.

Arrivals file (--arrivals JSON): {"source": "...", "corners": {"TT": {"<port id>": {"t_local_ps": x, "t_fwd_ps": y,
"p_up_ps": a, "p_dn_ps": b}, ...}, "FF": {...}}}; port ids = bind_clock_landings.json ports[].port.

  landing_phase_sign.py BIND_DIR [--arrivals A.json] [--margin-ps 100] [--lanes a,b | --lanes-from-bcl REPO]
                        [--out BIND_DIR/landing_phase_sign.json] [--tsv FILE]
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA = 'opentallas.landing_phase_sign.v1'


def landing_params(rtl, part_type, dst_bus, cache):
    """WNEG / FREG of the emitted u_cland_<dst_bus> ring in the destination partition type"""
    if part_type not in cache:
        txt = (rtl / f'{part_type}.sv').read_text()
        d = {}
        for m in re.finditer(r'ot_dp_clk_landing\s*#\(([^;]*?)\)\s*(u_cland_[A-Za-z0-9_]+)\s*\(', txt, flags=re.S):
            pr = dict(re.findall(r'\.(\w+)\s*\(\s*([^()]*?)\s*\)', m.group(1)))
            d[m.group(2)] = pr
        cache[part_type] = d
    return cache[part_type].get(f'u_cland_{dst_bus}')


def classify_corner(r, margin):
    d = r['t_local_ps'] - r['t_fwd_ps']
    hi, lo = d + r.get('p_up_ps', 0.0), d - r.get('p_dn_ps', 0.0)
    c = 'LEAD' if hi <= -margin else 'LAG' if lo >= margin else 'NEAR'
    return dict(d_ps=round(d, 2), lo_ps=round(lo, 2), hi_ps=round(hi, 2), cls=c)


def run(bind, arrivals=None, margin=100.0, lanes=None):
    bind = Path(bind)
    rtl = bind / 'rtl'
    cl = json.loads((bind / 'bind_clock_landings.json').read_text())
    tops = sorted(rtl.glob('*_bound_top.sv'))
    top = tops[0].read_text() if tops else ''
    inst_type = {m.group(3): m.group(1) for m in re.finditer(
        r'^    ([A-Za-z_][A-Za-z0-9_]*) (#\(.*\) )?([A-Za-z_][A-Za-z0-9_]*) \($', top, flags=re.M)}
    arr = json.loads(Path(arrivals).read_text()) if arrivals else dict(source=None, corners={})
    corners = sorted(arr.get('corners', {}))
    cache, rows = {}, []
    for p in cl['ports']:
        if lanes is not None and p['lane'] not in lanes:
            continue
        t = inst_type.get(p['dst'])
        prm = landing_params(rtl, t, p['dst_bus'], cache) if t else None
        wneg = None if prm is None else int(re.sub(r'\D', '', prm.get('WNEG', '0')) or 0)
        row = dict(port=p['port'], lane=p['lane'], src=p['src'], dst=p['dst'], src_region=p.get('src_region'),
                   dst_region=p.get('dst_region'), dst_bus=p['dst_bus'], kind=p.get('kind'), wneg=wneg,
                   bind_cycles=p.get('added_cycles'), corners={})
        for c in corners:
            a = arr['corners'][c].get(p['port'])
            if a is not None:
                row['corners'][c] = classify_corner(a, margin)
        if wneg is None:
            row['cls'] = 'UNTRACED'          # no emitted ring found for this crossing
        elif wneg == 0:
            row['cls'] = 'FIXED3'
        elif not corners or len(row['corners']) < len(corners):
            row['cls'] = 'UNMEASURED'
        else:
            cs = {v['cls'] for v in row['corners'].values()}
            row['cls'] = cs.pop() if len(cs) == 1 else 'NEAR'
        row['cycles'] = {'LEAD': 3, 'FIXED3': 3, 'LAG': 2}.get(row['cls'])
        rows.append(row)
    n = Counter(r['cls'] for r in rows)
    lane_adj = defaultdict(int)
    for r in rows:
        if r['cls'] == 'LAG':
            lane_adj[r['lane']] -= 1
    return dict(schema=SCHEMA, gate='ADVISORY', bind=str(bind), arrivals_source=arr.get('source'), corners=corners,
                margin_ps=margin, bind_added_cycles_per_crossing=cl.get('added_cycles_per_crossing'),
                physical_qualified=cl.get('physical_qualified'), counts=dict(n), landings=len(rows),
                near=[r['port'] for r in rows if r['cls'] == 'NEAR'],
                lane_cycle_adjust=dict(lane_adj),
                verdict=('PASS' if rows and set(n) <= {'LEAD', 'FIXED3'} else
                         'NEAR' if n.get('NEAR') else 'LAG_RECOUNT' if n.get('LAG') else 'UNMEASURED'),
                rows=rows)


def summary(lps):
    """the landing_phase_sign section of the bind record (bind_report.json) and the die sign-off record"""
    return dict(gate='ADVISORY', verdict=lps['verdict'], counts=lps['counts'], landings=lps['landings'],
                near=len(lps['near']), margin_ps=lps['margin_ps'], corners=lps['corners'],
                arrivals_source=lps['arrivals_source'], lane_cycle_adjust=lps['lane_cycle_adjust'])


def write_die_record(path, lps, detail=None):
    """create / update the die sign-off record's landing_phase_sign section (other sections are kept)"""
    path = Path(path)
    rec = json.loads(path.read_text()) if path.is_file() else dict(schema='opentallas.die_signoff.v1', sections={})
    rec.setdefault('sections', {})['landing_phase_sign'] = dict(summary(lps), bind=lps['bind'], detail=detail)
    path.write_text(json.dumps(rec, indent=1) + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('bind')
    ap.add_argument('--arrivals')
    ap.add_argument('--margin-ps', type=float, default=100.0)
    ap.add_argument('--lanes')
    ap.add_argument('--lanes-from-bcl', help='repo root: restrict to layer_prog/bound_ctl_lanes.LANES')
    ap.add_argument('--out')
    ap.add_argument('--tsv')
    ap.add_argument('--die-record', help='die sign-off record to update (e.g. physical/die_plan/s81/die_signoff.json)')
    a = ap.parse_args(argv)
    lanes = set(a.lanes.split(',')) if a.lanes else None
    if a.lanes_from_bcl:
        sys.path.insert(0, str(Path(a.lanes_from_bcl) / 'tools/s81_dv/layer_prog'))
        import bound_ctl_lanes as BCL
        lanes = set(BCL.LANES)
    rep = run(a.bind, a.arrivals, a.margin_ps, lanes)
    out = Path(a.out) if a.out else Path(a.bind) / 'landing_phase_sign.json'
    out.write_text(json.dumps(rep, indent=1) + '\n')
    if a.die_record:
        write_die_record(a.die_record, rep, detail=str(out))
    if a.tsv:
        cs = rep['corners'] or ['TT', 'FF']
        with open(a.tsv, 'w') as f:
            f.write('\t'.join(['port', 'lane', 'src', 'dst', 'src_region', 'dst_region', 'wneg']
                              + [f'{c}_d_lo_hi_ps' for c in cs] + ['class', 'cycles']) + '\n')
            for r in rep['rows']:
                f.write('\t'.join(map(str, [r['port'], r['lane'], r['src'], r['dst'], r['src_region'], r['dst_region'],
                                            r['wneg']] + [
                    (f"{r['corners'][c]['d_ps']}/{r['corners'][c]['lo_ps']}/{r['corners'][c]['hi_ps']}"
                     if c in r['corners'] else 'UNMEASURED') for c in cs] + [r['cls'], r['cycles']])) + '\n')
    print(f"{rep['verdict']}: {rep['landings']} landings {rep['counts']} margin {rep['margin_ps']} ps, "
          f"NEAR {len(rep['near'])}, corners {rep['corners'] or 'none (no routed clock)'}")
    return 0   # advisory


if __name__ == '__main__':
    sys.exit(main())
