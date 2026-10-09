# One generic HBM accelerator die for Qwen3-8B and DeepSeek-V4.1 Flash (stream hbm-generic, 2026-10-09)

This is a planning and sizing pass:
- No RTL was edited and no route was launched.
- Every rate below is an **estimate**, composed from the cited records. None of it may be published as a result (owner rule: measured composition only).
- The die figures were produced by `tools/hbm_accel_die_fp.py` at origin/main `7dc926e71`. They are reproducible with `python3 results/arch/hbm_generic_20261009/gen.py --die`.
- The machine-readable record is `plan.json`, written by `gen.py`.

Inputs:
- `results/arch/qwen_on_r25_20261008/PLAN.md` (P-min);
- `results/arch/coverage_20261008/T3.md`, `T4.md`;
- the Codex AR family inventory `results/rtl/qwen_r25_su_stage_20261009/ar_family_inventory/inventory.json` (467a3964f: 871 ops, 253 joined in 6 families, 618 unresolved in 22);
- `review_queue/{qwen_hbm_unify, qwen_r25_fmt3, hbm-indexer, mtp-die, ingest, hbm-system}.md`;
- REVIEW_20261009 V11 (fmt3 +10.07 mm²);
- mtp-die.log;
- `/api/elements` (375 rows, read 2026-10-09);
- `results/arch/token_path_20261008/hbm_ds.json`;
- `results/arch/qwen_tp8_vs_sysdie_20261009/result.json`.

## 0. Answer

**Yes, it is feasible.**

**The die fits.** r25s, plus the fmt3 widened 3×3 SM grid, plus the native indexer, MTP, KV write-back, ingest and PLL slots, measures:
- **798.49 mm²**, 31.73 × 25.16 mm;
- 59.5 mm² under the 858 mm² reticle;
- H margin 0.84 mm, W margin 1.27 mm.

The fmt3 grid trades width for height (r25: W +1.14 mm, H −0.57 mm). So the generic die is *lower* than r25s's 25.73 mm, the height that had been the binding limit.

**Qwen3-8B runs every op family on a hardware fast path or an exact SU fallback.** The rigid DS fast paths become static mode registers:
- norm D / segment / HC-mix / output format;
- RoPE pairing and rotary dimension, with tables kept as HBM data;
- softmax sink and multi-pass;
- SwiGLU output, clamp and route weight;
- SM weight format 3 (INT8);
- token width 18;
- collective group size;
- KV layout.

**Cost and rate:**

| | |
|---|---|
| Work | ~70–103 agent-days |
| Critical path | ~24–35 days (golden → SU modes → Qwen stage benches → composition) |
| Re-closures | rides the SU / norm / collective / front_c re-runs already in flight, plus small re-routes of 6 TT-era-closed control masters and the 15 closed svc segments. The DS indexer needs the svc re-route anyway. |
| Qwen TP4 AR | **~1,325–1,390 tok/s per user** (P-min fallback-only: 1,236–1,335) |
| Qwen with DSpark p = 4 | ~2,900–3,750 (τ not yet measured) |
| DeepSeek | unchanged within ≤ 0.45 % (1,716.3 → ≥ 1,708.8 AR worst case) |

**What Qwen loses:**
- About 35–40 % against the specialised Qwen HBM vehicle A (2,154 measured TP4, 421 MiB weight SRAM).
- About 4× against the Qwen ROM (5,492.7 priced TP4).
- The generic die is a **capability** for Qwen, not its headline. The ROM stays the Qwen design.

**Main risks:**
1. The svc single-PC KV read path. Unfixed, Qwen attention runs at ~1/32 bandwidth.
2. Mode logic lands on DS-critical blocks that are failing today (SU, norm, collective, front_c).
3. The fmt3 grid adds 8 activation wire stages and moves the SM groups. The committed indexer anchors collide with it; this is fixable, as shown below.
4. 618 Qwen ops still have no producer. Program lowering is the largest single item.
5. The `qwen_r25` golden needs owner sign-off (FP32 re-association only) and one quality run.
6. τ is unmeasured.

## 1. Block inventory

