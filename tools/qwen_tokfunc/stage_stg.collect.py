#!/usr/bin/env python3
"""TOK-FUNC-QW stage stg: fold RUNROOT/stg/{rel,pos,mut}/runs/*/bench.out + fixtures into RUNROOT/stg/result.json.
usage: stage_stg.collect.py RUNROOT"""
import json
import re
import sys
from pathlib import Path

FAMS = ('resid1', 'resid2', 'qk', 'silu', 'qkv', 'gu', 'od')
EXPECT_FAIL = re.compile(r'^(MUT_|LGOFF_(od_arf|lm_arf|qk_roperx)$|LGPOS_qk_roperx_ropelate$|LGMUT_)')


def parse(out):
    lines = out.read_text(errors='replace').splitlines()
    first = next((l for l in lines if l.startswith('DV_LOWER_')), lines[0] if lines else '')
    rc = next((int(l[3:]) for l in lines[::-1] if l.startswith('rc=')), None)
    m = re.match(r'DV_LOWER_(VEC|MAT) (\S+) (PASS|FAIL|REFUSED)\s*(\d+/\d+)?', first)
    r = dict(verdict=m.group(3) if m else 'ERROR', checks=m.group(4) if m else None, rc=rc)
    info = {}
    if '{' in first:
        try:
            info = json.loads(first[first.find('{'):])
        except ValueError:
            pass
    sp = re.search(r'span_cycles[=:"\s]+(\d+)', first)
    r['span_cycles'] = info.get('span_cycles', int(sp.group(1)) if sp else None)
    r['delivery_span_cycles'] = info.get('delivery_span_cycles')
    ig = re.search(r'isa_gold_words=(\d+)/(\d+)', first)
    r['isa_gold_words'] = f'{ig.group(1)}/{ig.group(2)}' if ig else None
    if r['verdict'] != 'PASS':
        r['detail'] = [l.strip()[:200] for l in lines if l.strip() and not l.startswith('rc=')][:6]
    return r


