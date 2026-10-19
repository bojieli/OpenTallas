# HBM-MTP deliverable 2: the P = 2 next HBM die, design spec and RTL plan (2026-10-18)

This is a design study for the die after d4g GEN2. It sits outside the release closure: the d4g GEN2 die, its kits and the release files are not touched. It runs on its own branches (`claude/hbm-mtp-*`) at normal or low fleet priority.

**Owner decision (10-18 ~20:30):** P = 2. The coordinator added full lanes, so the matrix lanes and the multi-query attention lanes are both in scope.

**Status:** this is a spec and a plan. **No production RTL is written until the owner gives the go.**

Inputs:
- D1 (`README.md`, `summary.json`, `model/`, `sm_area/`, `stats/`, on claude/hbm-mtp-next-1018@043140ff1);
- the d4g GEN2 plan, grants and geometry on main (`results/arch/hbm_die_d4g/plan/d4g_phy`, `grants_d4g.json`);
- two new P = 2 model runs made for this plan (`d2/p2_ablation.json` and `d2/p2_extra.json`, ot-epyc5). Both use the unchanged D1 model `tools/hgi_sim/hbm_plane_model.py`, and the base P = 2 point reproduces D1's 3,142.8 tok/s exactly.

Three terms recur:
- **P** is the number of physical lanes: accumulator lanes per SM MAC column, and query lanes per SM attention engine.
- **N** is the row count an ISA record carries. N is independent of P. DS MTP verify uses N = 6, which is DSpark gamma 5 plus 1. At P = 2, the SM therefore makes ceil(6/2) = 3 lane passes over each weight stream, while every non-SM unit runs one N = 6 record.

## 1. Expected throughput at P = 2

DS = DeepSeek-V4.1 on the d4g price of record:
- DS AR is 1,905.4 tok/s.
- DSpark tau is 4.159.
- The KV top-512 overlap uses the upper bound, the expert union uses the measured MTP-STATS mean, and the clock is 1.2 GHz.

| configuration | added die mm² (measured SM + estimates) | DS MTP tok/s | vs P=1 die (1,694) | DS 2-user agg. tok/s | notes |
|---|---:|---:|---:|---:|---|
| P = 1, the d4g die as built | 0 | 1,694.3 | 1.00x | 1,905.4 (1 user) | MTP is slower than AR on the die as built |
| **Phase A**: row field on every non-SM unit; no SM or attention lanes; VM as built | ~0.4 | **2,393.2** | 1.41x | n/a | no SM change |
| **Recommended P = 2**: full lanes plus the row field; VM as built (columns swapped) | ~33.7 cells, ~29.5 die (frame F-A) | **3,071.0** | 1.81x | 2,927.1 | union p90 bracket: about -2.5% |
| P = 2 plus VM growth (6 resident verify columns, +150k words) | 34.56 (D1) | 3,142.8 | 1.85x | 3,060.3 | +2.3% MTP and +4.5% multi-user for a hub SRAM change; **deferred** (see §3.9) |
| P = 2 with gamma 1 (N = 2, one pass) | same | 2,302.7 | 1.36x | n/a | the compiler keeps gamma 5 at P = 2 |

**Throughput per die mm².** The recommended P = 2 die gives 3,071 / ~671 mm² = **4.58 DS MTP tok/s per mm²**. The current die gives 2.64 for MTP and 2.97 for AR.

**Qwen3-8B (D1 model, QCHK-corrected 7bc2156cd).**
- Multi-user aggregate at P = 2 is 1,734 tok/s, against 946 for AR.
- DFlash b16 at P = 2 is 874 tok/s with the published tau (8.01) and 399 with the measured tau (3.656); b8 published is 1,212.
- QCHK (7bc2156cd) fixed the DFlash record-size/head-pass choice. DS rows are unchanged. DFlash stays below AR at P = 2 (a step costs 3.1–5.2 AR steps), so for Qwen the P = 2 die is a multi-user gain, not a DFlash gain.