Classes:
- **GENERIC**: works for both models as-is, at most a program mapping.
- **PARAMETERISE**: a rigid fast path gains static mode registers.
- **DS-ONLY**: kept as an optional engine, clock-gated idle under Qwen.

Closure states come from `/api/elements` on 2026-10-09, under option B. "Reopen" lists closed elements that go back to open.

| Block | Class | Parameters / change | Area Δ | Cycles | Timing risk | Closure state → reopen | Bench / golden |
|---|---|---|---:|---|---|---|---|
| `hfd_sm` ×32 (`smh_front_c/n/s`, `tile_e/w`) | PARAM | FMT {0 BF16, 1 FP8 block-dot, 2 FP4 (DS), **3 INT8→BF16** (Qwen)}; half-line issue; fmt 0–2 latency bypass-matched | **+10.07 mm²** (r25) / +11.34 (r25s); 3×3 grid, W +1.14, H −0.57 mm | +1 a dependent SM op (+2 with the two-stage fallback); activation class 73 → 81 stages | **HIGH**: front_c failing (nominal postCTS ≈ −267 ps); wide one- and two-stage routes in flight | front_c and tiles open/failing; **front_n/s closed → re-route** for the widened pins | fmt3 gate exists (256 codes, ordering, negatives); DS fmt 0/1/2 bit-identical regression |
| `hfd_svc_*` (17 masters ×2) | PARAM | kind-1 KV and kind-2 index-key reads **striped over all 32 PCs** (today one fixed `KV_PC`); kind-3 posted-write merge (dskv_wb strict, then ingest/loader round robin) | ~0.3 | Qwen 8K dense sweep reaches ≥ 90 % BW (one PC ≈ 1/32); DS index keys at full rate | LOW–MED (TT-closed, SS ≈ −200 ps) | **15 closed → re-route** (SE_s6/SW_s4 revoked) | KV-sweep BW bench with a PC-collapse negative; write-merge ACK bench |
| Attention `hfd_attn_half_lo/hi` ×64 (m6h1q quads) | GENERIC | Program mapping (details below) | 0 | KV-bound: 1,325 cycles a layer of KV stream at TP4 | as DS | half_lo first trial, half_hi failing; quads closed; none reopened | Qwen GQA stage at P8191, negative: wrong KV-head map |
| `ot_qwen_r25_causal_mask` | PARAM | MASK {DS window/selected rows, Qwen cache-length} | 0 | 0 | LOW | first trial | len−1 / len / len+1 mutants |
| Norm engine (`norm_engine_view`, `grp16`, fused norm hc/q/kv chains) | PARAM | D {5120, 4096}; SEG {off, 128} for QK-norm; HC_MIX {on, off}; OUT {FP8, BF16}; GAIN; eps port exists | ~0.5 | Qwen RMSNorm 300–400 → 150–200; QK-norm 200–300 → 100–150 a layer; DS 0 | MED (failing / re-running; static config decoded off-path) | open | Qwen RMSNorm 4096 and QK-norm 10×128 vs `qwen_r25` segmented tree; DS regression |
| RoPE (q/kv chains) + cos/sin tables | PARAM | PAIR {adjacent, **split-half i/i+64**}; ROT_DIM {64 tail, 128}; **tables are HBM data** (θ 1e6 / DS plain + YaRN), fetched per position | ~0.15 | Qwen 60–120 → 20–40 a layer; fetch 512 B a position, hidden | LOW–MED | open | pos 0 / 4095 / 8191; DS YaRN regression; table-fetch bench (also closes T3 gap 6) |
| Softmax (`ot_dsrom_su_softmax`) | PARAM | SINK_EN; MULTIPASS (global max, fixed-chunk exp+sum with carry-in, scale); NVMAX 40 kept, so 8,192 rows = 13 chunks | ~0.2 | Qwen 300–600 → 150–250 a layer | MED | open | 8 × 8,192 vs `qwen_r25` chunk order; negative: chunk swap; DS sink regression |
| SwiGLU fused chain | PARAM | OUT {FP8, BF16}; CLAMP_EN; ROUTE_W bypass (= 1.0 exact) | ~0.05 | Qwen 150–300 → 40–80 a layer | LOW | open | Qwen 3,072/die; DS regression |
| `hfd_su` lanes / `hfd_sfu` / `su_red` / `su_full` | GENERIC | Programmable fallbacks: row scale, residual, embedding dequant, argmax merge fallback | 0 | §2 | as DS | failing / re-running | per-program benches (Codex W23 quarter vehicle) |
| `hfd_su_result_ingress` | GENERIC | Unchanged. A row-scale-on-arrival mode is deferred: it would reopen a closed block to save ~80–160 cycles a layer | 0 | 0 | — | closed, kept closed | — |
| `hfd_cmdproc_n/s` | PARAM | TW 17 → 18; NCMD 256 holds the Qwen list; one model image resident | 0 | 0 | LOW | n closed → **reopen**; s revoked/re-running | ids 131071/131072/151935 (W21 smoke) |
| `ot_dshbm_argmax_m` | PARAM | IW 17 → 18; greedy | 0 | Merge on the collective's select: −~500 a token vs an SU merge | LOW (tiny) | closed → **reopen** | lowest-index tie across shards |
| `hfd_mtp` + `dspark_ctl` + `hdc_accept` | PARAM | TW 18; B {5, 4}; PMAX 8; NSLOT; STAGES {3, 1}; MARKOV_EN; UNION_EN | 0 | Qwen verify p = 4 shares the weight stream | MED | hfd_mtp first trial; ctl and accept closed → **reopen** | Qwen accept/commit/rollback with mutant; DS regression |
| `hfd_coll` (+ truecredit, owner half) | PARAM | GROUP {4/8/96, member map, owner order}; payload length; AR / AG / argmax-select (18 b) / multicast | ~0.05 | Qwen AR ≈ 1,350 cycles (928 ns measured endpoint + FEC) | as DS (failing) | open | TP4/TP8 AR at 4,096 FP32; DS TP-96 regression |
| `hfd_kvwb_native` / `dskv_wb` | PARAM | LAYOUT {DS ring, WR ≥ W + PMAX, owner die; Qwen linear `[l][kvh][K\|V][pos][128]` FP8}; cache-length register; dead-row rollback | 0.073 (slot) | posted + fence 30–60 a layer | LOW–MED | dskv_wb_spec failing | append + rollback mutants, both models |
| `hfd_host_ingest` | PARAM | MODE {DS ROWS/IKEY, Qwen QKV NHD → FP8 per-head rows} | ~0.1 | off-path | LOW | failing | ingest per layout, fence negative |
| Embedding fetch | PARAM | ROW_BYTES; FMT {BF16, INT8 + BF16 scale}; IDX 18 b | 0 | ~0.5k a token (Qwen) | — | — | row 151,935 |
| `hfd_quant` | PARAM | FP8 path shared (KV); FP4 index path DS-only (moves to idx_sel) | 0 | 0 | — | closed, kept | — |
| `hfd_vm`, stations, relays, mcast/meso/gath | GENERIC | Width-agnostic | 0 | +8 activation stages (fmt3 grid) | as DS | mixed | — |
| loader, barrier, router (dense bypass), SerDes, host, PHY, PLL | GENERIC | Router bypassed for dense layers (as the DS shared expert); loader loads either image | ~0.1 (PLL) | 0 | as DS | loader failing; router revoked | image load + boot gate |
| `hfd_hc` ×4 + HCP unit | DS-ONLY | hc_post, Sinkhorn | ~0.8 (HCP) | 0 for Qwen | HIGH (TT −2,696) | failing | DS only |
| Native indexer: `hfd_idx_score` ×4 + `hfd_idx_sel` | DS-ONLY | Replaces the `hfd_index_q` placeholder | 0 W/H | 0 | MED | first trials | DS only |
| MoE routing, expert union/steering | DS-ONLY | Dense bypass | 0 | 0 | — | router revoked | DS only |
| Compressor, Engram hash/history, L20 candidate merge, DS MTP heads | DS-ONLY | SU programs + small control; Engram tables are HBM data | ~0.1 | 0 | LOW | not on die (T3 gaps 5, 9) | DS only |

