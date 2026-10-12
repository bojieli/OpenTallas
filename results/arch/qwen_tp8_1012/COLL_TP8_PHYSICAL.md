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
