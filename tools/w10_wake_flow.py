#!/usr/bin/env python3
"""Narrow companion for the existing W10 ping-pong ROM SDC, preserving main's runner."""
import argparse
import hashlib
from pathlib import Path
import run_abi3_physical as flow


EXPECTED = ['set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_rom?]',
            'set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_rom?]']


def overlay(path):
    lines=[line for line in path.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if lines != EXPECTED:
        raise ValueError('only the existing two-cycle ping-pong ROM contract is permitted')
    return lines


def main(argv=None):
    ap=argparse.ArgumentParser(add_help=False)
    ap.add_argument('--sdc-append',type=Path,required=True)
    own,remaining=ap.parse_known_args(argv)
    path=own.sdc_append if own.sdc_append.is_absolute() else flow.ROOT/own.sdc_append
    extra=overlay(path)
    original=flow.sdc_lines
    def lines(view,block,clock_period_ns,constraints=None):
        block['extra_sdc_files']=[dict(path=str(own.sdc_append),sha256=hashlib.sha256(path.read_bytes()).hexdigest())]
        return original(view,block,clock_period_ns,constraints)+extra
    flow.sdc_lines=lines
    return flow.main(remaining)


if __name__=='__main__':raise SystemExit(main())
