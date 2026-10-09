#!/usr/bin/env python3
"""Coverage matrix: one row per function across the four target ledgers T1-T4.

Reads  results/arch/coverage_20261008/T{1,2,3,4}.json  (opentallas.coverage_ledger.v1, written by cov-T1..T4).
Writes results/arch/coverage_20261008/MATRIX.json     (opentallas.coverage_matrix.v1).

The authored part is in this file: ROWS (the normalised function names and which ledger nodes each one gathers),
NA (where a function does not apply to a target, and why), OWN (which stream owns each gap) and TP_MAP (how each
token-path view's operators map onto rows).  Everything else is derived from the ledgers, so a stream that edits its
ledger node (a gap closed, an element renamed, a bench added) changes the matrix on the next run.  The fleet viz
(tools/fleet_viz/coverage.py) imports build() from this file and runs it live on every ledger change.

    python3 results/arch/coverage_20261008/gen_matrix.py [--elements http://127.0.0.1:8765/api/elements] [--check]
"""
import json, re, sys, pathlib, datetime, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
TARGETS = ['T1', 'T2', 'T3', 'T4']
TARGET_INFO = {
    'T1': dict(model='Qwen3-8B', machine='Qwen ROM die r21b/r21c (TP4)', modes='AR only (owner: MTP rejected)', token_views=['qwen_rom']),
    'T2': dict(model='DeepSeek-V4.1', machine='DS ROM S81 array (1,792 mapping, 120 stages)', modes='AR + DSpark MTP', token_views=['ds_rom', 'ds_rom_mtp']),
    'T3': dict(model='DeepSeek-V4.1', machine='HBM accelerator r25 (TP-96)', modes='AR + DSpark MTP', token_views=['hbm_ds', 'hbm_ds_mtp']),
    'T4': dict(model='Qwen3-8B', machine='HBM accelerator r25 (unified die; TP group undefined)', modes='AR; MTP pending an owner decision', token_views=[]),
}
GAPS = ['MISSING_HW', 'NOT_ON_DIE', 'NOT_CLOSED', 'NOT_EXACT', 'NOT_PRICED', 'MODELLED_ONLY', 'UNENUMERATED']
# "uncovered" = the function has no hardware on a die; the views draw these strongest
UNCOVERED = {'MISSING_HW', 'NOT_ON_DIE'}