def main():
    R = Path(sys.argv[1]).resolve()
    S = R / 'stg'
    src_commit = (R / 'src' / 'ASM_COMMIT').read_text().strip() if (R / 'src' / 'ASM_COMMIT').exists() else None
    layers_req = list(range(36))
    fx = {}
    for L in layers_req:
        j = S / 'fx' / f'L{L}_fixture.json'
        if j.exists():
            d = json.loads(j.read_text())
            fx[L] = dict(ok=True, reproduction=all(all(v.values()) for v in d['reproduction'].values()))
        else:
            lg = S / 'fx' / f'L{L}.log'
            fx[L] = dict(ok=False, why=(lg.read_text(errors='replace').strip().splitlines()[-3:] if lg.exists() else 'not run'))
    cfgs, cycles, bad, mutants, gold_ok, gold_n = {}, {}, [], {}, 0, 0
    for c in ('rel', 'pos', 'mut'):
        d = S / c
        if not d.exists():
            continue
        st = {b.parent.name: parse(b) for b in sorted((d / 'runs').glob('*/bench.out'))}
        cc = dict(vflags=(d / 'vflags.txt').read_text().strip() if (d / 'vflags.txt').exists() else None,
                  built=bool((d / 'vtb.sha256').exists() and (d / 'vtb.sha256').read_text().strip()),
                  timing=(d / 'timing.txt').read_text().strip() if (d / 'timing.txt').exists() else None,
                  calibrate={f: (d / f).read_text(errors='replace').strip().splitlines()[-2:]
                             for f in ('build/slice_calibrate.out', 'build/calibrate.out', 'cal_mat/calibrate.out')
                             if (d / f).exists()},
                  vec_ages=f'stg/{c}/build/vec_ages.json' if (d / 'build/vec_ages.json').exists() else None,
                  stn_ages=f'stg/{c}/cal_mat/stn_ages.json' if (d / 'cal_mat/stn_ages.json').exists() else None,
                  slice_ages=f'stg/{c}/build/slice_ages.json' if (d / 'build/slice_ages.json').exists() else None,
                  stages=st)
        cfgs[c] = cc
        cy = {f: {} for f in FAMS}
        for name, r in st.items():
            want_fail = bool(EXPECT_FAIL.match(name))
            if want_fail:
                mutants[f'{c}/{name}'] = 'FAIL as required' if r['verdict'] == 'FAIL' else f'{r["verdict"]} (NOT killed)'
                if r['verdict'] != 'FAIL':
                    bad.append(f'{c}/{name} {r["verdict"]}')
                continue
            if r['verdict'] != 'PASS':
                bad.append(f'{c}/{name} {r["verdict"]} {r["checks"]}')
            m = re.match(r'L(\d+)_(\w+)$', name)
            if m and m.group(2) in cy:
                cy[m.group(2)][int(m.group(1))] = r['delivery_span_cycles'] or r['span_cycles']
            elif name in ('lm', 'emb'):
                cy[name] = r['span_cycles']
            if r['isa_gold_words']:
                a, b = map(int, r['isa_gold_words'].split('/'))
                gold_ok, gold_n = gold_ok + a, gold_n + b
        # compact: a family whose span is the same on every layer -> {"all_layers": v, "layers": n}
        for f in FAMS:
            vals = set(cy[f].values())
            if len(vals) == 1 and len(cy[f]) > 1:
                cy[f] = dict(all_layers=vals.pop(), layers=len(cy[f]), per_layer=cy[f])
        cy['vec_ages_json'] = cc['vec_ages']
        cy['stn_ages_json'] = cc['stn_ages']
        cycles[c] = cy
    missing_fx = [L for L, v in fx.items() if not v['ok']]
    for L, v in fx.items():
        if v['ok'] and not v['reproduction']:
            bad.append(f'fixture L{L} reproduction failed')
    required = {f'L{L}_{family}' for L in layers_req for family in FAMS} | {'lm', 'emb'}
    for c in ('rel', 'pos'):
        missing = required - set(cfgs.get(c, {}).get('stages', {}))
        if missing:
            bad.append(f'{c} missing {len(missing)} required stages: {sorted(missing)[:8]}')
    for line in (S / 'runlist.txt').read_text().splitlines() if (S / 'runlist.txt').exists() else []:
        c, name, *_ = line.split()
        if name not in cfgs.get(c, {}).get('stages', {}):
            bad.append(f'{c}/{name} NOT_RUN')
    for c in ('rel', 'pos'):
        if c in cfgs and not cfgs[c]['built']:
            bad.append(f'{c} build failed')
    if 'mut' in cfgs and not cfgs['mut']['built']:
        bad.append('mut build failed')
    if missing_fx:
        bad.append(f'fixtures missing for layers {missing_fx}')
    verdict = 'PASS' if not bad else 'FAIL'
    res = dict(
        stage='stg', grade='RTL-functional (source assembly)', src_commit=src_commit, verdict=verdict,
        golden=(f'per layer L0..L35 (TP4 36-layer ISA golden at P8191 re-executed per layer, reproduction-checked, '
                f'cut to TP8 compute die 0): bench hdc_golden expectation bit-exact on the RTL outputs AND == ISA gold '
                f'words; ISA-gold words matched {gold_ok}/{gold_n} (resid 4097, qk 768, silu 1536, qkv 768, gu 3072 per '
                f'layer per cfg; od = bench golden only, TP8 partials have no TP4 value); lm / emb bench golden'),
        cycles=cycles, ages={k: f'rel/{v}' for k, v in
                            [('slice', 'build/slice_ages.json'), ('vec', 'build/vec_ages.json'),
                             ('stn', 'cal_mat/stn_ages.json')]
                            if (S / 'rel' / v).exists()},
        mutants=mutants, failures=bad[:60],
        fixtures=dict(layers_ok=sorted(L for L, v in fx.items() if v['ok']), missing={L: fx[L]['why'] for L in missing_fx}),
        stand_ins=[
            'behavioural SRAM models (rtl/test/full_sm_service/sram_models.sv, rtl/test/hbm_rf_visibility/scale_sram_model.sv, '
            'rtl/test/qwen_dv/safe_storage/sram_model.sv) for the slice ASAP7 macros ot_sram_1r1w_{1024,128,256}x256 (kit uses _bb views)',
            'slice core qfd_dv_slice2 (tb FACE=0) without the qfd_dv_slice2_w/_e face pin wrappers',
            'off-chain legs driven by the bench at their compiled edges: TT ctlm head commands / stream table words, ROM tile '
            'words (int8 weights + scales), AR returns (collective), D2D to the KV die; RoPE row (pos cfg) via the return chain',
            'operands from the TP4 golden (TP4-folded all-reduce returns) applied to the TP8 die-0 cut; stage functions TP-agnostic',
        ],
        notes='rel params per brief (-GMU_NU=4 -GSU_LT=1); physical/ref_tile/qfd_dv_slice2_w/kit.env at c0f8097f3 has PARAMS=()',
        logs=['stg/runs.log', 'stg/fixtures.log', 'stg/timing.txt', 'stg/runlist.txt'] +
             [f'stg/{c}/runs/<name>/bench.out' for c in cfgs] + [f'stg/build_{c}.log' for c in cfgs],
        configs=cfgs)
    (S / 'result.json').write_text(json.dumps(res, indent=1) + '\n')
    print('STG', verdict, 'gold', f'{gold_ok}/{gold_n}', 'bad', len(bad), bad[:8])
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
