# qfd_n59_qbank6_b (QW-N59-6, 10-20) -- Q-seat SRAM bank child of the hardened native59 split (Q.STA.N59), clock-tree rebuild of qbank5

v6 = qbank5 RTL, synthesis, floorplan, pins and macro placement UNCHANGED (same source eab8ff8d2, QB_ALIGN=1 QB_LOCAL32=1, so the
pre-gate census below is the identical mapped netlist; the gate re-runs it).  Only the clock tree changes: CTS 16-sink / 40-um register clusters, 2 clustering levels, -no_obstruction_aware.
Why: qbank5 / qbank5_b CTS (ep6 10-20 02:21) measured TT boundary pin-flop spread 140 / 167 ps (> 80, clock rule FAIL).
Per-flop dump (QW-N59-6, TT, 4_1_cts.odb): S face (dd_i f_dd / face ctrl / beat, 927 flops) 458-483 ps; N face (dd_o / qb_row,
1076 flops) 471-504 ps in the centre 130 um but 555-598 ps at the corners (x < 65 or x > 390): the obstruction-aware H-tree
detours around the two abutted SRAM stacks, so the N-face corner leaves hang on long return wires.  The tree is now built
straight over the stacks (centre-fed H-tree from the S-face ck pin up the 91.8 um middle channel).  Neighbour matching: one
root, all pin flops within 80 ps at TT and FF, and the landed parent (lp.py) compensates this child's measured boundary mean.
Variants in parallel (owner 10-19 PARALLEL): qbank6 (tool clusters), qbank6_b (16/40 clusters, 2 levels), qbank6_c (unclustered).


Source: Codex N59v5 R3 eab8ff8d2 (branch codex/qw-n59v5-qbank-local-1020, evidence 722cd9bda,
results/arch/qw_n59v5_qbank_local_1020) with PARAMS QB_ALIGN=1 QB_LOCAL32=1 (production NU4/MCTX1/EMB_RELAY1 at the parent).
Floorplan / pins / macro placement = qfd_n59_qbank2 (518.4 x 388.8 exact sub-slot of the 518.4 x 648 native59 slot).
Kit _b = the same block with an unclustered H-tree CTS (parallel fallback, owner 10-19).
Why v5: v2 (qfd_n59_qbank2, 4c8cbd796) CTS-stage gate 10-20 02:15 on ot-epyc6: hold OK (30 ps after 2 chunks) but setup
WNS -793 / TNS -125k (b: -772 / -123k) and the v3 mapped census refused 328 drivers > 32 (max 259: qc_rep stage / context
decode, partition f_qb, select_q).  v5 localises every face control / predecode per lane (4 seat groups of 8 + override,
15/15/2-bit select + bypass publications, separate bypass address, 4 face beat copies) and adds a third kept 40-bit face
publication that owns the canonical override address (R2 merged it: 40 bits at 34 loads).  v2 gates cancelled 10-20 (superseded).

## PRE-GATE NATIVE CENSUS (mapped netlist, strict, R3 eab8ff8d2; receipts_round3/synth)
* drivers > 32 loads (data AND reset, BUF/INV transparent): 0 (R1 4 max 41, R2 40 max 34 -> R3 0).
* 10596 FF, 8 SRAM ot_sram_1r1w_32x512_m1; payload 8 x 32 x 512 = 131072 bit in SRAM; owner 96 + seen 32 bit per lane x 16
  = 2048 control bits (no runtime-indexed flop array > 2048 bit).
* pins: registered input / output levels 0 / 0, no comb through; tied outputs 0; 64 SRAM pin-role families PASS (SS lib).
* lint depth 405.1 ps / 10 levels.  Mapped SHA c4b911ade8f36f3f99b34e8783c9f91f10ed6c45933413e74d9bb6ce0ecc1429.
* Reach 405 um: not provable from synthesis; measured on this gate layout (dd_i -> dd_o relay ~350 um is the longest planned).
* Synthesis chip area 109,448 um2 incl. 8 x 12,746 macros -> std ~7.5k um2.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- every port lands in an S-face f_* face register (kept copies, 3 x 40-bit face publications); every output is a
  flop; rst_n 2 landing stages x 32 copies (kit).
2 Reach: PASS by construction (518.4 x 388.8; longest planned one-cycle wire dd_i -> dd_o ~350 um); measured at the gate.
3 Fanout: FIXED in v5 -- census 0 drivers > 32 (above).
4 Depth: PASS -- lint 405.1 ps / 10 levels; one-hot AND-OR read face, select from registered owner + local override.
5 Storage: PASS -- 131 kb payload in 8 SRAM; 2 kb control in 16 lane slices (128 b each).
6 Floorplan: PASS -- 8 macros on the 43.2 lattice in two abutted N-S stacks (track-legal pitch 76.176), column 0 MY so both
  rd_out faces the 91.8 um middle channel; full-width S / N std-cell bands; aspect 1.33.  Std utilisation is low (~7.5k um2
  std in a macro-bound outline); the outline is fixed by the 8 macros + parent slot, not by std area (waived: macro-bound).
7 Clock: FIXED in v6 (qbank5 TT spread 140 FAIL) -- one root ck at the S-face centre beside the face registers, tree straight over
  the SRAM stacks (16-sink / 40-um register clusters, 2 clustering levels, -no_obstruction_aware); own region ck_qb in the landed parent;
  io_hold_margin 0.03 (raised from 0.0 in qbank2); rule = pin-flop spread <= 80 at TT and FF.
8 Schedule: static; v5 adds 0 edges vs v4: SOFF3 / BOFF0 / ROFF4 (service +3, bank 0, outputs +4 in the landed parent).
