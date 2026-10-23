#!/usr/bin/env python3
"""Q-DIE11-RLY 10-18: the LAND PLAN of the Qwen compute die's forwarded half-cycle lanes (LANDING-CONTRACT L5):
one E per link, the same at TT and FF, from the die STA of a GEN that already carries the landing MCPs
(case/landing.sdc: set_multicycle_path -setup E0 -hold D-1 on each landing's a[*] / ea[*]).

  fwd_land_plan.py tcl  --lanes case/fwd_lanes.json --corner tt --out land_tt.tcl
      a Tcl snippet for the die STA session (after the clocks / landing.sdc and the parasitics are in): one line per
      lane  "OT_LAND <bid> <corner> <E0> setup <worst slack> hold <worst slack>"  at the landing pins
  fwd_land_plan.py plan --lanes case/fwd_lanes.json --logs sta_tt.log sta_ff.log --out land_plan.json [--D 4]
      S1 = setup_E0 - (E0 - 1) T and H0 = hold_E0 - (D - E0) T (the single-cycle arrival slacks) per corner;
      E = max over corners of 1 + ceil(-S1 / T) (>= 1); window check hold_E = H0 + (D - E) T >= 0 at TT and FF (a hold
      miss raises D, never E); K = E mod 8 (the reset calendar G = R0; --calendar JSON {bid: G - R0} overrides).
      The next GEN takes it with OT_SPLIT_LAND_PLAN=land_plan.json (E -> landing.sdc MCP, K -> the landing's k straps).
      QK-LANDEN 10-19 / RLYH0-EN 10-19: this K excludes the hop-0 en register edge (every lane: landh0 n = 1 and rlyh0
      n >= 2); the GEN adds it once (lane_groups.HOP0_EN_REG).
"""
import argparse, json, math, re
from pathlib import Path

T = 833.333


def pins(r):
    return f"{r['landing']}/a[*]" + ('' if r['n'] == 1 else f" {r['landing']}/ea[*]")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    t = sp.add_parser('tcl'); t.add_argument('--lanes', required=True, type=Path); t.add_argument('--corner', required=True)
    t.add_argument('--out', required=True, type=Path)
    p = sp.add_parser('plan'); p.add_argument('--lanes', required=True, type=Path)
    p.add_argument('--logs', nargs='+', required=True, type=Path); p.add_argument('--out', required=True, type=Path)
    p.add_argument('--D', type=int, default=4); p.add_argument('--calendar', type=Path)
    p.add_argument('--D-auto', help='QW-DIECLK4 10-20: comma list of ring depths (e.g. 4,6,8); per lane the smallest D '
                   'whose hold side holds at TT and FF (L5: a hold miss raises D, never E); the GEN instantiates that '
                   'landing depth.  H0 is measured at --D (the depth of the STA MCPs)')
    p.add_argument('--hold-margin', type=float, default=0.0, help='ps required on hold_E (with --D-auto)')
    a = ap.parse_args()
    fl = json.loads(a.lanes.read_text())
    if a.cmd == 'tcl':
        L = ['# Q-DIE11-RLY landing slacks (tools/qwen_split/fwd_land_plan.py tcl)',
             'proc ot_land_worst {pins kind} {',
             '  set p [find_timing_paths -to [get_pins $pins] -path_delay $kind -group_path_count 1]',
             '  if {[llength $p] == 0} { return NA }',
             '  return [get_property [lindex $p 0] slack]', '}']
        for r in fl['lanes']:
            if r.get('lane') == 'reset':
                continue
            L.append(f"puts \"OT_LAND {r['bid']} {a.corner} {r.get('E_sta', r['E'])} setup [ot_land_worst {{{pins(r)}}} max] "
                     f"hold [ot_land_worst {{{pins(r)}}} min]\"")
        a.out.write_text('\n'.join(L) + '\n')
        print(f'{a.out}: {len(fl["lanes"])} lanes')
        return
    cal = json.loads(a.calendar.read_text()) if a.calendar else {}
    meas = {}
    for lg in a.logs:
        for m in re.finditer(r'^OT_LAND (\S+) (\S+) (\d+) setup (\S+) hold (\S+)', lg.read_text(), re.M):
            meas.setdefault(m.group(1), {})[m.group(2)] = (int(m.group(3)), m.group(4), m.group(5))
    rows, fails = [], []
    for r in fl['lanes']:
        if r.get('lane') == 'reset':
            continue
        mm = meas.get(r['bid'], {})
        s1, h0 = {}, {}
        for c, (e0, s, h) in mm.items():
            if s != 'NA':
                s1[c] = float(s) - (e0 - 1) * T
            if h != 'NA':
                h0[c] = float(h) - (a.D - e0) * T
        if not s1:
            rows.append(dict(bid=r['bid'], n=r['n'], E=None, note='no STA slack at the landing pins')); continue
        E = max(1, max(1 + math.ceil(-v / T) for v in s1.values()))
        Dl = a.D
        for Dl in ([int(x) for x in a.D_auto.split(',')] if a.D_auto else [a.D]):
            if all(v + (Dl - E) * T >= a.hold_margin for v in h0.values()):
                break
        hold_E = {c: round(v + (Dl - E) * T, 1) for c, v in h0.items()}
        ok = all(v >= (a.hold_margin if a.D_auto else 0) for v in hold_E.values())
        K = (E + int(cal.get(r['bid'], 0))) % 8
        row = dict(bid=r['bid'], n=r['n'], E=E, K=K, s1={c: round(v, 1) for c, v in s1.items()},
                   h0={c: round(v, 1) for c, v in h0.items()}, setup_E={c: round(v + (E - 1) * T, 1) for c, v in s1.items()},
                   hold_E=hold_E, window_ok=ok, E_gen=r['E'], D=Dl)
        rows.append(row)
        if not ok:
            fails.append(r['bid'])
    hist, dh = {}, {}
    for x in rows:
        if x.get('D') is not None:
            dh[str(x['D'])] = dh.get(str(x['D']), 0) + 1
        if x.get('E') is not None:
            hist[str(x['E'])] = hist.get(str(x['E']), 0) + 1
    rec = dict(schema='opentallas.qwen_split.fwd_land_plan.v1', T_ps=T, D=a.D, rule='E = max over corners of 1 + ceil(-S1/T)',
               lanes_file=str(a.lanes), logs=[str(x) for x in a.logs], links=rows,
               D_auto=a.D_auto, hold_margin_ps=a.hold_margin if a.D_auto else None,
               summary=dict(links=len(rows), E_hist=hist, D_hist=dh, window_fail=fails, no_slack=[x['bid'] for x in rows if x.get('E') is None]))
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(rec['summary']))


if __name__ == '__main__':
    main()
