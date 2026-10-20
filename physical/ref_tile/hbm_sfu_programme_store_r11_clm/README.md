# hbm_sfu_programme_store_r11_cl: SFU programme store r11 cluster (CRITICAL: hbm_sfu_programme_store)

Owner: HBM-ELEMOWN3/SFUPS (2026-10-19). This kit replaces `hbm_sfu_programme_store_r10_cl`. The r10 `--cts` gate
(`ref_gate/hbm_sfu_programme_store_r10_cl-20261018-180939`, evidence on `claude/sfups-1018` a2df30323) FAILED: post-GRT
`repair_timing` stayed at SS WNS -256 ps on `pr_base[0][4]/D` (468 endpoints) for 6,953 s.

The cause was structural. A single per-row relay `pr_*` took the launch arguments from the E-face start pins
(y 891..949) and drove three leaves 830 um apart, about 1.5 mm of wire in two cycles. The same reach defect affected the
reset tree, the configuration chain heads, the write strobes, the row status pre-combine and the leaf-to-S-face output
registers.

## Structure

The cluster keeps the same 11 closed r10n2 leaves (`ot_hgi_sfu_store_stripe_leaf_r10`), the same outline
(1080 x 950.4), the same leaf positions and the same pin faces.

The head (`ot_hgi_sfu_programme_store_r11`) is now a set of forwarded multi-stage relays sized from the floorplan, with
one kept copy per destination. `relay_place_gen.py` draws each chain's path along the std-cell channels and places stage
k at its equal-arc point. It checks every register-to-register leg against the 405 um reach rule and writes
`relay_place.tcl`. That hook (spec `pin_hook_before_flops`) fixes each stage FIRM at its point and packs it legally.
`relay_release.tcl` (spec `pre_dpl_extra`) releases the stages for DPL. The full plan is in `relay_plan.json`.

| path | stages | longest leg (um) |
|---|---|---|
| reset rs2 -> leaf / site | KR = 3 (+ ra at the leaf, ra/rb/rbd1 at the site; ST site KR+KS) | 371.6 (P2) |
| IO launch (sv + args) | KI = 2, stage 1 beside the io_start pins, equal for IO0/IO1/IO2 | 344.4 (IO2) |
| programme launch args | KL = 4, stage 1 beside the start pins, equal for all 8 leaves | 382.1 (P2) |
| programme start sv | KL = 4 from p_sv_q (fixed at the v12 x c12 crossing beside the IO leaves) | < 200 |
| config chain-head data | P0 1, P3 3, P6 4, IO0 2 (= KI) | < 330 |
| write strobes | depth(l) = KC(chain) + 2 x chain position (P0..P7: 1 3 5 3 5 7 4 6; IO 2 4 6) | 343.2 (P0) |
| status | KS = 2 per leaf, then one r7c agreement / status combine beside the status pins, + 2 pads | 338.1 (P5) |
| outputs | KO = 4 (3 relays + the S-face pin registers o_ctl / o_io) | < 320 |

In total the head has 11,843 relay flops, all `(* keep *)` top-level registers. The r10 netlist kept such copies:
`cr_data0` and `cr_data3` stayed 256 flops each.

## Priced cycles (handed to the SFU schedule)

| quantity | r10 | r11 |
|---|---|---|
| IO side (io_word, IO status, IO fault) vs r7c | +1 | +6 (KI + KO) |
| programme side (compiler_control, programme status, programme fault) vs r7c | +3 | +11 (KI + 1 + KL + KO) |
| arith_start advance (`make_qswiglu_io_calendar.py`) | 2 (`io_store_r10.hex`) | 5 (`io_store_r11.hex`) |
| split engine delay D / status DS | 5 / 3 | 10 / 8 |
| first configuration write after rst_n release | 4 edges | 7 edges (reset relay +3, once per power-up) |
| io_start_v after the last configuration write | >= 4 idle edges | >= 4 idle edges (unchanged) |

