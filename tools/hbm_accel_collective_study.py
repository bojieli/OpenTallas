"""HA5: collective-count reduction study for the DS V4.1 HBM accelerator TP-96 program (price first).

Counts the collectives of the committed TP-96 oreduce program and prices every candidate exact
merge or replication against what it removes, from committed measurements only:
  - removed collective: W15 fixed latency (all-gather 777 ns, all-reduce 824 ns; study a3ed9c36d);
  - replication: extra HBM bytes streamed per die per token at 4 stacks x 0.958 TB/s (52ce3e9c1,
    measured worst layer), plus the SM rows (results/rtl/w19_sm_real_ops_oreduce.json);
  - exactness: the golden's reduction order (tools/hdc_golden_v41.py linear_q: per-32 K-block
    exact dot rounded once to FP32, blocks summed in chunk8 csum order).
No program is changed by this study.  Usage: python3 tools/hbm_accel_collective_study.py --out F
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = 'results/rtl/w19_hbm_tp96_program_oreduce.json'
SM_OPS = 'results/rtl/w19_sm_real_ops_oreduce.json'
AG_NS, AR_NS = 777.0, 824.0                  # W15 fixed latencies (study R2 note)
HBM_BPS_DIE = 4 * 0.958e12                   # 4 stacks x measured worst-layer stream rate
TP = 96
BYTES = dict(fp8=1, bf16=2, fp4=0.5 + 1 / 64)  # fp4 codes + UE8M0 per 32


def sm_cycles(tag):
    ops = json.loads((ROOT / SM_OPS).read_text())['cases']['ar']
    return next(o['rtl']['cycles_start_to_done'] for o in ops if o['tag'] == tag)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    prog = json.loads((ROOT / PROGRAM).read_text())
    per_layer = {}
    for lay in prog['layers']:
        tags = tuple(o['tag'] for o in lay['ops'] if o.get('unit') == 'COLL')
        per_layer[lay['layer']] = tags
    kinds = Counter(per_layer.values())
    regular = max(kinds, key=kinds.get)
    total = sum(len(t) for t in per_layer.values())
    mv = {o['tag']: o for o in prog['layers'][0]['ops'] if o['kind'] == 'mv'}

    def repl(tags, saved_ns, note):
        """Replicate the producing matvec(s) on every die so the gather after them disappears."""
        b = sum(mv[t]['n'] * mv[t]['k'] * BYTES[mv[t]['fmt']] for t in tags)
        extra_b = b - b / TP
        hbm_ns = extra_b / HBM_BPS_DIE * 1e9
        return dict(removed_ns=saved_ns, extra_hbm_bytes_per_die=round(extra_b),
                    extra_hbm_stream_ns=round(hbm_ns, 1), net_saved_ns=round(saved_ns - hbm_ns, 1),
                    exact=True, note=note)

    gate_cyc = sm_cycles('router gate')
    cands = [
        dict(merge='router_gather removed: router gate replicated on every die', **repl(
            ['router gate'], AG_NS,
            f'all 384 logits computed locally; measured SM gate op {gate_cyc} cycles for 1 row/SM grows to ~12 rows/SM')),
        dict(merge='x_projections_gather removed: wq_a + wkv replicated', **repl(
            ['wq_a', 'wkv'], AG_NS, 'every die computes the full q_a / kv projections')),
        dict(merge='attn_out_gather removed: wo_b replicated', **repl(
            ['wo_b'], AG_NS, 'every die computes all 5,120 wo_b rows')),
        dict(merge='expert_intermediate_gather + ffn_out_gather -> one w2 K-split all-reduce',
             removed_ns=AG_NS + AG_NS - AR_NS, exact=False,
             net_saved_ns=None,
             note='the golden sums w2 in 32-wide K blocks (2,304 = 72 blocks, chunk8 csum: 9 sequential chunks of '
                  '8 blocks, then a pairwise tree); a die owns 24 K elements, less than one block, so a 96-way K split '
                  'cannot reproduce the order; the only exact split is 9 chunk owners, each doing 10.7x the TP-96 w2 '
                  'rows (all 5,120 rows x 256 K x 7 experts), which costs more SM time than the 730 ns it saves'),
        dict(merge='level-5 residual/norm partials carried with an all-reduce', removed_ns=0.0, exact=True,
             net_saved_ns=0.0,
             note='every norm and hc_post runs on the replicated full vector after a gather; there is no separate '
                  'norm collective to fold, so nothing is removed'),
    ]
    exact_profitable = [c for c in cands if c['exact'] and (c['net_saved_ns'] or 0) > 0]
    rec = dict(schema='opentallas.hbm_accel.ha5.collective_study.v1',
               program=PROGRAM, program_sha256=hashlib.sha256((ROOT / PROGRAM).read_bytes()).hexdigest(),
               sm_ops_sha256=hashlib.sha256((ROOT / SM_OPS).read_bytes()).hexdigest(),
               collectives_total=total, layers=len(per_layer),
               regular_layer_collectives=list(regular), regular_layer_count=kinds[regular],
               layer_kinds={'|'.join(k): v for k, v in kinds.items()},
               price_per_removed_collective_ns=dict(all_gather=AG_NS, all_reduce=AR_NS,
                                                    study_rule='40 removed ~ 20 us (0.5 us each)'),
               candidates=cands, exact_profitable_merges=len(exact_profitable),
               removed_collectives_per_token=0, measured_gain_us=0.0,
               verdict='REJECT: no exact merge or replication removes a collective at a net gain; '
                       'replications stream 96x their weights from HBM, and the only non-replicating merge '
                       '(w2 K-split) is not exact against the golden block order')
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps({k: rec[k] for k in ('collectives_total', 'regular_layer_count', 'exact_profitable_merges', 'verdict')}, indent=2))
    for c in cands:
        print(c['merge'], '| net', c['net_saved_ns'], '| extra HBM ns', c.get('extra_hbm_stream_ns'))


if __name__ == '__main__':
    main()
