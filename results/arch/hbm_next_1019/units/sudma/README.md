# HBM-NEXT-UNITS-SUDMA: N-row SU / DMA / ARGMAX records (next HBM die, P = 4)

Lane HBM-NEXT-UNITS-SUDMA, 2026-10-19. Branch `claude/hbm-next-units-sudma-1019`. This is next-release work, not a release gate.

All benches ran on the fleet with Verilator 5.050 (`verilator.txt` in each folder), using `tools/hbm_next/hnx_sudma_bench.sh` from a `git archive` bundle. Each folder holds the verdict file, every run log, and the mutant fail witnesses.

## Measured row II against the price (CMTP `isa_rows.py` row-II table)

| Record | Engine (d4g master unchanged unless stated) | cycles(N), first command to last write | Measured II | Price | Verdict |
|---|---|---|---:|---:|---|
| SU.VOP un-indexed, `AB` (A per row, B broadcast), n = 7,168 (nv = 14 vectors of 512) | Whole static SU `ot_hbm_su_static_top` behind the new `ot_hnx_su_rowx` | N1 160, N2 204, N3 248, N4 292, N6 380 | **44** | su nv = 7 | EXACT. The II is 6.3x the price. |
| SU.VOP un-indexed, `ABC` = bf16(A·B + C), A and C per row | same | N1 216, N4 432, N6 576 | **72** | 7 | EXACT. The II is 10x the price. |
| SU.VOP indexed (route gather A[I] → O) | `ot_hnx_su_indexed_scalar_rows` (copy of the H-MTP2 successor). R1 = the d4g single-row engine, 36 = 36. | R1 36, R2 37, R3 38, R4 39, R5 40, R6 41, R8 43 | **1** | 1 | EXACT, matches the price. |
| DMA.KVWB_DS into the 256-slot ring | die master `ot_hgi_dma_back_static_vp4_banks`, no RTL change | R1 36, R2 44, R3 52, R4 60, R6 76. R6 at slot 200: 76. Ring wrap R6 at slot 253: 104 (2 moves). R4 at slot 255: 88. | **8** | ~2 (c1 − first access) | EXACT. II is 4x the price. A wrap costs +28 once per ~256/N steps. |
| ARGMAX.LOCAL | `ot_hnx_argmax_static_rows` (copy of the H-MTP2 successor) on the real SW VM slice and the closed argmax18 engine | P1 211, P6 1,056 (P6 packed 1,058) | **169** | 6 | EXACT on 3 seeds. II is 28x the price (VM read is one sector per edge). |

Notes on the table:
- **SU.VOP N = 1 is the d4g SU bit for bit.** With row code 0, `ot_hnx_su_rowx` passes every word unchanged, one edge later.
- **`ab_n4_abs`** is the unrolled d4g image: absolute addresses, row codes 0. It runs the unchanged d4g SU and produces the same expected files and the same 292 cycles as the row-relative image. The row counter therefore changes programme capacity, not time.

## SU.VOP row counter (highest risk; new RTL)

**Mechanism.** `rtl/hbm_next/su/ot_hnx_su_rowx.sv` sits between each quarter's programme producer (the 2422-bit line) and the quarter. It changes control only.
- The programme holds row 0's commands, plus a 20-bit row code for each edge and quarter. The row code is the "4-b N field + stride select" of D2_PLAN §3.5.
- The record's ROWX strides are static inputs. The CP converts them to SU units: VM sector, store row, and control vector base.
- For each valid command, the stage adds row × stride to:
  - the vmr sector and store row (per read operand A to I);
  - the vmw sector and store row (O and R);
  - the five control `vb` fields.
- **Fault checks:** a sector that leaves its quarter, or a vb that leaves its 128-row frame.
- **Timing:** REG 1, so the compiler's start advance grows by 1 edge.

**Why it is needed: capacity.** Distinct 256-bit column words over the image (`programme_*.json`, `dict_words_per_col`):

| Image | N1 | N4 | N6 |
|---|---:|---:|---:|
| `AB`, row-relative | 805 | 981 | 981 |
| `AB`, absolute (d4g unrolled) | 805 | 2,357 | 3,349 |
| `ABC`, row-relative | 1,029 | 1,365 | 1,365 |
| `ABC`, absolute | 1,029 | 3,157 | 4,501 |

The row-relative dictionaries stop growing at N ≥ 3. Only the edge-index table grows, with the record's edges.

**Why II is 44 and not nv = 7: the binding resource, measured.**
- Each pinned store bank has ONE write port, shared by the VM fill and the lane result. `ot_hbm_su_static_pgslice` faults if both land on one edge (`st_conflict`).
- So each row costs 2·nv write edges per per-row VM operand (32 VM ports fill one 512-word vector every 2 edges), plus nv result-write edges:
  - II = (2k + 1)·nv + 2, where k is the number of per-row VM operands;
  - `AB`: k = 1, so II = 44;
  - `ABC`: k = 2, so II = 72.
- The lanes (one vector per edge) and the drains (vmw reads) are not binding.
- The schedule with guard 0 (`ab_n4_g0`, II 42) FAILS on the DUT's own slice fault. That is the fail witness that the write port binds.

**What the price misses.** The model's `su nv` assumes 1,024 lanes and does not count the VM fill or the store write port. Per row, the real SU costs about 6 to 10 times its price.
- Absolute size is small. SU busy is ~157k of a 1.28M-cycle P = 6 verify. The SU_DMA lever is worth 38.7k cycles (D1).
- But the per-row SU cost should be re-priced as II = (2k + 1)·nv512 + 2 in `isa_rows.py`. That is CMTP's call.
- The fix that would reach the price is a datapath change: a second store write port, or fill bypass into the lane operand. It is outside this lane's "control only" scope, and it is not proposed, because the SU is not the bottleneck.

