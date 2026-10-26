# TP8 collective cluster: physical spec (qwen-tp8/coll, 2026-10-12)

This is the physical spec for `ot_coll_tp8_die` (`rtl/rom/ot_coll_tp8_die.sv`), the collective of SPEC.md section 3. It is built as one hardened cluster through `tools/ref_tile`. The spec file is `tools/ref_tile/specs_qwen_tp8/coll_tp8_rt.json` and the kit is `physical/ref_tile/coll_tp8_rt`.

## Contents

- **Cross-package engine.** The TP4 engine `ot_rom_oneshot_die_m` is reused unchanged with the MARGIN-8 parameters of `qfd_io_collective` pr2s: PR 2, TXK 1, FPIPE 2, IBH 1, MEMM 1, FSL 1, DEPTH 32. It contributes:
  - 4 hardened `ot_coll_fold_slice` children;
  - 4 source FIFO macros (`ot_sram_1r1w_32x546_m1`).
- **In-package pre-fold.** 4 more instances of the same hardened `ot_coll_fold_slice` master (closed as `coll_fold_slice_rt-rt1-ae9fa22a9`), fed `{0, 0, hi, lo}`. No new hard child is introduced, and no parameters are set on children.
- **Credit-managed queues.** 9 more `ot_sram_1r1w_32x546_m1` macros:

  | Queue | Macros | Purpose |
  |---|---|---|
  | LB | 2 | local partials |
  | PQ | 2 | peer partials |
  | EQ | 1 | engine feed |
  | LQ | 2 | local results |
  | TQ | 1 | results to the peer |
  | RQ | 1 | peer results |

  The small IB queue (8) and the message-mode queue (32) are flops.
- **Totals.** 8 hard children (181.44 × 181.44 µm) and 13 SRAM macros (177.768 × 81 µm).

## Outline and floorplan

The cluster outline is **1,123.2 × 950.4 µm** (8.64 µm lattice). Children sit on the 43.2 µm lattice, all in R0. Every channel is at least 34 µm, and every block is at least 41 µm from each face.

| Column | x (µm) | Contents (y from S) |
|---|---|---|
| A | 43.2 | LB0, LB1, PQ0, PQ1, RQ, TQ, LQ0 (macros, pitch 129.6) |
| B | 259.2 | pre-fold slices 0-3 (pitch 216); src W, sum E |
| C | 475.2 | EQ (bottom), LQ1 (top); the middle is glue: pairing, the engine's heads/s0, and the merger |
| D | 691.2 | engine fold slices 0-3; src W (from the heads in C), sum E |
| E | 907.2 | engine source FIFO macros 0-3, under the SerDes face |

**Die slot.** The cluster replaces `qfd_io_collective` and needs about 1.07 mm² against TP4's 0.34 mm² (529 × 643). It fits inside the TP4 `io_coll*` slot (2,302 × 1,564 µm). Reserve 1.5× that slot (about 2,820 × 1,915 µm) for the 3-port SerDes adapters and the UCIe adapter, which sit beside the cluster.

## Port faces and pin plan

Pins are grouped by base name, as `ref_tile` requires.

| Face | Ports | Bits |
|---|---|---|
| W, UCIe (the in-package peer abuts on the UCIe edge) | `up_*` (P tx: valid, rec[546], ready, cr_in), `dp_*` (P rx: valid, rec[546], cr_out), `ur_*` (R tx: rec[514]), `dr_*` (R rx: rec[514]) | about 2,130 |
| E, SerDes | `sx_*` (3 ports tx: valid[3], rec[3 × 546], ready[3], cr_in[3]), `sr_*` (3 ports rx: valid[3], rec[3 × 546], cr_out[3]) | about 3,290 |
| S, local | `in_valid`, `in_cr`, `in_data[512]`, `in_last`, `in_mode`, `in_tag[32]` (the sequencer side, as TP4) | 548 |
| N | `clk`, `rst_n`, `out_valid`, `out_data[512]`, `out_last`, `out_rank[3]`, `out_err`, `fault`, `fault_code[5]` | 525 |

On the E face, SerDes port j connects to package (PKG + 1 + j) mod 4. Each port has its own registered copy of the engine's tx record, so each copy can sit at its own port band.

## Registered boundaries

- **Inputs.** Every input lands in a pin flop: `in_*`, `dp_*`, `dr_*`, `sr_*`, all ready and credit inputs.
- **Outputs.** Every output leaves a flop: `in_cr`, `up_*`, `ur_*`, `sx_*`, `dp_cr_out`, `dr_cr_out`, `sr_cr_out`, `out_*`. `fault` and `fault_code` are sticky registers.
- **No same-cycle cross-block handshake.**
  - All links are credit-based: P credits = PQ depth (64), R credits = RQ depth (32), engine local credits = 4, SerDes credits = the engine's DEPTH 32.
  - Reservations bound every queue that has no back-pressure (engine results: LQ 1 per reduce word or 4 per gather word, TQ 1 per reduce word).