The latency from start to the first word is +5 edges against r10 for each SFU invocation. The static schedule issues
`io_start_v` 5 edges earlier, so the cost per token is 0 when the start-lead slot is free. Otherwise the cost is at most
5 edges per invocation. The die schedule (H-D4G) must bind D = 10 and the r11 IO image.

## Benches

All benches run on fleet Verilator 5.050 (ot-epyc9).

- `tb_sfu_store_r11_lockstep` compares r7c against r11 on every output at every edge (ISHIFT 6, PSHIFT 11).
  - Modes 0-4 must report POSITIVE PASS.
  - The mutants chain (P4 strobe one hop early), noshift, rowskew (row R3 start one relay early), ioskew (IO2 IO launch
    one relay early) and flip must all be REJECTED.
- `tb_hgi_sfu_split_equiv STORE11=1` must report POSITIVE PASS. The mutants flip11, early, chain11, noshift11,
  rowskew11 and ioskew11 must FAIL. Their fail witnesses are under
  `results/rtl/ref_tile/hbm_sfu_programme_store_r11_cl/fail_witness/`.

## SAFE-DESIGN checklist (owner 10-19)

1. **Pins: PASS.** Every host input is captured by a pure pin flop (`p_*`). Every output is a pin register (o_ctl, o_io,
   status pads). Reset lands in two registered stages at the rst_n pin (rs1, rs2).
2. **Reach: fixed.** Every head leg is a relay leg of 405 um or less in the plan (worst 382 um). The leaf-internal chain
   hops are unchanged: about 370 um P6>P7 and IO0>IO1, and about 200 um for each leaf's own-status gate. The gate verifies
   the plan with `OT_RELAY_PLACE matched ...` and the placement timing.
3. **Fanout: PASS.**
   - The launch precompute feeds 8 stage-1 copies. p_sv_q feeds 8.
   - p_cfg_data feeds 3 chain-head copies (P0, P3, P6). rs2 feeds 18 relay chains.
   - No relay register drives more than one destination.
   - Kept copies: keep on top-level registers (no paramod). Check the flop count at the gate.
4. **Depth: PASS (planned).**
   - The launch precompute (12-bit compare and subtract) sits at the start pins.
   - The status combine computes the r7c agreement on registered relays: the 8 x 32-bit ordinal compare plus OR, then
     one register. r10 measured 283 ps and 9 levels on the comparable leg.
   - There is no combinational in-to-out path. The textbook lint at the gate checks this.
5. **Storage: PASS / waived-with-reason.** There is no runtime-indexed flop array. The relay chains are spatially
   distributed forwarding stages (one stage per leg of about 200-380 um), not a co-located delay line, so the
   ring-buffer rule does not apply. The only co-located delay is the 2-deep status pad.
6. **Floorplan: PASS (unchanged from r10).**
   - Leaves sit on the 43.2 lattice with 60.48 um column channels and full-width row channels.
   - The aspect ratio is 1.14.
   - S-face pin density is 4.0/um (compiler_control 1742 / 430 um, io_word 471 / 117 um). The E face carries 621 pins
     over 946 um.
   - r10 fill was 0.60. r11 adds about 4k um2 of relay flops, so fill should be about 0.62 (the gate measures it).
7. **Clock: PASS on the r10 measurement; re-measured at this gate.**
   - Balanced spine. r10 gate TT/FF pin-flop spread was 27.3 / 62.8 ps. io_hold_margin is 0.03.
   - About 15k sinks after the relays (guidance only).
   - Regional roots with landed crossings are not built yet. Every cross-cluster leg is now a registered short hop, so a
     later regional split needs no RTL change.
8. **Schedule: PASS.** The design is static, with no credits or backpressure. Every added edge is priced in the table
   above and handed to the compiler (`io_store_r11.hex`, advance 5) and the die schedule (D = 10, status 8, reset
   contract 7).