# ------------------------------------------------------------------------------------------------ rows
# (fid, group, function, plane, phase, {target: [ledger node ids]})   T2/T3 ids are written without their 'T2-'/'T3-' prefix.
ROWS = [
    # host / prefill
    ('host.request_in', 'host', 'Request in (command / doorbell, prompt, session)', 'control', 'host', dict(T1=['H01'], T2=['H01'], T3=['H01'], T4=['host.request_in'])),
    ('host.token_out', 'host', 'Token out (completion per token, MTP multi-token emit)', 'control', 'host', dict(T1=['H02'], T2=['H02'], T3=['H02'], T4=['host.token_out'])),
    ('host.phy', 'host', 'Host physical port (PCIe / host link on the SerDes)', 'control', 'host', dict(T1=['H03'], T3=['H03'], T4=['host.request_in'])),
    ('prefill.handoff', 'host', 'Prompt / GPU-prefill hand-off (decode starts at position P)', 'control', 'prefill', dict(T1=['H05'], T2=['H03'], T3=['H03'], T4=['host.prefill_handoff'])),
    ('prefill.kv_ingest', 'host', 'Prefill-KV ingest into the decode HBM (layout, FP8 pack, fenced completion)', 'control', 'prefill', dict(T1=['H04'], T2=['H04'], T3=['H03'], T4=['host.prefill_kv_ingest'])),
    ('host.multi_user', 'host', 'Multi-user context / KV placement / batching', 'control', 'host', dict(T1=['M01'], T2=['U01'], T3=['H04'], T4=['batch.multi_user'])),
    # boot
    ('boot.weights', 'boot', 'Weight image (mask ROM, or HBM load at boot) incl. LM head', 'control', 'boot', dict(T1=['B01'], T2=['B01'], T3=['B01'], T4=['boot.weight_image', 'boot.lm_head_table'])),
    ('boot.embedding', 'boot', 'Embedding table load + boot check', 'control', 'boot', dict(T1=['B02'], T4=['boot.embedding_table'])),
    ('boot.rope_tables', 'boot', 'RoPE cos/sin table load (HBM-resident tables)', 'control', 'boot', dict(T2=['B03'], T4=['boot.rope_tables'])),
    ('boot.engram_tables', 'boot', 'Engram hash tables load / table storage', 'control', 'boot', dict(T2=['B03'], T3=['B02'])),
    ('boot.program', 'boot', 'Program / configuration / descriptor load', 'control', 'boot', dict(T1=['B03'], T2=['B02'], T3=['B03'], T4=['boot.program_config'])),
    ('boot.reset', 'boot', 'Reset / power-up / power-gating sequencing', 'control', 'boot', dict(T1=['B04'], T2=['B05'], T3=['B05'], T4=['boot.reset_clocks'])),
    ('boot.clocks', 'boot', 'Clock generation (PLL) and distribution', 'control', 'boot', dict(T1=['B05'], T2=['B04'], T3=['B04'], T4=['boot.reset_clocks'])),
    ('boot.hbm_init', 'boot', 'HBM PHY init / training / controller bring-up', 'control', 'boot', dict(T1=['B06'], T2=['B06'], T3=['C07'])),
    ('boot.link_training', 'boot', 'Link training / link-up gate, FEC lock', 'control', 'boot', dict(T1=['B04'], T2=['B07'], T4=['boot.reset_clocks'])),
    ('boot.csr', 'boot', 'Configuration / status / fault registers (CSR)', 'control', 'boot', dict(T1=['B07'], T2=['F02', 'B02'], T3=['F04'], T4=['boot.program_config'])),
    # decode control
    ('ctl.token_loop', 'control', 'Token loop: position counter, fed-back token, token return to the source', 'control', 'decode', dict(T1=['C01'], T2=['C01', 'C05'], T3=['C02'], T4=['dec.token_loop', 'head.feedback'])),
    ('ctl.inter_die', 'control', 'Inter-die / stage sequencing: start fan-out, barriers, stage hand-off, hops', 'control', 'decode', dict(T1=['C02'], T2=['C03', 'C04'], T3=['C03'], T4=['L.residual2_handoff'])),
    ('ctl.die_sequencer', 'control', 'Per-die layer program sequencing (issue, DYN offsets, substage concurrency)', 'control', 'decode', dict(T1=['C03', 'C04'], T2=['C02'], T3=['C01'], T4=['dec.token_loop'])),
    ('ctl.kv_addr', 'control', 'KV address generation, cache length, causal / window / candidate masks', 'control', 'decode', dict(T1=['C05', 'C10'], T2=['C07', 'C10'], T3=['C04'], T4=['L.cache_len_mask'])),
    ('ctl.kv_append', 'control', 'KV append (write-back of the new K/V, CKV, index-key rows; write-done)', 'control', 'decode', dict(T1=['C06'], T2=['D19'], T3=['D20', 'D25'], T4=['L.kv_append'])),
    ('ctl.kv_stream', 'control', 'KV / window-row stream and prefetch from HBM', 'control', 'decode', dict(T1=['C07'], T2=['D19'], T3=['D36', 'D29'], T4=['L.kv_stream'])),
    ('ctl.hbm_service', 'control', 'HBM controller service (refresh-aware scheduling, PC ready, latency)', 'control', 'decode', dict(T2=['C08'], T3=['C07'])),
    ('ctl.weight_stream', 'control', 'HBM weight stream at >= 90 % of peak + prefetch-window flow control', 'control', 'decode', dict(T3=['C08'], T4=['L.weight_stream', 'L.window_release'])),
    ('ctl.rope_supply', 'control', 'RoPE position -> cos/sin supply', 'control', 'decode', dict(T1=['C08'], T2=['C09'], T3=['D19'], T4=['boot.rope_tables'])),
    ('ctl.const_rom', 'control', 'Constant ROM (norm weights, RoPE rows) as hardware', 'control', 'decode', dict(T1=['C09'])),
    ('ctl.transport', 'control', 'On-die operand / result transport (relays, x-broadcast, result gather, credits)', 'control', 'decode', dict(T1=['C12'], T2=['C06'], T3=['D12', 'D52'])),
    ('ctl.collective', 'control', 'Collective engine / fabric + link flow control', 'control', 'decode', dict(T1=['C13'], T2=['C12'], T3=['C05'], T4=['L.allreduce1', 'L.allreduce2'])),
    ('ctl.link_fec', 'control', 'Die-to-die PHY with FEC / CRC / retry', 'control', 'decode', dict(T1=['C14'], T2=['C13'], T3=['C06'], T4=['fault.link'])),
    ('ctl.expert_dispatch', 'control', 'Expert dispatch / combine control and routed-expert fetch', 'control', 'decode', dict(T2=['C11'], T3=['D45'])),
    ('ctl.engram_history', 'control', 'Engram token history per user', 'control', 'decode', dict(T2=['C15'], T3=['D03'])),
    ('ctl.compressor_state', 'control', 'Compressor open-group slot state', 'control', 'decode', dict(T2=['D20'], T3=['D24'])),
    # sampler
    ('smp.final_norm', 'sampler', 'Final (hc_pre +) RMSNorm', 'data', 'decode', dict(T1=['D23'], T2=['D39'], T3=['S01'], T4=['head.final_norm'])),
    ('smp.lm_head', 'sampler', 'LM head matvec', 'data', 'decode', dict(T1=['D24'], T2=['D40'], T3=['S02'], T4=['head.lm_head'])),
    ('smp.argmax', 'sampler', 'Greedy argmax + cross-die merge', 'control', 'decode', dict(T1=['S01'], T2=['D41'], T3=['S03', 'S04'], T4=['head.argmax'])),
    ('smp.stop', 'sampler', 'Stop condition (EOS ids, max tokens, context length)', 'control', 'decode', dict(T1=['S02'], T2=['C14'], T3=['S05'], T4=['host.stop_condition'])),
    ('smp.nongreedy', 'sampler', 'Non-greedy sampling (not claimed: greedy contract)', 'control', 'decode', dict(T1=['S03'], T2=['C16'], T3=['S06'])),
    # decode data, common
    ('d.embed', 'data', 'Embedding row fetch (+ dequant / copy expand)', 'data', 'decode', dict(T1=['D01', 'D02'], T2=['D01'], T3=['D01'], T4=['dec.embed_fetch'])),
    ('d.norm_pre', 'data', 'Pre-attention / pre-FFN RMSNorm', 'data', 'decode', dict(T1=['D03', 'D17'], T2=['D11'], T3=['D11'], T4=['L.rmsnorm1', 'L.rmsnorm2'])),
    ('d.act_quant', 'data', 'Activation quantisation before FP8/FP4 matvecs', 'data', 'decode', dict(T2=['D12'], T3=['D11'])),
    ('d.weight_dequant', 'data', 'Weight dequant (per-row scale on every matvec)', 'data', 'decode', dict(T1=['D05'], T4=['L.qkv'])),
    ('d.qkv', 'data', 'Q / KV projections (a_proj, wq_b, wkv)', 'data', 'decode', dict(T1=['D04'], T2=['D13', 'D16'], T3=['D13', 'D14', 'D21'], T4=['L.qkv'])),
    ('d.proj_gather', 'data', 'TP gather of projection shards', 'data', 'decode', dict(T2=['D14'], T3=['D17'])),
    ('d.qk_norm', 'data', 'q / k (kv) norms', 'data', 'decode', dict(T1=['D07'], T2=['D15', 'D18'], T3=['D18'], T4=['L.qk_norm'])),
    ('d.rope', 'data', 'RoPE rotation of q and k', 'data', 'decode', dict(T1=['D08'], T2=['D17', 'D18'], T3=['D18', 'D22'], T4=['L.rope'])),
    ('d.kv_quant', 'data', 'KV quantisation (FP8)', 'data', 'decode', dict(T1=['D09'], T2=['D18'], T3=['D18'], T4=['L.kv_append'])),
    ('d.attn_scores', 'data', 'Attention scores', 'data', 'decode', dict(T1=['D10'], T2=['D27'], T3=['D37'], T4=['L.attn_scores'])),
    ('d.softmax', 'data', 'Softmax (+ sink for DS) and normalise', 'data', 'decode', dict(T1=['D11', 'D13'], T2=['D28'], T3=['D37'], T4=['L.softmax'])),
    ('d.attn_pv', 'data', 'P . V', 'data', 'decode', dict(T1=['D12'], T2=['D29'], T3=['D37'], T4=['L.attn_pv'])),
    ('d.o_proj', 'data', 'Attention output projection (wo_a / wo_b; inverse RoPE for DS)', 'data', 'decode', dict(T1=['D14'], T2=['D30'], T3=['D38', 'D39'], T4=['L.o_proj'])),
    ('d.allreduce_attn', 'data', 'Attention-output collective (all-reduce / gather)', 'data', 'decode', dict(T1=['D15'], T2=['D31'], T3=['D38', 'D39'], T4=['L.allreduce1'])),
    ('d.residual', 'data', 'Residual add + layer hand-off', 'data', 'decode', dict(T1=['D16', 'D22'], T3=['D40'], T4=['L.residual1', 'L.residual2_handoff'])),
    ('d.ffn_up', 'data', 'FFN gate / up (dense, or routed + shared experts)', 'data', 'decode', dict(T1=['D18'], T2=['D35', 'D36'], T3=['D46'], T4=['L.gate_up'])),
    ('d.swiglu', 'data', 'SwiGLU (clamped x route weight for DS)', 'data', 'decode', dict(T1=['D19'], T2=['D35', 'D36'], T3=['D47'], T4=['L.swiglu'])),
    ('d.ffn_down', 'data', 'FFN down projection', 'data', 'decode', dict(T1=['D20'], T2=['D35'], T3=['D49'], T4=['L.down'])),
    ('d.allreduce_ffn', 'data', 'FFN collective (all-reduce / gathers)', 'data', 'decode', dict(T1=['D21'], T2=['D37'], T3=['D48', 'D51'], T4=['L.allreduce2'])),
    ('d.matvec_reduce', 'data', 'Matvec partial-sum reduction / result return path', 'data', 'decode', dict(T1=['D06'], T2=['D38'], T3=['D52'])),
    # decode data, DeepSeek only
    ('ds.engram_hash', 'deepseek', 'Engram n-gram hash (L1, L14)', 'data', 'decode', dict(T2=['D02'], T3=['D02'])),
    ('ds.engram_fetch', 'deepseek', 'Engram table row fetch', 'data', 'decode', dict(T2=['D03'], T3=['D04'])),
    ('ds.engram_transport', 'deepseek', 'Engram row transport / gather collectives', 'data', 'decode', dict(T2=['D04'], T3=['D05', 'D07'])),
    ('ds.engram_proj', 'deepseek', 'Engram wkv projection + key norms', 'data', 'decode', dict(T2=['D05'], T3=['D06'])),
    ('ds.engram_gate', 'deepseek', 'Engram gate + residual add', 'data', 'decode', dict(T2=['D06'], T3=['D08'])),
    ('ds.hc_norm_fn', 'deepseek', 'Hyper-connection mix norm + hc_fn matvec (80 a token)', 'data', 'decode', dict(T2=['D07', 'D08'], T3=['D09'])),
    ('ds.hc_sinkhorn', 'deepseek', 'HC pre/post gates + comb softmax + Sinkhorn', 'data', 'decode', dict(T2=['D09'], T3=['D10'])),
    ('ds.hc_pre_post', 'deepseek', 'hc_pre collapse / hc_post mix', 'data', 'decode', dict(T2=['D10'], T3=['D11', 'D40'])),
    ('ds.compressor', 'deepseek', 'Compressor (KV-source layers: pooling, norm, FP4)', 'data', 'decode', dict(T2=['D20'], T3=['D15', 'D23'])),
    ('ds.idx_key', 'deepseek', 'Indexer key (wk, k_norm, RoPE, FP4) + index-key append', 'data', 'decode', dict(T2=['D21'], T3=['D23', 'D25'])),
    ('ds.idx_query', 'deepseek', 'Indexer query (wq_b, RoPE, FP4, weights_proj)', 'data', 'decode', dict(T2=['D22'], T3=['D16', 'D26', 'D27'])),
    ('ds.idx_score', 'deepseek', 'Indexer score scan over compressed keys', 'data', 'decode', dict(T2=['D23'], T3=['D28', 'D29'])),
    ('ds.cand_blocks', 'deepseek', 'Candidate blocks (L20) + mask', 'data', 'decode', dict(T2=['D24'], T3=['D30', 'D31', 'D32'])),
    ('ds.idx_topk', 'deepseek', 'Index top-512 + merge', 'data', 'decode', dict(T2=['D25'], T3=['D33', 'D34'])),
    ('ds.sel_gather', 'deepseek', 'Selected compressed-KV row gather', 'data', 'decode', dict(T2=['D26'], T3=['D35'])),
    ('ds.router', 'deepseek', 'MoE router (gate, sqrt-softplus, top-6, route weights, gather)', 'data', 'decode', dict(T2=['D32', 'D33', 'D34'], T3=['D41', 'D42', 'D43', 'D44'])),
    ('ds.moe_combine', 'deepseek', 'MoE combine (expert sum + shared)', 'data', 'decode', dict(T2=['D37'], T3=['D50'])),
    # MTP
    ('mtp.seed_capture', 'mtp', 'Main-hidden capture at L37-L39 + transport to the seed', 'data', 'mtp_draft', dict(T2=['M01', 'M02'], T3=['P01'], T4=['mtp.draft_state'])),
    ('mtp.seed', 'mtp', 'DSpark seed (main_proj, norm, stage wkv rows)', 'data', 'mtp_draft', dict(T2=['M03'], T3=['P02'], T4=['mtp.draft_state'])),
    ('mtp.dsk', 'mtp', 'DSpark window cache (dsk ring) storage + write', 'control', 'mtp_draft', dict(T2=['M04'], T3=['P03'], T4=['mtp.draft_state'])),
    ('mtp.draft', 'mtp', 'Draft compute (block input + DSpark stages)', 'data', 'mtp_draft', dict(T2=['M05', 'M06'], T3=['P04'], T4=['mtp.draft'])),
    ('mtp.draft_head', 'mtp', 'Draft head + Markov bias + serial draft argmax chain', 'data', 'mtp_draft', dict(T2=['M08', 'M09', 'M10'], T3=['P04'], T4=['mtp.draft'])),
    ('mtp.draft_transport', 'mtp', 'Draft fan-out / draft collectives / FEC on draft crossings', 'control', 'mtp_draft', dict(T2=['M07'], T3=['P05', 'P15'])),
    ('mtp.sequencer', 'mtp', 'MTP control block / sequencer on a die', 'control', 'mtp_accept', dict(T2=['M11'], T3=['P16'])),
    ('mtp.verify_batch', 'mtp', 'Verify-batch formation + wavefront / multi-column issue', 'control', 'mtp_verify', dict(T2=['M12', 'M13'], T3=['P06'], T4=['mtp.verify_batch'])),
    ('mtp.verify_pass', 'mtp', 'Verify pass through all layers (+ routed-expert union)', 'data', 'mtp_verify', dict(T2=['M15'], T3=['P07', 'P08'], T4=['mtp.verify_attn'])),
    ('mtp.visibility', 'mtp', 'In-pass causal KV visibility / visibility fence / per-position transients', 'control', 'mtp_verify', dict(T2=['M14', 'M25'], T3=['P13'])),
    ('mtp.verify_kv_append', 'mtp', 'Verify-pass KV append for the verified positions', 'data', 'mtp_verify', dict(T3=['P09'])),
    ('mtp.verify_engram', 'mtp', 'Per-position Engram hash with speculative history', 'data', 'mtp_verify', dict(T2=['M16'], T3=['D03'])),
    ('mtp.verify_head', 'mtp', 'Verify head (norm + LM head + argmax per position)', 'data', 'mtp_verify', dict(T2=['M17'], T3=['P07'], T4=['mtp.verify_head'])),
    ('mtp.accept', 'mtp', 'Accept compare (longest prefix) + squash broadcast', 'control', 'mtp_accept', dict(T2=['M18', 'M19'], T3=['P10'], T4=['mtp.accept'])),
    ('mtp.commit', 'mtp', 'Commit: position += a+1, emit, next anchor', 'control', 'mtp_accept', dict(T2=['M20'], T3=['P11'], T4=['mtp.commit_pos'])),
    ('mtp.rollback_kv', 'mtp', 'KV ROLLBACK of rejected positions (window, CKV, index keys, compressor slot)', 'data', 'mtp_accept', dict(T2=['M21', 'M22'], T3=['P12'], T4=['mtp.kv_rollback'])),
    ('mtp.rollback_dsk', 'mtp', 'Rollback of DSpark dsk rows', 'data', 'mtp_accept', dict(T2=['M23'], T3=['P12'])),
    ('mtp.rollback_engram', 'mtp', 'Rollback of the Engram token history', 'control', 'mtp_accept', dict(T2=['M24'], T3=['P12'])),
    ('mtp.scratch', 'mtp', 'Draft / verify scratch service', 'control', 'mtp_accept', dict(T3=['P14'])),
    ('mtp.tau', 'mtp', 'Acceptance rate tau (software-measured, 6-class blend)', 'control', 'mtp_accept', dict(T3=['P17'])),
    # fault
    ('f.kv_integrity', 'fault', 'KV HBM transaction integrity (tagged completions)', 'control', 'fault', dict(T1=['F01'], T2=['F02'])),
    ('f.mem_ecc', 'fault', 'HBM / SRAM / mutable-state protection (ECC or equivalent)', 'control', 'fault', dict(T1=['F02'], T2=['F01'], T3=['F01', 'F02'], T4=['fault.hbm_ecc'])),
    ('f.emb_ecc', 'fault', 'Embedding HBM copy SECDED + boot-check fault', 'control', 'fault', dict(T1=['F03'])),
    ('f.link', 'fault', 'Link faults (CRC, replay, sequence gap, link down)', 'control', 'fault', dict(T1=['F04'], T2=['F03'], T3=['F03'], T4=['fault.link'])),
    ('f.aggregation', 'fault', 'Fault aggregation to the host, watchdog, stall export', 'control', 'fault', dict(T1=['F05'], T2=['F02'], T3=['F04'])),
    ('f.traps', 'fault', 'Core / sequencer / overflow traps (fail closed)', 'control', 'fault', dict(T1=['F06'], T2=['F02'], T3=['F04'], T4=['fault.overflow'])),
    ('f.bounds', 'fault', 'Address-bound / context-limit enforcement', 'control', 'fault', dict(T1=['F07', 'C11'], T2=['C14'], T3=['S05'], T4=['host.stop_condition'])),
]