Attention mapping detail (GENERIC row):
- GQA uses one KV head a tile, with 4 of 16 head lanes busy at AR and 16 at DSpark p = 4.
- head_dim 128 runs as two 64-wide slices.
- The cache-length mask uses the pad bit.
- Rejected: a per-lane KV group select. It would reopen the closed quads for no gain while attention is KV-bound.

**Totals.** Area deltas sum to ~12.5 mm² on r25 basis: fmt3 10.07, plus ~2.4 of mode logic and slots.
- Only fmt3 changes the outline.
- The rest sits inside existing masters or the spine and side-band slots.
- The DS-ONLY share of the die (hc 12.2 + indexer ~25 + router and misc ~1) is ~38 mm², about 4.8 % of the die.

**Closed blocks that reopen:**
- `smh_front_n/s` (pins);
- `cmdproc_n`, `argmax_m`, `dspark_ctl`, `hdc_accept` (TW 18; tiny, ~1–2 h routes each);
- 15 svc segment masters (PC striping, shared with DS).

Everything else rides blocks that are already open or failing.

**Change from P-min (owner decision 10-09).**
- P-min kept argmax, dspark_ctl and accept closed, using SU programs, and ran norm, softmax, SwiGLU and RoPE as SU programs.
- The "genuinely generic" mandate parameterises those fast paths instead.
- P-min remains the zero-reopen fallback for each one.

