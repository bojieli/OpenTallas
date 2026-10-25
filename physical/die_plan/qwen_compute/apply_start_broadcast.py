#!/usr/bin/env python3
"""Adopt owner decision 13c on the Qwen compute plan, with no data-path changes.

The START xt1 proof (claude/qc-tok-start2-1025@1a6dbd1f6) used the
release plan plus this exact key: reset.start = broadcast. Boot is S+130;
calendar-relative edges and data latency are unchanged.
"""
import argparse
import json
from pathlib import Path


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