**What each feature buys at P = 2.** The table shows the DS MTP verify cycles each feature saves per step, measured by removing that feature alone (`d2/p2_ablation.json`).

| feature | verify cycles saved | DS MTP without it | share of the P = 2 gain |
|---|---:|---:|---:|
| SM lanes (matrix and attention) | 405,502 | 2,503.5 | largest |
| HC rows (HC_MIX + 3 Sinkhorn) | 269,656 | 2,686.6 | 2nd, **model-basis risk, see M2** |
| FUSED rows (HC pre-norm / post) | 201,983 | 2,788.2 | II measured (P6 RTL) |
| ATT multi-query lanes | 177,387 | 2,827.0 | needs exactness gate E1 |
| COLL rows | 163,567 | 2,849.4 | |
| IDX rows (index queries, top-k, union) | 63,743 | 3,021.6 | |
| SU / DMA / QDQ / ARGMAX rows | 37,631 | 3,070.1 | small, but the same row-counter mechanism |
| VM growth | 37,140 | 3,071.0 | deferred |

**Unit occupancy.** In the P = 2 verify, the SM is busy 591.7k cycles and COLL 586.3k. COLL is now almost co-critical, and its load does not fall at higher P (586k at P = 6). The next lever after P = 2 is therefore COLL, not more SM lanes.

## 2. Mechanisms (all statically scheduled; no flow control is added on the die)

- **The record header carries a row count N** (4 b, N ≤ 16), plus a per-row descriptor stride for each operand.
  - The unit runs setup once, then N rows at its II.
  - Row r runs at POS = POS0 + r, and the compiler places every row's issue cycle.
  - No unit acquires a ready/valid interface.
- **SM lanes.** Each HBM weight word (BDC line) is broadcast to 2 accumulator lanes.
  - Each lane is an unmodified copy of the production column, so it keeps the golden reduction order exactly (D1: bit-exact at P = 1 to 8).
  - The HBM bandwidth (99 B/cycle/SM), the PHY, SM_HBM, SM_X and SM_OUT are unchanged.
- **Lane addressing without new pins.** The SM front holds an "x target lane" and a "result lane" register, set from the SM.MATVEC slot field (HGI-1 spec 6.7, param [4:2]).
  - x-write beats go to lane p's x-store copy. They still use the same 2,048-b xw beat, taking P times the beats.
  - Results are published lane-major on the unchanged rv/rrow/rdata port; the consumer knows the order from the static schedule.
  - **The SM column pin set is therefore unchanged**, and only its geometry changes.

## 3. Per-unit spec

### 3.1 SM matrix column x2 (owner H-SM; HF-5 owns the release SM tile)

- **Leaf.** Each leaf holds 2 copies of the **closed** block-dot column view (`smh_bdc_ref_p50`, 112.32 x 142.56 um), 2 copies of the BF16 column (closed `tcl` / `tcl_gu` + `tct` views) and 2 x stores (`xs`).
  - Between them sits a registered weight/control broadcast: one extra flop stage per lane, duplicated at the source, so fan-out is 2.
  - Using hard copies instead of a flat `bdc_p2` gives up the ~2k shared flops: a lane costs 1.0 column instead of 0.89, about +0.9 mm² on the die. In exchange, every MAC datapath stays a closed view.
- **Measured cost per lane** (MTP-AREA): block-dot +6,404 um² of cells, BF16 column +15,700 um², x store +15.6k um² of SRAM. Per die at P = 2 that is 7.3 + 18.0 + 8.0 = 33.3 mm².
- **Timing.** At P = 2 there is no new logic depth (synthesis WNS is the same at P = 1 and P = 8).
  - The tcc shared valid/first net reaches 2.2 ns unbuffered at P = 2. It must come from per-lane duplicated source flops, not from one net.
  - The +1-cycle broadcast tree is needed only at P ≥ 4.
