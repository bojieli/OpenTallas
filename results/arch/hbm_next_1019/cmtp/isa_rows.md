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
| 37:20 | `rtab` | no | rsel: VM word address of row-table row 0 (32-word aligned, < 2^18); else 0 |
| 44:38 | `emask` | no | rsel: bit k (A..I order) = operand k steps by the entry's e field instead of rho; else 0 |
| 87:45 | `rsv45` | no | reserved, 0 |
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
| IDX.UNION | 5 | none; imm_a = experts E (DS 384); imm_b = slot pitch K (DS 6, e = rho x K + kappa) | A = U32 top-k ids, m = N rows of n = k, each row strictly ascending (IDX.TOPK order 1); O = U32 union ids ascending (O.n >= U); D[0] = U (a CTL.LOOP [17] count); R = U row-table rows of 32 words (R.stride = 32): word 0 = c_u, words 1..c_u = entries {rho, e} in ascending rho, kappa = rank of u in row rho |
| CTL.USERS | 8 | [3:0] N - 1 when no ROWX (slot0 = 0); with ROWX: N, slot0 | A = U32 [2 N]: {token_s, pos_s} for s = 0 .. N - 1; sets DYN bank slot0 + s: POS = POS_SLOT = pos_s, POS1 = POS_SLOT1 = pos_s + 1, TOKEN = token_s, SLOT = slot0 + s, DS selectors (16..62) from pos_s; range-checked against cp_vocab / cp_ctx_max |
| CTL.TOKX | 5 | [0] users: 0 = MTP commit (k beats at pos + i - 1), 1 = one beat per user slot | A = U32 [1 + n]: A[0] = k (MTP: 1 <= k <= ncol) or N (users), A[1..] = tokens; completion beats {token, pos, slot} (users: pos = bank POS of slot0 + i); END follows |
| CTL.ACCEPT | 7 | none | A = U32 [1]: a = accepted drafts (0 .. ncol - 1); commit n <- n + 1 + a; IDX.EHASH history restored to slot a; no other state rolls back (rule R-POS) |
| SM.MATVEC | 0 | [1:0] fmt, [5:2] positions - 1 (HGI-1 [4:2] widened; with ROWX it must equal N - 1, or 0 with rsel) | unchanged |

**Row II (cost of an N-row record = c1 + (N - 1) (II + rgap))**

| Family | II (cycles) | Basis | Source |
|---|---|---|---|
| SM.MATVEC | pass plan | PRICED | sm_pass_plan: line issues / max(1, issues per line / 1.374) of the AR record |
| ATT.QK/PV | union stream | PRICED | fixed spans once + comp x U(N)/U(1) a pass, passes = ceil(N / P); E1 PASS (att4/E1.md) |
| FUSED.HC_PRE_NORM | 197.0 | MEASURED | P6 RTL 8fe5d18bd: (1,451 - 466) / 5 |
| FUSED.HC_POST | 100.0 | PRICED | SU chain 25,600 words / 256 |
| FUSED.QDQ_* | n / 32 | PRICED | quantiser 32 elements a cycle |
| HC.HC_MIX* | 250.0 | PRICED | HCP W256 x6 measured II 250; Sinkhorn 634 / 3 units; GATE <= 950 (STUDY d), static engine 4,385 FAILS |
| COLL.* | c1 - 741.7 | PRICED | one message train: endpoint + crossing + tail (741.7) once, payload x N |
| IDX.TOPK | 47.0 | PRICED | router top-6 RTL 47 cycles a row |
| IDX.INDEX | c1 x 152 / 658.9 | PRICED | one key stream; query ingest 152 of the 658.9-cycle frame a row |
| IDX.UNION | N x 6 / 8 + 24 | PRICED | 8 ids a cycle into a 384-b bitmap + per-expert table write (CMTP estimate) |
| SU.VOP | su nv | PRICED | timing.su_cost at 2 m minus m: lane beats a row, depth once |
| DMA.* | c1 - first access | PRICED | first access once, rows at full bandwidth |
| ARGMAX.LOCAL | 6.0 | PRICED | per-row reduce tail |
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
- **Pass plans:**
  - DS MTP verify (N = 6): pass 1 runs positions 0–3 on lanes 0–3; pass 2 runs position 4 on lanes 0–1 and position 5 on lanes 2–3, each pair split by K or by rows. That is 1.5 to 1.8 line issues per line against 2.0, so the SM time is max(1, issues / 1.374) = 1.09–1.31× AR against 1.456×.
  - The draft block (N = 5, g = 4): 1.25 to 1.4 issues, at most 1.02× AR.

**R6. Expert union (gate E2).** The golden's `moe` sums a position's routed experts in **ascending expert id** order, sequentially from +0, with each route weight applied inside the expert before w2. It then adds the shared expert and rounds once to BF16 (`hdc_golden_v41.Model.moe`, read 2026-10-19).

The union form keeps this order exactly:
1. `IDX.UNION` turns the N rows' ascending top-6 lists into the ascending union, the loop count U and one row table per union expert. The tables list (ρ, e = 6ρ + κ), where κ is the rank of u in position ρ's own list.
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