# where a function does not apply (a cell with no member and no NA entry is an UNENUMERATED gap)
QWEN, DS = ('T1', 'T4'), ('T2', 'T3')
NA = {}
def _na(fids, tgts, why):
    for f in fids:
        for t in tgts: NA[(f, t)] = why
_na([r[0] for r in ROWS if r[1] == 'deepseek'] + ['ctl.expert_dispatch', 'ctl.engram_history', 'ctl.compressor_state', 'd.act_quant', 'd.proj_gather',
     'boot.engram_tables', 'mtp.verify_engram', 'mtp.rollback_engram'], QWEN, 'DeepSeek-only operator (Qwen3-8B has no Engram / HC / indexer / MoE / FP8 activations)')
_na([r[0] for r in ROWS if r[1] == 'mtp'], ['T1'], 'AR only by owner decision (dspark_verdict.json AR_MODE)')
_na(['mtp.dsk', 'mtp.draft_transport', 'mtp.sequencer', 'mtp.visibility', 'mtp.verify_kv_append', 'mtp.rollback_dsk', 'mtp.scratch', 'mtp.tau'], ['T4'],
    'T4 ledger lists Qwen MTP only at function level, pending the owner decision on Qwen MTP on r25')
_na(['ctl.weight_stream'], ['T1', 'T2'], 'weights live in mask ROM, not streamed')
_na(['boot.embedding'], ['T2', 'T3'], 'embedding is part of the weight image (DS ROM head dies / HBM image)')
_na(['boot.embedding'], [], '')
_na(['ctl.const_rom'], ['T2', 'T3', 'T4'], 'norm weights / tables are in the weight image (no separate constant ROM)')
_na(['d.weight_dequant'], DS, 'FP8 / FP4 block scales are applied inside the matvec element')
_na(['d.weight_dequant'], [], '')
_na(['f.emb_ecc', 'boot.csr', 'host.phy', 'f.kv_integrity', 'f.bounds', 'boot.hbm_init', 'boot.link_training'], [], '')
_na(['f.emb_ecc'], ['T2', 'T3', 'T4'], 'only T1 copies the embedding into HBM (r21c); elsewhere covered by f.mem_ecc')
_na(['ctl.hbm_service'], ['T1', 'T4'], 'enumerated under ctl.kv_stream (T1) / ctl.weight_stream (T4)')
_na(['boot.rope_tables'], ['T1'], 'RoPE rows live in the constant ROM (ctl.const_rom)')
_na(['boot.rope_tables'], ['T3'], 'enumerated under ctl.rope_supply (T3-D19: no producer)')
_na(['smp.nongreedy'], ['T4'], 'not claimed (greedy contract)')
_na(['d.residual'], ['T2'], 'DeepSeek residual is the hc_post mix (ds.hc_pre_post)')
_na(['ctl.transport'], ['T4'], 'r25 transport shared with T3 (T3-D12 / D52); T4 maps no separate node')
_na(['d.matvec_reduce'], ['T4'], 'r25 result gather shared with T3 (T3-D52)')
_na(['mtp.tau'], ['T2'], 'T2.md lists tau 4.159 under "not counted as gaps" (software-measured acceptance, not a hardware function)')
_na(['mtp.scratch'], ['T2'], 'HBM-accelerator scratch service; the S81 wavefront keeps no draft / verify scratch rows')
_na(['mtp.verify_kv_append'], ['T2'], 'verify positions use the AR append path (T2-D19 / ctl.kv_append) inside the wavefront; visibility is mtp.visibility')