- **x load.** A pass loads x for 2 positions: 2 x 13 = 26 beats per SM fragment, against 13. The 128-row x store is double-buffered so the load hides under the weight stream. **Not priced yet: M1.**
- **Front and back end** (`ot_smh_static_front`, `ot_hbm_accel_smh_be*`):
  - the lane registers, the slot-field decode and the lane-major result order (a per-lane gather tag bit);
  - the record's pass loop: ceil(N/P) passes, each pass re-reading the weight line from HBM, priced in the model as max(1, ceil(N/P)/1.374) of the line time.

### 3.2 Multi-query attention (option B attention on the SM engines; owner H-SM attention, HF-5 cluster)

- **KV-line-stationary operation.** Each KV line (K and V) is streamed once per record. It carries a 2-bit lane mask: the union of the 2 lanes' top-512 selections plus each lane's own 128-line window (window lines exact, positions p and p+1).
- **Per lane:** QK through the BF16 column lane, online-softmax state (max and sum), and PV accumulation. Each lane has its own copy of `pvacc` / `pv_merge`, `sum_capture` and the q / partial store (`pstore`).
- **Shared spans, paid once per record:** first access, dispatch, publish and the cross-SM merge.
- **Masking.** A masked line leaves a lane's state untouched, which is exact.
- **Exactness gate E1.** Each lane must see its own selected lines in the golden order.
  - That holds if the union is streamed in ascending line index and the golden (and the P = 1 RTL) reduce in ascending index order.
  - If the golden reduces in top-k (score) order, the shared stream does not reproduce that order for both lanes. Then the ATT feature is dropped: -177k cycles, giving 2,827 tok/s at P = 2. No reordering is ever accepted (AGENTS level-6 rule).
- **Window ring.** DMA.KVWB_DS appends both rows before the attention rows, so the ring grows to 256 slots (+128 HBM rows a layer). There is no ISA change: O.m = B.m = 256.

### 3.3 FUSED / norm rows (owner H-SU, FUSED on the LL lanes of the SU slices)

- **What changes:** FUSED.HC_PRE_NORM and HC_POST take N rows. Gain sectors are held across rows. Two r slots let row p+1's phase A overlap row p's csum/rsqrt tail. Each row has its own scalar set (PRE 4 words, POST 20 words).
- **Evidence:** the RTL already exists and is measured. P6 RTL 8fe5d18bd, in `results/arch/hbm_mtp_1015/p6_rtl_2330`, gives II 197.
- **Area:** about 0.1 mm² of flops across the 16 SU slices.
- **FUSED.QDQ:** the quantiser takes rows at n/32.

### 3.4 HC mix and Sinkhorn (owner HC, `ot_hbm_hc_eng_static`, `ot_hbm_hc_q_static` x4)

- **What changes:**
  - HC.HC_MIX streams N h rows against stationary mix weights (the HCP x6 mode, measured II 250).
  - 2 more `ot_hdc_sinkhorn` units are added (16 quotient paths and a 512-entry seed each, ~0.06 mm² each), so the Sinkhorn II is 634/3 and stays below 250.
  - SU pre/post rows are added, and the HC_q quadrant clients get the row counter.
- **Model-basis risk M2.** The model prices HC rows at II 250, the HCP W256 measured x6 mode.
  - The static HC engine itself (codex/hc-static-engine-1014 a35449ada, 128 MAC lanes) measured 9,554 cycles for P1 and 31,481 for P6. That is a further-row II of **4,385**, and its P1 is 8.2x the 1,160-cycle price.
  - If the die's HC engine is that engine, most of the 270k-cycle HC row gain is not real.
  - This must be resolved before any HC RTL: which engine is bound in GEN2, and what its row II is.

### 3.5 SFU / SU programme (owners H-SU, H-ELEM-B)

- **What changes:**
  - SU.VOP takes a row counter, for both the indexed (route gather) and un-indexed forms.
  - SFU chains get row stepping.
  - The programme words get a 4-b N field and a stride field, in `ot_hbm_su_programme_pslice_q4` x4, `ot_hgi_sfu_programme_store_r10` x4 and `ot_hbm_su_programme_root_h`.
