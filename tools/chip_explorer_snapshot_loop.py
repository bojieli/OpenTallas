#!/usr/bin/env python3
"""Snapshot the closure loop's job state for the Chip Explorer's Element stories.

The closure loop commits a verdict under results/closure_loop/ only when a block CLOSES. Failed routes
(NEEDS_RTL with measured SS/FF) and queued/running variants live only in the loop's job state
(~/.local/state/closure_loop/jobs). The stories show a not-yet-closed element at its current measured
state, so this tool copies the relevant fields of those jobs into a committed snapshot,
site/chip_explorer/inputs/loop_attempts.json, which tools/chip_explorer_build.py reads.

Only fields the loop itself wrote are copied (status, SS/FF/DRC, reason, source commit, purpose); nothing
is computed. Re-run it, rebuild and commit to refresh the page.

Usage: python3 tools/chip_explorer_snapshot_loop.py [--jobs DIR]
"""
import argparse, datetime, json, glob, os
from pathlib import Path

R = Path(__file__).resolve().parents[1]
OUT = R / 'site/chip_explorer/inputs/loop_attempts.json'

# Blocks named by the Element stories (tools/chip_explorer_build.py STORIES[*].blocks / .attempts).
BLOCKS = [
    'ot_s81_bf_native', 'ot_s81_bf_native_root_phase', 'ot_s81_pq_ret_root_cam', 'ot_v41_pqc_spine_screen',
    'ot_v41_rom_elem_q_qxpq_w10', 'dsfd_coll_lane_e', 'dsfd_coll_lane_w', 'dsfd_colt_lane', 'ot_meso_fifo_w512d8g1',
    'ot_meso_fifo_w512d4', 'ot_dsrom_su_fdiv_hr', 'ot_dsrom_su_fdiv_tile', 'ot_dsrom_su_softmax_exp_tile',
    'ot_dsrom_su_softmax_exp_hr', 'hfd_coll_pkt_fifo_ii1', 'hfd_coll_pkt_fifo_ii3', 'hfd_coll_credit_prod',
    'hfd_result_relay64_ew', 'hfd_result_relay64_ns', 'qfd_tile', 'qfd_tile_e', 'qfd_hub_fr', 'qfd_hub_fr_w648',
    'qfd_link_rx128', 'qfd_ctrl_shift_00', 'qfd_ctrl_pc_00',
]
KEEP_STATUS_METRICS = {'NEEDS_RTL', 'NEEDS_HUMAN', 'CLOSED', 'ECO'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', default=os.path.expanduser('~/.local/state/closure_loop/jobs'))
    a = ap.parse_args()
    out = {}
    for f in sorted(glob.glob(os.path.join(a.jobs, '*.json'))):
        try:
            j = json.load(open(f))
        except Exception:
            continue
        spec = j.get('spec') or {}
        b = spec.get('block')
        if b not in BLOCKS:
            continue
        m = j.get('metrics') or {}
        row = dict(job=j.get('name'), status=j.get('status'), updated=j.get('updated'),
                   commit=((spec.get('source') or {}).get('commit') or '')[:9],
                   branch=(spec.get('source') or {}).get('branch'),
                   owner=spec.get('owner'), purpose=(spec.get('purpose') or '')[:600])
        if j.get('status') in KEEP_STATUS_METRICS and m.get('ss_ps') is not None:
            row.update(ss_ps=m.get('ss_ps'), ff_ps=m.get('ff_ps'), drc=m.get('drc'), reason=(j.get('reason') or '')[:300])
        elif j.get('status') in KEEP_STATUS_METRICS:
            row.update(reason=(j.get('reason') or '')[:300])
        out.setdefault(b, []).append(row)
    snap = dict(schema='opentallas.chip-explorer.loop-attempts.v1',
                taken=datetime.datetime.now().astimezone().isoformat(timespec='minutes'),
                source='closure-loop job state (~/.local/state/closure_loop/jobs on the loop host); failed and in-flight '
                       'routes only exist there; closed blocks are also committed under results/closure_loop/',
                blocks=out)
    OUT.write_text(json.dumps(snap, indent=1) + '\n')
    print(OUT, sum(len(v) for v in out.values()), 'jobs in', len(out), 'blocks')


if __name__ == '__main__':
    main()
