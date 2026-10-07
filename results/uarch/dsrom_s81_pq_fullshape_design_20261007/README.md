# S81 production PQ: full-shape partition design

Claude design, 2026-10-07. Not adopted and not physically qualified. Codex `pq_parent` owns the exact adapter proof, so this directory contains no RTL candidate.

`python3 tools/s81_pq_fullshape_design.py` regenerates `design.json`. The tool checks the hashes of Codex's read-only snapshot `pq_snapshot_1117`: `pq_parent_binding.py` b2d619a4, `full_inventory` 614fcd26 and `half_inventory` 4b38ddb1. These inputs are uncommitted until the owner's final gate. The tool also derives every width from the pinned RTL text (`ot_v41_spine_pqc_w17w10.sv` and `ot_v41_ret.sv`). It fails closed on any assertion listed in its docstring. `geometry_extract.json` is the die generator's model for the actual 1792-pair layer die, built in Python only with no ORFS run. Its options and generator hash are recorded inside the file.

## 1. Problem, re-derived

| Quantity | Value | Source |
|---|---|---|
| PHW / SAW / KMAX (both mappings) | 9 / 11 / 6,144 | snapshot inventories (half: 120 stages; full: 98) |
| PQ operand storage | bb 2·KMAX×16 = 196,608 + qb 2·(KMAX/32)×256 = 98,304 + eb 3,840 = **298,752 b** | spine RTL declarations; equals the inventory maximum |
| R128 screen 6/8/256 | 12,448 b, so production is **24.0×** larger | the same formula at KMAX 256 |
| Phase / stream ROM | 1,024×64 / 2,048×48, which is 3 `ot_rom_4096x72` | inventory |
| Native broadcast | **1,633 b** = cfg 13 + go 4 + q beat 549 + BF beat 1,067 | `bc_in`. `bt_b` and `bt_pos` are each sent twice, so only 1,627 distinct bits. |
| Legacy die lane | 564 b = x0 283, x1 266, cc 15. It has no BF data, no `go_bf` and no `go_tag`. | `dsrom_s81_fulldie.py` |
| Return per region | Legacy raw tree word 66 + {fault, busy} = 68. The root output is 69 b (v, row 16, pos 3, fp32, bf16, e). With fault and busy the lane is 71 b. | `ot_v41_ret_root` ports |
| Roots | ROOTD = QD = 128: 128×65 + 128×66 = **16,768 b each, 2,146,304 b for 128** | ret RTL declarations |
| Native parent pins | **19,529** from the snapshot `native_ports(9,11)`. Codex's DEF count is 19,355, which is 174 fewer (see the reconciliation request). | |

The R128 screen cannot qualify production for three reasons. Its storage is 1/24 of production and sits in flops. It has no macro read/write timing. It also lacks the native 1,633-bit bus, 128 real roots (each stateful, with its own rounding, counters and fault), and the VM read/write crossings.

## 2. Options

Areas are per layer die. Root, core-logic and RWB areas are **estimates** (see `estimates` in `design.json`) and are not closure evidence.

| Option | Partition | Largest block pins | Area added | Verdict |
|---|---|---|---|---|
| A: monolithic native | One R128 block holding the spine, 128 roots and the return path, with the 1,633-b lane | 19,657 | 2.66 + lane 21.5 | Reject. Not a closable block, and it pulls every region's root into the hub. |
| B: split, native lane | Roots in frames, 12 RWB in gather, core at VM north, 1,633-b lane | 4,156 | 2.66 + 21.5 | Reject. The lane infrastructure grows 2.9× and buys no function. |
| **C: split, union lane (W2)** | As B, but q and BF beats overlay one lane: **1,085 b** on BF dies, 567 b at q slots and q-only dies | 4,156 | 2.66 + **9.8** (BF dies only; 7.3 if BF slots sit at the column foot) | **Recommended baseline.** It is a pure re-wiring of the native fields with no stream change. |
| D: split, serial union (W3) | As C, but each BF beat spans two lane cycles: **568 b** everywhere, with a deserialiser at each BF slot | 4,156 | 2.66 + 0.14 + 0.25 deserialisers | Run in parallel with C. Adopt only after the measured BF-beat adjacency comes in and the exact gate passes. |
| E: central roots | Roots and RWB as one hub block next to gather | — | 2.34 compact | Reject. The hub columns are full (8 slabs, 173 µm channels), and the die has only 302 µm of x slack. |

