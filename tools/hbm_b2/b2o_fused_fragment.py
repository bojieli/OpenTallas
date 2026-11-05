#!/usr/bin/env python3
"""HBM-21 (SS39-TOK, COORD 11-05 ruling (A) on the 14:43 ASK): CANDIDATE FUSED fragment of a B2o S-role VM calendar,
built by construction.  CANDIDATE ONLY: FUSED timing is unproven until the d44v RR table exists; no plan-of-record claim.

Form (C2 option (a), COORD 11-05 08:01; HBM-BIND-5 08:08 pair leaf ot_hnx_fused_vm_pair): the 16 FUSED lanes of a hub
use the 8 S banks, two lanes per bank, on rq0/wq0 (group 0) of vmb_Q<k>_mu1.  The pair leaf steers rr by its own tag,
so the calendar only has to grant group 0.  Construction: a frame of P edges; edge 0 grants group 0 read+write on all 8
S banks for the even lanes, edge 1 for the odd lanes; edges 2..P-1 stay free for the other S clients (DMA back rq1,
SM xload rq2, COLL rq3, IDX rq4, packet 5; SM writer wq1, kq 2, cw 3, packet 4, ccw 5).  Collision-free by construction:
a bank has one read and one write owner per edge, and FUSED edges are reserved before any other client is merged; a
merge onto a FUSED edge, or two clients on one bank edge, is refused.  The FUSED share is 2/P of each S bank's edges.

  b2o_fused_fragment.py --period P [--other other.json] --out prog.json [--manifest manifest.json --name NW.u_calendar_Q_q0]
other.json: [{"edge": e, "dir": "r"|"w", "owner": o, "banks": [..], "client": "IDX"}]  (edge in 0..P-1)
Output: hbm_vm_static_calendar.compile_schedule programme (universal layout, B2o RG5/WG2 = d4g SW params) + fields
candidate_fused {read_pcs, write_pcs, share, status 'CANDIDATE: FUSED timing unproven until the d44v RR table'};
--manifest writes a b2o_cal_static_check manifest with that allow-list.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import hbm_vm_static_calendar as C  # noqa: E402

READ_OWNERS, WRITE_OWNERS = range(1, 6), range(1, 6)   # group 0 = FUSED only; write 6 (dq) never on S


def build(period, other=()):
    if period < 2:
        raise ValueError('period must leave the two FUSED edges')
    words = [dict() for _ in range(period)]
    used = set()
    for e in (0, 1):
        words[e].update(rslot_v=0xff, wslot_v=0xff, rslot=0, wslot=0)
        used |= {(e, d, b) for d in 'rw' for b in range(8)}
    for o in other:
        e, d, own = int(o['edge']), o['dir'], int(o['owner'])
        if not 0 <= e < period or d not in 'rw':
            raise ValueError(f'bad entry {o}')
        if own not in (READ_OWNERS if d == 'r' else WRITE_OWNERS):
            raise ValueError(f"{o.get('client')}: owner {own} not allowed on an S bank ({d})")
        for b in o['banks']:
            if (e, d, b) in used:
                raise ValueError(f"{o.get('client')}: edge {e} bank {b} {d} already booked")
            used.add((e, d, b))
            w = words[e]
            w[d + 'slot_v'] = w.get(d + 'slot_v', 0) | 1 << b
            w[d + 'slot'] = w.get(d + 'slot', 0) | own << (3 * b)
    abi = json.loads((C.ROOT / 'results/arch/hbm_vm_static_1014/quadrant_abi.json').read_text())
    spec = C.layout(abi, 'SW', universal=True)       # SW params RG5/WG2 = every B2o bank body
    prog = C.compile_schedule(spec, dict(base=0, loops=1, cycles=words))
    prog['candidate_fused'] = dict(read_pcs=[0, 1], write_pcs=[0, 1], share=f'2/{period}',
                                   lanes='even lanes edge 0, odd lanes edge 1, all 8 S banks',
                                   status='CANDIDATE: FUSED timing unproven until the d44v RR table; no plan-of-record claim')
    return prog


def manifest(prog, name):
    f = prog['candidate_fused']
    return dict(calendars=[dict(name=name, role='S', programme=prog,
                                allow_group0=dict(read=f['read_pcs'], write=f['write_pcs']))])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--period', type=int, default=4)
    ap.add_argument('--other', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--manifest', type=Path)
    ap.add_argument('--name', default='NW.u_calendar_Q_q0')
    a = ap.parse_args()
    prog = build(a.period, json.loads(a.other.read_text()) if a.other else ())
    a.out.write_text(json.dumps(prog, indent=1) + '\n')
    if a.manifest:
        a.manifest.write_text(json.dumps(manifest(prog, a.name), indent=1) + '\n')
    print(f"B2O_FUSED_FRAGMENT period {a.period} words {len(prog['configuration_writes'])} share {prog['candidate_fused']['share']} CANDIDATE")


if __name__ == '__main__':
    main()