- **Datapath:** no change. The II is SU nv x N with depth paid once.
- **Review:** `hbm_sfu_programme_store` and `hbm_su_static_kind` are critical prefixes, so they go through coordinator gate review (no REVIEW.json, no self-submit).

### 3.6 COLL rows (owner H-COLL)

- **What changes:**
  - ROW_GATHER, TOPK_MERGE, the kv gather and ARGMAX_MERGE take N rows as one message train. The endpoint, crossing and tail are paid once (the 741.7-cycle fixed part).
  - The shared ALL_GATHER and GROUP_REDUCE_MCAST carry N times the payload, and ring AG flits are multiplied by N. Flit width is unchanged.
  - The record-adapter row counter and stride adders go in the q2/q3 COLL parents, `ot_hgi_coll_ctl_v5` (a critical prefix), `ot_hgi_coll_gq_issue/land` and the TKM.
  - Link and ring widths are unchanged.
- **Exactness gate E2 (MoE combine).** Each position's routed-expert outputs must be combined in that position's own top-6 order, not in union order. The ROW_GATHER order list is emitted per position by the compiler.

### 3.7 IDX rows and expert union (owner H-IDX)

- **IDX.INDEX:** N queries run over **one** key stream. The query store becomes N x 4,096 words, which is new SRAM in `ot_hbm_idx_query_static` (260 x 260 um now, +~0.10 mm² die).
  - The array ingest stays serial per query (152 cycles of the 658.9 frame).
- **IDX.TOPK:** a heap row reset per row.
- **The verify expert-UNION record, which is new.** It holds a 384-b union bitmap plus a per-expert lane list (which positions route to which expert). It lives in `ot_hbm_idx_topk_link_static` and `ot_hbm_idx_ctl_static`.

### 3.8 MoE expert union (compiler, SM, COLL)

- **Weight streaming:** the verify streams each union expert's weights once. MTP-STATS measures the union of the 6 positions at a mean of 24.66 experts out of 384, p90 30.
- **Grouped GEMM:** for each expert, the routed positions' x are gathered into the 2 lanes. On average P_e = 36/24.66 = 1.46 positions are routed to an expert, so ceil(P_e/2) is 1 pass in most cases.
- **Area:** none. The new items are the union record (§3.7), the egather payload scaling and the per-position combine order (E2).

### 3.9 VM (owner H-DIE): no change in this die (deferred)

- **What growth would buy:** keeping the 6 verify columns (h + PRE) resident needs +150k words (2^18 → 2^18.9), which is about +57% of the VM in the 4 quadrant slices plus `hfd_vms_bank` (a critical prefix). It buys +2.3% DS MTP and +4.5% DS multi-user.
- **Recommendation:** keep the as-built column swaps (SWAP_IN 336 / SWAP_OUT 241 cycles a column, `ds_mtp_kernels` bodies). The reasons are the owner rule "only significant gains" and the hub cut / VM closure risk.
- **Revisit:** only if multi-user becomes a headline.

### 3.10 Drafter overlap (owner H-MTP; compiler only)

- **The draft:** the DSpark draft runs on the same die as R = 5-row records on the 2 lanes. The stages are dsa 21.3k, dsb 89.7k, dhead 11.4k, Markov 15.6k and demb 1.8k cycles, about 139.8k in all.
- **The overlap:** the seed of the next draft (main_proj / wkv over the 6 verify columns) is scheduled jointly with the verify head on the S2 command-processor schedule. The credit is small (1,094 cycles), because everything after the accept depends on the accepted token.
- **Hardware:** no new hardware. CTL.TOKX (k completion beats, SPEC_GAP Q-MTP-1) is the only ISA item.

### 3.11 Compiler (owner H-ISA / HBM-MTP; `ds_mtp_verify`, `ds_mtp_rows`, `ds_mtp_draft`, `hbm_plane_model`)

- **What it emits:** P = 2 programmes as real HGI records, not only priced records:
  - the N field and strides;
  - the SM pass loop with the lane and slot field;
  - the expert-union record and per-expert lane lists;
  - the per-position combine order (E2);
  - the 256-slot KV window ring;
  - the attention union stream with lane masks (E1);
  - the joint seed/head schedule.