Union rule: `f_xs_v` and `f_xb_v` are never both 1 in the same cycle (one streamer head plus the family bit; the tool asserts this from the RTL). The lane therefore carries `cfg_go, cfg_ph[9], cfg_np[3], go, go_bf, go_tag[2], b[3], pos[3], xs_v, xb_v` at bits 0–24. The q payload `p, sv, q0, e0, q1, e1` (542 b) and the BF payload `bsv[4], u[32], d[1024]` (1,060 b) both overlay bit 25 upward. The full layouts with lsb/msb are in `design.json.lanes`, and the tool asserts that every native field appears once and untruncated for its family.

## 3. Recommendation (C, with D launched in parallel)

### Partition

**128 `ot_v41_ret_root` (R128), one per region.**
- Placement: in the frame's empty q position. Each frame has 4 BF + 10 q = 14 pairs in 16 positions, so 2 positions are empty, at 510.84 × 183.6 µm each.
- Size: about 132 × 132 µm (estimate).
- Clock: the column clock, the same domain as the node tree, so there is no crossing.
- Faces: S `tree_in` 67 b, N `ret_out` 71 b into the existing `rstg` sub-column. Each face has a relay station within 100 µm.
- Storage: flops plus per-entry parity (256 b). SRAM would save only about 1.7k µm² per root while adding 2 macros, a 1RW/1R1W conflict and a read cycle inside the pairing loop.
- Microarchitecture obligation: the 128-entry associative search does not fit one 833 ps cycle. Register the match and free vectors, then encode in the next stage with bypass of the previous cycle's insert or remove, and register the queue head. Pairing decisions stay identical; each root pass costs +1 cycle.

**12 RWB, one per tier-half (10 or 11 regions).**
- Function: spine return stages 0–3, the per-tag configuration replica (458 b), VM write and row counts.
- Placement: inside `sp_gather`, abutting each `hr_<half><tier>` end block. The VM is 173 µm away.
- Pins: at most 1,843 per block.

**PQ core, at most 0.32 mm² (estimate).**
- Placement: the hub slot at the VM north face, 1015.2 × 794.9 µm. A WFC child soft reservation of 1015 × 449 µm currently holds it, so the die owner must relocate that reservation or widen the hub by up to 302 µm of die x slack.
- Pins: 4,156. The S face carries VM read (2,069) by abutment. The W/E faces carry the lane (1,085) to the `hx_W` and `hx_E` end blocks, which should move onto these faces. The E face carries the 3 ROM macros.
- Sub-blocks: `pq_xbuf` and `pq_ctl`.

### SRAM and control inventory

The macro is `ot_sram_1r1w_128x256_m1_r2c2`: 94.8 × 41.1 µm, 3,894 µm², min period 435 ps SS.

| Array | Macros | Layout |
|---|---|---|
| bb | 4 replicas × 8 = 32 | Word = 2 lanes × 8 subs × 16 b; row = hi (96 of 128 rows used). Each of the 4 BF byte groups reads its own row, so each owns a replica. One loader block writes 4 macros with full words. |
| qb | 4 banks | Bank = (index bit 3, bit 0); row = (i>>4)·4 + ((i>>1)&3), 96 rows used. The reads (blk0, blk1) and the writes (blk, blk+1) never share a bank. |
| eb | none | 3,840 flops |
| Protection | none | 64-b-slice parity, 14,208 flop bits; mismatch raises a sticky fault and fails closed. SECDED would need a compiled 1R1W 128×288 macro (+12.5 % width) and is priced as the alternative. |

The tool proves both macro maps exhaustively at KMAX 6144. Reads never occur during a write by protocol, because `have` lags the write edge; this is a bench assertion obligation. Total: **36 macros**, 0.197 mm² including halos.

### Clocks

The PQ core and the RWB run in `stream_1p2`. The VM is `serial_0p9`, so VM read and write cross through `ot_ratio_cdc_fifo` with credits. The roots and lane stations run in the column clock, behind the existing meso column FIFOs. Nothing runs at half rate; the D option is a full-rate two-cycle protocol with real enables.