## 2. Per-model token path on the generic die

### Qwen3-8B, TP4, P8191, AR, batch 1

Basis: `qwen_on_r25` §4.
- Bytes a die: 2,043 MB, so **645k stream cycles** at 3.80 TB/s.
- Exposed serial chain a layer: 2 all-reduces at 2,700, first access plus attention tail 1,700, die wire 500–1,000, plus the SU term.

| Family (Codex inventory) | Ops | Fast path on the generic die | SU fallback (P-min) | Cycles a layer: fallback → fast |
|---|---:|---|---|---|
| qkv, o, gu, down | 144 | SM fmt3 INT8 (stream-bound) | fmt0 BF16-widened image (2× bytes; bring-up) | stream |
| row_scale_qkv/o/gu/down | 144 | SU program on arrival (no reopen) | same | 80–160 → 80–160 |
| prenorm (RMSNorm ×2 + final) | 73 | norm engine D4096 / HC off / BF16 | SU vred + rsqrt | 600–800 → 300–400 |
| QKnorm | 36 | norm engine SEG 128 | SU segmented reduction | 200–300 → 100–150 |
| RoPE | 36 | RoPE chain split-half / 128 | SU XOR-64 lane offsets | 60–120 → 20–40 |
| roundQ (KV FP8) | 36 | kv-chain quant tail | SU program | 40–80 → 10–30 |
| attention_qk / attention_pv | 72 | attention tiles, GQA mapping | — | KV stream (1,325) + tail |
| softmax | 36 | fused SINK off, MULTIPASS | 3-pass SU | 300–600 → 150–250 |
| pv_normalize | 36 | fused in softmax pass 3 | SU divide | 30–60 → 0–10 |
| SwiGLU | 36 | fused OUT BF16 / CLAMP off / ROUTE_W bypass | SU program | 150–300 → 40–80 |
| residual | 72 | fused into the next norm input | SU add | 40–80 → 0–20 |
| all_reduce_o / all_reduce_down | 72 | TU TP4 group, 256 words | same | 2,700 |
| kv_append / kv_fence | 72 | kvwb Qwen layout, posted | same | 30–60 |
| embedding | 1 | svc row fetch + SU dequant | same | ~0.5k a token |
| head + head_scale | 2 | SM fmt3 (155.6 MB a die streamed) | BF16-widened | in stream (+49k) |
| argmax_local / merge / gather | 3 | argmax_m IW 18 + collective 18-bit select | per-die 17-bit + SU merge | −~500 a token |

SU term: P-min 2,000–3,500 a layer, against **954–1,641** for the fast paths. The ratio 0.47 comes from the bottom-up family sums.