**Bench.**
- Files: `rtl/hbm_next/su/tb/tb_hnx_su_rows.sv` (fork of `tb_hbm_su_static_top`) and the generator `tools/hbm_next/su_rows_compile.py`. The golden is `hdc_golden` mul/add/bf16 in NumPy, independent of the DUT.
- What is checked: every LG write (edge, quarter, port, sector, mask, data), the lane write count on every edge, zero DUT and rowx faults, and that every expectation is consumed.
- Positive cases: `AB` at N = 1, 2, 3, 4, 6 and the N = 4 absolute image; `ABC` at N = 1, 4, 6.
- Mutants (N = 4), one per new mechanism:

| Mutant | What it breaks | Result |
|---|---|---|
| MUT 1 | vmr sector stride | FAIL, 2,688 errors: rows 1 to 3 compute on the wrong A (`run_s1_ab_n4.log`) |
| MUT 2 | control vb stride | FAIL, 2,688 errors: rows 1 to 3 write zeros (`run_s2_ab_n4.log`) |
| MUT 3 | vmw sector stride | FAIL, 2,688 errors (`run_s3_ab_n4.log`) |
| MUT 4 | store-row stride | FAIL, 2,688 errors: rows 1 to 3 overwrite row 0's store rows (`run_s4_ab_n4.log`) |

## DMA.KVWB_DS into the 256-slot ring (CMTP R8 / R-POS)

**Mechanism: compile time only, no RTL delta in the d4g master.**
- In d4g the HBM address comes from the move227 that the collar fires. The ring index is the compiler's (POS_SLOT mod 256): 8 bits, which is the "+1 index bit".
- An N-row record is ONE move with m = N (dense, 2,048 B a row).
- A record that crosses slot 255 is split into two moves. The split move is commanded on the calendar after the engine releases, at first_drain + chunks + 2, with a 16-edge lead. The engine faults on a move while busy; the first bench draft hit that fault, and its log was superseded.

**Bench:** `rtl/hbm_next/dma/tb/tb_hnx_dma_kvwb_ring.sv`. It checks every beat's HBM sector, lane, payload and fixed edge (drain + K + ord/8, K = 2).

**Mutants, all FAIL:**
- MUT 1, the 7-bit (d4g 128-slot) index: bad slots;
- MUT 2, no wrap split: the move writes past slot 255;
- MUT 3, the VM row stride dropped.

## Indexed route gather and ARGMAX.LOCAL rows

Both are hnx copies of the H-MTP2/sudma successors from 10-16 (`64e68da45`). Those were measured then on Verilator 5.032 or Icarus; they are now re-run on 5.050. The ARGMAX bench, vector tool and RTL were restored from `64e68da45` with hnx names; the SW slice and argmax18 changes since then are default-compatible.
- **Gather:** R1 36 equals the d4g engine's `fixed_cycles` 36. MUT 1, 2 and 3 FAIL.
- **ARGMAX:** 3 seeds PASS. The 4 faults are the deliberate illegal records. MUT 1, 2 and 3 FAIL on every seed.

## Not done (next list, in risk order)

1. **Row code and stride as real programme columns.** Add a 20-bit row column to `ot_hbm_su_programme_pslice_q4` / `pslice_c5` (an 11th column, or bits of column 9's 118 unused bits), and the ROWX strides to `su_programme_root_h5`. `sfu_programme_store_r10` is a CRITICAL prefix: report only, with no REVIEW.json and no submit. `ot_hnx_su_rowx` itself is the gateable tile, with an hnx kit.
2. **Reducer row class** (red a/b/dst scratch and RF tag stride) for norm-style SU.VOP rows with per-row reductions. Without it, the compiler gives each row its own scratch words in the image, and only the red column dictionary grows.
3. **SFU chain row stepping** (`ot_hgi_sfu_core_split3`, `sfu_lg_pair_tap_leaf*`). The store already loops (`start_loops`); the address step per loop is still to do.
4. **FUSED.QDQ rows** (host `hb_quant_*`, n/32) and position-addressed **DMA.LOAD** rows. Neither was measured here. H-MTP2 found no die-bound static load-record engine; the load path is the HBM service VM delivery.
5. **CMTP re-price** of the PRICED row-II entries:

| Family | Measured II |
|---|---|
| SU.VOP | (2k + 1)·nv512 + 2 |
| DMA.KVWB_DS | 8, plus 28 a wrap |
| ARGMAX.LOCAL | 169 |
| indexed SU gather | 1 |

## Files

- RTL:
  - `rtl/hbm_next/su/ot_hnx_su_rowx.sv`
  - `rtl/hbm_next/su/ot_hnx_su_indexed_scalar_rows.sv`
  - `rtl/hbm_next/argmax/ot_hnx_argmax_static_rows.sv`
- Benches:
  - `rtl/hbm_next/su/tb/tb_hnx_su_rows.sv`
  - `rtl/hbm_next/su/tb/tb_hnx_su_indexed_rows.sv`
  - `rtl/hbm_next/dma/tb/tb_hnx_dma_kvwb_ring.sv`
  - `rtl/hbm_next/argmax/tb/tb_hnx_argmax_rows.sv`
- Tools:
  - `tools/hbm_next/su_rows_compile.py`
  - `tools/hbm_next/hnx_argmax_rows_vectors.py`
  - `tools/hbm_next/hnx_sudma_bench.sh` (stages g, d, a, s0 to s4)
- Evidence: `su_vop/`, `gather/`, `kvwb/`, `argmax/`. Bundles: SU at `09d204bf0`, KVWB at `00c8e4f22`, ARGMAX at `55d57ac5a`, gather at `09d204bf0`.