### Flow control

| Interface | Design |
|---|---|
| VM read | Changes to request/response: the loader consumes `x_q` on its valid. The credit FIFO is 14 deep. Rate is at most 0.75 words per stream cycle, so an exposed K = 6,144 load costs about +64 cycles. |
| VM write | Per-region FIFO with credit, 12 deep. The root has no backpressure, so the mapping must keep each region's row rate at or below 0.75 per cycle over any window longer than the FIFO. This needs an input from Codex. |
| Broadcast and root input | Unchanged: timed, with no flow control. |
| Configuration replica | A 13-station chain. It must land before the op's first row; this is an assertion. |

### Cycle price

The conservative cost is 17 cycles per phase: root +3, plus the larger of the VM-write path (5) and the row-count retire path (14; 13 stations from VM north to gather). At the measured +1-return-cycle sensitivity (pq_qelem 1596.7 → 1596.2 tok/s) that is about **0.53 % AR**. This is a linear estimate on historical phases, not the 1792 geometry. The retire path is hidden whenever a free PQ slot exists and the issuer does not wait for idle.

### Dies

The design adds **0 dies** if roots fit in the frames, the RWBs fit in `sp_gather`, and the VM-north slot is provided. HALF needs the 1,085-b lane on 160 of its 480 dies; FULL needs it on all 392.

Fallback: a tier-channel row of root blocks (+143 µm per tier). If that costs a slot, the mapping drops to 13 pairs a region, which multiplies the stage count by 14/13.

## 4. Staged hardening (each block closable, with registered faces)

1. Run three blocks in parallel:
   - `ret_root_r128` (about 132 µm square, one master for 128 instances; exact gate with a mis-pairing negative control);
   - `pq_xbuf` (36 macros plus parity);
   - `rwb` (one master with N = 11 or 10).
2. `pq_ctl`, after the R128 screen's hierarchical area report.
3. Lane infrastructure in the die generator: column FIFO W1,085, x-chain stations 1,087 b, BF-slot stations. q-only dies carry the 567-b q lane (legacy 564 + 3).
4. The `pq_core` parent at VM north.
5. Die integration, then full-die SS/FF/DRC/IR.

## Requested inputs

- **(Codex)** Hierarchical cell area of the R128 screen, split into core and return side.
- **(Codex)** Per-stage maximum adjacency of BF beats from `native_stream`. This gates option D.
- **(Codex)** The maximum rows per region per window. This sizes the VM write FIFO.
- **(Codex)** Reconciliation of 19,355 DEF pins against 19,529 port bits.
- **(die owner)** The VM-north slot and moving `hx_W` and `hx_E` to the core faces.
- **(CDC owner)** The measured `ot_ratio_cdc_fifo` latency (4 cycles assumed).

## Gated items (all must pass before adoption)

- Root pipelined-CAM exactness.
- Union-lane don't-care proof plus its negative control.
- Exactness of the VM request/response loader change.
- VM write sustain rate.
- Synthesis screens replacing every area estimate.
- Die-generator legality.

## Reproducibility (added in 3b695b614 and later; the design record above is unchanged from d95b57661)

`inputs/` holds byte-exact copies of the Codex snapshot files the tool reads. `inputs/SHA256SUMS` pins them, and `inputs/REPO_INPUTS.SHA256SUMS` pins every repository file the tool reads. The tool verifies both lists and fails closed on any mismatch.

The default output is `reproduce/design.json`. `design.json` is kept as the historical d95b57661 output; it differs from the reproduced file only in the provenance keys `sources.snapshot` and `sources.snapshot_origin`.

A clean `git archive` rerun outside the home directory reproduced `reproduce/design.json` byte-identically. Two tamper tests (one snapshot input, one RTL file) each exit 1. Details are in `reproducibility.json`.

## Historical pin of the geometry generator (b0829f869 / 8a12d98ec)

`tools/dsrom_s81_fulldie.py` on main has changed since the pin (commit 5aba116fc). The exact generator that built `geometry_extract.json` is therefore pinned at `inputs/pinned/tools/dsrom_s81_fulldie.py` (553d47cc), and `REPO_INPUTS.SHA256SUMS` now points to that copy. A rerun from a `git archive` of origin/main 48890ca59, overlaid with this tool and the `inputs/` directory, reproduces `reproduce/design.json` byte-identically.