| Qwen | Cycles a token | tok/s per user | vs P-min |
|---|---:|---:|---:|
| TP4 P-min (all SU fallbacks) | 899k–971k | 1,236–1,335 | — |
| **TP4 generic (fast paths)** | **863k–906k** | **1,325–1,390** | +4–7 % |
| TP4 + DSpark p = 4 (τ unmeasured; 2.2–2.7×) | — | ~2,900–3,750 | — |
| TP2 generic (half the silicon) | 1.51M–1.55M | 774–796 | — |
| TP8 generic (scale-out sensitivity, +20 cycles an AR) | 542k–585k | 2,052–2,214 | — |

**Aggregate, TP4 instance (model):**
- Weights 2.51 GB a die; KV 151 MB a user a die; capacity ~937 users at 36 GB stacks.
- KV-stream ceiling ~25.2k tok/s; SU-occupancy ceiling 20–35k.
- Central estimate **~16–25k tok/s an instance**, against the Qwen ROM TP4's 25,362 (tile-window bound).
- SM compute at batch and VM capacity are not checked.

**Lost against the specialised designs:**
- Against **vehicle A** (Qwen HBM tile die, 421 MiB SRAM, measured 2,154 TP4, 5,055 with DSpark), the generic die is −35 to −40 % AR.
  - The cause is structural: no weight SRAM, so the head streams (+49k cycles) and no 22 MB window hides the serial chain (~250–320k → ~215–260k with the fast paths).
  - Weight SRAM for the head alone (~300 mm²) does not fit.
- Against the **Qwen ROM** (5,492.7 TP4; 6,586.9 TP8-A), it is ~4× lower per user.
- The fast paths win only 4–7 %. The weight stream (645k) dominates, so the parameterisation is about coverage and exactness more than rate.

### DeepSeek-V4.1, TP-96, 1M

Unchanged: AR 1,716.3, MTP 3,700.3 (priced candidates).
- All modes are static. DS runs fmt 0–2, D5120, HC on, FP8 out, adjacent RoPE and sink on, all bit-identical to today.
- Worst-case cost: +1 adapter cycle on the 343 critical SM ops if fmt 0–2 are not bypass-matched, plus +8 activation stages each from the fmt3 grid. That is ≤ +3,087 cycles, **≤ 0.45 %**: 1,716.3 → ≥ 1,708.8.
- Gains: DS also gets the RoPE table producer (T3 gap 6), multi-PC index-key reads (needed by the native indexer) and the write path (T3 gap 3) from the shared svc work.

## 3. Die replan

| Variant (generator, `7dc926e71`) | mm² | W × H (mm) | Overlaps |
|---|---:|---|---:|
| r25 (adopted) | 753.19 | 30.59 × 24.62 | 0 |
| r25s (attention split) = r25sm (+ MTP, loader) | 787.15 | 30.59 × 25.73 | 0 |
| r25 + fmt3 wide (reproduces Codex 763.26) | 763.26 | 31.73 × 24.05 | 0 |
| r25s + fmt3 wide | 798.49 | 31.73 × 25.16 | 0 |
| r25s + R25M + R25IQG (as committed) | 787.15 | 30.59 × 25.73 | **1**: `idx_selector` × `hb_su_full` |
| … + fmt3 wide (as committed) | 798.49 | 31.73 × 25.16 | **5**: `idx_score_SW/NW` × SW/NW SM groups, + selector |
| **R25G candidate**: the above, with indexer anchors rebased by the cx shift (+571.968 µm) and the selector moved above `hb_su_full` (y 17,244.72) | **798.49** | **31.73 × 25.16** | **0** (geometry-only) |

**Findings:**
1. **≤ 858 mm² and H ≤ 26 mm both hold.** The margins are 59.5 mm², H 0.84 mm and W 1.27 mm.
2. **The committed indexer topology is r25-absolute and needs rebasing.**
   - `tools/hbm_indexer_die_topology.py` hard-codes `x = 10,732.608 / 16,994.88` for the scorers and `(14,164.416, 17,169.84)` for the selector.
   - Under fmt3 the SM groups widen by 572 µm, and the scorers overlap 4 SMs.
   - Under r25s the hub shifts, and the selector overlaps `hb_su_full`.
   - Rebased, both fit, with ~2.4 mm of free mid-channel on each side of the spine for a 2.0 mm scorer.
   - The fix is generator-only (indexer / mtp-die owners).
