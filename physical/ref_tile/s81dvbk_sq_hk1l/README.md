# s81dvbk_sq_hk1l -- TOPK selector quarter, HARD-CHILD hierarchy (dsdv_bksel_q, S81-TOPK8 2026-10-20)

Successor of the flat HQ3 kit (s81dvbk_sq_hq3 @a86fd4882). Same RTL and edges (HQ3 + OT_HARD_CHILDREN + INPUT_RAW input landing (OT_S81PH_HQ_INPUT_RAW, source 267559433)).
The 16 hist32 bank instances (ot_s81ph_hq_hist, BANK0 master + constant digit/group inversions) bind the CLOSED
view physical/ref_tile/s81dvbk_hist32_b0r3/views/ot_s81ph_native_sel_hist_bank (s81dvbk_hist32_b0r3-hb0r3-bd6f52e8c,
CLOSED 8cadc26d5: TT +239.7 / FF +23.1, DRC 0, native max25, reach 87.3, pin spread 13.5 TT / 14.2 FF).
Geometry = MODELONLY 46e59d924 (results/arch/s81_topk_hard_model_1020): 518.4 x 648, 8 coarse banks below / 8 fine above a
full-width 54 um std band (y 302.4..356.4), line SRAMs in an E column (upper three moved 2.16 um down for the 20 um N pin-face
edge rule), OFQ / FQ SRAMs beside the band.

## Why (HQ3 classification, S81-TOPK8)
HQ3 CTS gate (agidock case 040058) stalled in post-CTS FF hold repair: WNS -45.134 ps at
u_pi.g_pl[0].u_p.g_cst[0].a0[125] (packer s1_e) from iteration 30 to >6,700; 22,797 endpoints inside the 30 ps margin.
Ideal-clock STA on its 3_place.odb (results: scratch s81-topk8/sta_{FF,SS}.log): FF hold all MET (worst +0.9 ps incl. 25 ps
uncertainty); the stuck endpoint's SS setup slack is +480 ps, so it is not setup-blocked. The violations are propagated
clock skew on 1-inverter flop->flop pipeline hops (i0->i1_p, i1_p->s1_e, c*_p) across one flat 52.5k-sink tree.
Fourth flat-quarter hold grind (succ3 single tree, succ4 K16, succ4k8 K8, HQ3 K16): structural fix = hierarchy.
SS setup -65.8 at u_in.g_f[50] (pre-first-FF type decode) is SS sensitivity only; INPUT_RAW (hk1l) removes that decode.

## Safe-design checklist (owner 10-19)
1. Pins: PASS (unchanged HQ3: u_in s0, QIO cq0/cq, sq/sq1, oq/oq1 pin flops; reset lands in 2 kit stages). Bank pins: inputs
   captured at the bank HPIPE / kept gsel registers, outputs registered (closed view).
2. Reach: by model <= 399.6 um planning (bank faces to band anchors); the gate measures actual placed hops.
3. Fanout: HQ3 mapped census max32 / 0 viol (hard banks remove 16 x bank logic from the parent); the gate's mapped native
   census must repeat max <= 32 for this parent before floorplan.
4. Depth: unchanged (HQ3); gbin OR-join of 8 registered bank outputs is the same combinational join as before.
5. Storage: PASS (16 SRAM macros unchanged; bank counters inside the closed child).
6. Floorplan: macros + children on the model positions (43.2 lattice origins for children), full-width std band, >=20 um
   edge margins, aspect 1.25. Fill measured at gate (model: 40.9 % total).
7. Clock: K16 regional roots (succ4 recipe) + hard-child clock references (child insertion TT ~114 / FF ~94); the gate must
   show pin-flop and linked child-flop spread <= 80 ps TT+FF. io_hold 0.03.
8. Schedule: PASS, 0 added edges (same RTL edges; OT_HARD_CHILDREN only drops the default-equal bank parameters).
SLOT CHANGE: quarter 324x540 -> 518.4x648 (+0.64 mm2 for the full TOPK); needs coordinator/die admission before binding.