# ------------------------------------------------------------------------------------------------ owners
# Streams the coordinator assigned; 'verified' records what each stream's log in /home/ubuntu/claude-takeover-20261007 shows.
LOGDIR = '/home/ubuntu/claude-takeover-20261007'
STREAMS = {
    'qwen-system': 'Qwen control plane (host_if / pkg ctl / rst seq / CSR placement), constant ROM, kvc, split spine',
    'emb-hbm-impl': 'Qwen embedding in HBM (r21c): RTL, e2e bench, boot load, SECDED',
    'ingest': 'host / KV-ingest masters on every die (qfd_io_host, dsfd_host, hfd_loader)',
    'mtp-rom': 'DS-ROM MTP blocks: dsfd_mtp_seq, WFC shims, draft fan-out',
    'mtp-hbm': 'HBM MTP blocks: hfd_mtp (ctl, accept, spec_state_f, union, argmax), fence, topk',
    'mtp-die': 'MTP die recipes: draft dies, head-die slot, placement, links, HBM fit',
    'mtp-exact': 'MTP exactness benches: ROM MTP cached RTL, wavefront, HBM connected top',
    'mtp-rollback': 'MTP rollback hardware (dsk rows, HBM ring addressing)',
    'engram': 'Engram E-side: hash, HBM-resident tables on the home dies (owner option A 2026-10-09), row transport, history (both DS targets)',
    's81-dies': 'S81 scan / head dies, array v2 composition (rack at 120 stages), die slots',
    'ds-control': 'S81 control plane, EOS, RoPE boot, ECC, re-measure of modelled terms',
    'hbm-indexer': 'HBM indexer on r25 (scores, top-k, candidates)',
    'hbm-system': 'HBM write-back, HC mix / Sinkhorn, RoPE producer, host loop, EOS, PLL / reset / retry, expert steering / fetch',
    'qwen-hbm-unify': 'Qwen3-8B on r25 (T4): program, dtype, RoPE, vocab, GQA, token path',
    'closure-drive': 'block-closure streams: drive-* (15-min closure-loop drive), s81-tail, safe-* variants, die evidence',
    'owner-decision': 'out of scope by an owner decision (listed so the scope stays explicit)',
}
STREAM_LOGS = {'closure-drive': 'drive-*.log', 'owner-decision': None}

