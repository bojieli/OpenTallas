# s81sl_capc2 (LEAD2-S81/CAPC2, 2026-10-19) -- S81.STA.PAR.1 release capture cluster

Top `ot_s81sl_capc2` (no parameters) = `ot_s81sl_cap_p1 #(.PINPIPE(1), .EDLY(24), .WL3DLY(16))`. It is the CLOSED 267b CAPC
(`s81sl_capc_p1_die_slew`: PINPIPE 1 faces, rt + 2 x tr hard children) plus the two TOK.DS.BENCH.1 calendar leaves as hard
children:

| inst | view | at (um) | role |
|---|---|---|---|
| u_p.u_core.g_hard.u_rt | s81sl_cap_rt (closed) | 43.2, 43.2 | n6 + FIN + DEC |
| u_p.u_core.g_hard.u_tw | s81sl_cap_tr (closed) | 43.2, 302.4 | W tree |
| u_p.u_core.g_hard.u_te | s81sl_cap_tr (closed) | 216, 302.4 | E tree |
| u_p.u_core.g_ed.u_ed | s81sl_cap_ed D24 (CLOSED 08889f37d) | 216, 216 | E tree word +24 -> rt e_* |
| u_p.u_core.g_ld3.u_ld3 | s81sl_cap_ld D16 (CLOSED 636f4c670) | 43.2, 216 | W lane 3 +16 -> u_tw |

In the hard build (`OT_HARD_CHILDREN`) the ED/LD leaves are instanced WITHOUT a parameter override (a hard view has no
parameters; an override would rename them `$paramod`), with a `$fatal` guard that EDLY / WL3DLY are 0 or exactly the
hard-view delays 24 / 16.  The slice sites (ot_s81sl_slice, _c1x, _c3x, landed _c1x_lp / _c3x_lp, slice_flat_gen.py) bind
`ot_s81sl_capc2 u_cap` (was `ot_s81sl_cap`), so the die GEN binds this view by name.

Benches (Verilator 5.050, ot-epyc6): `cap_p1_gold_bench.sh` = the golden cap_model vectors with the s_16_24 launch advance
(E lanes -24, W lane 3 -16): all 1280 rows written at W + 2, every lane arrival on its edge, fault 0; mutants EDLY 23 and
WL3DLY 15 FAIL (witnesses results/rtl/s81_slice_1017/capc2_1019).  `cap_p1_cal_bench.sh` = cycle equivalence against the
closed 3-child RTL fed through TB delay lines.  `cap_p1_bench.sh` (EDLY 0) regression of the closed PINPIPE 1 RTL.

Hold budget: `tile` with no pin pads (inhold / outhold false).  The level-1 die-budget admission (registered_cluster_budget)
is keyed to the 267b identity (top / sources / params / children); a new identity needs a ROOT candidate receipt.

## Safe-design checklist (owner 10-19)
1. Pins: PASS -- RTL PINPIPE 1 registers all 721 input + 451 output bits; reset lands in 2 registered stages (g_pin.rst_l0/l1).
2. Reach: PASS (gate to confirm) -- longest seams: N-face pin regs -> rt N face ~250 um, te S face -> ED -> rt ~150 um, W lane 3
   pin regs -> LD -> u_tw W face ~130 um; all < 405; max-wire repair 80 um (orfs_vars, as 267b).
3. Fanout: PASS -- no new logic in the parent; leaves are closed views; keep_pin_regs on.
4. Depth: PASS -- no comb in->out; ED/LD are pin reg -> RF ring -> pin reg.
5. Storage: PASS -- ED 66 x 22 b / LD 70 x 14 b register-file rings inside the closed leaves (< 2 kb each).
6. Floorplan: PASS/WARN -- all 5 children R0 on the 43.2 lattice, channels >= 20 um (56.16 rt-ED/LD, 38.88 ED/LD-trees, 82.08
   tree-tree), full-width 43.2 south std band; outline = child stack + 20 um core channels (336.96 x 414.72 after gen snap),
   aspect 1.23; fill 36 % WARN (closed children + lattice set it; a 388.8 stack gives a 12.96 um channel: gen FAIL).
7. Clock: PASS (gate to confirm) -- centre-fed spine on the south band (as 267b), hard-child boundary refs, io_hold_margin 0.03;
   neighbour check per linked pair (te-ED, ED-rt, LD-tw, tw-rt) <= 80 ps TT+FF after the gate.
8. Schedule: static.  Added edges vs the closed 3-child CAPC: +24 on every E-column word, +16 on W lane-3 words (compiler
   --shifts s_16_24, TOK2), on top of the PINPIPE +1 in / +1 out / reset +2 owed since 267b.  INBOX lines in lanes/LEAD2-S81.md.
