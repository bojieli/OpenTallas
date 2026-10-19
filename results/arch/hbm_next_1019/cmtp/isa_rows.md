# HGI-1R: N-row records for the next HBM die (P = 4)

Lane HBM-NEXT-CMTP, 2026-10-19. This is next-release work, not a release gate. **Single source:** `tools/hbm_next/isa_rows.py`. The tables in §2 are generated from it, and `python3 tools/hbm_next/isa_rows.py --selftest` fails if they differ.

Implementers: HBM-NEXT-UNITS (FUSED, HC, COLL, IDX, SU, DMA, ARGMAX and the CP decode), HBM-NEXT-SM4 (SM.MATVEC lanes, the remainder pass: K-split or row-split), HBM-NEXT-ATT4 (ATT rows). Consumers: the CMTP compiler and HBM-NEXT-VEH.

## 1. What changes, and what does not

HGI-1 (`docs/HBM_GENERIC_INTERFACE.md` §6) already lets one SM record serve up to 8 position slots (param [4:2]). No other unit has a row count. Every other unit runs one record per position, and each record pays its setup and fixed latency again.

HGI-1R adds one optional 256-bit part, **ROWX**, to any record:

- **The flag.** UOP `op[5]` (header bit 123) set means "a ROWX part follows". It comes after the SUT (when `tmpl` = 1) and before the MDESCs.
  - No HGI-1 op code reaches `op[3]` (the longest op list has 8 entries), so the bit is free.
  - An HGI-1 decoder sees op ≥ 32 and faults with completion status 3. A die without row support therefore refuses an N-row record; it never silently runs only row 0. The self-test proves this against the unchanged `tools/hgi_sim/records.decode_one`.
- **Every HGI-1 record is still legal and encodes byte for byte as before.** The UOP, MDESC and SUT layouts, the DYN codes, the memory map and the doorbell are all unchanged.

The two terms are separate:
- **N** is the row count of a record (1 to 16): verify positions, draft block rows, or users.
- **P = 4** is the die's physical lane count. Only the SM and the attention engines see P. Every other unit runs N rows at its row II.

## 2. Encoding (generated)

<!-- BEGIN isa_rows.py tables (generated: python3 tools/hbm_next/isa_rows.py --md-tables) -->

**ROWX (256 bits)**

| Bits | Field | Signed | Meaning |
|---|---|---|---|
| 3:0 | `nm1` | no | N - 1: row count N = 1 .. 16 (with rsel: the upper bound of the table count) |
| 7:4 | `slot0` | no | first row's DYN bank / slot (0 .. 15); row r uses bank slot0 + rho(r); UOP slot must equal slot0[2:0]; slot0 + N - 1 <= 15 |
| 15:8 | `rgap` | no | extra cycles between row starts beyond the unit's row II (static-schedule spacing; 0 = back to back) |
| 17:16 | `rpl` | no | SM.MATVEC only: remainder-pass layout (r = N mod P rows, g = P / r lanes a row, a power of two): 0 idle lanes, 1 K-split (lane q of a row group takes K part q), 2 row-split (lane q takes output-row part q), 3 reserved; other units 0 (see sm_pass_plan) |
| 18:18 | `rsel` | no | rows from the VM row table at rtab + 32 L: N = U32(word 0) <= nm1 + 1, row r takes entry word 1 + r |
| 19:19 | `rsv19` | no | reserved, 0 |
| 38:20 | `rtab` | no | rsel: VM word address of row-table row 0 / of the ATT plan (32-word aligned, < 2^19: the grown VM, PROG 10-19; was 18 b in 1.0); else 0 |
| 45:39 | `emask` | no | rsel: bit k (A..I order) = operand k steps by the entry's e field instead of rho; else 0 |
| 50:46 | `hsh` | no | HBM row-stride shift: an HBM operand steps rs_k << hsh BYTES a row (0 = bytes, the 1.0 meaning; users mode: 12 = 4 KiB units, so the 24-bit rs reaches +-32 GiB per-user KV regions); VM strides are never shifted |
| 87:51 | `rsv51` | no | reserved, 0 |
| 111:88 | `rs_A` | yes | row stride of operand A (signed; HBM bytes, multiple of 32 / VM FP32 words; 0 = broadcast; must be 0 when A is absent or a STREAM / NONE descriptor) |
| 135:112 | `rs_B` | yes | row stride of operand B (signed; HBM bytes, multiple of 32 / VM FP32 words; 0 = broadcast; must be 0 when B is absent or a STREAM / NONE descriptor) |
| 159:136 | `rs_C` | yes | row stride of operand C (signed; HBM bytes, multiple of 32 / VM FP32 words; 0 = broadcast; must be 0 when C is absent or a STREAM / NONE descriptor) |
| 183:160 | `rs_D` | yes | row stride of operand D (signed; HBM bytes, multiple of 32 / VM FP32 words; 0 = broadcast; must be 0 when D is absent or a STREAM / NONE descriptor) |
| 207:184 | `rs_O` | yes | row stride of operand O (signed; HBM bytes, multiple of 32 / VM FP32 words; 0 = broadcast; must be 0 when O is absent or a STREAM / NONE descriptor) |
| 231:208 | `rs_R` | yes | row stride of operand R (signed; HBM bytes, multiple of 32 / VM FP32 words; 0 = broadcast; must be 0 when R is absent or a STREAM / NONE descriptor) |
| 255:232 | `rs_I` | yes | row stride of operand I (signed; HBM bytes, multiple of 32 / VM FP32 words; 0 = broadcast; must be 0 when I is absent or a STREAM / NONE descriptor) |