3. **`--ds-var r25imws` fails to import on main.** `hbm_mtp_native_contract.stop_model` is missing (memory `head-can-fail-to-import`).
4. **Mode logic (~1.5 mm² of cells) goes inside the existing SU quarters and the spine.** Hub-quarter utilisation must be confirmed. Even a +5 mm² growth of the quarters (W) leaves ~55 mm².
5. **Worst case.** If the indexer side bands fail GRT, Alternative B (column taps) keeps W, or a scorer column costs ~0.9 mm of W. That gives ~821 mm² at W 32.6 mm, which still fits.
6. **A companion die for the DS-only engines is not recommended.**
   - It would save ≤ 38 mm² on a die that already fits.
   - It would put the per-layer HC/Sinkhorn (80 instances a token) and the stack-adjacent indexer key stream (8.7 kb/cycle a stack) on a die crossing. That costs DS latency for no Qwen gain.
   - It remains the structural option only if fmt3 has to fall back to the SM3 reference geometry plus something larger. The SM3 reference is 777.6 mm², 20 mm² less.

**Not in the die:**
- weight SRAM;
- a direct TP4 ring;
- a D4096 second norm master;
- a per-lane GQA select.

The rejections in P-min stand.

## 4. Array replan

One die type and one switch fabric: the Tomahawk Ultra tier, our protocol, owner-reduces in fixed order, switch multicast.
- Group membership is `hfd_coll` configuration: group ID, size, member map and owner-order table.
- The per-die SerDes slab (18 mm², 9 `ot_pdie_serdes`) is unchanged.

| | DeepSeek-V4.1 | Qwen3-8B TP4 (headline) | Qwen TP8 (sensitivity) | Qwen TP2 |
|---|---|---|---|---|
| Dies an instance | 96 (TP-96) | 4 | 8 | 2 |
| HBM stacks | 384 | 16 | 32 | 8 |
| Collectives a token | AR / AG per layer, 96-die argmax select, Engram gathers ×4, L20 candidate merge, MTP draft broadcast | 2 AR a layer (4,096 FP32 = 256 words, ~1.13 µs) + argmax select over 4 | same, +20 cycles an AR | same, 2 endpoints |
| Weights a die | DS share (FP8/FP4) + Engram rows as HBM data | 2.51 GB INT8 (embedding replicated) | 1.57 GB | 4.41 GB |
| Per user | 1,716 AR / 3,700 MTP | ~1,325–1,390 AR | ~2,050–2,210 | ~775–795 |

**Mixed deployment:**
- A switch domain is partitioned at boot into DS pods of 96 dies and Qwen groups of 4 or 8 dies. One 96-die pod = 1 DS instance or 24 Qwen TP4 instances.
- Isolation uses collective group IDs plus per-group switch multicast entries. No traffic crosses groups.
- Repartitioning means a weight and program reload through `hfd_loader` (Qwen 2.5 GB a die) and a cmdproc image swap. The time is in seconds, which is not on the token path.
- Rule: a DS pod's 96 dies must sit within one TU tier, as today. Qwen groups take the remaining ports.
- TP8 needs no fabric change. On the ROM board, TP8 needed a K4 board, but here every die already reaches the switch.

## 5. Work estimate (agent-days; `plan.json` `work`)

