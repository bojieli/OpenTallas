#!/usr/bin/env python3
"""hbm-generic (2026-10-09): one HBM accelerator die for Qwen3-8B and DeepSeek-V4.1 Flash.

Planning + sizing record. No RTL edits, no routes. Writes plan.json next to this file.
Every rate here is an ESTIMATE composed from the cited records; nothing is a measured rate.

Die geometry figures were produced by tools/hbm_accel_die_fp.py at origin/main 7dc926e71 (see `die_fit.runs`);
re-run with `python3 gen.py --die` from the repo root to recompute them (slow, ~2 min a variant).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CLK = 1.2e9
RETICLE = dict(W_mm=33.0, H_mm=26.0, mm2=858.0)

# ------------------------------------------------------------------ die fit (measured with the generator)
DIE_RUNS = [
    # name, variant expression, mm2, W um, H um, overlaps, note
    ('r25', 'R25 (ADOPTED)', 753.19, 30590.352, 24621.84, 0, 'adopted round'),
    ('r25s', 'R25S (attention split into half tiles)', 787.15, 30590.352, 25732.08, 0, 'owner 10-08: split tiles'),
    ('r25sm', 'R25S + R25M (hfd_mtp spine slot, native loader memory ports)', 787.15, 30590.352, 25732.08, 0,
     'mtp-die: MTP + loader add no W/H'),
    ('r25+fmt3', 'R25 + sm_physical_grid (3,3), sm_wh 3214.08 x 1131.84, side_padding 207.36', 763.26, 31734.288,
     24051.6, 0, 'reproduces Codex qwen_r25_fmt3 wide (+10.07 mm2)'),
    ('r25s+fmt3', 'R25S + fmt3 wide SM grid', 798.49, 31734.3, 25161.8, 0, 'geometry_only'),
    ('r25s+m+iqg', 'R25S + R25M + R25IQG (native indexer, as committed)', 787.15, 30590.4, 25732.1, 1,
     'hb_su_full x idx_selector: selector anchor is an r25 absolute coordinate'),
    ('r25s+m+iqg+fmt3', 'R25S + R25M + R25IQG + fmt3 wide (as committed)', 798.49, 31734.3, 25161.8, 5,
     'idx_score_SW/NW at hard-coded x=10,732.608 overlap the widened SW/NW SM groups (4) + selector (1)'),
    ('R25G candidate', 'R25S + R25M + R25IQG + fmt3 wide, indexer anchors re-based by the cx shift (+571.968 um) '
     'and idx_selector moved above hb_su_full (y 17,244.72)', 798.49, 31734.3, 25161.8, 0,
     'geometry_only: 0 overlaps, 0 outside; network paths / pin transforms unqualified'),
]


def die_runs_live():
    sys.path.insert(0, str(ROOT / 'tools'))
    import inspect
    import hbm_accel_die_fp as F
    import hbm_indexer_die_topology as T
    wide = dict(sm_wh=(3214.08, 1131.84), sm_physical_grid=(3, 3), side_padding_um=207.36)

    def merge(*vs):
        out = dict(vs[0])
        for v in vs[1:]:
            for k, x in v.items():
                if k in F.R25 and F.R25[k] == x:
                    continue
                out[k] = {**out[k], **x} if isinstance(x, dict) and isinstance(out.get(k), dict) else x
        return out
    src = inspect.getsource(T.install)
    src = src.replace("x=10732.608 if half=='W' else 16994.88", "x=(10732.608 if half=='W' else 16994.88)+DX")
    src = src.replace("add('idx_selector',sel_master,14164.416,17169.84", "add('idx_selector',sel_master,14164.416+DX,SELY")
    out = []
    for name, v, go, patch in [('r25s+fmt3', merge(F.R25S, wide), True, None),
                               ('R25G candidate', merge(F.R25S, F.R25M, F.R25IQG, wide), True, (571.968, 17244.72))]:
        if patch:
            sc = dict(T.__dict__)
            sc['DX'], sc['SELY'] = patch
            exec(compile(src, T.__file__, 'exec'), sc)
            T.install = sc['install']
        m = F.build(v, geometry_only=go)
        g = m['geo']
        L = F._legality(m)
        out.append(dict(name=name, mm2=round(g['W'] * g['H'] / 1e6, 2), W=g['W'], H=g['H'], overlaps=L['overlaps']))
    return out



# ------------------------------------------------------------------ block inventory (r25s masters + planned additions)
# cls: GENERIC | PARAMETERISE | DS-ONLY.  area_mm2: delta for the die.  reopen: closed elements that go back to open.
# closure: /api/elements 2026-10-09 (option B: TT setup >= 0, FF hold >= 0, DRC 0).
BLOCKS = [
 dict(block='hfd_sm (smh_front_c/n/s, smh_tile_e/w) x32', cls='PARAMETERISE', area_mm2=10.07,
      params='FMT {0 BF16, 1 FP8 block-dot, 2 FP4 (DS), 3 INT8->BF16 (Qwen)}; half-line issue for fmt3; fmt0-2 bypass-matched latency',
      cycles='+1 per dependent SM op (one-stage adapter; +2 with the two-stage fallback); activation wire class 73->81 stages',
      timing='HIGH: front_c failing (nominal postCTS setup ~-267 ps); wide one-stage and two-stage routes in flight',
      closure='front_c failing/re-running; tile_e/w failing; front_n/s closed (TT era) -> re-route for widened pins',
      reopen=['ot_hbm_accel_smh_front_n', 'ot_hbm_accel_smh_front_s'],
      bench='fmt3 gate (exists: 256 codes, ordering, negatives) + DS fmt0/1/2 bit-identical regression on the new source'),
 dict(block='hfd_svc_* stream service (17 segment masters x2)', cls='PARAMETERISE', area_mm2=0.3,
      params='kind-1 KV and kind-2 index-key reads striped over all 32 PCs of a stack (today one fixed KV_PC); kind-3 posted writes merged (dskv_wb strict, then ingest/loader RR)',
      cycles='Qwen: makes the 8K dense KV sweep reach >= 90 % of die bandwidth (one PC is ~1/32 rate); DS: index keys at full rate',
      timing='LOW-MED: segments are TT-era closed with SS ~-200 ps; 34 instances to re-route',
      closure='15 of 17 closed (TT era); SE_s6 / SW_s4 revoked', reopen=['hfd_svc_* (15 masters)'],
      bench='KV-sweep bandwidth bench (Qwen 8K dense; DS window+selected rows) with a PC-collapse negative; write-merge ACK bench'),
 dict(block='hfd_attn_half_lo/hi x64 (ot_attn_tile_m6h1q quads)', cls='GENERIC', area_mm2=0.0,
      params='program mapping only: GQA = one KV head a tile, 4 of 16 head lanes at AR (16 at DSpark p=4); head_dim 128 = two 64 slices; cache-length mask via the pad bit',
      cycles='KV-bandwidth bound (1,325 cycles a layer of KV stream at TP4); lanes not binding',
      timing='as DS (half tiles first trial / failing)', closure='half_lo first trial, half_hi failing; quads closed', reopen=[],
      bench='Qwen GQA attention stage at P8191 vs qwen_r25 (chunk8 + pairwise), negative: wrong KV-head map',
      rejected='per-lane KV group select (reopens closed quads, no gain while KV-bound)'),
 dict(block='ot_qwen_r25_causal_mask', cls='PARAMETERISE', area_mm2=0.0,
      params='MASK {DS window/selected rows, Qwen cache-length causal}', cycles='0', timing='LOW', closure='first trial in flight',
      reopen=[], bench='mask mutant at len-1 / len / len+1'),
 dict(block='norm engine (ot_hbm_norm_engine_view, norm_grp16, su_fused norm hc/q/kv chains)', cls='PARAMETERISE', area_mm2=0.5,
      params='D {5120 DS, 4096 Qwen}; SEG {off, 128} for QK-norm (10 segments a die at TP4); HC_MIX {on DS, off}; OUT {FP8 DS, BF16 Qwen}; GAIN on; eps port (exists)',
      cycles='Qwen RMSNorm ~300-400 -> 150-200 a norm; QK-norm 200-300 -> 100-150 a layer; DS 0 (static mode)',
      timing='MED: engine and grp16 failing/re-running; modes are static config registers decoded off-path',
      closure='failing / re-running; grp8 needs redesign', reopen=[],
      bench='Qwen RMSNorm 4096 BF16 and QK-norm 10x128 vs qwen_r25 segmented tree order; DS norm regression bit-identical'),
 dict(block='RoPE (su_norm q/kv chain) + cos/sin table fetch', cls='PARAMETERISE', area_mm2=0.15,
      params='PAIR {adjacent (DS), split-half i/i+64 (Qwen)}; ROT_DIM {64 tail, 128}; tables are DATA in HBM (theta 1e6 plain / DS plain+YaRN x4), fetched per position over svc kind-1',
      cycles='Qwen 60-120 -> 20-40 a layer; table fetch 512 B/pos (Qwen), ~1 KB (DS) hidden under the layer stream',
      timing='LOW-MED: a 2:1 lane-partner mux on open SU chains', closure='open (SU chains failing)', reopen=[],
      bench='Qwen split-half at pos 0 / 4095 / 8191; DS YaRN regression; table-fetch bench (also closes T3 gap 6: no table producer)'),
 dict(block='softmax (ot_dsrom_su_softmax in the SU)', cls='PARAMETERISE', area_mm2=0.2,
      params='SINK_EN {DS on, Qwen off}; MULTIPASS: pass1 global max, pass2 exp+sum in fixed chunk order with sum carry-in, pass3 scale; NVMAX 40 (640 rows) kept, Qwen 8,192 rows = 13 chunks',
      cycles='Qwen 300-600 -> 150-250 a layer', timing='MED (on failing SU)', closure='open', reopen=[],
      bench='Qwen 8 heads x 8,192 softmax vs qwen_r25 chunk order; sink-on DS regression; negative: chunk-order swap'),
 dict(block='SwiGLU fused chain (ot_dsrom_su_swiglu)', cls='PARAMETERISE', area_mm2=0.05,
      params='OUT {FP8 DS, BF16 Qwen}; CLAMP_EN; ROUTE_W bypass (=1.0 exact)', cycles='Qwen 150-300 -> 40-80 a layer',
      timing='LOW', closure='open', reopen=[], bench='Qwen SwiGLU 3,072/die vs qwen_r25; DS regression'),
 dict(block='hfd_su lane array / hfd_sfu / hfd_su_red / su_full', cls='GENERIC', area_mm2=0.0,
      params='programmable: SU fallbacks for every family, row scale, residual, embedding dequant, argmax merge fallback',
      cycles='see qwen.su_family_model', timing='as DS', closure='hfd_su / hfd_sfu failing; ot_su12_* failing', reopen=[],
      bench='per-program exact benches (Codex W23 plain AR quarter is the vehicle)'),
 dict(block='hfd_su_result_ingress', cls='GENERIC', area_mm2=0.0,
      params='unchanged; optional ROW_SCALE-on-arrival mode deferred (would reopen a closed block for ~80-160 cycles a layer)',
      cycles='0', timing='-', closure='closed (TT era)', reopen=[], bench='-'),
 dict(block='hfd_cmdproc_n/s', cls='PARAMETERISE', area_mm2=0.0,
      params='TW 17 -> 18; NCMD 256 holds the Qwen launch list (36 layer kernels + head); one model image resident at a time',
      cycles='0', timing='LOW', closure='cmdproc_n closed (TT era), cmdproc_s revoked/re-running', reopen=['hfd_cmdproc_n'],
      bench='token ids 131071 / 131072 / 151935, pos 524288 (Codex W21 smoke exists, control only)'),
 dict(block='ot_dshbm_argmax_m', cls='PARAMETERISE', area_mm2=0.0, params='IW 17 -> 18 (vocab <= 262,144); greedy only (non-greedy sampling not claimed by either model)',
      cycles='Qwen argmax merge on the collective select instead of an SU merge (~-500 a token)', timing='LOW (tiny)',
      closure='closed (TT era)', reopen=['ot_dshbm_argmax_m'], bench='tie / lowest-index rule across die shards'),
 dict(block='hfd_mtp (dspark_top) + ot_dshbm_dspark_ctl + ot_hdc_accept', cls='PARAMETERISE', area_mm2=0.0,
      params='TW 18; B {5 DS, 4 Qwen}; PMAX 8; NSLOT; STAGES {3 DS, 1 Qwen DSpark}; MARKOV_EN; UNION_EN (DS experts only)',
      cycles='Qwen verify p=4 shares the weight stream (2.2-2.7x est., tau unmeasured)', timing='MED: hfd_mtp first trial; ctl/accept TT-era closed',
      closure='hfd_mtp first trial; dspark_ctl / accept closed (TT era)', reopen=['ot_dshbm_dspark_ctl', 'ot_hdc_accept'],
      bench='Qwen accept/commit/rollback with negative mutant; DS MTP regression'),
 dict(block='hfd_coll (TU endpoint) + truecredit / owner banked half', cls='PARAMETERISE', area_mm2=0.05,
      params='GROUP {size 4/8/96, member map, owner-order table}; payload length; ops AR / all-gather / argmax-select (18-bit idx) / multicast',
      cycles='Qwen TP4 AR 256 words = 928 ns endpoint (measured ar_matched_p1) + ~0.2 us FEC = ~1,350 cycles', timing='as DS (failing)',
      closure='failing / re-running', reopen=[], bench='TP4 and TP8 AR at 4,096 FP32 vs fixed-order golden; DS TP-96 regression'),
 dict(block='hfd_kvwb_native / dskv_wb', cls='PARAMETERISE', area_mm2=0.073,
      params='LAYOUT {DS ring pos mod WR (WR >= W+PMAX), CKV/IK owner die; Qwen linear [layer][kvhead][K|V][pos][128] FP8}; cache-length register; dead-row rollback',
      cycles='posted (0 exposed) + fence ~30-60 a layer', timing='LOW-MED', closure='dskv_wb_spec failing; slot reserved (R25IMW)',
      reopen=[], bench='append + rollback mutant, both models'),
 dict(block='hfd_host_ingest (+ loader write merge)', cls='PARAMETERISE', area_mm2=0.1,
      params='MODE {DS ROWS/IKEY, Qwen QKV: vLLM NHD pages FP32/BF16/FP8 -> FP8 per-head rows}', cycles='off the token path',
      timing='LOW', closure='failing / re-running', reopen=[], bench='GPU-prefill KV ingest, both layouts, fence negative'),
 dict(block='embedding fetch (svc kind-1 + SU dequant)', cls='PARAMETERISE', area_mm2=0.0,
      params='ROW_BYTES; FMT {DS BF16 row, Qwen INT8 + BF16 row scale}; IDX 18 b', cycles='~0.5k a token (Qwen)', timing='-',
      closure='-', reopen=[], bench='row 151,935 fetch + dequant'),
 dict(block='hfd_quant (actquant)', cls='PARAMETERISE', area_mm2=0.0,
      params='FP8 E4M3 path shared (KV); FP4 index path DS-only (moves to idx_sel under R25I)', cycles='0', timing='-',
      closure='closed (TT era)', reopen=[], bench='-'),
 dict(block='hfd_vm x4 (+ VM8 sub-tiles), mcast/meso/stn/gath stations, relays', cls='GENERIC', area_mm2=0.0,
      params='width-agnostic (2,048-b x lanes); Qwen 4,096 BF16 hidden fits', cycles='activation class +8 stages from the fmt3 SM grid',
      timing='as DS', closure='VM halves failing / flow failures; most stations closed', reopen=[], bench='-'),
 dict(block='hfd_loader, hfd_barrier, hfd_router (dense bypass), serdes slab, host slab, HBM PHY, PLL', cls='GENERIC', area_mm2=0.1,
      params='router: dense layers bypass routing (as the DS shared expert); loader loads either model image', cycles='0',
      timing='as DS', closure='loader failing; router revoked; barrier closed', reopen=[], bench='image load + boot gate'),
 dict(block='hfd_hc x4 (hc_post lanes + Sinkhorn) + HCP unit', cls='DS-ONLY', area_mm2=0.8,
      params='kept; clock-gated idle under Qwen', cycles='0 for Qwen', timing='HIGH (TT -2,696 ps)', closure='failing', reopen=[],
      bench='DS only'),
 dict(block='native indexer: hfd_idx_score x4 + hfd_idx_sel (replaces hfd_index_q placeholder)', cls='DS-ONLY', area_mm2=0.0,
      params='kept; idle under Qwen', cycles='0 for Qwen', timing='MED (first trials)', closure='first trials in flight', reopen=[],
      bench='DS only', note='placed in the mid-channel side bands; must be re-anchored on the fmt3 grid (see die_fit)'),
 dict(block='MoE routing (hfd_router top-k, expert union, expert steering)', cls='DS-ONLY', area_mm2=0.0,
      params='bypass for dense', cycles='0 for Qwen', timing='router FF -69', closure='revoked', reopen=[], bench='DS only'),
 dict(block='compressor / Engram hash + history / candidate merge / DS MTP heads (Markov, 3 stages)', cls='DS-ONLY', area_mm2=0.1,
      params='SU programs + small control; Engram tables are data in HBM', cycles='0 for Qwen', timing='LOW', closure='not on die (T3 gaps 5, 9)',
      reopen=[], bench='DS only'),
]

# ------------------------------------------------------------------ work items (agent-days; deps by id)
WORK = [
 dict(id='W0', item='Owner sign-off: generic mandate replaces P-min where they differ (TW 18 on argmax/dspark_ctl/accept; fused modes)', days=(0, 0), deps=[]),
 dict(id='W1', item='uarch_model + token_path_export qwen_hbm target (+ unified_composition / reprice) for the generic die', days=(3, 4), deps=['W0']),
 dict(id='W2', item='qwen_r25 golden in r25 arithmetic (SM ring/tree, attention chunk8+pairwise, SU vred, segmented norm, chunked softmax, TU owner order) + one quality run', days=(4, 6), deps=['W0']),
 dict(id='W3', item='SM fmt3 to adoption: wide route verdicts, N/S pin re-routes, die network (activation 73->81), DS fmt0-2 regression', days=(4, 6), deps=[]),
 dict(id='W4', item='SU fused modes: norm D/SEG/HC/OUT, RoPE PAIR/ROT, softmax SINK/MULTIPASS, SwiGLU OUT/CLAMP/ROUTE_W; ride the open SU/norm re-runs', days=(10, 14), deps=['W2']),
 dict(id='W5', item='Token width 18: cmdproc, argmax_m, dspark_ctl, accept, hfd_mtp params; 4 small re-routes', days=(2, 3), deps=['W0']),
 dict(id='W6', item='svc multi-PC KV/IK striping + kind-3 write merge; 15 closed segment masters re-routed (shared with the DS indexer)', days=(5, 8), deps=[]),
 dict(id='W7', item='Collective group config TP4/8/96 + argmax select 18 b + Qwen payloads', days=(3, 4), deps=[]),
 dict(id='W8', item='KV write-back layouts + rollback; host ingest Qwen QKV mode; RoPE/embedding table images', days=(5, 7), deps=[]),
 dict(id='W9', item='Program lowering: 22 unresolved Qwen families (618 ops) + re-target the 6 joined families to the fast modes; cmdproc launch list, SM descriptors, SU programs, KV layout, TP4 TU group', days=(12, 18), deps=['W0']),
 dict(id='W10', item='Qwen stage benches at P8191 (one exact stage per layer type + head + MTP accept/rollback), each with a negative mutant', days=(8, 12), deps=['W2', 'W4', 'W6', 'W9']),
 dict(id='W11', item='DS regression benches for every parameterised block in DS mode (bit-identical to the current DS goldens)', days=(4, 6), deps=['W3', 'W4', 'W5', 'W6']),
 dict(id='W12', item='Die: R25G generator variant (r25s + fmt3 wide + indexer re-anchored + MTP/kvwb/ingest/PLL), die views, GRT, clock plan, wire re-price', days=(4, 6), deps=['W3']),
 dict(id='W13', item='Qwen tau on the 6-class blend + DSpark drafter image on r25 + MTP verify/accept bench', days=(4, 6), deps=['W5', 'W9']),
 dict(id='W14', item='Measured composition: Qwen TP4 AR (+TP8 sensitivity), DS delta; publish only measured', days=(2, 3), deps=['W1', 'W10', 'W11', 'W12']),
]

# ------------------------------------------------------------------ Qwen3-8B token model (TP4 basis from qwen_on_r25 PLAN §4)
QW = dict(layers=36, hidden=4096, q_heads=32, kv_heads=8, head_dim=128, inter=12288, vocab=151936, pos=8191)
BW_DIE = 3.80e12            # sustained B/s a die (vehicle A measured 95 % of 4.0 TB/s), qwen_on_r25 PLAN §4
STACK_BYTES = 36e9          # configs/hardware/leading_node_market.json stack_capacity_bytes
STACKS = 4


def qwen_bytes(tp):
    lw = (QW['hidden'] * QW['hidden'] * 2 + QW['hidden'] * QW['kv_heads'] * QW['head_dim'] * 2
          + 3 * QW['hidden'] * QW['inter'])           # q, o, k, v, gate, up, down (INT8 = 1 B a weight)
    layers = QW['layers'] * lw / tp
    head = QW['vocab'] * QW['hidden'] / tp
    kv = QW['layers'] * (QW['kv_heads'] / tp) * QW['pos'] * QW['head_dim'] * 2   # FP8 K + V
    return dict(layers=layers, head=head, kv=kv, total=layers + head + kv)


# exposed serial chain a layer (cycles), qwen_on_r25 PLAN §4 (estimates)
CHAIN_FIXED = dict(all_reduce=(2700, 2700), first_access_attn_tail=(1700, 1700), die_wire=(500, 1000))
SU_FALLBACK = (2000, 3500)  # PLAN §4 "SU programs" term (all families as generic SU programs)

# per-family SU-chain estimates a layer (cycles lo/hi): fallback program vs parameterised fast path
FAMILIES = [
    # family, ops/token, fallback (lo,hi), fast (lo,hi), fast-path block and mode
    ('prenorm (RMSNorm 4096, x2/layer + final)', 73, (600, 800), (300, 400),
     'norm engine D=4096, HC_MIX=off, OUT=BF16, GAIN=on'),
    ('qk_norm (per head 128, gain)', 36, (200, 300), (100, 150), 'norm engine SEG=128 (10 segments a die at TP4)'),
    ('rope (split-half, 128, theta 1e6)', 36, (60, 120), (20, 40), 'rope chain PAIR=split-half, ROT=128, table from HBM'),
    ('roundQ (KV FP8 E4M3)', 36, (40, 80), (10, 30), 'kv chain quant tail (DS kv chain already quantises to FP8)'),
    ('softmax (8 q heads x 8,192 rows)', 36, (300, 600), (150, 250), 'fused softmax SINK=off, MULTIPASS chunked (NVMAX 40 kept)'),
    ('pv_normalize', 36, (30, 60), (0, 10), 'fused into softmax pass 3 / attention tail'),
    ('swiglu', 36, (150, 300), (40, 80), 'fused swiglu OUT=BF16, CLAMP=off, ROUTE_W=bypass'),
    ('residual (x2)', 72, (40, 80), (0, 20), 'fused with the next norm input (dataflow level 5)'),
    ('row_scale_qkv/o/gu/down', 144, (80, 160), (80, 160), 'SU program on arrival (no closed-block reopen)'),
    ('kv_append / kv_fence', 72, (30, 60), (30, 60), 'kvwb LAYOUT=qwen_linear, posted'),
]


def su_terms():
    fb = [sum(f[2][i] for f in FAMILIES) for i in (0, 1)]
    fa = [sum(f[3][i] for f in FAMILIES) for i in (0, 1)]
    ratio = (fa[0] / fb[0], fa[1] / fb[1])
    # scale onto the PLAN's SU term so the fallback reproduces the published P-min estimate
    fast = (SU_FALLBACK[0] * ratio[0], SU_FALLBACK[1] * ratio[1])
    return dict(bottom_up_fallback=fb, bottom_up_fast=fa, ratio=ratio, plan_fallback=SU_FALLBACK, fast=fast)


def qwen_rate(tp, fast, ar_extra=0.0):
    b = qwen_bytes(tp)
    stream = b['total'] / BW_DIE * CLK
    su = su_terms()
    s = su['fast'] if fast else su['plan_fallback']
    fx = [sum(v[i] for v in CHAIN_FIXED.values()) for i in (0, 1)]
    per_layer = (fx[0] + s[0] + 2 * ar_extra, fx[1] + s[1] + 2 * ar_extra)
    if fast:   # fmt3 wide SM: +8 activation wire stages and +1 adapter cycle on 7 dependent SM ops a layer
        per_layer = (per_layer[0] + 7 * 9, per_layer[1] + 7 * 9)
    token_fixed = 5500.0            # embed + head scale + argmax merge + host turn (PLAN §4 residual)
    if fast:
        token_fixed -= 500.0        # argmax merge on the collective's 18-bit select instead of an SU merge
    cyc = (stream + QW['layers'] * per_layer[0] + token_fixed, stream + QW['layers'] * per_layer[1] + token_fixed)
    return dict(tp=tp, bytes_mb={k: round(v / 1e6, 1) for k, v in b.items()}, stream_cycles=round(stream),
                chain_per_layer=[round(x) for x in per_layer], cycles=[round(c) for c in cyc],
                tok_s=[round(CLK / cyc[1], 1), round(CLK / cyc[0], 1)])


def qwen_aggregate(tp=4):
    b = qwen_bytes(tp)
    weights_die = (b['layers'] + b['head']) + QW['vocab'] * QW['hidden'] * 1.0 + QW['vocab'] * 2   # + replicated embedding
    kv_user_die = b['kv']
    cap_users = int((STACKS * STACK_BYTES - weights_die) / kv_user_die)
    kv_bound = BW_DIE / kv_user_die                      # per instance (each die streams its share in parallel)
    su = su_terms()['fast']
    su_bound = (CLK / (QW['layers'] * su[1]), CLK / (QW['layers'] * su[0]))
    return dict(weights_gb_per_die=round(weights_die / 1e9, 2), kv_mb_per_user_die=round(kv_user_die / 1e6, 1),
                capacity_users=cap_users, kv_bound_tok_s=round(kv_bound), su_bound_tok_s=[round(x) for x in su_bound],
                aggregate_estimate_tok_s=[round(min(kv_bound, su_bound[0]) * 0.8), round(min(kv_bound, su_bound[1]))],
                grade='model (KV-stream and SU-occupancy ceilings; SM compute at batch and VM capacity not checked)')


def work_totals():
    tot = (sum(w['days'][0] for w in WORK), sum(w['days'][1] for w in WORK))
    by = {w['id']: w for w in WORK}
    memo = {}

    def finish(i, k):
        if (i, k) not in memo:
            w = by[i]
            memo[(i, k)] = w['days'][k] + max([finish(d, k) for d in w['deps']] or [0])
        return memo[(i, k)]
    crit = (max(finish(i, 0) for i in by), max(finish(i, 1) for i in by))
    path, cur = [], max(by, key=lambda i: finish(i, 1))
    while cur:
        path.append(cur)
        deps = by[cur]['deps']
        cur = max(deps, key=lambda d: finish(d, 1)) if deps else None
    area = sum(b['area_mm2'] for b in BLOCKS)
    return dict(agent_days=tot, critical_path_days=crit, critical_path=list(reversed(path)), block_area_delta_mm2=round(area, 2))


def main():
    live = None
    if '--die' in sys.argv:
        live = die_runs_live()
    su = su_terms()
    rates = {}
    for tp, extra in ((2, -10.0), (4, 0.0), (8, 20.0)):
        rates[f'TP{tp}'] = dict(p_min_fallback=qwen_rate(tp, False, extra), generic_fast=qwen_rate(tp, True, extra))
    mtp = dict(speedup=(2.2, 2.7), basis='qwen_on_r25 PLAN §5 DSpark p=4 estimate; tau NOT measured on the 6-class blend',
               tok_s_tp4=[round(rates['TP4']['generic_fast']['tok_s'][0] * 2.2), round(rates['TP4']['generic_fast']['tok_s'][1] * 2.7)])
    ds = dict(ar_tok_s=1716.3, mtp_tok_s=3700.3, ar_cycles=699175.7, source='results/arch/token_path_20261008/hbm_ds.json',
              critical_sm_ops=343,
              generic_delta_cycles=dict(fmt3_adapter_if_not_bypass_matched=343, fmt3_activation_stage_growth_worst=343 * 8,
                                        modes_static=0),
              ar_tok_s_worst=round(CLK / (699175.7 + 343 * 9), 1))
    rec = dict(
        schema='opentallas.hbm-generic-plan.v1', stream='hbm-generic', date='2026-10-09', clock_hz=CLK,
        grade='planning estimate; no measured rate; no RTL edited; no route launched',
        reticle=RETICLE, die_fit=dict(runs=[dict(zip(('name', 'variant', 'mm2', 'W_um', 'H_um', 'overlaps', 'note'), r))
                                           for r in DIE_RUNS], live=live),
        qwen=dict(shape=QW, su_family_model=dict(families=[dict(family=f[0], ops_per_token=f[1], fallback=f[2], fast=f[3],
                                                                    fast_path=f[4]) for f in FAMILIES], **su),
                  chain_fixed=CHAIN_FIXED, rates=rates, mtp=mtp, aggregate_tp4=qwen_aggregate(4),
                  references=dict(vehicle_a_tp4_measured=2154.2, vehicle_a_dspark=5055.0, qwen_rom_tp4_priced=5492.7,
                                  qwen_rom_tp8a_modelled=6586.9, qwen_rom_tp4_aggregate=25362)),
        ds=ds, blocks=BLOCKS, work=WORK, work_totals=work_totals())
    (HERE / 'plan.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(su=su, rates={k: {kk: (vv['cycles'], vv['tok_s']) for kk, vv in v.items()} for k, v in rates.items()},
                          mtp=mtp, agg=rec['qwen']['aggregate_tp4'], ds=ds['ar_tok_s_worst'], work=work_totals(), live=live), indent=1))


if __name__ == '__main__':
    main()
