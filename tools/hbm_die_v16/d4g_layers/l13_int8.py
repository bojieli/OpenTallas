#!/usr/bin/env python3
"""TW5-GEN2E 10-19: GEN2e contract post-layer L13 -- Qwen INT8 SM path (COORD 0ki, SMB-INT8 claude/smb-int8-1019 @e592ae5d0).

    l13_int8.py IN_contract.json[.gz] OUT_contract.json --report R.json

Every ot_hbm_accel_smh_attn instance gets ENABLE_INT8 = 1: the opt-in ot_smh_static_int8 -> ot_hbm_accel_int8_line #(.PIPE(1))
packet-ingress path (results/rtl/hbm_qwen_layer_tput_1018/smb_int8_1019/rtl_change_note.json: +~2.7k flops, INT8->BF16
64-lane converter + 1099-bit mux, +2 packet->front cycles for INT8 lines only; Qwen SM.MATVEC fmt 3 executable on the die
SM; without it the BF16-widened image costs -17.6 % Qwen tok/s).  Ports do not change (parameter only); the two new RTL
files are found by the synth module index (rtl/hbm_accel/sm/static/ot_smh_static_int8.sv, rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv)
and are recorded in each instance's rtl_deps.  Exit != 0 when no SM instance is found or the RTL lacks the parameter."""
import argparse, gzip, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
M = 'ot_hbm_accel_smh_attn'
DEPS = ['rtl/hbm_accel/sm/static/ot_smh_static_int8.sv', 'rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv']


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('inp'); ap.add_argument('out'); ap.add_argument('--report', required=True)
    a = ap.parse_args()
    c = json.load(gzip.open(a.inp, 'rt') if a.inp.endswith('.gz') else open(a.inp))
    src = (ROOT / 'rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv').read_text()
    prob = []
    if not re.search(r'parameter\s+(integer\s+|int\s+|bit\s+)?ENABLE_INT8', src):
        prob.append('ot_hbm_accel_smh_attn.sv has no ENABLE_INT8 parameter (merge claude/smb-int8-1019 e592ae5d0)')
    for d in DEPS:
        if not (ROOT / d).exists():
            prob.append(f'missing {d}')
    done = []
    for n, v in c['instances'].items():
        if v['master'] == M:
            v.setdefault('params', {})['ENABLE_INT8'] = 1
            v['rtl_deps'] = sorted(set(v.get('rtl_deps', []) + DEPS))
            v['note'] = (v.get('note') or '') + ' | l13_int8 (COORD 0ki): ENABLE_INT8 1 (Qwen INT8 SM.MATVEC path, SMB-INT8 e592ae5d0)'
            done.append(n)
    if not done:
        prob.append(f'no {M} instance')
    rep = dict(layer='l13_int8', instances=sorted(done), n=len(done), deps=DEPS, problems=prob)
    Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    if prob:
        print('L13_FAIL', prob); sys.exit(1)
    Path(a.out).write_text(json.dumps(c))
    print('L13_OK ENABLE_INT8=1 on', len(done), M)


if __name__ == '__main__':
    main()