| ID | Item | Days | Depends on |
|---|---|---:|---|
| W0 | Owner sign-off: the generic mandate replaces P-min where they differ | 0 | — |
| W1 | uarch_model + `token_path_export` `qwen_hbm` + unified composition / reprice | 3–4 | W0 |
| W2 | `qwen_r25` golden (r25 orders, incl. segmented norm and chunked softmax) + one quality run (~2.2 GPU-h) | 4–6 | W0 |
| W3 | fmt3 to adoption: wide route verdicts, N/S pin re-routes, die network 73 → 81, DS regression | 4–6 | — (in flight) |
| W4 | SU fused modes: norm, RoPE, softmax, SwiGLU (on the open SU/norm re-runs) | 10–14 | W2 |
| W5 | TW 18: cmdproc, argmax_m, dspark_ctl, accept, hfd_mtp params + 4 small re-routes | 2–3 | W0 |
| W6 | svc multi-PC KV/IK striping + kind-3 write merge; 15 segment re-routes (shared with DS) | 5–8 | — |
| W7 | Collective groups TP4/8/96 + 18-bit argmax select | 3–4 | — |
| W8 | KV write-back layouts and rollback; ingest Qwen QKV; RoPE and embedding table images | 5–7 | — |
| W9 | **Program lowering**: 22 unresolved families (618 ops) + retarget the 6 joined families to the fast modes; launch list, SM descriptors, SU programs, KV layout, TU group | 12–18 | W0 |
| W10 | Qwen stage benches at P8191 (one per layer type + head + MTP accept/rollback), each with a negative mutant | 8–12 | W2, W4, W6, W9 |
| W11 | DS regression benches for every parameterised block in DS mode | 4–6 | W3, W4, W5, W6 |
| W12 | R25G generator variant (rebased indexer) + die views, GRT, clock plan, wire re-price | 4–6 | W3 |
| W13 | Qwen τ on the 6-class blend + DSpark drafter on r25 + verify/accept bench | 4–6 | W5, W9 |
| W14 | Measured composition: Qwen TP4 (+TP8), DS delta | 2–3 | W1, W10, W11, W12 |

**Total: 70–103 agent-days.**

**Critical path: W0 → W2 → W4 → W10 → W14, 24–35 days.** W9 runs in parallel at 12–18 days and is the next-longest chain into W10.

**ETA impact on the HBM target:**
- **DS.** Little new work lands on its path: the svc striping and write path are needed anyway, and TW 18 and fmt3 are already in flight.
  - The real risk is that SU/norm/coll/front_c mode logic slips the closure of blocks that are DS-critical and already failing.
  - Mitigation: modes ride as default-off parameters in successor variants, and DS adopts the current variant if the moded one does not close first.
  - Expected DS slip: **0 to +1 week**.
- **Qwen-on-HBM.** First exact token in ~4–5 weeks; a measured composition in ~5–6 weeks with ~6 parallel streams.

## 6. Feasibility and risks

**Yes.**
- One die at 798.5 mm² (≤ 821 worst case), H 25.16 mm, runs both models.
- Every Qwen op family has a hardware fast path or an exact SU fallback.
- DS loses ≤ 0.45 %.

Risks, ranked:
1. **svc KV read path (both models).** Kind-1 KV reads use one fixed PC a stack. Qwen's 8K dense sweep cannot meet the ≥ 90 % rule without striping, and the DS indexer needs the same change for kind-2. It reopens 15 closed segment masters. Do it first (W6).
2. **Mode logic on failing DS-critical blocks:** front_c (fmt3), norm engine, SU chains, coll. Keep every mode a static, registered config decoded off the datapath, with fmt 0–2 latency bypass-matched. Gate each with a DS bit-identical regression (W11).
3. **fmt3 geometry.** It costs +10–11 mm², +8 activation stages, and SM-group movement that breaks the committed indexer anchors (fixable; rebased geometry shown). The die network is not yet qualified (geometry-only).
4. **Program lowering scale.** 618 of 871 Qwen ops have no producer. This is the largest item, and only the control smoke (W21) exists.
5. **Golden and quality.** `qwen_r25` changes Qwen's reference order (FP32 re-association, segmented norm, chunked softmax). It needs owner sign-off plus one quality run.
6. **Qwen rate.** The generic die is ~35–40 % below vehicle A and ~4× below the Qwen ROM. MTP is the main lever, and τ is unmeasured.
7. **Open DS gaps are not closed by this plan:** HC/Sinkhorn on die, the expert-dispatch ≥ 90 % rule, PLL and reset, Engram and compressor placement (T3).

Owner decisions requested: `/home/ubuntu/claude-takeover-20261007/review_queue/hbm-generic.md`.
