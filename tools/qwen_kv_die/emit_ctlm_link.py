#!/usr/bin/env python3
"""Emit opt-in ctlm die-link successor while preserving the released emitter.

The control tile's link timing must use the same LNK/CLNK as the upper
subtiles and real die stations. This exposes existing, exact timing
parameters; it does not establish a routed view or token gain.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/redesign_qwen'))
import split_ctrl as S


def emit():
    old = S.emit_tt_ctlm()
    replacements = {
        'module ot_qfd_tt_ctlm #(': 'module ot_qfd_tt_ctlm_link #(',
        'parameter integer XW = 24, parameter integer IS = 1, parameter integer OS = 1':
            'parameter integer XW = 24, parameter integer IS = 1, parameter integer OS = 1,\n'
            '    parameter integer LNK = 0, parameter integer CLNK = 0',
        '.LNK(0)': '.LNK(LNK)',
        '.CLNK(0)': '.CLNK(CLNK)',
    }
    text = old
    for before, after in replacements.items():
        if text.count(before) != 1:
            raise ValueError(f'expected one anchor: {before!r}, got {text.count(before)}')
        text = text.replace(before, after)
    return text, old


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--model-out', type=Path, required=True)
    a = ap.parse_args()
    text, old = emit()
    pinned = ROOT / 'rtl/qwen_sys/redesign_qwen/ot_qfd_tt_ctlm.sv'
    if old != pinned.read_text():
        raise SystemExit('released emitter differs from pinned ctlm; inspect before generating successor')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(text)
    model = dict(schema='opentallas.qwen.ctlm-link-successor.v1',
                 source_sha256=hashlib.sha256(pinned.read_bytes()).hexdigest(),
                 successor_sha256=hashlib.sha256(text.encode()).hexdigest(),
                 default_equivalent=True, adoption='requires actual die-link counts, exact bench and routed qualification',
                 model=dict(macs_per_cycle_delta=0, memory_bytes_per_cycle_delta=0,
                            replica_count=1, mux_fanout_area_delta=0,
                            boundary_bits_per_cycle_delta=0, registers_at_default_delta=0,
                            result_latency_cycles='5 + 2*LNK; control timing shifted by CLNK; actual RTL latency must be measured',
                            upper_select_delay_cycles='CLNK + 2 + LNK - CR (must be nonnegative)',
                            clock_hz=1200000000),
                 old_sources_unchanged=True)
    a.model_out.parent.mkdir(parents=True, exist_ok=True)
    a.model_out.write_text(json.dumps(model, indent=2) + '\n')
    print(json.dumps(model))


if __name__ == '__main__':
    main()
