# FABLE-PD-S81-1515: S81 col element input face (IFN half-cycle) setup

2026-11-15 15:10 PST. Fable PD review for COORD; cc S81-GOTAG-SETUP-1115, DIE-S81-92, S81-TAPROWS.
Types read: col_h9_r0_p6 (pilot pg of S81-SEAM-RST-1115, epyc10) and col_h10_r2 (kw43 attempt_3, epyc10), both at 4_cts.odb, placement parasitics, kit 4_cts.sdc, TT and FF (FF with the kit core_taps_ff.sdc overlay; grid window and vclk as in the TT SDC). Pre hold repair.
Scripts and outputs: epyc10 /srv/opentallas-scratch2/claude/fable-pd-s81-1515/ (m1..m4.tcl, m*_h9_*.out, m*_h10_*.out). Read-only, nothing written to a kit.

## Verdict

Set IFN = 0 on the col element halves (hw / he): capture the whole data input face on the rising edge. The half-cycle input flop was built for a parent-flop sender; in col there is no such sender. Every one of the 4,832 element data input pins per type is driven by a core macro (4,816 by dsfd_qbank_S, 16 go_tag by ot_s81_cfg7_seq). So no per-pin split is needed, and it is a parameter change, not an RTL edit, with 0 cycles (no calendar or LATCHECK change).

IFN = 0 must land together with the measured per-port tap window (R-CLOCK-2c). With the senders on their grid taps and the flat 208 ps window kept, rising-edge capture closes the hw half and h10 (except 3 go_tag pins on one slow net), but the he half of h9 has almost no valid window: the he pins that already capture on the rising edge today are at -102.8 TT setup with +74.4 FF hold (item 2). The flat window is charged on both setup and hold of this cross-port link, 416 of the 833 ps; each ps taken off it comes back on both sides.

The sender-input failures the lane then met are a second, separate link (ROM -> cfg7_seq) and need clock rows, not RTL.

## Measured

"PE" = rising-edge equivalent: the IFN = 1 slack moved by half a period (+416.5 setup, -416.5 hold), i.e. a rising-edge flop at the clock insertion the IFN flop has today. Senders on grid taps (baseline), flat window, 25 ps hold uncertainty. Worst pin per group.

| type / half | IFN=1 setup TT | PE setup TT | PE setup TT, window 0 | PE hold TT | PE hold FF |
|---|---|---|---|---|---|
| h9 hw, xs/cfg/go (2,408 pins) | -260..-310 | +107..+156 | +315..+364 | +31..+88 | -33.5..+15 (227 pins < 0) |
| h9 hw, go_tag (8) | -369.2 | +47.3 | +255.3 | +149.5 | +59.3 |
| h9 he, xs/cfg/go (2,408) | -198..-287 | +129..+218 | +337..+426 | -60..-7 | -126..-90 (about 1,400 pins < 0) |
| h9 he, go_tag (8) | -253.4 | +163.1 | +371.1 | +18.0 | -59.5 |
| h10 hw, xs/cfg/go | -197..-242 | +175..+220 | +378..+423 | +119..+159 | +41..+80 |
| h10 hw, go_tag (8) | -510.7 | -94.2 (3 pins < -42) | +108.8 | +95.7 | +20.1 |
| h10 he, xs/cfg/go | -72..-150 | +266..+345 | +469..+548 | -14..+19 | -98..-68 |
| h10 he, go_tag (8) | -231.8 | +184.7 | +387.7 | +33.7 | -45.5 |

1. Driver class (MEASURED, DB net trace): 4,832 of 4,832 data input pins are core-driven in both types. Zero parent-flop drivers. rst_n is separate (RSTP relay) and not part of this.

2. Real rising-edge capture already exists in the signed halves (MEASURED, the best stand-in for IFN = 0): 18 of the 48 cfg_d bits per half (29-41, 43-47) have only setup_rising / hold_rising arcs in the lib, no IFN flop. These 144 pins per type are captured on the rising edge straight from qbank_S today, flat window, pre-repair:

   | pins (72 each) | setup TT | pins < -42 | hold TT | hold FF |
   |---|---|---|---|---|
   | h9 hw | +38.8 | 0 | +126.5 | +39.4 |
   | h9 he | -102.8 | 19 | +207.0 | +74.4 |
   | h10 hw | +139.7 | 0 | +170.5 | +83.1 |
   | h10 he | +45.6 | 0 | +211.3 | +79.7 |

   The other 30 cfg_d bits (IFN) in the same rows: -92..-308 TT, 349 of 480 pins < -42. So a core -> element link on a full cycle holds at FF without pads in all four cases and meets setup in three; h9 he is short by 61 ps against the -42 gate with the flat window and would be at about +5 with a 100 ps window.

