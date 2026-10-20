# S81-SCAND: option D with a measured index-scan reader (10-18)

Lane S81-SCAND. Coordinator decision 0iq adopted option D (S81-BALANCE B3): spread each full-scan layer's index keys
over the HBM stacks of the dies that already hold the layer, and score all 6 MTP positions per key read.
This lane replaces the modelled reader term with a measurement and records what the RTL on p4l does and does not do.

Files:
- `scand_bench.py` is the fleet bench driver. It produced `reader_1stack.json` on ot-epyc5 with Verilator 5.050.
- `scand.py` writes `scand.json`, the composition per k.

## 1. RTL check on p4l (bind9)

| question | answer | evidence |
|---|---|---|
| Is an index reader/scorer bound on p4l at all? | **No.** bind9 instantiates `dsdv_svc_rs` / `_entry` ×16, `dsdv_bk_sel`, `dsdv_bk_col`, the G-unit, seq_host, slices, frames, ctrl and PHY. None of them contains the IDX_Q parser, query store, key stream or `ot_hdc_v41x_idx_score_quarter`. `dsdv_svc_att` decodes frame types 1, 2, 3, 5, 6, 7, 9, 12 and 13, but not type 4 (IDX_Q). The S81-PH reader `dsfd_svc_idx` / `ot_s81_svcq_idx` has no S81-DV successor ("re-home … idx reader": S81U-SVC open item 3, never done). | `results/arch/s81_dv_1016/bind9/die.v.gz`; `rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv` |
| (a) Does it accept a partial top-k from other dies and merge it? | **Yes, as a design mechanism; unverified on p4l.** The token path already merges partial top-k across dies. Each TP4 rank runs a local top-512 (`topk_local`), then `topk_merge` all-gathers 4 × 512 (551 cycles), then `topk_final` selects over them (178 cycles, measured on `ot_hdc_v41x_sel`, whose arithmetic is `bk_sel`'s). Option D widens this to 4k × 512 candidates and adds one q fan-out/return leg pair per stage of distance (729 cycles, measured). No new kind of RTL is needed. However, the p4l binding of the candidate path (edge link → `bk_sel` V rung, BEAT + REBASE words) is not proven for D, and it is not proven for today's TP4 merge either. | `results/arch/token_path_20261009/ds_rom.json` `L*.attn.idx.topk_*`; `results/rtl/dsrom_reindex_candidates_20261004/select.json` |
| (b) Does it score 6 queries per key read? | **No.** The scorer (`ot_s81_svcq_idx` → `ot_hdc_v41x_idx_score_quarter`, NK 4 × 4 slices) holds one query (32 heads) and scores 16 keys/cycle. One stack delivers about 11.7 keys/cycle (measured: 262,144 keys in 22,461 cycles). Time-multiplexing 6 queries would therefore be scorer-bound, at 6 × N / 16 cycles. That gains only 1.37× over 6 separate reads, not 6×. Full B3 needs 6 query stores, about 4.4× the score MACs (≥ 70 key-queries/cycle) and 6 concurrent top-k selections a die. `bk_sel` has 4 quarter tiles, of which 1 is fed at 1 stack, under a single-segment control. | `rtl/dsrom_sys/s81_ph/svc/q/ot_s81_svcq_idx.sv` header; `reader_1stack.json` |

**RTL written: none.**
- The smallest change that (b) needs, a multi-query scorer, would modify an element that is not on the die.
- What comes first is binding an index reader on p4l (S81 die lanes). It adds area on the `svc_rs` region (plan `facts.rsv.content` "svc 1/16 13.43 mm² estimate, no RTL").
- B3 is therefore **not 0 mm²**: it scales the scorer and the selector and is unpriced.
- No closed tile is touched. `dsdv_svc_rs` and `bk_sel` are not closed, so nothing was submitted.

## 2. Measured 1-stack reader (option D key layout)

**Bench.** The 10-04 W11 quarter-per-stack reader (`ot_hdc_v41x_idx_kstream_range` plus the per-PC refresh-aware HBM model, NPC 32). Every key, mask, last flag and refusal bit is checked.
- Each bench stack is one p4l die (1 HBM3E stack) scanning M = ceil(K_rank / k) keys.
- The slower of two ring placements is charged.
- CLK 833 ps, WB 128, GA 120.
- The HBM model has had its REFpb fix since 10-04. The 65,536-key run gives 5,801 cycles against the 10-04 5,821.

| per-die keys | used for | cycles (p1 / p2) | charged |
|---|---|---|---|
| 262,144 | L20 k=1 (today's p4l) | 22,461 / 23,066 | 23,066 |
| 131,072 | L20 k=2, L2 k=1 | 11,636 / 11,462 | 11,636 |
| 87,382 | L20 k=3 | 7,700 / 7,581 | 7,700 |
| 65,536 | L20 k=4, L2 k=2 | 5,801 / 5,794 | 5,801 |
| 43,691 | L2 k=3 | 3,724 / 3,654 | 3,724 |
| 32,768 | L2 k=4 | 2,835 / 2,763 | 2,835 |

The idx.score node is the reader plus the +116 adders, unchanged. At D k=3 the nodes come out as:
- **L20:** 7,816 cycles, plus 1,814 for the leg pair and the 12 × 512 merge, against a price of 5,937.
- **L2/L8/L14:** 3,840 + 1,814 against 2,951.
- **Re-index L24–L36:** unchanged by D (SCANCHK price, +783).

## 3. Composition and ledger

| k | AR tok/s | MTP tok/s | e2e loss AR / MTP (DAG basis) |
|---|---|---|---|
| 1 (p4l today, measured) | 1,185.6 | 3,455.7 | 5.34 / 10.15 % |
| 2 | 1,212.4 | 3,635.3 | 2.86 / 4.98 % |
| **3 (adopted)** | **1,224.1** | **3,711.7** | **1.77 / 2.76 %** |
| 4 | 1,221.6 | 3,709.9 | 2.00 / 2.81 % |

- **k=1 check:** it reproduces SCANCHK's priced 1,186.4 / 3,454.7.
- **D k=3 against the model:** it matches the modelled 1,223.8 / 3,710.2.
- **B3's 3,829 is not reachable** without the multi-query scorer described in section 1.

**MTP is back under 5 %: 2.76 %.** Ledger row S81.SCAN_STACKS_P4L is updated to D k=3:
- measured 9,630 against price 5,937;
- `within_unit_limit` true;
- status proposed;
- S81 proposed total 11.05 → 3.63 %, and accepted + proposed 13.11 → 5.69 %.

`tools/token_compose_xdie.py` now charges `scand.json` by_k.3 with these terms:
- the reader part as measured-old-RTL;
- the legs and merge as priced;
- the re-index gathers as priced;
- the wave term as priced.

DS ROM in `token_path_1018`: AR 1,186.4 → **1,224.1**, MTP 3,454.7 → **3,711.7**. Checks: CHECK PASS, and `tests/test_token_compose_xdie.py` passes 15 tests.

**Assumptions** (single-user exact, unverified for multi-user):
- The neighbour stages' stacks are idle during the L20/L2 scan in AR.
- In the MTP wavefront the borrowed dies' HBM is shared with their own layers' window and CKV reads, under a static, compiler-placed schedule that is not measured.