- **Macros.** Every macro read is captured in the queue's 2-entry output buffer before any logic.
- **Clock.** The cluster uses a clock spine (the `ref_tile` default for clusters), with leaf targets that include the slices' TT insertion.

## Latency (bench, UCIe 14 / SerDes 40 cycles)

See `el1011-qwen-tp8.log` for the bench cycle counts. The pre-fold adds the 23-cycle slice pipeline plus about 2 × 14 UCIe cycles. Each die folds only half the words through the engine, which cuts the serialisation of the cross-package level to 128 words.

## Open item

PKG and DIE, like the TP4 engine's RANK, are synthesis parameters. The route uses the representative PKG 0 / DIE 0. A single die mask for all 8 dies needs them turned into straps. That is a change to the engine, so it belongs to the TP4 line `el1011-q-coll`.

## Cut analysis (owner rule "CUT ANALYSIS BEFORE RTL", 2026-10-12) and the v2 floorplan

Reproduce with `python3 tools/qwen_tp8_coll_cut.py`.

**Capacity.** Horizontal tracks across a vertical cut: M4 (48 nm pitch, 20.8 tracks/µm, no cluster PG) plus M6 (64 nm pitch, minus the M6 PG pair, 13.5 tracks/µm). M2 is held back for cell-local wiring, and M7 is vertical. A track counts only over the y-span that no block blocks on that layer. The fold slice blocks M1–M6. The SRAM macro blocks M1–M4, so M6 passes over it.

**Faces.** The W (UCIe) face carries 2,130 pins, 2.24/µm. The E (SerDes) face carries 3,290 pins, 3.46/µm. Against M4 + M6 pin slots at 2 tracks per pin (about 17 slots/µm), these use 0.13 and 0.20 of the face. In v2 the S face carries 548 pins over x 43–302 on M5, 0.22 of its slots.

**Per-cut results.**

| Cut (column middle) | v1 demand / tracks | v1 util | v2 demand / tracks | v2 util |
|---|---|---|---|---|
| A, queues | 3,291 / 20,818 | 0.16 | 2,160 / 19,130 | 0.11 |
| B, pre-fold slices | **4,315 / 7,713** | **0.56** | 1,166 / 7,713 | 0.15 |
| C, glue | 5,298 / 29,255 | 0.18 | 5,298 / 30,943 | 0.17 |
| D, engine slices (unchanged TP4 engine) | 3,250 / 7,713 | 0.42 | 3,250 / 7,713 | 0.42 |
| E, engine FIFOs | 2,184 / 25,880 | 0.08 | 2,184 / 25,880 | 0.08 |

**v1 fails at column B.** The slices leave only 224.6 µm of the 950.4 µm height free on M4 and M6. Through that space v1 routes all the queue traffic between column A and the glue in column C: the LB and PQ heads, the LQ0 and RQ reads, the result bus, and the S-face input. On top of that, 1,024 pairing wires leave column C and wrap around to the slices' W-face src pins.

**v2 restructure (`coll_tp8_rt2`).** The outline grows to 1,166.4 × 950.4 µm.
- **Column A at x 43.2.** It holds 8 macros at a 108 µm pitch, bottom to top: LB0, LB1, PQ0, PQ1, TQ, RQ, LQ0, LQ1. The result queues and the merger now sit by the UCIe R pins, and LQ1 leaves column C.
- **Pairing channel.** An 81 µm A|B channel holds the pairing logic, which faces the pre-fold src faces directly.
- **Columns B–E.** B is at x 302.4. C (EQ and the engine heads) is at x 518.4, D at 734.4 and E at 950.4.
- **Pin ranges.**
  - S face: `in_*` over x 43–302.
  - N face: `out_*` and `fault*` over x 43–302; `clk` and `rst_n` over x 562–605.
  - W face: `up_*` and `dp_*` over y 43–475; `ur_*` and `dr_*` over y 475–907.

**v2 result.** The worst cut is 0.42, at the unchanged engine column D. The RTL is unchanged, so the benches stand.

**IO hold (lesson from TP4 pr2s-835975149).** pr2s failed FF hold at −67.7 ps, with 2,194 input-to-register endpoints at −384.6 ps. Its IO reference was the internal register `*s0_v*`, which sits about 400 ps later than the input pin flops. Both ref_tile kits instead take the reference from the median input pin flop (`refglob "*"`) and use the cluster clock spine. The `--cts` gate measures the spread of the pin flops' insertion delay.
