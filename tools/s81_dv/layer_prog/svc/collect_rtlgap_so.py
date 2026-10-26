#!/usr/bin/env python3
"""RTLGAP-SO (10-21): collect the bench_allq (tb_svc_lower ALLQ on the 16 real slices) and bench_so (tb_so_golden on the
16 real SM shares) receipts into results/rtl/s81_rtlgap_so_1021/{bench_allq,bench_so}/check.json.

  collect_rtlgap_so.py --allq DIR [--mut NAME=DIR ...] --so DIR --out results/rtl/s81_rtlgap_so_1021
"""
import argparse, json, re, shutil
from pathlib import Path


def fields(line):
    return dict(re.findall(r'(\w+)=(\S+)', line))


def last(path, tag):
    p = Path(path)
    if not p.is_file():
        return None
    ls = [l for l in p.read_text(errors='replace').splitlines() if l.startswith(tag + ' ')]
    return ls[-1] if ls else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--allq', required=True)
    ap.add_argument('--mut', action='append', default=[])
    ap.add_argument('--so', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out)
    # ---------------------------------------------------------------- bench_allq
    ba = out / 'bench_allq'; ba.mkdir(parents=True, exist_ok=True)
    runs = {}
    for name in ('base_s1', 'base_s2', 'slot_s1', 'pio_early_s1', 'allq_off_s1'):
        f = Path(a.allq) / f'run_{name}.log'
        l = last(f, 'SVCLOW')
        if l is None:
            continue
        runs[name] = dict(line=l, sched=last(f, 'SVCLOW_SCHED'), allq=last(f, 'SVCLOW_ALLQ'), verdict=fields(l).get('verdict'))
        shutil.copy(f, ba / (f'run_{name}.log' if name.startswith('base') else f'mut_{name}_fail_witness.log'))
    for m in a.mut:
        nm, d = m.split('=', 1)
        f = Path(d) / 'run_base_s1.log'
        l = last(f, 'SVCLOW')
        if l is None:
            continue
        runs[f'rtl_{nm}'] = dict(line=l, sched=last(f, 'SVCLOW_SCHED'), allq=last(f, 'SVCLOW_ALLQ'), verdict=fields(l).get('verdict'))
        shutil.copy(f, ba / f'mut_rtl_{nm}_fail_witness.log')
    for x in ('sources.sha256', 'verilator.version'):
        if (Path(a.allq) / x).is_file():
            shutil.copy(Path(a.allq) / x, ba / x)
    base_ok = all(runs.get(k, {}).get('verdict') == 'PASS' for k in ('base_s1', 'base_s2'))
    muts = {k: v['verdict'] for k, v in runs.items() if not k.startswith('base')}
    rec = dict(schema='opentallas.s81_dv.compiler_bench.v1', family='svc', layer='L0', variant='ALLQ (-DOT_SVC_ALLQ, CFG[54])',
               pass_=base_ok and all(v == 'FAIL' for v in muts.values()) and len(muts) >= 2,
               ops_proven=['attn.pv (ALL 512 dims x 16 heads on ONE die: E entry tiles 0..7, W entry tiles 8..15)',
                           'attn.own_row_write', 'attn.window_load', 'attn.scores', 'attn.max', 'attn.exp'],
               vehicle='the 16 real dsdv_svc_rs slices (protect-lib, DIE 0, ST 0, -DOT_SVC_ALLQ), driven only by lower_svc.py '
                       '(OT_SVC_ALLQ=1) images at the compiled cycles; HBM elastic per-PC model seeds 1 / 2',
               checks='8192 P.V values (16 heads x 512 dims) bit-exact vs fixture attn.pv; per entry 320 words back to back '
                      'from the SAME compiled pv_first, last at pv_first + 319; both jd done at the compiled cycle; all '
                      'scores / SE rows / P beats / PV frame bit-exact as bench_svc_p; no fault',
               mutants={'slot': 'compiler: OWN_ROW pos off by one', 'pio_early': 'compiler: P injection 150 early',
                        'allq_off': 'compiler: CFG[54] dropped (only quarter ST drains)',
                        'rtl_nop': 'RTL -DRTLGAP_MUT_ALLQ_NOP: drains all, P stays gated to quarter ST',
                        'rtl_slot': 'RTL -DRTLGAP_MUT_ALLQ_SLOT: tiles 0 / 1 drain windows swapped'},
               runs=runs)
    rec['pass'] = rec.pop('pass_')
    (ba / 'check.json').write_text(json.dumps(rec, indent=1) + '\n')
    # ---------------------------------------------------------------- bench_so
    bs = out / 'bench_so'; bs.mkdir(parents=True, exist_ok=True)
    sr = {}
    for m in ('base', 'cs_swap', 'hm_shift'):
        f = Path(a.so) / f'run_{m}.log'
        l = last(f, 'SOGOLD')
        if l is None:
            continue
        sr[m] = dict(line=l, verdict=fields(l).get('verdict'))
        shutil.copy(f, bs / (f'run_{m}.log' if m == 'base' else f'mut_{m}_fail_witness.log'))
    for x in ('sources.sha256', 'verilator.version', 'so_images.json'):
        for d in (Path(a.so), Path(a.so).parent / 'so_img'):
            if (d / x).is_file():
                shutil.copy(d / x, bs / x)
    so_ok = sr.get('base', {}).get('verdict') == 'PASS' and all(v['verdict'] == 'FAIL' for k, v in sr.items() if k != 'base') \
        and len(sr) >= 3
    rec = dict(schema='opentallas.s81_dv.compiler_bench.v1', family='svc_so', layer='L0', pass_=so_ok,
               ops_proven=['attn.normalize (bf16(pv / den))', 'attn.normalize.unrope (inverse RoPE, rows 28..31)',
                           'attn.den / attn.sink consumed (SE den held by the SM)'],
               vehicle='16 real ot_s81_su_sms (-DSU_SMU_T, cfg_g = head), each behind the dsdv_svc_att SMJ decode; q = '
                       'lower_svc SE frame + lower_svc.so_frames (534 words); SE operand rows and P.V = the REAL tb_svc_lower '
                       'ALLQ RTL dumps (P.V transposed by a pure permutation = the PVSO ingress stand-in; never fixture attn.pv)',
               checks='per head 8 SE e rows (= fixture attn.exp FP32) + 32 SO o rows (= fixture attn.normalize.unrope BF16), '
                      'addresses / masks per ot_s81_su_smq, constant SO latency, o_den reached, no o_fu / o_fo',
               mutants={'cs_swap': 'compiler: cos / sin parameter rows exchanged', 'hm_shift': 'compiler: operand head mask one head off'},
               runs=sr)
    rec['pass'] = rec.pop('pass_')
    (bs / 'check.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(allq={k: v['verdict'] for k, v in runs.items()}, so={k: v['verdict'] for k, v in sr.items()}), indent=1))


if __name__ == '__main__':
    main()
