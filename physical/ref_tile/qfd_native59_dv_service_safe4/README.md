# qfd_native59_dv_service_safe4 (QW-N59-3, 10-19) -- structural rebuild after the safe3 / safe3b / safe3c gate FAILs

Why (safe3c, measured; all three safe3 kits ended GATE_STALL 14400 s in CTS hold repair, terminal records committed):
  * setup: placed-design STA (ideal clock, 3_place.odb) WNS -864 ps, dr_o[449] <- e3: 1,614 ps for a 770 ps cycle.
    The path is the embedding word p_ecq (W-face pin register) -> dr_o (S-face pin flop) with the e3/k3 select
    (520 loads) on the way: ~1 mm of one-cycle wire (checklist 2 and 3 violations). SRAM read -> kq_data +22 ps,
    SRAM write +135 ps, p_x3s -> u_kvn.seat +133 ps (ideal clock): those are not the failure.
  * clock: ck pin at the NW corner (alphabetical pin order), 25,172 sinks, average sink wire 560 um, pin-flop
    arrival TT 745..874 / FF 611..732 ps (spread 129 / 121 > 80).
  * hold: repair stuck at -124.651 ps (u_kvn.seat) for > 16k iterations: a hold buffer there breaks setup.
Changes (same ports, same function; all benches below PASS, mutants FAIL, Verilator 5.050 fleet witnesses
results/rtl/mu_qwen_1018/n59_safe4):
  * RTL EMB_RELAY 1: one registered relay between p_ecq / p_esq and dr_o for the embedding (group 1) words, the
    select as 16 KEPT copies (one per 32-bit dr_o segment, <= 33 loads). +1 edge on embedding words only
    (dr_o group 1 at cmd + 7 .. + 71); group 0 attention words, x3, tx, native_ret unchanged.
  * pins: every port has its own range; ck alone at the N-face centre (257.7-260.7 um: centre-fed root);
    emb_code_q from the SW corner up the W face, dr_o from the SW corner along the S face, dr_o bits descending,
    so dr_o[i] and emb_code_q[i] are a near-constant ~0.44 mm apart (two hops with the relay). Max 4.3 pins/um.
  * reset: rst_cp_land 56 kept copies (1,420 loads -> <= 26 / copy; safe3 had 45), 2 landing stages.

DIE / COMPILER OBLIGATIONS: bind master qfd_native59_dv_service_r1 with EMB_RELAY=1; the embedding dr_o words move
+1 edge (compiler: the group 0 / group 1 collision window shifts by one edge for group 1). Q-ready production bound
(QW-QREADY: W5.dd_wo -> native59.dd_i age 20) still must be certified by the successor GEN before binding.

## SAFE-DESIGN checklist (owner 10-19)
1 Pins: PASS -- RTL flop-first on every input/output (pin_regs opt-out reason recorded); rst_n 2 landing stages, 32 kept copies.
2 Reach: FIXED -- the measured > 1 mm W->S embedding path is split by the relay and the pin ranges put both ends at the
  SW corner (~0.44 mm, two hops). Remaining one-cycle wires checked on the CTS gate layout.
3 Fanout: FIXED -- e3/k3 520-load select -> 16 + 16 KEPT copies; reset forest (rst_cp_* <= 32 loads, land 56 copies).
4 Depth: PASS (ideal-clock STA at safe3c: every non-dr_o class measured >= +22 ps) / PENDING CTS gate.
5 Storage: PASS -- 16 kb Q payload in 8 SRAM macros; no runtime-indexed flop arrays > 2 kb.
6 Floorplan: PASS by construction -- 8 macros on the 43.2 lattice, full-width southern std-cell band, pins on full
  N / S / W faces (<= 4.3 pins/um), outline = the die slot 518.4 x 648 (total util 40 %, std-cell density 10 %: macro bound).
7 Clock: FIXED -- one root ck, centre-fed (N-face centre) instead of the NW corner; io_hold_margin 0.03; rule = pin-flop
  spread <= 80 TT+FF (PENDING CTS gate).
8 Schedule: static, no backpressure; +1 edge on the embedding words handed to the compiler (above).