- **Per layer:** the compiler chooses lanes ≤ P (D1: +1.3 cycles, so uniform P = 2).
- **Binaries:** the programmes must run on the P = 2 RTL in per-layer sims. This is the same standard as the token-pass release gate: real cycles, static schedule.

## 4. Tile list (d4g GEN2 → P = 2)

Area is the outline (hard) or the slot. Risk is the timing-closure risk of the P = 2 version.

| element (instances) | d4g GEN2 state | P = 2 change | area now → P = 2 | risk |
|---|---|---|---|---|
| leaf block-dot `ot_hbm_accel_smh_bdc` (512 → 1,024) | CLOSED, native | **unchanged view, x2 per leaf** | 16,012 um² each | none (reused) |
| leaf BF16 column `tcl` / `tcl_gu` + `tct` (x512 → x1,024 sets) | CLOSED, native | **unchanged views, x2 per leaf** | as closed | none (reused) |
| leaf x store `smh_xs` (x512 → x1,024) | xs native FAIL (boundary spread 106/102 at TT/FF, HF-5) | unchanged view, x2; takes the release fix | 4 x 128x256 SRAM each | low (inherits the release fix) |
| **SM tile `smh_tile_rp4lp` (static) → NEW `rp4lp2`** (256) | release gate 2 running (PL-SMT landed form; gate 1 FAIL = IO clock reference, M6 overflow at the W macro column) | NEW: 2 leaves x (+bdc, +tcl x2, +tct, +xs) = +10 hard children (~18 → ~28); per-lane broadcast flops; ck_n/ck_s landed regions kept | 457.92 x 1,598.4 = 0.732 mm² → **544.32 x 1,598.4 = 0.870 mm²** (+18.9%; need +0.133) | **HIGH**: densest macro columns on the die, base tile not yet closed |
| **SM attention tile `rp4a` → NEW `rp4a2`** (in smh_attn) | not yet built (HF-5: smh_attn needs rp4a from the same generator) | NEW: as rp4lp2 plus per-lane pv_merge / sum_capture / pstore, line-mask input | as rp4lp2 + ~5% | **HIGH**: depends on release rp4a |
| SM front `ot_smh_static_front` + fc_t / fc_b / fc_xl / fc_xr | fc_t FAIL r0a launch, fc_xr FAIL structural (one-stage relay), fc_b / fc_xl near-miss (HF-5) | changed: x/result lane registers, slot-field decode; relay widths unchanged | ~same | medium (inherits the HF-5 fixes) |
| SM back end `ot_hbm_accel_smh_be*` (6 variants) | in release cluster | changed: lane-major publish tag, pass loop | ~same | low-medium |
| SM attention engine parts `pvacc`, `attn_be`, `attn_issue`, `pstore` | in release cluster | changed: per-lane state x2, lane-mask issue, per-lane cross-SM merge | +~0.3 mm² die (D1 att item) | medium |
| **SM column cluster `smh_attn` / `smh_static`** (16) | release BLK.14 running (landed parent via lp.py) | NEW parent: 16 rp4(a)2 tiles; pins unchanged; re-placed; landed regions | 1,939.68 x 6,955.2 → **2,285.28 x 6,955.2** (+17.8%) | **medium-high** |
| xq pillars `ot_hgi_sm_xload_*` (pegress, bfqg, bdring) | release kits (pegress is a critical prefix) | **unchanged** (the lane is decided in the SM front) | same | none |
| `ot_hbm_su_static_pgslice` (16, FUSED LL lanes) | release cluster | changed: FUSED rows (II 197 measured), +~6k um² each | 1,797.12 x 2,825.28 slot, fits | low-medium |
| `ot_hbm_su_static_qcore` (4), `ot_hbm_su_reduce_static` (4) | release | changed: SU.VOP row counter | same | low |
| SU / SFU programme `pslice_q4` (4), `sfu_programme_store_r10` (4), `su_programme_root_h` | release (sfu store = critical prefix) | changed: N + stride fields in the programme word | same | low (coordinator review) |
| `ot_hgi_sfu_core_split3` (4), `sfu_lg_pair_tap_leaf*` | release | changed: SFU chain row stepping (control) | same | low |
| `ot_hbm_hc_eng_static` (1), `ot_hbm_hc_q_static` (4) | release | changed: HCP x6 row mode, +2 `ot_hdc_sinkhorn`, row sequencing | 5,223 x 1,953 slot, +0.12 mm² | **medium** (+ model risk M2) |
| COLL `q2_hard_v5` (3) / `q3_hard_v7x` (1), `coll_ctl_v5`, `gq_issue/land` (4+4), `ring_b_stop` (4), TKM | release (q2/q3 parents BLK.9.1 failing) | changed: row counter + stride adders; payload trains; widths unchanged | same (+0.02 mm²) | low-medium (wait for the release parent fix) |
| IDX `idx_query_static` | release | changed: N x 4,096-word query store (new SRAM) | 260 x 260 → ~400 x 400 | medium (SRAM added to a small tile) |
| IDX `idx_topk_link_static`, `idx_ctl_static`, `idx_selector_static` | release | changed: heap row reset, union record (384-b bitmap + lane lists) | same | low-medium |
| IDX score cluster `ot_hbm_idx_score_static` (2) | release | **unchanged** (the key stream is shared; per-query ingest is serial) | same | none |
| DMA `ot_hgi_dma_back_static_vp4_banks_cp` (2) | release | changed: KVWB N rows, 256-slot ring index (+1 b), position rows | same | low |
| ARGMAX `ot_hbm_argmax_static_sw_vm` | release | changed: ARGMAX.LOCAL rows | same | low |
| host CP `ot_hbm_host_cp_rxs` | release | changed: CTL.TOKX, header N | same | low |
| VM (vms banks, glue, calendar, `idx_vm_share2`) | release | **unchanged** (VM growth deferred) | same | none |
| PHY, SerDes, UCIe, PC / svc, refcfg, fault leaves, clock gen | release | unchanged | same | none |

