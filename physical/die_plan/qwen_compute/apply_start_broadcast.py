#!/usr/bin/env python3
"""Adopt owner decision 13c on the Qwen compute plan, with no data-path changes.

The START xt1 proof (claude/qc-tok-start2-1025@1a6dbd1f6) used the
release plan plus this exact key: reset.start = broadcast. Boot is S+130;
calendar-relative edges and data latency are unchanged.

START roles (PATH-QC-B12 10-25, blocker B1 of the QC<->KV token path; reset_tree.start_roles, main 229753c06): the
types that must run BEFORE the one global START are declared reset.start_role = bootstrap (raw delivered wavefront
reset at the published offsets + one registered local START tap); every other type stays mission (START-gated).
No reset.start_port: no QC leaf reads a die-top START; the token is admitted by sys_face.fwd_epoch (the KV die's
forwarded epoch strobe bump), so the local START taps of the bootstrap types have no consumer.
"""
import argparse
import json
from pathlib import Path


BOOTSTRAP_TYPES = {
    # u_sys_face.u_cseq (qfd_d2d_cal_seq_ovl_rope) is the only driver of the d2d_rom link end's cfg_* / cal_start; the
    # glue also replays the HOST program into tt_pw and the boot ROM -- the KV boot handshake needs all of it before S
    "glue": "D2D calendar/cal sequence (sys_face u_cseq -> d2d_rom cfg/cal_start), boot + program replay",
    # program_obs / cal_program_obs AUTH ledgers and admit_ready = boot_done && rp_program_ready need tt_ctlm out of
    # reset while the program loads (before S)
    "tt_ctlm": "program load ledgers + admit_ready during boot",
}


def apply(raw):
    if raw.get('die', {}).get('name') != 'qwen_compute':
        raise ValueError('START adoption is scoped to qwen_compute')
    reset = raw.get('reset', {})
    if reset.get('release') != 'wavefront':
        raise ValueError('START broadcast requires the approved wavefront reset')
    old = reset.get('start')
    if old not in (None, 'broadcast'):
        raise ValueError(f'refusing to replace another START contract: {old}')
    reset['start'] = 'broadcast'
    for tn in sorted(BOOTSTRAP_TYPES):
        r = raw['partition_types'][tn].setdefault('reset', {})
        if r.get('start_role') not in (None, 'bootstrap'):
            raise ValueError(f'refusing to replace START role {r["start_role"]!r} of type {tn}')
        r['start_role'] = 'bootstrap'
    return raw


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path)
    args=ap.parse_args()
    raw=json.loads(args.plan.read_text())
    apply(raw)
    args.plan.write_text(json.dumps(raw, indent=1)+'\n')


if __name__ == '__main__':
    main()