3. Why the half differs: the IFN flops sit at 346-386 ps (hw) and 510-585 ps (he) from the element clk pin (TT lib; FF 282-324 / 403-474). The existing rising-edge cfg_d flops sit at 332-342 (hw) and 201-303 (he). PE hold is negative only where the capture flop is deep (he IFN position); the shallow he flops are the ones short on setup in item 2. For h9 he the depth that meets both gates with the flat window is a band of about 30 ps (INFERENCE from item 2: setup -102.8 TT, hold +74.4 FF on the same flop group). Data seen from the element clk pin: earliest change FF about +280 ps (hw) / +300 ps (he) or later; latest arrival TT within +250 ps past the next edge for xs/cfg/go, +300 for go_tag (h9), flat window included.

4. Sender clk -> out (question b): go_tag 397.5 / 401.3 TT max, 388 TT min, 287-301 FF min; qbank_S 371-403 TT, 347 TT min, 280 FF min. It is the uncompensated core insertion (271; s and bs are grid-tap cores, bound 272 in core_latency.txt) plus clk-q 126 at 26-36 fF. The output is already a pin flop. Nothing to retime inside without a cycle.

5. The lane's "313 ps short" is about 100 too large on the face: its window-0 run moved one side of the t -> c pair (+104). With both ports at their mean the cross-port pair gains the full 208: h9 hw go_tag -161.2, xs_q1 -101.9, cfg_d -99.6; h10 hw go_tag -307.7, the rest of h10 >= -38.8. Clock rows alone still do not close it (h9: face -102 and ROM link -12 trade 1:1, and a measured window is not 0). The conclusion of pilot A stands.

6. Second link, not IFN (MEASURED): the cfg7_seq inputs q0..q6 are driven by the ROM macros c<k>_0..6 (1,848 of 1,848 pins), not by parent flops. Path: ROM clk at 278-308 (tap delay chain tb0_d0..d6 plus cb0), clk -> rd_out 520-525, buffers and wire about 220, cfg7_seq setup credit 82 (h9; -33 on the s15 bfp view), s clk pin at 121-184. Flat window: h9 -220.3 (833 pins < -42), h10 -305.1 (1,003 pins). Window 0: h9 -12.3 (0 pins < -42), h10 -102.1 (q5 65 pins, q4 23, q3 2). ROM address inputs: +24.0 (h9), -47.6 (h10, 3 pins) with the flat window. The parent-flop-driven sender pins are bs i_x0 / i_x1 (2,196 pins): setup +64..+103, no problem.

7. h10 go_tag outlier: s11 go_tag[1], fanout 2, 36 fF, slew 142: BUFx6f 136 + BUFx6f 42 + BUFx3 52 + wire = 246 ps after a 401 ps clk -> out, s11 clk pin at 184. Same pattern on e13 (-480). A net repair, not a structure problem.

## Answers

(a) Per-pin IFN by driver class: the split is empty in col. All data pins are core-driven, so IFN = 0 on the whole face. The RF-J failure (rf1s, FF -239 on 2,342 inputs) was the element core signed against the legacy input contract in_min -40 (a zero-delay parent flop) with 460 ps insertion; it was a contract result, not a measured col driver. Against the real senders the same form has FF hold +39..+83 on the 144 pins per type that already use it, and TT setup +39..+140 on three of the four half groups, -103 on h9 he (item 2). FF hold for the rest: -33..+80 with hw-like capture depth, -45..-126 with he-like depth, pre-repair, flat window (table). A hold pad on these nets takes the same amount from setup, so on h9 he the room comes from the window, not from pads.

(b) Sender retiming: no. 397 is inherent to the grid-tap view (item 4). Stronger output drive saves at most about 50. Moving the core earlier is the zero-sum pilot A.

(c) Station on the link: works only as +1 cycle on 13 families (4,832 flops per type, 216 types), new compiler dates, LATCHECK rows, LEC and token re-proof. INFERENCE: with the flat window a grid flop into the hw IFN pin is still about -30..-80 (required 313 against tap 250 + clk-q + wire). Fallback only. FF hold stays at +T/2 (safe).