**Count:** 2 new tile types (`rp4lp2`, `rp4a2`) and 1 new parent (the P = 2 SM column). About 14 tile types change in control only, and every other element is unchanged.

**Tile hygiene (owner 10-15):** no new SM leaf variant. The leaf is a P-parameter of the release generator, and the closed views are reused.

## 5. Die floorplan and GRT impact

- **The SM row is the only geometry change.** 8 SM columns per half (S and N) grow from 1,939.68 to 2,285.28 um wide (+345.6 each, +2,765 per row).
  - The d4g SM bands have **empty side margins** of 961 um at x 0–961 and x 19,239–20,200. Nothing else is placed in the band rows, which hold only the SMs, the xq pillars in the 540-um gaps and the pleafs.
  - The row therefore absorbs ~1.84 mm of the growth.
- **Frame F-A (recommended).** The SM tile grows in x only (544.32 x 1,598.4).
  - The die becomes ~21.13 x 31.77 mm = **~671 mm²** (+29.5).
  - The SM-row gaps (xq pillars) are kept, and the hub keeps its blocks, centred.
  - Reticle: the short-side margin goes from 5.80 to 4.87 mm, and the long side is unchanged. OK.
  - The tile aspect improves from 3.5:1 to 2.9:1 ("no long-thin").
- **Frame F-B (fallback).** The tile grows in both directions (522.72 x 1,684.8).
  - The die becomes ~20.44 x 32.46 mm = ~664 mm².
  - The cost is the long-side reticle margin: it shrinks to 535 um against the 500 required, too thin after SMFRAME already took 276 um a half.
  - F-B is rejected unless F-A's outer-SM path cost is worse than estimated.
- **Links.** No new link class and no new long link is added.
  - SM_HBM, SM_X, SM_OUT and KV_DESC keep their bit counts (lane addressing is internal).
  - The 4 outer SMs per half move ~1.2 mm further from their PC stop: SM_HBM longest goes from 2.90 to ~4.1 mm, which is +3 forwarded half-cycle relay hops at the 405-um reach on an existing fixed-latency lane. Priced at a few cycles per SM record, it is noise against 1.43M cycles a step.
  - The inner SMs move by less than 0.2 mm.
