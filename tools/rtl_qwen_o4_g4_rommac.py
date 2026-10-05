#!/usr/bin/env python3
"""Cycle-equivalence gate of the banked-macro Qwen O4 ROM/MAC neighbourhood.

Runs rtl/test/tb_qwen_o4_g4_rommac.sv under Icarus: ot_qwen_o4_g4_rommac
(11 code banks a pair column, 2 scale banks a group, the test ROM standing in
for the macro view) against the unchanged ot_hdc_matvec fed by flat
synchronous ROMs holding the same words. Every matvec output is compared
every cycle over four INT8 ops that cross code and scale bank boundaries,
reach the top code bank and use K-splits. PASS means the bank select adds no
cycle and no data change to the matvec contract.
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['rtl/hdc/ot_hdc_delay.sv', 'rtl/hdc/ot_hdc_fp32_mul_pipe.sv', 'rtl/hdc/ot_hdc_fpu.sv',
           'rtl/proto/ot_fp32_add_rne_pipe.sv', 'rtl/hdc/ot_hdc_sfu.sv', 'rtl/hdc/ot_hdc_fastfp.sv',
           'rtl/hdc/ot_hdc_matvec.sv', 'rtl/physical/ot_qwen_o4_g4_rommac.sv', 'rtl/test/tb_qwen_o4_g4_rommac.sv']


def run():
    with tempfile.TemporaryDirectory() as d:
        exe = str(Path(d) / 'tb.vvp')
        subprocess.run(['iverilog', '-g2012', '-s', 'tb_qwen_o4_g4_rommac', '-o', exe, *SOURCES],
                       cwd=ROOT, check=True, capture_output=True, text=True)
        r = subprocess.run(['vvp', exe], cwd=ROOT, check=True, capture_output=True, text=True)
    line = [ln for ln in r.stdout.splitlines() if 'rommac equivalence' in ln]
    ok = bool(line) and line[-1].startswith('PASS')
    return dict(schema='opentallas.qwen-o4-g4-rommac-equivalence.v1',
                status='PASS' if ok else 'FAIL', result=line[-1] if line else r.stdout[-400:],
                scope='bank select/OR of the macro-bound neighbourhood vs the flat-ROM matvec; test ROM '
                      'content, not the via-map views; no physical timing',
                added_cycles=0 if ok else None,
                source_sha256={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
                tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    rec = run()
    s = json.dumps(rec, indent=1) + '\n'
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(s)
    print(s, end='')
    raise SystemExit(0 if rec['status'] == 'PASS' else 1)