def _ids(*xs): return set(xs)
# ownerless work that is not one ledger node (PLAN.md section 0)
STRUCTURAL = [
    dict(id='O1', scope='all targets: token-path re-export (tools/token_path_export.py, unified_composition.py, reprice_20261008.py; qwen_hbm() missing)',
         rows='every NOT_PRICED / MODELLED_ONLY cell', classes=['NOT_PRICED', 'MODELLED_ONLY'],
         why='functional owners deliver block cycles, but nobody re-exports the token path (token-path stream STOP 21:10, reprice STOP 18:25); T4 has no view',
         proposed='new token-path re-export stream on the 15-min drive cadence; qwen-hbm-unify writes qwen_hbm()'),
]
# OWN[target] = [(node-id regex, owner, {gap class: owner override})]; first match wins. owner None = ownerless.
# NOT_CLOSED goes to closure-drive unless the node is new RTL of its functional owner or has no die slot (NOT_ON_DIE /
# MISSING_HW), in which case the functional owner carries it until the block has a master.
OWN = {
    'T1': [
        (r'^(D01|B02|F03)$', 'emb-hbm-impl', {}),
        (r'^(H03|H04|H05)$', 'ingest', {}),
        (r'^(H01|H02|B03|B04|B07|C0[1-9]|C1[01]|S01|S02|F01|F05|F06|F07|M01|D06)$', 'qwen-system', {}),
        (r'^B05$', None, {'_why': 'PLL macro / slot: no stream owns clock generation on the Qwen die', '_proposed': 'qwen-system (die-top) or a new die-top/PLL stream'}),
        (r'^F02$', None, {'_why': 'KV data ECC policy (SECDED vs cite HBM3E on-die ECC) has no owner', '_proposed': 'qwen-system (kvc) after an owner policy call'}),
        (r'^B06$', None, {'_why': 'HBM PHY init is a vendor-abstract behaviour with no bench', '_proposed': 'cite vendor; qwen-system if a bring-up bench is wanted'}),
        (r'^C12$', None, {'_why': 'relay / wire stages priced from counts; re-price on r21b routed parasitics needs a token-path re-export (token-path stream stopped)', '_proposed': 'token-path re-export (new stream) fed by die evidence'}),
        (r'^(C14|D15|D21)$', 'closure-drive', {'MODELLED_ONLY': None, 'NOT_ON_DIE': None,
            '_why': 'UCIe / SerDes PHY latency is a vendor abstract (not a measured term)', '_proposed': 'token-path re-export: cite vendor latency'}),
        (r'^S03$', 'owner-decision', {}),
    ],
    'T2': [
        (r'^(D02|D03|D04|D05|C15|M16)$', 'engram', {}),
        (r'^M24$', 'engram', {'NOT_EXACT': 'mtp-exact'}),
        (r'^(M01|M02|M03|M05|M06|M09|M17)$', 'mtp-die', {}),
        (r'^M04$', 'mtp-die', {}),
        (r'^M23$', 'mtp-rollback', {}),
        (r'^M07$', 'mtp-rom', {'NOT_PRICED': 'mtp-die'}),
        (r'^(M11|M18|M19|M20|M25)$', 'mtp-rom', {'NOT_ON_DIE': 'mtp-die'}),
        (r'^(M12|M13)$', 'mtp-rom', {'NOT_ON_DIE': 's81-dies', 'NOT_EXACT': 'mtp-exact', 'MODELLED_ONLY': 'mtp-exact'}),
        (r'^M14$', 'mtp-exact', {'NOT_ON_DIE': 's81-dies'}),
        (r'^(M21|M22)$', 'mtp-exact', {}),
        (r'^(C01|C02|C03|C05|C08|C09|C13|C14|U01|F01|F02|F03|B03|D08|D23|D25|D26|D27)$', 'ds-control', {}),
        (r'^C04$', 's81-dies', {}),
        (r'^(H0[1-4])$', 'ingest', {}),
        (r'^(B05|D01)$', 's81-dies', {}),
        (r'^B06$', None, {'_why': 'HBM PHY calibration has no bench (vendor behaviour)', '_proposed': 'ds-control (bring-up bench) or cite vendor'}),
    ],
    'T3': [
        (r'^(D23|D28|D30|D31|D32|D33|D34)$', 'hbm-indexer', {}),
        (r'^(D20|D25|D24|C04|P09)$', 'hbm-system', {}),
        (r'^(D09|D10|D19|H01|H02|C01|C02|S05|B04|B05|C06|D45|F03)$', 'hbm-system', {}),
        (r'^(H03|B01|B02|B03)$', 'ingest', {}),
        (r'^(D02|D03|D05|D07)$', 'engram', {}),
        (r'^(P01|P02|P03|P06|P08|P10|P11|P13|P14|P16)$', 'mtp-hbm', {'NOT_ON_DIE': 'mtp-die', 'NOT_EXACT': 'mtp-exact'}),
        (r'^(P04|P05|P15)$', 'mtp-die', {}),
        (r'^P12$', 'mtp-rollback', {'NOT_EXACT': 'mtp-exact', 'NOT_ON_DIE': 'mtp-die'}),
        (r'^(C05|C07|F01)$', None, {'_why': 'vendor terms (Tomahawk Ultra tier, HBM PHY + controller, HBM ECC): labelled, not ours to build', '_proposed': 'token-path re-export: keep vendor citations'}),
        (r'^(F02|F04)$', None, {'_why': 'on-die SRAM protection choice / fault-trap bench: no stream assigned', '_proposed': 'hbm-system'}),
        (r'^(D17|D38|D39|D43|D48|D51|S04)$', 'closure-drive', {'MODELLED_ONLY': None,
            '_why': 'switch-tail cycles are modelled (47,700 cycles, 6.8 % of AR); no stream re-measures them', '_proposed': 'hbm-system (collective) + token-path re-export'}),
        (r'^P17$', 'owner-decision', {}),
    ],
    'T4': [
        (r'^host\.prefill_(handoff|kv_ingest)$', 'ingest', {'NOT_PRICED': 'qwen-hbm-unify'}),
        (r'.*', 'qwen-hbm-unify', {'NOT_CLOSED': 'closure-drive'}),
    ],
}
UNENUM_OWNER = {
    'T1': lambda g, f: 'emb-hbm-impl' if 'emb' in f else 'ingest' if g == 'host' else 'qwen-system',
    'T2': lambda g, f: 'engram' if 'engram' in f else 'ingest' if g == 'host' else 'mtp-die' if g == 'mtp' else 'ds-control',
    'T3': lambda g, f: 'engram' if 'engram' in f else 'ingest' if g == 'host' else 'mtp-hbm' if g == 'mtp' else 'hbm-indexer' if f.startswith('ds.idx') or f == 'ds.cand_blocks' else 'hbm-system',
    'T4': lambda g, f: 'ingest' if f.startswith('prefill') else 'qwen-hbm-unify',
}

def owner_of(target, nid, cls, node):
    short = nid.split('-', 1)[1] if target in ('T2', 'T3') and nid.startswith(target + '-') else nid
    for rx, own, ov in OWN[target]:
        if re.search(rx, short):
            meta = {'why': ov.get('_why'), 'proposed': ov.get('_proposed')}
            if cls in ov: return ov[cls], meta
            if own is None and cls == 'NOT_CLOSED': return 'closure-drive', meta
            if cls == 'NOT_CLOSED' and own not in (None, 'owner-decision') and not (set(node.get('gap') or []) & UNCOVERED) \
                    and own in ('qwen-system', 'ds-control', 'hbm-system', 'engram', 's81-dies') and short not in NEW_RTL.get(target, ()):
                return 'closure-drive', meta
            return own, meta
    return ('closure-drive' if cls == 'NOT_CLOSED' else None), {'why': 'no rule', 'proposed': None}
# nodes whose NOT_CLOSED belongs to the functional owner (new RTL it is routing itself)
NEW_RTL = {'T1': {'D01', 'F03', 'B02', 'H04', 'H01', 'H02'}, 'T2': {'D03', 'D02', 'M11', 'M18'}, 'T3': {'D28', 'D20', 'D25'}}