- **Cuts (≤ 0.55–0.60 rule).**
  - The hub cuts are unchanged in bits (worst v 0.397 / h 0.431 today). The die gets 0.93 mm wider, so the horizontal-cut ratios fall slightly.
  - The SM column N-face xw window (2,063 bits over 360.72 um, cut 0.549, 5.72 pins/um) is unchanged in bits. The face is 345.6 um wider, so the window can widen to ~440 um (cut ~0.45).
  - The result window (271 bits) is unchanged.
  - Inside the SM column, the x-write bus and the result gather lanes are unchanged in width: lane-major time-multiplexing plus a 1-bit lane tag.
- **Clocking (landed-regions standard).**
  - The P = 2 tile keeps the ck_n/ck_s regional roots and the per-root IO domains (PL-SMT 2444d768c form). Its hard children grow from ~18 to ~28, so the CTS check is pin-flop spread ≤ 80 ps at TT/FF per region.
  - The SM column parent stays a landed parent with fixed-latency crossings.
  - No zero-skew tree spans mm.
- **GRT risk.** The risk sits in the SM tile's macro columns: the release gate 1 already showed M6 overflow at the W macro column with 18 children. Adding 10 hard children there is the dominant routing risk of the whole P = 2 die. Hence the SM tile goes first (§6).

## 6. Ordered build plan

The plan builds the low-risk pieces first and starts the riskiest tile on day 0. Times are wall-clock with parallel lanes on the fleet, in this project's measured cadence: a tile gate takes ~4–8 h, a tile route and STA ~8–24 h, a die GEN+GRT+STA ~1 day.

