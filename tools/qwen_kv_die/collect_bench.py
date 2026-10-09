#!/usr/bin/env python3
"""kv-die 2026-10-09: fold the layer-step bench campaigns (rtl/test/qwen_kv_die/bench_run.sh results.jsonl, one per
PHY latency case) into results/arch/qwen_kv_die_20261009/bench.json.

    python3 tools/qwen_kv_die/collect_bench.py --case typical:5:DIR/results.jsonl --case best:3:... --case worst:9:... \
        --params ROM_ST=28,KV_ST=1,LINK=7,QX=29,RX=28,KVL=34 --src COMMIT --out results/arch/qwen_kv_die_20261009/bench.json
"""
import argparse
import json
from pathlib import Path

MUTANTS = {
    'mut1': 'KV end: one extra RES link credit (TIGHT sizing, VM stalled 300 cycles) -> ROM-end receive-buffer overrun',
    'mut2': 'KV merge off: the t = T-1 rows come from HBM as poisoned (0xA5) -> wrong attention',
    'mut3': 'one flit dropped in the UCIe macro model (ROM -> KV) -> sequence fault',
    'mut4': 'ROM end: link credit owed at receive-buffer push instead of pop (TIGHT, stalled) -> overrun',
    'mut5': 'Q beats 0 / 1 swapped on the KV die -> wrong attention',
    'mut7': 'fence OFF with the posted rows stalled 400 cycles (credit-stalled kvn path): the T-1 read reaches the poisoned '
            'HBM row before the merge -> wrong attention',
    'mut8': 'BASE RTL with the posted rows stalled 400 cycles: the write-then-read fence holds the T-1 read -> must stay '
            'exact',
    'mut6': 'BASE RTL in the TIGHT credit-stress sizing (RES link buffer 4, VM credits 4, VM stalled 300 cycles) -> '
            'must stay exact',
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', action='append', required=True)
    ap.add_argument('--params', required=True)
    ap.add_argument('--src', required=True)
    ap.add_argument('--rtl', default=None, help='attention RTL statement (default: the _p successors)')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    params = {k: int(v) for k, v in (x.split('=') for x in a.params.split(','))}
    out = dict(schema='opentallas.qwen-kv-die.bench.v1', date='2026-10-09', source_commit=a.src,
               bench='rtl/test/qwen_kv_die/ot_qkvd_layer_tb.sv + tb_qkvd_layer.cpp (build_qkvd_tb.sh, bench_run.sh)',
               golden='tools/hdc_golden.py via tools/qwen_nearhbm_attn_ref.py vectors (TP4 die share: 8 q heads, 2 KV '
                      'heads, head_dim 128, FP8 E4M3 KV, scale F(1/sqrt 128))',
               attention_rtl='ot_qwen_nearhbm_attn_stack_p + ot_qwen_nearhbm_attn_hub_p (timing successors, via the '
                             'bench shims), R = 8 row engines a stack, DPI host-float FP32 add / mul stand-ins (the '
                             'repo precedent: identical to the real units at head_dim 16, real_vs_dpi_hd16.json)',
               **({'attention_rtl_used': a.rtl} if a.rtl else {}),
               hbm_model='per-engine in-order queues, 750 B / cycle / stack, 16-cycle latency; t = T-1 rows poisoned',
               checks='RES (1,024 FP32) bit-exact vs gold, the 4 posted KV rows, 65 EMBQ / EMBD words in order, 2 '
                      'HCTL words, the TOKEN word, every fault flag 0; stall = 1 withholds the VM RES credits 300 cycles',
               params=params, cases={})
    for spec in a.case:
        name, lat, path = spec.split(':', 2)
        rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
        base = [r for r in rows if r['run'] == 'base']
        muts = {r['run']: r for r in rows if r['run'] != 'base'}
        step = [r['res']['marks']['res_last_at_vm'] - r['res']['marks']['ctl_sent'] for r in base
                if r['res'] and r['res']['ctx'] >= 8191]
        c = dict(params=dict(params, PHY_LAT=int(lat)), adapter_plus_phy=3 + int(lat) + 3,
                 exact_all=all(r['rc'] == 0 and r['res'] and r['res']['exact'] for r in base),
                 runs=len(base), layer_step_8192=max(step) if step else None,
                 vectors=[dict(vec=r['vec'], stall=r['res']['stall'], exact=r['res']['exact'], cycles=r['res']['cycles'],
                               marks=r['res']['marks'], poisoned_rows_merged=r['res']['poisoned_rows_merged'])
                          for r in base if r['res']])
        if muts:
            c['mutants'] = {}
            for k, r in sorted(muts.items()):
                res = r['res'] or {}
                expect_pass = k in ('mut6', 'mut8')
                caught = (r['rc'] != 0) and not res.get('exact', False)
                c['mutants'][k] = dict(what=MUTANTS.get(k, ''), rc=r['rc'], exact=res.get('exact'),
                                       mismatches=res.get('mismatches'), faults=res.get('faults'),
                                       verdict=('PASS (exact)' if (expect_pass and r['rc'] == 0) else
                                                'FAIL (should be exact)' if expect_pass else
                                                'CAUGHT' if caught else 'NOT CAUGHT'))
        out['cases'][name] = c
    out['ok'] = all(c['exact_all'] for c in out['cases'].values()) and all(
        m['verdict'] in ('CAUGHT', 'PASS (exact)') for c in out['cases'].values() for m in c.get('mutants', {}).values())
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(dict(ok=out['ok'], steps={k: v['layer_step_8192'] for k, v in out['cases'].items()},
                          mutants={k: {m: x['verdict'] for m, x in v.get('mutants', {}).items()} for k, v in out['cases'].items()})))


if __name__ == '__main__':
    main()