(d) Clock rows plus measured window: not a fix for the face (item 5). It is the fix for the ROM link (item 6) and the margin for (a): every 1 ps taken off the window adds 1 ps to both PE setup and PE hold on this face. No new FF hold family (lane: 712 vs baseline).

(e) Nothing better found. A capture-side latch has the same T/2 deadline as the negedge flop. A negedge or lockup stage on the sender output costs the same half cycle.

## Ranked fix

1. IFN = 0 halves, 0 cycles, with the measured window of item 3 below in the same delta. Owner S81-GOTAG-SETUP-1115 (pilot and proof), DIE-S81-92 (rows, as its own delta).
   - Build hw and he with IFN 0, OLAT 1 from the romq_split_1106 recipe (2 masters). Generator: delta_romq_split_1106.py emits `#(.OLAT(1))` and the split wrapper defaults IFN to 1; emit `.IFN(0)` there. No RTL source edit.
   - Input contract of the halves from the real parent, not legacy in_min -40: earliest data change FF +280 ps after the core clk pin, latest TT arrival 250 ps past the next edge (300 for go_tag). With -40 the core flow pads 240 ps on 2,342 inputs inside the macro and the face fails again.
   - Read in the built lib: setup_rising / hold_rising of the data pins. hw-like depth (330-390 TT) is right for hw. For he, neither today's IFN depth (510-585: PE hold FF -126) nor today's rising-edge depth (201-303: setup -103) is right with the flat window; about 300-370 TT is the band (INFERENCE). Do not tune the core for it: take the window.
   - Type pilots h9 and h10 to CTS with senders on grid taps, each read twice: flat window and the measured per-port window. Pass = face setup >= -42 TT, FF hold >= 0 after the normal pregrt_ff_hold build, no new sender-input family. Expect h9 he to fail the flat-window read by 30-100 ps and pass the measured one if the bs / s tap ports and the clk_c ports come in at 150 ps or less.
   - Proof: halves kit LEC; type kit LEC; tb_qxpq_go_boundary with TB_DUT_IFN 0 and 1 (same cycle) and its mutant; check_native_go_split.py / tb_native_go_split re-run with the IFN 0 call (it names "IFN 1 default"); LATCHECK 873/873 unchanged; token run on the col types.
2. ROM -> cfg7_seq clock rows (item 6). Owner S81-TAPROWS with DIE-S81-92. Put each s<k> on the same tap port as its ROMs c<k>_0..6 (the cross-port 208 becomes CRPR), and keep the s clk pin no earlier than the ROM clk pin. INFERENCE: up to +100 later on s<k> is affordable after fix 1 (face PE at window 0 +255 h9, +109 h10; ROM address side has +24 flat). Needs its own pilot numbers; h10 q5 is -102 at window 0.
3. Measured per-port window (R-CLOCK-2c), already asked of S81-TAPROWS: required companion of fix 1 for the he half (at least 61 ps off the 208 on the bs -> element pair, h9), margin for fix 2. Not a substitute for fix 1: with IFN = 1 the face is still -102..-161 (h9) at window 0.
4. go_tag net repair (item 7): 16 nets per type, large hold room (+96..+150 PE TT on hw). Needed for the 3 h10 pins at PE -94.

## Stop list

- Sender cores on clk_c (pilot A) or any uniform early/late shift of s* / bs* as the face fix.
- Per-pin IFN split; there is no parent-flop-driven data pin on a col element.
- Link station / +1 cycle (c), unless fix 1 fails its pilot.
- IFN = 0 halves signed against in_min -40.
- Negedge or lockup stage on sender outputs; capture-side latch.
- Reading S/q0..q6 as parent-flop links: they are ROM read paths.
- Using -263 / "313 short" as the window-0 face number (item 5).

## Limits

PE is arithmetic on measured IFN = 1 slacks; the true IFN = 0 capture flops are the next stage inside the element and their insertion is known only after the halves are built (item 2 is the measured stand-in, 144 pins per type, and it is less favourable than PE on h9 he). The window value the die will give these ports is not known to me. FF runs: core taps from core_taps_ff.sdc, grid window and vclk from the TT SDC. 4_cts, placement parasitics, before hold repair. Two of 216 types read. ROM address slack at window 0 was not read (script error); the flat-window value is measured.