**Day 0, before any RTL (needs the owner's go): close the model gaps, ~0.5 day.**
- M1: price the P x x-load beats and the lane-major result publish in `ds_mtp_verify` (expected < 1%).
- M2: settle the HC row II basis, i.e. which HC engine GEN2 binds, and its measured row II. If it is the 4,385 engine, re-price or redesign HC rows before HC RTL.
- M3: done. QCHK 7bc2156cd re-timed the Qwen DFlash rows (§1).
- E1 / E2: read the golden's reduction orders for sparse attention and the MoE combine. That decides whether the ATT lanes stay in scope.

**Track SM, the riskiest, started first and run continuously:**
1. **S1, leaf RTL + bench (0.5 day).** `ot_hbm_sm_leaf_p2`, built from the closed bdc / tcl(_gu) / tct / xs views and the per-lane broadcast flops. It is checked bit for bit and cycle for cycle against 2 production columns, extending the MTP-AREA bench. It has an alias mutant plus a committed fail witness, on Verilator 5.050.
2. **S2, `rp4lp2` kit + gate (2–3 days to closed).**
   - The kit comes from the PL-SMT generator with P = 2, in F-A geometry.
   - First gate on day 1. Iterate on the release gate 2 findings (IO domains, M6 at the macro column) without forking the generator. Review it as a critical tile (gate PNG + checklist: macros on the 43.2 lattice, one std-cell band, full-face pins ≤ 6/um, clock beside the register mass, spread).
   - **Target: SM P = 2 tile CLOSED by ~day 3–4.**
3. **S3, `rp4a2` attention variant (+2 days after the release rp4a exists).** Per-lane PV state plus the lane-mask input. Its bench covers the union stream with masks against 2 single-query runs (E1).
4. **S4, SM column parent P = 2 (2–3 days).** The front/BE lane registers and pass loop, the landed parent, top-down pins (unchanged set, new geometry), gate + route.

**Track rows, low risk, parallel from day 0 (each item = RTL delta + bench + mutant witness + re-gate of the touched tile):**
- **R1 (1 day):** the ISA header N + stride (generic decode), host CP / CTL.TOKX, and the programme stores (SU pslice, SFU store, SU root).
- **R2 (1 day each, parallel):**
  - DMA KVWB rows + the 256-slot ring;
  - ARGMAX rows;
  - SU.VOP rows;
  - COLL row trains (after the release q2/q3 parent fix);
  - IDX top-k row reset + the union record.
- **R3 (1–1.5 days):** FUSED rows, porting the measured P6 RTL into the pgslice LL lanes.
- **R4 (1.5 days, after M2):** HC row mode + 2 Sinkhorn units.
- **R5 (1.5 days):** the IDX.INDEX N-query store (SRAM in `idx_query`).
- **Milestone after R1–R5:** the Phase-A die (no SM change) is complete at **2,393 tok/s DS MTP**, which is already above AR.

**Track compiler (parallel from day 0, 2–3 days):**
- `ds_mtp_verify` / `ds_mtp_rows` / `ds_mtp_draft` emit real P = 2 HGI programmes (§3.11);
- the per-layer programme checker;
- the joint seed/head schedule.

**Track die (stand-ins early, per the 10-18 efficiency rule):**
- **D1 (day 1–2):** `plan_d4g.py` F-A frame + grants transform (as `d4g_sm_frame.py` does for y). Bind/GEN/GRT/STA with P = 2 SM stand-ins (outline + pins of the F-A tile) to catch hub and relay issues at once.
- **D2 (day 6–9):** real views as they close, then die GRT overflow 0 + die STA ≥ 0 (TT setup / FF hold).

**Track per-layer RTL sims (day 8–11):**
- one DS layer verify step at N = 6 on the P = 2 RTL (SM pass loop, union attention, row records), real cycles against the model price (within 10%: the throughput qualification);
- one draft step;
- one 2-user AR step.

**Expected end:** SM P = 2 tile closed by ~day 4, the Phase-A row pieces by ~day 5, the P = 2 die GRT+STA by ~day 9–10, and the per-layer sims by ~day 11–12. That is about **2 weeks of wall time** with ~6 parallel lanes, all at normal/low priority behind the release.

## 7. Risks and decisions for the owner

1. **The SM P = 2 tile builds on a release tile that has not closed yet** (rp4lp gate 2 running, rp4a not built). Plan: run the P = 2 gate in parallel and carry over every release fix. Do not wait, and do not fork the generator.
2. **M2, the HC row II basis**, could remove up to 270k cycles of the gain: up to -12.5% on DS MTP, from 3,071 down to ~2,690 (P = 2 noHC = 2,686.6). It must be resolved first.
3. **E1, the attention reduction order:** if the golden is not in index order, the ATT lanes are dropped (2,827 tok/s at P = 2, −~0.3 mm²).
4. **The KV top-512 overlap is unmeasured** (the GPU run was not approved). The headline is the upper bound, so a real overlap only raises it: the lower bracket is +~4.7%.
5. **HBM capacity for 2 users x 1M KV** is not checked (multi-user rows).
6. **VM growth deferred** (+2.3% MTP / +4.5% multi-user). The owner can re-open it if multi-user becomes a headline.

**Decision asked: GO / NO-GO on production RTL for the plan above,** with frame F-A, no VM growth and full lanes (subject to E1).

## Records

- `d2/p2_ablation.py`, `d2/p2_ablation.json`: P = 2 single-feature ablation plus no-VM / no-VM-no-ATT, run on ot-epyc5 from the D1 tree 043140ff1.
- `d2/p2_extra.py`, `d2/p2_extra.json`: Phase-A (row field only, no lanes, no VM growth) and 2-user with and without VM growth.
- Geometry: main `results/arch/hbm_die_d4g/plan/d4g_phy/{compact.P.json,eval.json}`, `grants_d4g.json` (SM column 1,939.68 x 6,955.2; die 20,200 x 31,773.52; cuts v 0.397 / h 0.431; SM xw window 0.549).
- Tile states: lanes/HF-5.md, lanes/PL-HBM9.md, RELEASE_TREE H.STA.BLK.9/14 (10-18 ~19:00).
