#!/usr/bin/env python3
"""Price matched select measurements in the existing S58 near-HBM graph.

Only AR L20 sizes actually measured by the campaign are substituted. Other
layers, scoring, migration and MTP remain explicit unmeasured dependencies.
No adoption verdict or 161-cycle whole-tail assumption follows from this tool.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import arch_budget_v41 as A
import decode_critical_path as D
import uarch_model as u


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(ctx, tail):
    cap_path = ROOT / 'results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json'
    cap = json.loads(cap_path.read_text())
    pairs = {r['stages']: r for r in cap['all_stage_capacity_rows']}[58]['BF16_pairs_per_die']
    u.PRESETS['proposal']['bf16_stripe_macros'] = 2 * pairs
    cyc = 1 / u.PRODUCT_CLOCK_HZ
    orig = u._cons_adjust
    replaced = []

    def adj(g, P, *args, **kwargs):
        # Identical variant(i) surgery at 723243a4a, before retiming.
        for name, nd in g.nodes.items():
            if name.endswith(('.idx.topk_local', '.cand.topk_local')):
                nd['stream'] = True
                nd['issue'] /= 4
                k = 512 if name.endswith('.idx.topk_local') else 2048
                nd['depth'] += (math.ceil(4*k/64) + D.tselect_latency(4*k)) * cyc
        answer = orig(g, P, *args, **kwargs)
        if P == 1 and tail is not None:
            name = 'L20.attn.idx.topk_local'
            nd = g.nodes[name]
            want_n = ctx // 4
            assert f'of {want_n} keys' in nd['desc'], nd['desc']
            replaced.append(dict(node=name, keys=want_n,
                                 previous_composed_depth_cycles=nd['depth']/cyc,
                                 measured_select_tail_cycles=tail))
            nd['depth'] = tail * cyc
            answer = g.solve(True)[next(n for n in g.nodes if n.endswith('token.return'))]
        return answer

    u._cons_adjust = adj
    try:
        with u._cons_ctx(ctx):
            p = u.cons_v41_rom(58, 8, 36, bf16='columns', clock_hz=u.PRODUCT_CLOCK_HZ,
                field_concurrency=u.FIELD_CONCURRENCY,
                added_latency=dict(u.SOFTPLUS_FIX, **u.W11_STREAM_SS, **u.PLUS_LAT),
                dyn_scale=u.PRODUCT_DYN_SCALE, slow_domain=(.9e9, 'w18'), elem_stages=8,
                ss_wire=True, serial=u.PRODUCT_SERIAL, die=u.DIE_SHRUNK_INTERIM,
                vmh=u.VMC_FUSED, hub_block=u.PRODUCT_HUB)
    finally:
        u._cons_adjust = orig
    return dict(ar_us=1e6/p['ar_tokens_s_b1'], ar_tok_s=p['ar_tokens_s_b1'], replaced=replaced)


def migration():
    import numpy as np
    from dsrom_edge_scorer_campaign import boundaries, stack_of
    sys.path.insert(0, str(ROOT))
    from runtime.prefill.v41_aux_kv_rows import INDEX_ROW_BYTES
    from runtime.prefill.v41_main_kv_row import ROW_BYTES
    rows = []
    for start in (50000, 262112):
        for d in range(0, 32, 8):
            n = start + d
            before, after = boundaries(n), boundaries(n+1)
            pos = np.arange(n)
            a, b = stack_of(pos, n), stack_of(pos, n+1)
            moved = int(np.count_nonzero((a != b) | ((pos-before[a]) != (pos-after[b]))))
            total = moved * 2 * (INDEX_ROW_BYTES + ROW_BYTES)
            rows.append(dict(n=n, next_n=n+1, before=before.tolist(), after=after.tolist(),
                relocated_old_rows=moved, index_payload_read_write_bytes=moved*2*INDEX_ROW_BYTES,
                compressed_KV_payload_read_write_bytes=moved*2*ROW_BYTES,
                payload_bytes_lower_bound=total, ideal_3_6_TBps_us_lower_bound=total/3.6e6))
    files = [ROOT/p for p in ('tools/dsrom_edge_scorer_campaign.py', 'rtl/dsrom_sys/ot_dsrom_edge_layout.sv',
        'runtime/prefill/v41_aux_kv_rows.py', 'runtime/prefill/v41_main_kv_row.py')]
    files.append(Path(__file__))
    return dict(schema='opentallas.dsrom-edge-contiguous-migration.v1',
        native_index_bytes=INDEX_ROW_BYTES, native_compressed_KV_bytes=ROW_BYTES, rows=rows,
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in files},
        note='Payload-only lower bounds if both index and compressed KV use dense quarter mapping; no migration engine installed here. Shared HBM read/write, quiescence, sector strobes, ACK and finite buffering add cost. Changing N without relocation is incorrect. Not measured token latency.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--old-select', type=Path, required=True)
    ap.add_argument('--select', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--migration-out', type=Path)
    args = ap.parse_args()
    old, new = (json.loads(p.read_text()) for p in (args.old_select, args.select))
    assert old['pass'] and new['pass'] and not old['dirty'] and not new['dirty']
    def cases(j):
        return {r['case']: r for r in j['groups']['shipped']['modes']['hbm_rate']['per_case']}
    rows = []
    for ctx in (200000, 1048576):
        case = f'l20_full_scan_ctx{ctx}_n{ctx//4}'
        before, after = cases(old)[case], cases(new)[case]
        assert before['n_keys'] == after['n_keys'] == ctx//4
        assert before['scan_cycles'] == after['scan_cycles']
        priced = run(ctx, None)
        historical = run(ctx, before['last_key_to_selection_out'])
        measured = run(ctx, after['last_key_to_selection_out'])
        rows.append(dict(context=ctx, case=case, modeled_nearhbm=priced,
            old_L20_tail_substituted=historical, contiguous_L20_tail_substituted=measured,
            measured_L20_contribution_us=(before['last_key_to_selection_out']-after['last_key_to_selection_out'])/1200,
            partial_graph_AR_rate_delta_percent=100*(measured['ar_tok_s']/historical['ar_tok_s']-1)))
    files = [ROOT/p for p in ('tools/uarch_model.py', 'tools/decode_critical_path.py', 'tools/arch_budget_v41.py',
        'results/uarch/dsrom_4096_comparable_capacity_20261002/partition_token_options.json')]
    files += [args.old_select, args.select, Path(__file__)]
    rec = dict(schema='opentallas.dsrom-edge-measured-contribution.v1', basis='723243a4a S58 near-HBM variant(i)',
        rows=rows, source_sha256={str(p):sha(p) for p in files},
        adopted=False, headline_qualified=False,
        unresolved=['Other layer sizes131072/4096 (1M) and25000/4096 (200K) are unmeasured by these select records.',
          'Full score-path and simultaneous four-stack/hub system timing are not inferred from select-only input.',
          'N growth requires actual installed index/CKV migration; its bytes and latency are not charged here.',
          'MTP multi-position behavior, contextual SS/FF and routing remain unqualified.'])
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(rec,indent=2)+'\n')
    if args.migration_out:
        args.migration_out.parent.mkdir(parents=True, exist_ok=True)
        args.migration_out.write_text(json.dumps(migration(), indent=2)+'\n')
    for row in rows:print(row['context'],row['measured_L20_contribution_us'],row['partial_graph_AR_rate_delta_percent'])


if __name__ == '__main__':
    main()