# ------------------------------------------------------------------------------------------------ token-path map
# rules: (regex, [fids]); matched against the operator id (ROM views, after stripping V./layer prefixes) or 'label' (HBM views)
_DS = [
    (r'^embed$', ['d.embed']), (r'^(attn|ffn)\.hc\.(sumsq|rsqrt|fn)$', ['ds.hc_norm_fn']), (r'^(attn|ffn)\.hc\.(pre_post|sinkhorn)$', ['ds.hc_sinkhorn']),
    (r'^head\.hc_pre$', ['ds.hc_pre_post', 'smp.final_norm']), (r'^(attn|ffn)\.hc_(pre|post)$', ['ds.hc_pre_post']),
    (r'^(attn|ffn)\.norm\.', ['d.norm_pre']), (r'^(attn\.(quant|q_quant|z_quant)|ffn\.(quant2?|shared_quant))$', ['d.act_quant']),
    (r'^attn\.(a_proj|wq_b)$', ['d.qkv']), (r'^attn\.a_allgather$', ['d.proj_gather']), (r'^attn\.(q_norm|kv_norm)\.', ['d.qk_norm']),
    (r'^attn\.q_rope$', ['d.rope']), (r'^attn\.kv_rope_qdq$', ['d.rope', 'd.kv_quant']), (r'^attn\.window_load$', ['ctl.kv_stream']),
    (r'^attn\.own_row_write$', ['ctl.kv_append']), (r'^attn\.scores', ['d.attn_scores']), (r'^attn\.(max|exp|den|sink|normalize)', ['d.softmax']),
    (r'^attn\.pv$', ['d.attn_pv']), (r'^attn\.wo_[ab]$', ['d.o_proj']), (r'^attn\.out_allreduce$', ['d.allreduce_attn']),
    (r'^(substage_hop\d|unplaced_hops|head\.hop|hop_in)$', ['ctl.inter_die']), (r'^token\.return$', ['ctl.token_loop']),
    (r'^ffn\.(router|softplus_sqrt|bias|top6|top6_order|route_w|weights|router_allgather)', ['ds.router']),
    (r'^ffn\.(ids_hop|ret_hop)', ['ctl.expert_dispatch']),
    (r'^ffn\.(experts_gu|shared_gu)', ['d.ffn_up']), (r'^ffn\.(shared_)?swiglu', ['d.swiglu']), (r'^ffn\.down', ['d.ffn_down']),
    (r'^ffn\.combine_allreduce$', ['d.allreduce_ffn', 'ds.moe_combine']), (r'^eng\.(lead_flit|rows_allgather)$', ['ds.engram_transport']), (r'^eng\.hash$', ['ds.engram_hash', 'ctl.engram_history', 'mtp.verify_engram']), (r'^eng\.hbm_read$', ['ds.engram_fetch']), (r'^eng\.(wkv|knorm)$', ['ds.engram_proj']), (r'^eng\.', ['ds.engram_gate']),
    (r'^attn\.idx\.q$', ['ds.idx_query']), (r'^attn\.idx\.score$', ['ds.idx_score']), (r'^attn\.idx\.topk_', ['ds.idx_topk']), (r'^attn\.idx\.newkey$', ['ds.idx_key']),
    (r'^attn\.(gather|rows_allgather)$', ['ds.sel_gather']), (r'^attn\.cmp\.(pool|norm\.|row_qdq)', ['ds.compressor', 'ctl.compressor_state']),
    (r'^attn\.cmp\.(wk|k_norm\.|k_rope_qdq)', ['ds.idx_key']), (r'^attn\.cand\.', ['ds.cand_blocks']),
    (r'^head\.norm\.', ['smp.final_norm']), (r'^head\.lm_head$', ['smp.lm_head']), (r'^head\.argmax', ['smp.argmax']),
    (r'^draft\.head\d', ['mtp.draft_head']), (r'^draft\.markov\d', ['mtp.draft_head']), (r'^draft\.fixed$', ['mtp.draft']),
    (r'^wave\.', ['mtp.verify_batch']), (r'^accept\.seed$', ['mtp.seed', 'mtp.seed_capture']), (r'^accept\.commit$', ['mtp.commit', 'mtp.rollback_kv']),
    (r'^accept\.round$', ['mtp.accept']), (r'^accept\.engram_rewind$', ['mtp.rollback_engram']),
]
_HBM = [
    (r'^hbm:embedding_row$', ['d.embed']), (r'^(sufused|su|quant):hc_pre_norm$', ['ds.hc_pre_post', 'd.norm_pre', 'd.act_quant']),
    (r'^xload:', ['ctl.transport']), (r'^barrier$', ['ctl.transport']),
    (r'^sm:(wq_a|wkv|wq_b)', ['d.qkv']), (r'^(coll|tail):x_projections_gather$', ['d.proj_gather']),
    (r'^(sufused|su|quant):q_norm_kv_row$', ['d.qk_norm', 'd.rope', 'd.kv_quant']), (r'^su:q_rope$', ['d.rope', 'ctl.rope_supply']),
    (r'^hbm:window_rows$', ['ctl.kv_stream']), (r'^(su:attend|attn:tile_)', ['d.attn_scores', 'd.softmax', 'd.attn_pv']),
    (r'^sm:wo_[ab]', ['d.o_proj']), (r'^(coll|tail):(o-group tree reduce|attn_out_gather)', ['d.allreduce_attn']),
    (r'^(sufused|su):hc_post$', ['ds.hc_pre_post']),
    (r'^(sm:router gate|su:router_act|(coll|tail):router_gather|su:route$|du:router_top6)', ['ds.router']),
    (r'^hbm:expert_fetch$', ['ctl.expert_dispatch']), (r'^(sufused:)?swiglu$', ['d.swiglu']),
    (r'^sm:routed gate/up', ['d.ffn_up']), (r'^sm:expert slot \d w2', ['d.ffn_down']),
    (r'^(coll|tail):(expert_intermediate_gather|ffn_out_gather)$', ['d.allreduce_ffn']), (r'^su:moe_sum$', ['ds.moe_combine']),
    (r'^du:engram_fetch$', ['ds.engram_fetch', 'ds.engram_hash', 'ds.engram_transport']), (r'^sm:engram\.wkv$', ['ds.engram_proj']), (r'^du:engram_mix$', ['ds.engram_gate']),
    (r'^sm:compressor\.', ['ds.compressor']),
    (r'^(sm:indexer\.(weights_proj|wq_b)|(coll|tail):indexer\.q_gather|du:index_q)', ['ds.idx_query']),
    (r'^du:index_scores$', ['ds.idx_score']), (r'^(du:topk_local|select:96x512|(coll|tail):96 x 512 index merge)', ['ds.idx_topk']),
    (r'^(hbm:ckv_source_rows|(coll|tail):selected compressed-KV rows)', ['ds.sel_gather']), (r'^du:cand_', ['ds.cand_blocks']),
    (r'^(sufused|su|quant):final_norm$', ['smp.final_norm']), (r'^sm:LM head$', ['smp.lm_head']), (r'^(su:argmax_local|(coll|tail):argmax merge)$', ['smp.argmax']),
    (r'^hcp:hc_mixes', ['ds.hc_norm_fn', 'ds.hc_sinkhorn']),
    (r'^draft compute', ['mtp.draft', 'mtp.draft_head', 'mtp.dsk']), (r'^draft collectives', ['mtp.draft_transport']),
    (r'^union:', ['mtp.verify_pass']), (r'^seed:', ['mtp.seed', 'mtp.seed_capture']),
    (r'^accept / commit', ['mtp.accept', 'mtp.commit', 'mtp.rollback_kv', 'mtp.sequencer']),
]
_QWEN = [
    (r'^embed$', ['d.embed']), (r'^rmsnorm\d$', ['d.norm_pre']), (r'^qkv$', ['d.qkv', 'd.weight_dequant']),
    (r'^qknorm_rope$', ['d.qk_norm', 'd.rope', 'd.kv_quant', 'ctl.kv_append', 'ctl.rope_supply']),
    (r'^attn_kv$', ['d.attn_scores', 'd.attn_pv', 'ctl.kv_addr']), (r'^softmax_norm$', ['d.softmax']), (r'^o_proj$', ['d.o_proj']),
    (r'^allreduce1$', ['d.allreduce_attn', 'ctl.collective']), (r'^allreduce2$', ['d.allreduce_ffn', 'ctl.collective']),
    (r'^attn_tail$', ['d.residual', 'ctl.kv_append']), (r'^gate_up$', ['d.ffn_up', 'd.swiglu']), (r'^down$', ['d.ffn_down']),
    (r'^residual$', ['d.residual']), (r'^kv_prefetch$', ['ctl.kv_stream']),
    (r'^head\.lm_head$', ['smp.final_norm', 'smp.lm_head', 'smp.argmax']),
]
TP_MAP = {
    'qwen_rom': dict(target='T1', field='id', strip=r'^L\d+\.', rules=_QWEN),
    'ds_rom': dict(target='T2', field='id', strip=r'^(V\.)?(L\d+\.|mtp\.\d\.)?', rules=_DS),
    'ds_rom_mtp': dict(target='T2', field='id', strip=r'^(V\.)?(L\d+\.|mtp\.\d\.)?', rules=_DS,
                       prefix_rows={r'^mtp\.\d\.': ['mtp.draft'], r'^V\.head\.': ['mtp.verify_head'], r'^V\.embed$': ['mtp.verify_batch']}),
    'hbm_ds': dict(target='T3', field='label', strip=None, rules=_HBM),
    'hbm_ds_mtp': dict(target='T3', field='label', strip=None, rules=_HBM),
}

