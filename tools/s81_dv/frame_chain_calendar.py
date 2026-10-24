#!/usr/bin/env python3
"""Chained-frame landing calendar check (S81-P9-FC 10-23; successor of TOKc-S81b's frame_chain_calendar.py).

One row per frame of a die.v (needs the GEN land plan for the lane flights) or of a dv_slice_cut slice_top.sv (the
dv_flight_sim F of each frame lane is read from the cut; --land-plan only for F = 0 lanes left unwrapped).  Model and
window: frame_chain_reset_v2.inspect -- per lane dt = first forwarded edge at the landing - landing release, with
chained lanes clocked by the upstream frame's LANDED xk (upstream hop-0 gate + parity + upstream flight, then own
ICG + parity + flight); a lane passes when dt < K + 1 at tt and ff (late) and dt > 0 at tt (early).  EARLY_WARN
(reported, not a verdict): release after the lane epoch G (LANDING-CONTRACT L3) or a coincident first edge at ff.  Exit 1 when any frame fails, or when a
chained frame needs a reset delay (the GEN must have run frame_chain_reset_v2).

usage: frame_chain_calendar.py NETLIST [--land-plan land.json] [--sync 4] [--json out.json] [--all]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from frame_chain_reset_v2 import inspect, calendar_rows  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('netlist')
    ap.add_argument('--land-plan')
    ap.add_argument('--sync', type=int, default=4, help='frame rst_n -> landing release edges (FRH10 pad 2 + rsync 2)')
    ap.add_argument('--json')
    ap.add_argument('--all', action='store_true', help='print every frame, not only chained ones and failures')
    a = ap.parse_args()
    land = json.loads(Path(a.land_plan).read_text()) if a.land_plan else None
    frames, changes, _, _ = inspect(Path(a.netlist).read_text(), a.sync, land)
    rows = calendar_rows(frames)
    bad = sorted(i for i, r in rows.items() if not r['ok'])
    for i, r in sorted(rows.items()):
        if a.all or r['upstream'] or not r['ok']:
            print(i, 'up=' + (','.join(r['upstream']) or '-'), 'Rrel', r['release'], 'K', r['K'],
                  ' '.join(f"{c}: F {r['F'][c]} dt {r['dt'][c]} G-R {r['gate_slack'][c]}" for c in r['dt']),
                  'late %+.1f early %+.1f' % (r['late'], r['early']),
                  ('INFEASIBLE' if changes[i].get('infeasible') else 'need +%d' % changes[i]['delay']) if i in changes else '',
                  'OK' if r['ok'] else 'FAIL', 'EARLY_WARN' if r['early_warn'] else '')
    warn = sorted(i for i, r in rows.items() if r['early_warn'])
    print(f'FRAME_CHAIN_CALENDAR early_warn {len(warn)} {warn}')
    print(f'FRAME_CHAIN_CALENDAR frames {len(rows)} chained {sum(1 for r in rows.values() if r["upstream"])} '
          f'window_fail {len(bad)} {bad} need_delay {sorted(changes)}')
    if a.json:
        Path(a.json).write_text(json.dumps(dict(netlist=a.netlist, rows=rows, window_fail=bad, early_warn=warn,
                                                need_delay={i: c.get('delay', 'infeasible') for i, c in changes.items()}), indent=1) + '\n')
    sys.exit(1 if bad or changes else 0)


if __name__ == '__main__':
    main()