**Row-table entry (U32)**

| Bits | Field | Meaning |
|---|---|---|
| 3:0 | `rho` | row / position / user index: DYN bank slot0 + rho, operands step by rho x rs |
| 7:4 | `rsv4` | 0 |
| 15:8 | `e` | expert-slot index for the operands selected by emask (IDX.UNION: rho x imm_b + kappa) |
| 31:16 | `rsv16` | 0 |

**New and defined operations**

| Operation | Code | `param` / immediates | Operands and semantics |
|---|---:|---|---|
| IDX.UNION | 5 | none; imm_a = experts E (DS 384); imm_b = slots a position row K (DS image 7 = 6 routed + the shared expert slot; e = rho x K + kappa) | A = U32 top-k ids, m = N rows of n = k, each row strictly ascending (IDX.TOPK order 1); O = U32 union ids ascending (O.n >= U); D[0] = U (a CTL.LOOP [17] count); R = U row-table rows of 32 words (R.stride = 32): word 0 = c_u, words 1..c_u = entries {rho, e} in ascending rho, kappa = rank of u in row rho |
| IDX.KVUNION | 6 | [3:0] lanes NL - 1 (NL <= P), [7:4] slot0 (the lanes' first DYN bank), [8] users (lanes are users: disjoint KV, masks exclusive), [24:16] line budget a SM (<= 256: the static calendar's reserved ATT span); imm_a = W (window rows, DS 128); imm_b = list-store rows a lane (DS 512) | A = U32 selection lists, m = NL rows of n = k (row l = lane l's TOPK_MERGE selection, strictly ascending, k <= imm_b), A.stride = row stride; window of lane l = positions POS_SLOT(slot0 + l) - W + 1 .. POS_SLOT(slot0 + l) (>= 0); R = the attention PLAN: 32 SM blocks of PLAN_WORDS (R.base 32-aligned; layout isa_rows.md R10); D = the lane map (D.n >= 16 + 128 NL): D[0] = union lines U, D[1 + l] = T_l, D[5 + l] = run chunks nrun_l, D[9] = max lines a SM (<= param [24:16] budget, else E_RANGE), D[10] = nodes, D[16 + 128 l + k] = node of lane l run k = {sm [4:0], node [9:5]} |
| ATT.QK/PV plan | QK 0 / PV 1 | unchanged (HGI-1) | with ROWX rsel = 1 and emask = 0: the KV-UNION PLAN mode (R10): rtab = the IDX.KVUNION plan base; row rho = query lane rho (bank slot0 + rho, rs on its q / p / score / output operands); SM s streams the lines of plan block s once, lane l applies the lines whose mask bit l is set on its own ordinal |
| CTL.USERS | 8 | [3:0] N - 1 when no ROWX (slot0 = 0); with ROWX: N, slot0 | A = U32 [2 N]: {token_s, pos_s} for s = 0 .. N - 1; sets DYN bank slot0 + s: POS = POS_SLOT = pos_s, POS1 = POS_SLOT1 = pos_s + 1, TOKEN = token_s, SLOT = slot0 + s, DS selectors (16..62) from pos_s; range-checked against cp_vocab / cp_ctx_max |
| CTL.TOKX | 5 | [0] users: 0 = MTP commit (k beats at pos + i - 1), 1 = one beat per user slot | A = U32 [1 + n]: A[0] = k (MTP: 1 <= k <= ncol) or N (users), A[1..] = tokens; completion beats {token, pos, slot} (users: pos = bank POS of slot0 + i); END follows |
| CTL.ACCEPT | 7 | none | A = U32 [1]: a = accepted drafts (0 .. ncol - 1); commit n <- n + 1 + a; IDX.EHASH history restored to slot a; no other state rolls back (rule R-POS) |
| SM.MATVEC | 0 | [1:0] fmt, [5:2] positions - 1 (HGI-1 [4:2] widened; with ROWX it must equal N - 1, or 0 with rsel) | unchanged |

**Row II (cost of an N-row record = c1 + (N - 1) (II + rgap))**

| Family | II (cycles) | Basis | Source |
|---|---|---|---|
| SM.MATVEC | pass plan | PRICED | sm_pass_plan: line issues / max(1, issues per line / 1.374) of the AR record; SM4 lane-major publish skew +8 a further lane a pass (hnx_rp4lp4 LSKEW, MEASURED) |
| ATT.QK/PV | union stream | MEASURED | ATT4 bench: span = fixed 113-127 + 7.8 a union row (= fixed + comp x U(N)/U(1)), passes = ceil(N / P); shared 4-lane merge PV span 16-40 shorter (a1); E1 PASS; plan mode R10 |
| FUSED.HC_PRE_NORM | 81.0 | MEASURED | UNITS-FUSED hnx FUSED engine (@e70d3285a): 404 + 81 (N - 1), KX = 4 x slots, rgap 0 (KX = 2 needs rgap >= 64); price 160; old P6 RTL 197 |
| FUSED.HC_POST | 103.0 | MEASURED | UNITS-FUSED hnx FUSED engine: 196 + 103 (N - 1) (price 100) |
| FUSED.QDQ_* | n / 32 | PRICED | quantiser 32 elements a cycle |
| HC.HC_MIX* | 250.0 | MEASURED | UNITS tb_hnx_hc_eng4 (hnx root + 4 ring quarters): HC_MIX 998 + 250 (N - 1), bit-exact N = 1..8 |
| COLL.ALL_GATHER / ALL_REDUCE | 3K/2 | MEASURED | UNITS-COLL ot_hnx_coll_gq: one fire + 40-edge drain, 3K/2 edges a further row (K ring indices) = the price c1 - 741.7 |
| COLL.ROW_GATHER | 623.0 | MEASURED | UNITS-COLL rows: R = 623 flits a rail at the DS verify shape (price 1,449; payload-proportional elsewhere) |
| COLL.ARGMAX_MERGE | 32.0 | MEASURED | UNITS-COLL rows: 53 + 32 (N - 1) (price 12.7-23.7) |
| COLL.TOPK_MERGE | c1 - 741.7 | PRICED | one message train: endpoint + crossing + tail once, payload x N |
| IDX.TOPK | 49.2 | MEASURED | UNITS-IDX ot_hnx_idx_topk_rows_static (price 47.0) |
| IDX.INDEX | 232.0 | MEASURED | UNITS-IDXN (@5bf6d2d50): 1,297 + 232 (N - 1), keys read once a record (replay buffer), 8 row streams, 4 time-shared selectors (price 152 of the 658.9 frame) |
| IDX.UNION | 48/67/90/101/142 (N 1/2/3/4/6) | MEASURED | UNITS-IDX ot_hnx_idx_union_static (idx packet client, ~18.6 a row; price N x 6 / 8 + 24) |
| IDX.KVUNION | (W + N k) / 8 + 320 | PRICED | merge of N ascending lists at 8 ids a cycle + 32 plan blocks x 320 words at 32 words a cycle; runs on IDX beside the ROW_GATHER the ATT record waits for anyway (off the critical path) |
| SU.VOP | 2k ceil(e / 512) | MEASURED | UNITS-SUDMA2 write-port split (@a42351330): AB 28 / ABC 56 at e = 7,168 (k per-row VM operands; VM fill bandwidth binds); indexed gather 1 (= price) |
| DMA.KVWB_DS | 8.0 | MEASURED | UNITS-SUDMA kvwb: 36 + 8 (N - 1), +28 a 256-slot ring wrap (price 2) |
| DMA.* | c1 - first access | PRICED | first access once, rows at full bandwidth |
| ARGMAX.LOCAL | 22.0 | MEASURED | UNITS-SUDMA2 ot_hnx_argmax_wide_rows: II 22 (1,347 words / 8 a beat on one slice; price 6 needs a ~4-slice row spread) |
| CTL.* | 0.0 | n/a | CTL rows are not issued (USERS / TOKX take N from the record) |

<!-- END isa_rows.py tables -->

Record layout: `UOP (16 B) | SUT (32 B, if tmpl) | ROWX (32 B, if op[5]) | MDESC (32 B) per set opnd bit, A B C D O R I`.

## 3. Semantics (normative, bit-exact)

**R1. Expansion.** An N-row record means exactly the in-order sequence of its N single-row HGI-1 records (`isa_rows.expand`). Row r (r = 0 … N−1) is the record with ROWX removed, and:
- its DYN bank is `slot0 + ρ(r)`;
- every present descriptor k has `base + ρ(r) · rs_k` (or `base + e(r) · rs_k` when `rsel` and `emask[k]` are set);
- for the SM, param [5:2] is 0, so each row is a single-position MATVEC.

ρ(r) = r for static rows. With `rsel`, ρ(r) and e(r) come from entry r of table row L, and N is that row's count. Every other field (`n`, `m`, `stride`, `lstride`, `dyn_sel`, `indexed`, …) is evaluated per row exactly as HGI-1 §6.4 defines it, in the row's own bank.

**R2. Row independence.** No row may read a VM word that an earlier row of the same record writes. The compiler checks this (`check_rows_independent`), and the static checker re-checks it. The hardware may therefore overlap rows.

**R3. Retirement.** The record retires, and its unit's `wait` bit clears, when the last row's writes are visible. Wait masks and predicates apply to the whole record. A predicate is evaluated once, in bank `slot0`.

**R4. Shared streams.** A unit may share one stream across rows only where the result equals R1 bit for bit:
- the SM weight line: line hold;
- the IDX key stream;
- the COLL message train: endpoint, crossing and tail once, then the payloads in row order;
- the ATT KV union stream. E1 PASS (`att4/E1.md`): the union is streamed in ascending line order with per-lane masks.

**R5. SM lanes and the remainder pass** (the P = 4 SM).
- **Line hold.** One HBM read of each weight line is issued to the lanes once per pass.
- **Full passes.** Rows 4p … 4p + 3 go to lanes 0 … 3, with the whole K and every output row.
- **The last pass** (r = N mod 4 rows, g = 4 / r lanes per row, which must be a power of two). `rpl` selects its layout:
  - **`rpl` = 0, idle.** r lanes run and the other 4 − r lanes idle.
  - **`rpl` = 1, K-split.** Remainder row j runs on lanes j·g … j·g + g − 1, and lane q of that group takes **K part q**. A K part is one of the g aligned power-of-two runs of leaves of the golden's padded pairwise tree over the csum chunk sums (R-ARITH chunk8: 8 block-dot terms a chunk for FP8/FP4, 8 elements for BF16). The tree's own top log2 g levels combine the parts.
  - **`rpl` = 2, row-split.** Lane q of the group takes **output-row part q** of the record's rows on that SM. No combine is needed.
- **Exactness.** Both split forms are exact by construction:
  - the K-split performs the same additions in the same tree;
  - the row-split partitions independent dot products.

  The self-test checks the K-split bit for bit with `hdc_golden_v41.csum`: 1,280 trials over the DS K shapes, 2- and 4-way, including random, wide-exponent, cancelling and −0 terms. An empty K part is the tree's own +0 padding.
- **What it costs.** A K-split pass costs its largest part's share of the lines. That share is 0.5 only when the chunk count is a power of two; at K = 5,120 (20 chunks, tree split 16 | 4) it is 0.8. A row-split pass costs ⌈rows / g⌉ / rows of the lines, which is no gain when an SM holds a single output row (for example `wq_a`: 13 rows a die). The compiler picks the cheapest layout per record (`best_rpl(N, P, nc, rows)`).
- **Hardware needs (SM4):**
  - a g-source lane-group broadcast in the remainder pass (two or four held lines at once);
  - for the K-split, g partial binary-counter accumulator sets for each remainder row;
  - a weight read order that interleaves the parts. That is the compiler's per-SM weight layout, not hardware.
- **What this means on the SM4 leaf** (CMTP 10-19, read against `rtl/hbm_next/sm/hnx_rp4lp4_leaf.sv` @ f43d62ae5). Each lane there is one unmodified d4g leafh with its own accumulator, and `hnx_rp4lp4_lanefan` broadcasts ONE row bundle `rl1` (818 b: control, 788-b weight word, x read address) to all P lanes.
  - **The "2 accumulator sets per remainder row" are the 2 lanes of a pair.** Lane 0 holds row r's K-part-0 partial for position 4, and lane 1 holds its K-part-1 partial. Lanes 2 and 3 do the same for position 5. No lane needs a second accumulator, and no per-lane beat mask is needed.
  - **What is new is the supply:** 2 different weight words in the same issue cycle. Word A (K part 0) goes to lanes 0 and 2, and word B (K part 1) goes to lanes 1 and 3, each with its own x read address (the part's K offset). The x target mask loads position 4 into lanes 0–1 and position 5 into lanes 2–3, with no change to the lane-select mechanism.
    - As built, that is a second row bundle per leaf: +818 b into each leaf, and the tile's `rin_n` / `rin_s` doubled, or a 2× row-port rate.
    - The row-split (`rpl` = 2) needs the same second word but no combine.
  - **The K-split also needs:**
    - (i) Each lane closes its row after its own part's chunks. The part-0 lane closes on an aligned power-of-two subtree; a short last part is the tree's +0 padding, which leaves the value unchanged.
    - (ii) **One FP32 add a remainder row**, P0 + P1, in RNE with part 0 as the left operand: the top level of the golden tree. For g = 4 (the draft at N = 5) it is two levels, (P0 + P1) + (P2 + P3). That adder is in no closed view. It goes either on the publish path (lane 2j+1's word arrives LSKEW = 8 cycles after lane 2j's, so the merge adds instead of forwarding, which needs a pipelined FP32 add) or downstream as a VOP.
  - **What it buys:** MTP 3,500.1 against 3,393.0 tok/s without it, +3.2 % (`area_options.json` `a` against `a_norpl`). 4 users gain nothing (N = P). The draft (N = 5) carries most of the gain.
  - **CMTP recommendation:** SM4 builds `rpl` = 0 first. That needs no second row word and no adder, and `rpl` = 0 is the HGI-1R default. The split stays an opt-in lever, built only if the second row bundle fits the tile's pin and track budget.
- **Pass plans:**
  - DS MTP verify (N = 6): pass 1 runs positions 0–3 on lanes 0–3; pass 2 runs position 4 on lanes 0–1 and position 5 on lanes 2–3, each pair split by K or by rows. That is 1.5 to 1.8 line issues per line against 2.0, so the SM time is max(1, issues / 1.374) = 1.09–1.31× AR against 1.456×.
  - The draft block (N = 5, g = 4): 1.25 to 1.4 issues, at most 1.02× AR.

**R6. Expert union (gate E2).** The golden's `moe` sums a position's routed experts in **ascending expert id** order, sequentially from +0, with each route weight applied inside the expert before w2. It then adds the shared expert and rounds once to BF16 (`hdc_golden_v41.Model.moe`, read 2026-10-19).

The union form keeps this order exactly:
1. `IDX.UNION` turns the N rows' ascending top-6 lists into the ascending union, the loop count U and one row table per union expert. The tables list (ρ, e = Kρ + κ), where κ is the rank of u in position ρ's own list and K = `imm_b` = the slots of one position row of the expert cells (the DS image: K = 7, the six routed slots plus the shared expert's slot, because the expert outputs of all slots form one row array).
   - **As emitted (step 4, `emitter.py`):** `IDX.UNION` (A = the TOPK rows' ids, m = N) → `CTL.LOOP` (count from VM = D[0]) { w1, w3 `rsel` records } `CTL.ENDLOOP` → the SwiGLU (an ordinary N-row record over all slots) → the 6 intermediate gathers as ordinary N-row records (one a slot κ, no union needed) → `CTL.LOOP` { w2 `rsel` } `CTL.ENDLOOP`. B (the expert weights) is indexed by the loop counter over the union list (I = O of `IDX.UNION`). Each loop record is checked on a synthetic union: every iteration's row ρ writes exactly cell (ρ, κ) of position ρ's κ-th expert, and the loop covers all 6N cells once.
2. The grouped GEMM is a `CTL.LOOP` over U (count from VM) of `rsel` records. On each:
   - B is indexed by the expert id;
   - A steps by ρ;
   - the GLU's route weight C and the outputs O step by e (`emask`).

   So each position's expert output lands in its own combine slot κ.
3. The combine is unchanged and per position: slots κ = 0 … 5 in order, then the shared expert.

The union changes only which weight lines are streamed, and how often. It never changes an addition. **E2: PASS by construction.** The ascending-id slot order is HGI-1 G15, the golden's order.

**R7. Positions and users.**
- **MTP mode** (the doorbell): bank s has POS = pos, POS_SLOT = pos + s and POS_SLOT1 = pos + s + 1. Verify records address per-position state with POS_SLOT.
- **Users mode** (`CTL.USERS`): bank s carries user s's own {token, pos}, and POS = POS_SLOT. Users-mode records are therefore the AR program's records with ROWX added: every row reads its own user's KV through its own bank, and each user's per-user regions step by `rs`.

**R8. Rule R-POS (commit and rollback).** Every on-die write that depends on a position is addressed by that position:
- the window ring, slot POS_SLOT mod 256;
- compressed-KV rows and index keys, group (POS_SLOT div ratio);
- the DSpark rows.

A rejected position's writes are therefore rewritten by the next step before any read. `CTL.ACCEPT` is the commit marker; the only state it restores is the IDX.EHASH token history. The window ring is **256** slots: a power of two ≥ 128 + N − 1, so that a 6-row KVWB cannot overwrite a slot inside an earlier row's window (`test_mtp_rows`). That is +128 HBM rows a layer, with no ISA change (KVWB O.m = ATT B.m = 256).

**R9. Completion.** `CTL.TOKX` emits k beats {token, pos, slot}: k = accepted + 1 in MTP mode, or N, one per user, in users mode. Then END follows.

**R10. Attention KV-union plan (`IDX.KVUNION` → ATT plan mode).** HGI-1R 1.1, CMTP step 4, asked for by ATT4 (`att4/E1.md` §4, `ot_hnx_att4_issue` mask / x loaders). Reference: `isa_rows.kv_union_plan`, `plan_words`, `plan_lane_lists` (the self-test decodes the VM images exactly as the engines do and rebuilds every lane's golden list).

- **`IDX.KVUNION`** (IDX op 6, no ROWX; one record a lane pass, issued after the `COLL.TOPK_MERGE` that writes the lanes' selections, beside the `COLL.ROW_GATHER` the ATT record waits for anyway):
  - inputs: A = the NL lanes' selections (U32, strictly ascending, row stride A.stride; absent in window-only layers) and each lane's bank POS_SLOT (window = POS_SLOT − W + 1 … POS_SLOT, W = imm_a);
  - **union stream (E1 C1):** all lanes' window rows ascending by position, then all compressed rows ascending (users: lane-major, disjoint);
  - **lane ordinals (C2):** lane l's lines are the stream entries in its own list, in stream order (= its golden list); T_l = W_l + k_l;
  - **aligned runs (C4):** nrun_l = the smallest power of two with ⌈⌈T_l / 8⌉ / nrun⌉ ≤ 32, divided by the best of 1 / 2 / 4; run k = ordinals [8 nrun k, 8 nrun (k + 1));
  - **jobs (ATT4 "balanced"):** run index k of all lanes is ONE job when its union ≤ 0.75 × the lanes' sum, else one job a lane; LPT onto the 32 SMs (largest first, least-loaded SM, lowest index on ties, ≤ 16 nodes a SM); an SM runs its jobs back to back in ascending k;
  - **static span:** param [24:16] = the line budget a SM that the calendar reserved (ATT record span = fixed + budget beats). A plan that needs more faults (E_RANGE). Collision = fault; no stall.
- **Plan block** of SM s at R.base + 320 s (U32):

| words | content |
|---|---|
| 0 | lines (≤ 256 = `MROWS` of `ot_hnx_att4_issue`) |
| 1 | nodes (≤ 16) |
| 2 … 17 | node i: lane [1:0], run k [13:2], length in ordinals [29:14], in stream order (a lane's runs ascending) |
| 32 … 287 | line word i: [31] = 1 window row {ring lane [29:28], position [27:0]} (ring slot = position mod 256); [31] = 0 list-store row r (lane ⌊r / 512⌋'s TOPK_MERGE list, entry r mod 512; MTP: the lowest lane that holds it) |
| 288 … 319 | lane masks: line i, lane l = bit 4 (i mod 8) + l of word 288 + 2 ⌊i / 16⌋ + ⌊(i mod 16) / 8⌋ (the `mw_data` layout: row 16 a + i, lane l = bit NL i + l at NL = 4) |

- **Lane map** D: D[0] = U, D[1 + l] = T_l, D[5 + l] = nrun_l, D[9] = the largest SM line count, D[10] = nodes, D[16 + 128 l + k] = {SM [4:0], node [9:5]} of lane l's run k (the cross-SM merge order: run k ascending, the P = 1 pairwise merge per lane).
- **ATT plan mode:** an ATT.QK / ATT.PV record with ROWX `rsel` = 1, `emask` = 0, n = NL lanes (≤ P; one record a lane pass, `slot0` = the pass's first lane) and `rtab` = the plan base. Row ρ = lane ρ (bank `slot0` + ρ; q / p / scores / outputs step by rs). SM s streams the lines of block s once; lane l applies a line only when its mask bit is set, counting its own ordinal; the node table gives each lane's run boundaries (run_first / run_last) and the x-store load (p_l of ordinals 8 nrun k …). A list-store row or ring lane in a line word is applied with that operand's own stride (rs << hsh), not with ρ.
- **Exactness:** E1 PASS conditions C1–C4 hold by construction (the self-test checks lane lists, chunk alignment of every node on its SM, and that the zero-insertion, lane-swap and misaligned-node mutants are caught). C5 (causality, KVWB before ATT) is the compiler's: the KVWB N-row record precedes the attention records in every segment.
- **Measured / priced:** the self-test plans at T = 640 × 4 lanes give 24 (full overlap) / 58 (0.6) / 72 (disjoint) lines on the busiest SM, the ATT4 balanced numbers (24 / 72). The calendar reserves 128 lines (`ATT_BUDGET`, above the model's upper bound 109 at disjoint). `IDX.KVUNION` itself is PRICED (row II table).

**R11. Users-mode HBM regions (`hsh`).** In users mode (`CTL.USERS`) every per-user HBM operand steps by its rs per row, with `hsh` = 12, so rs counts 4 KiB units and the 24-bit field reaches ±32 GiB. Per-user HBM = the HBM state some record of the layer writes, the HBM operands of `DMA.KVWB_DS`, `COLL.ROW_GATHER` (compressed-row source and list store), ATT and IDX, and every read overlapping them. **`IDX.INDEX`'s index keys are implicit** (no descriptor), so in users mode its ROWX carries `rs_I` (I itself absent) = the key-store step per row, shifted by `hsh` (the one exception to "no stride on an absent operand"; UNITS-IDX to implement). The emitter picks the smallest power-of-two user stride whose shifted regions collide with no other HBM interval of the segments (`emitter/mu/emitter.json` `users_hbm`). Weights, scales and tables keep rs = 0 (shared by all users).

**R12. ATT4 production front: lane masks, the KVWB window ring, the 32-SM spread** (CMTP step 5, answer to ATT4 10-19 03:05; no new field, all of it already in R8 / R10 / R11).
- **Lane-mask record = the plan block, not a separate record.** `IDX.KVUNION` writes, per SM s, the plan block at R.base + 320 s: line words 32 … 287 and the lane masks 288 … 319 in the `mw_data` layout of `ot_hnx_att4_issue` (line i, lane l = bit 4 (i mod 8) + l of word 288 + 2 ⌊i / 16⌋ + ⌊(i mod 16) / 8⌋). The ATT plan-mode record (`rsel` = 1, `emask` = 0, `rtab` = R.base) makes SM s load its block's 32 mask words and ≤ 256 line words before its first line beat; that load is inside the record's fixed span (the calendar reserves `ATT_BUDGET` = 128 lines a SM; a block over param [24:16] faults E_RANGE). ATT4's issue-side loader reads exactly these words; `isa_rows.plan_words` / `plan_lane_lists` are the reference (self-test decodes them as the engine does).
- **KVWB window ring record.** `DMA.KVWB_DS` with ROWX n = N (MTP: the N verify positions; users: N users) is ONE row record; row r writes position POS_SLOT(slot0 + r) to ring slot POS_SLOT(slot0 + r) mod 256 of O (O.m = 256 rows, 2,048 B a row; the ring address comes from the bank's POS_SLOT, never from ρ · rs). MTP: rs_O = 0, one ring shared by every lane (plan ring lane 0). Users: rs_O << `hsh` = the user's region, one ring a user (plan ring lane = the user's lane). A record that crosses slot 255 is two moves on the static calendar (the second at first_drain + chunks + 2, 16-edge lead; UNITS-SUDMA `tb_hnx_dma_kvwb_ring`): cost 36 + 8 (N − 1), +28 on a wrap. C5: the KVWB record precedes `IDX.KVUNION` and every ATT record of the segment (the emitter orders it; `static_check` C2 RAW).
- **32-SM spread.** The (lane, run) jobs go onto all 32 SMs by `kv_union_plan` step 4 (run k of all lanes one job when its union ≤ 0.75 × the lanes' sum, else one job a lane; LPT, lowest SM on ties, ≤ 16 nodes a SM). Busiest SM at T = 640 × 4 lanes: 24 / 58 / 72 lines at full / 0.6 / disjoint overlap (ATT4 balanced 24 / 72; the 20-SM aligned grouping's 128 at disjoint is not used). The cross-SM merge order is the lane map D[16 + 128 l + k] (run k ascending, the P = 1 pairwise merge per lane).

**HGI-1R 1.1 changes (CMTP step 4).** `rtab` grows to 19 bits (the 2^19-word VM, PROG 10-19); `emask` moves to [45:39]; new `hsh` [50:46]; reserved [87:51]. IDX op 6 = KVUNION; ATT plan mode. No implemented RTL decodes `rtab` / `emask` yet (SM4 builds `rpl` = 0 first; UNITS-COLL takes nm1 / rs_A / rs_O only), so nothing built changes.

## 4. Static timing contract

Every row of every record has a compile-time start cycle:

> start(row r) = issue + c1_overlap + r · (II_unit + rgap)

- **II_unit** is the unit's fixed row II (the table in §2: PRICED until UNITS measures it).
- **rgap** lets the compiler space rows to meet link and buffer slots.

The hardware never stalls a row for flow control: no credit, no ready and no backpressure on the die (owner 10-14). A row that would need a resource at a cycle another record holds is a **compile-time collision**. The static checker (`tools/hbm_next/static_check.py`) faults on it, and on any buffer over- or underflow. Off-die boundaries (HBM, SerDes, host) keep their existing elastic interfaces.

## 5. What the remainder-pass layouts buy (DS MTP verify, N = 6 on P = 4)

| SM pass plan | line issues per weight line | SM time vs AR record | note |
|---|---:|---:|---|
| D1 price (no split): 4 + 2 rows | 2.0 | 1.456 | lanes 2–3 idle in pass 2 |
| **K-split (`rpl` = 1)**: 4 rows, then 2 rows × 2 K halves, power-of-two chunk count | **1.5** | **1.092** | exact (R5); needs SM4's 2 accumulator sets per remainder row |
| K-split at K = 5,120 (20 chunks, tree split 16 \| 4) | 1.8 | 1.310 | |
| **row-split (`rpl` = 2)**: 2 rows × 2 output-row halves, an even row count per SM | **1.5** | **1.092** | exact; no extra accumulator |
| draft block N = 5 (g = 4), K-split or row-split | 1.25–1.4 | 1.0–1.02 | mostly hidden under the HBM share |

The compiler prices each SM record with its own K (chunk count nc) and its own rows per SM, and takes the cheapest layout (`best_rpl`). Rows per SM come from the SM layout rule (rows split over the die's SMs). The re-timed tok/s are in `results/arch/hbm_next_1019/cmtp/retime.md`.

## 6. Change process

This is an amendment draft under HGI-1 §9.5. It becomes normative for the next die when SM4 and UNITS land their decode and benches. Every UNITS row-II measurement replaces its PRICED entry in `isa_rows.py`, and the tables here are re-rendered from it. Lanes that need a field change ask CMTP; this file is not edited by hand.