def tp_rows(design, node):
    """fids of one token-path operator (used by the fleet viz to colour the flow graph and the die replay)."""
    m = TP_MAP[design]
    raw = node.get(m['field']) or ''
    key = re.sub(m['strip'], '', raw) if m.get('strip') else raw
    out = []
    if m['field'] == 'id' and design.endswith('_mtp'):
        for rx, f in m.get('prefix_rows', {}).items():
            if re.search(rx, raw): out += f
        if raw.startswith('mtp.') and out:     # draft stages run the AR operator set on draft dies: draft rows only
            return list(dict.fromkeys(out))
    for rx, f in m['rules']:
        if re.search(rx, key): out += f; break
    out += m.get('phase_rows', {}).get(node.get('phase'), [])
    return list(dict.fromkeys(out))

# ------------------------------------------------------------------------------------------------ derivation
CL_ORDER = ['NONE', 'FAILED', 'RUNNING', 'PARTIAL', 'CLOSED']
def closure_state(node, by_id):
    txt = str(node.get('closure') or '')
    m = re.match(r'\s*see (\S+)', txt)
    if m and m.group(1) in by_id: txt = str(by_id[m.group(1)].get('closure') or '')
    u = txt.upper()
    g = set(node.get('gap') or [])
    for k, v in (('NOT CLOSED', 'FAILED'), ('NEEDS', 'FAILED'), ('FAILED', 'FAILED'), ('REVOKED', 'FAILED'), ('RUNNING', 'RUNNING'),
                 ('IN FLIGHT', 'RUNNING'), ('PARTIAL', 'PARTIAL'), ('INTERIM', 'PARTIAL'), ('CLOSED', 'CLOSED'), ('NONE', 'NONE')):
        if u.lstrip().startswith(k) or (k in ('FAILED', 'RUNNING', 'CLOSED') and re.search(r'\b' + k + r'\b', u[:40])):
            s = v; break
    else:
        s = 'NONE' if 'NOT_CLOSED' in g else 'CLOSED'
    if s == 'CLOSED' and 'NOT_CLOSED' in g: s = 'PARTIAL'
    if 'NOT_CLOSED' not in g and s in ('NONE', 'FAILED'): s = 'n/a' if not (node.get('hw_element') or '').strip() else s
    return s

TOK = re.compile(r'[A-Za-z_][A-Za-z0-9_]{3,}')
def element_names(text, names):
    if not names: return []
    out = []
    for t in TOK.findall(text):
        if t in names: out.append(t)
        elif len(t) >= 8 and '_' in t:
            out += [e for e in names if e.startswith(t + '_') and re.fullmatch(r'(\d+|[a-z]{1,2})', e[len(t) + 1:])]
    return list(dict.fromkeys(out))

def load_ledgers(read):
    L = {}
    for t in TARGETS:
        txt = read(t + '.json')
        if txt is None: continue
        d = json.loads(txt)
        nodes = d['nodes'] if isinstance(d, dict) else d
        meta = {k: v for k, v in d.items() if k != 'nodes'} if isinstance(d, dict) else {}
        L[t] = dict(nodes=nodes, meta=meta)
    return L