## Current-main basis (branch claude/s81-pq-fullshape-design-v2-20261007; historical verdict above unchanged)

Regenerate with these commands:
1. `python3 tools/s81_pq_geometry_extract.py --base-commit <main> --out current_main/geometry_extract.json`
2. `python3 tools/s81_pq_stream_stats.py --half <half matrix_map> --full <full matrix_map> --out current_main/stream_stats.json`. The matrix maps come from `tools/dsrom_bf_geometry_alloc.py` at 9a31097cd; the local rerun reproduced the remote hashes byte-for-byte (half 8dfa6dae, full bf7863a4; about 10 min and 1.6 GB each).
3. `python3 tools/s81_pq_fullshape_design.py --basis current`
4. `python3 tools/s81_pq_fullshape_compare.py`

The pins are listed in `current_main/inputs/REPO_INPUTS.SHA256SUMS`. Codex's inputs are now committed on main with the snapshot hashes, so the tool reads `tools/s81/pq_parent_binding.py` and `results/uarch/dsrom_s81_pq_parent_20261007/*_inventory.json` and checks their hashes. All changed numbers and their reasons are in `current_main/comparison_current_main.json`.

### What did not change

- **Generator.** The 5aba116fc drift only adds an exact-rectangle pin kind for the HBM VM8 retile. Rebuilding the S81 layer die with the pinned generator and with the current generator gives identical frames, slots, corridors, hub, end blocks and stations.
- **Inventories and mappings.** Stages, dies, pins, lane widths (1,633 / 1,085 / 568), SRAM (36 macros) and roots are all unchanged.

### What changed

- **Spine source.**
  - The production native partition (Codex's `native_elaboration.json`) is built from the v13b spine at d0178820d (ecac11e1), not main's older `rtl` file; v13b is pinned under `current_main/inputs/rtl`.
  - Width, field order and storage are unchanged.
  - v13b has RG 8 and RPT 2, a two-stage BF16 read, the aq12m quantiser, +1 row-write cycle and +1 configuration cycle. These latencies belong to the reference spine; the partition does not add them.
- **Cycles: 17 → 15 per phase (estimated AR loss 0.53 % → 0.47 %).**
  - The v13b parent already pays RPT 2 on its root inputs. In the split design, the end block abuts the RWB, so those repeaters are replaced rather than added.
  - This is still a **partial price**. The 1,792 per-token critical-phase list (46,681 compiled phases, of which only the token-active subset is on the path) is not composed.
- **VM write FIFO: 12 (HALF) and 14 (FULL).**
  - Measured: at most 10 rows per region per phase (HALF) and at most 14 (FULL).
  - Because the FIFO holds the whole burst, the earlier requirement that the VM side sustain 0.75 rows per cycle is retired.
- **Serial lane (option D).**
  - HALF has at most 2 back-to-back BF beats and adds 0 phase-end cycles; beats shift by at most 2 cycles.
  - FULL has runs of up to 6 and costs 1,280 cycles over 139 BF phases, at most 32 per phase.
  - Refinement: **D becomes the preferred lane for HALF BF dies** (+0.4 mm² versus +9.8 mm²), subject to its exactness gate on beats delayed by up to 2 cycles. FULL keeps C.
- **RWB is pin-limited.** The 722 / 794 return pins on one face give outlines of 221 × 140 and 243 × 140 µm at about 15 % cell utilisation. Total RWB area becomes 0.397 mm² (was 0.102 mm²). They still fit in the end-block columns beside `sp_gather`.
- **Budget sheets.** Each hardening-stage block now has pins per face, the face length those pins need (3.26 pins/µm), area, and a clock-insertion target taken from the measured mean of the nearest measured analogue block in `results/rtl/budgets_20261006/measured_insertion.json`. These are targets, not measurements.

| Block | Insertion target, SS / FF (ps) | Analogue |
|---|---|---|
| Root | 373 / 238 | `ot_s81ph_root_tile` |
| RWB | 427 / 267 | `dsfd_cfifo` |
| PQ core | 620 / 373 | q-element |
| Lane station | 140 / 74 | `dsfd_stnh_566x1` |