def build(ledgers, element_set=None, now=None):
    element_set = set(element_set or [])
    by = {t: {n['id']: n for n in L['nodes']} for t, L in ledgers.items()}
    full = lambda t, i: (t + '-' + i) if t in ('T2', 'T3') and not i.startswith(t + '-') else i
    used = {t: set() for t in ledgers}
    rows, ownerless = [], []
    def cell_for(fid, group, t, members):
        if t not in ledgers: return dict(state='missing_ledger')
        ids = [full(t, i) for i in members if full(t, i) in by[t]]
        missing = [full(t, i) for i in members if full(t, i) not in by[t]]
        if not ids:
            if (fid, t) in NA and not missing: return dict(state='na', why=NA[(fid, t)])
            own = UNENUM_OWNER[t](group, fid)
            return dict(state='gap', nodes=[], gaps=[dict(cls='UNENUMERATED', owner=own, nodes=[], note='function applies but the %s ledger has no node for it%s' % (t, (' (ids gone: ' + ', '.join(missing) + ')') if missing else ''))],
                        owner=own, hw=None, die=None, rtl=None, exact=None, closure='n/a', priced=None, cycles=None, elements=[])
        used[t].update(ids)
        ns = [by[t][i] for i in ids]
        gaps = {}
        for n in ns:
            for c in n.get('gap') or []:
                own, meta = owner_of(t, n['id'], c, n)
                k = (c, own)
                g = gaps.setdefault(k, dict(cls=c, owner=own, nodes=[]))
                g['nodes'].append(n['id'])
                if own is None:
                    g['why'] = meta.get('why'); g['proposed'] = meta.get('proposed')
        gl = sorted(gaps.values(), key=lambda g: (GAPS.index(g['cls']), str(g['owner'])))
        gset = {g['cls'] for g in gl}
        cls_list = [closure_state(n, by[t]) for n in ns]
        cl = min((c for c in cls_list if c in CL_ORDER), key=CL_ORDER.index, default='n/a')
        srcs = sorted({n.get('cycles_source') or 'none' for n in ns})
        cyc = [n.get('cycles') for n in ns if isinstance(n.get('cycles'), (int, float))]
        text = ' '.join(str(n.get(k) or '') for n in ns for k in ('hw_element', 'die', 'closure'))
        owners = [g['owner'] for g in gl if g['owner']]
        prim = max(set(owners), key=lambda o: (sum(1 for g in gl if g['owner'] == o and g['cls'] != 'NOT_CLOSED'), owners.count(o))) if owners else None
        return dict(state='gap' if gl else 'covered', nodes=ids, gaps=gl, owner=prim,
                    function=[n.get('function') for n in ns], hw_element=[n.get('hw_element') for n in ns], die=[n.get('die') for n in ns],
                    hw=not ('MISSING_HW' in gset), on_die=not ('NOT_ON_DIE' in gset),
                    rtl=all(bool(n.get('rtl')) for n in ns) and 'MISSING_HW' not in gset,
                    exact=all(bool(n.get('exact_bench')) for n in ns) and 'NOT_EXACT' not in gset,
                    closure=cl, closure_text=[str(n.get('closure') or '')[:240] for n in ns],
                    priced=('no' if 'NOT_PRICED' in gset else 'modelled' if 'MODELLED_ONLY' in gset else '/'.join(srcs)),
                    in_token_path=[n.get('in_token_path') for n in ns], cycles=(sum(cyc) if cyc else None),
                    elements=element_names(text, element_set), notes=[str(n.get('notes') or '')[:400] for n in ns])
    for fid, group, fn, plane, phase, mem in ROWS:
        cells = {t: cell_for(fid, group, t, mem.get(t, [])) for t in TARGETS}
        rows.append(dict(fid=fid, group=group, function=fn, plane=plane, phase=phase, cells=cells))
    # ledger nodes that no row gathers: own rows, so nothing a stream adds to a ledger is lost
    for t, L in ledgers.items():
        for n in L['nodes']:
            if n['id'] in used[t]: continue
            fid = 'unmapped.%s.%s' % (t, n['id'])
            mem = {t: [n['id']]}
            cells = {tt: (cell_for(fid, 'unmapped', tt, mem.get(tt, [])) if tt == t else dict(state='na', why='node exists only in the %s ledger (not yet normalised)' % t)) for tt in TARGETS}
            rows.append(dict(fid=fid, group='unmapped', function=n.get('function', n['id']), plane=n.get('plane'), phase=n.get('phase'), cells=cells))
    for r in rows:
        for t, c in r['cells'].items():
            for g in c.get('gaps') or []:
                if g['owner'] is None:
                    ownerless.append(dict(target=t, fid=r['fid'], function=r['function'], cls=g['cls'], nodes=g['nodes'], why=g.get('why'), proposed=g.get('proposed')))
    summ = {}
    for t in TARGETS:
        cs = [r['cells'][t] for r in rows]
        s = dict(rows_applicable=sum(1 for c in cs if c['state'] in ('gap', 'covered')), covered=sum(1 for c in cs if c['state'] == 'covered'),
                 with_gap=sum(1 for c in cs if c['state'] == 'gap'), uncovered=sum(1 for c in cs if any(g['cls'] in UNCOVERED for g in c.get('gaps') or [])),
                 by_class={k: sum(1 for c in cs if any(g['cls'] == k for g in c.get('gaps') or [])) for k in GAPS},
                 by_owner={})
        for c in cs:
            for g in c.get('gaps') or []:
                s['by_owner'][g['owner'] or 'OWNERLESS'] = s['by_owner'].get(g['owner'] or 'OWNERLESS', 0) + 1
        s['nodes'] = len(ledgers[t]['nodes']) if t in ledgers else 0
        summ[t] = s
    return dict(schema='opentallas.coverage_matrix.v1',
                generated=now or datetime.datetime.now().strftime('%Y-%m-%d %H:%M PT'),
                generator='results/arch/coverage_20261008/gen_matrix.py',
                targets={t: dict(TARGET_INFO[t], title=(ledgers.get(t, {}).get('meta', {}).get('title')), ledger='results/arch/coverage_20261008/%s.json' % t,
                                 nodes=len(ledgers[t]['nodes']) if t in ledgers else 0) for t in TARGETS},
                gap_classes=GAPS, uncovered_classes=sorted(UNCOVERED),
                streams={k: dict(scope=v) for k, v in STREAMS.items()},
                ownerless=ownerless, ownerless_structural=STRUCTURAL, summary=summ, rows=rows,
                token_map_note='tp_rows(design, node) in gen_matrix.py maps each token-path operator to rows; the fleet viz applies it live')

def token_maps(designs):
    """{design: {node id: [fids]}} for token-path records {design: record}."""
    return {d: {n['id']: tp_rows(d, n) for n in rec['nodes']} for d, rec in designs.items() if d in TP_MAP}

def verify_streams(logdir=LOGDIR):
    """what each assigned stream's log shows (start, last line, last time)."""
    import glob, os
    out = {}
    for s in STREAMS:
        pat = STREAM_LOGS.get(s, s + '.log')
        if pat is None: out[s] = dict(log=None, status='n/a'); continue
        files = sorted(glob.glob(os.path.join(logdir, pat)), key=os.path.getmtime)
        if not files: out[s] = dict(log=None, status='NO LOG: assigned, not started (or logging elsewhere)'); continue
        f = files[-1]; lines = [l for l in open(f, errors='replace').read().splitlines() if l.strip()]
        last = lines[-1] if lines else ''
        out[s] = dict(log=f, lines=len(lines), mtime=datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M'),
                      status='started only' if len(lines) <= 1 else 'active', last=last[:300])
    return out

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--elements', default='http://127.0.0.1:8765/api/elements')
    ap.add_argument('--tokens', default='results/arch/token_path_20261008')
    ap.add_argument('--out', default=str(HERE / 'MATRIX.json'))
    ap.add_argument('--check', action='store_true', help='fail on ledger nodes no row gathers')
    a = ap.parse_args()
    led = load_ledgers(lambda n: (HERE / n).read_text() if (HERE / n).exists() else None)
    names = []
    try:
        names = [r['element'] for r in json.load(urllib.request.urlopen(a.elements, timeout=10))['rows']]
    except Exception as e:
        print('elements: %s (element join skipped)' % e, file=sys.stderr)
    m = build(led, names)
    m['elements_source'] = a.elements if names else None
    v = verify_streams()
    for s, info in v.items(): m['streams'][s].update(info)
    # token-path coverage: per design, operators by row and the cycles they carry
    tp = {}
    root = pathlib.Path(a.tokens)
    rows = {r['fid']: r for r in m['rows']}
    for d in TP_MAP:
        p = root / (d + '.json')
        if not p.exists(): continue
        rec = json.loads(p.read_text())
        t = TP_MAP[d]['target']
        unm, gapc, unc, tot = 0, 0.0, 0.0, 0.0
        for n in rec['nodes']:
            fs = tp_rows(d, n)
            if not n.get('critical'): continue
            tot += n['cycles']
            if not fs: unm += 1; continue
            gs = {g['cls'] for f in fs for g in rows[f]['cells'][t].get('gaps') or []}
            if gs - {'NOT_CLOSED'}: gapc += n['cycles']
            if gs & UNCOVERED: unc += n['cycles']
        tp[d] = dict(target=t, operators=len(rec['nodes']), critical_cycles=round(tot, 1), unmapped_critical_ops=unm,
                     cycles_on_rows_with_gaps_beyond_closure=round(gapc, 1), cycles_on_uncovered_rows=round(unc, 1))
    m['token_paths'] = tp
    unmapped = [r['fid'] for r in m['rows'] if r['group'] == 'unmapped']
    pathlib.Path(a.out).write_text(json.dumps(m, indent=1) + '\n')
    print('wrote %s: %d rows (%d unmapped), %d ownerless gaps; tp %s' % (a.out, len(m['rows']), len(unmapped), len(m['ownerless']),
          {d: (x['unmapped_critical_ops'], x['cycles_on_uncovered_rows']) for d, x in tp.items()}))
    if a.check and unmapped:
        print('unmapped ledger nodes: ' + ', '.join(unmapped), file=sys.stderr); sys.exit(1)

if __name__ == '__main__':
    main()
