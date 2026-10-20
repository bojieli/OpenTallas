# hcoll_v5r_ctl_n1s0_v74p -- d4g COLL release leaf n1s0 (VM_RT 74), PIPELINED successor of v74w (L2H-COLLP 10-19)
RTL ot_hgi_coll_ctl_v5r_n1s0_safephys #(VM_RT 74, SAFE_DELAY 1, MUL_PIPE 1). Geometry = v74w (outline 259.2 x 345.6, macros unchanged).
Parallel twins: hcoll_v5r_ctl_n1s0_v74p (v74w geometry) and _v74q (v74x geometry), in parallel with the v74w coordinator review.
Bind whichever closes first; cancel the others.

SAFE-DESIGN checklist (owner 10-19) -- v74p/v74q (L2H-COLLP), after the v74w/v74x gates (WARN: GRT 0, spread <=41/37, TT setup
-14..-53 ps placement-RC on the iter_mul stage-3 combine pd->m_rgx_l / pc->m_del_l, ~19 levels):
1 Pins: PASS -- v74 ABI; inst/taps/hgi_*/issue_done and every observed input captured at its pin flop (MUL_PIPE adds the
  hs/hb/issue_done pin flops), outputs flop Q; reset 2-stage face landing then 9 kept D1 copies; pin_min_tracks 4 (<=5.2/um).
2 Reach: PASS -- outline 259.2 x 345.6, every pin->flop and flop->macro path < 405 um Manhattan.
3 Fanout: PASS -- reset copies max 32; the new stage-3a regs (u/w x3, xa/xv/xl/xh) each drive one adder (no new fanout).
4 Depth: FIXED -- the 7-term 32-bit combine (gate: 18-19 levels, -14..-53 ps at placement RC) is split into two registered
  rungs: 3a = one 2-operand 32-bit add + one 3-operand 24-bit add, 3b = one 2-operand 32-bit add (~<=12 levels each).
5 Storage: PASS -- 4 fixed-delay SRAMs (2x 128x256 p192_mir, 2x 32x128 p192_rc); macro faces 5.1/um (<=6).
6 Floorplan: PASS (geometry of v74w: GRT 0) -- macros on the 43.2 lattice, two macro columns, no abutment, >=33 um std
  channels at every pin face (row halo 6.48), >=49 um horizontal channels between macro rows; one continuous std band;
  aspect 1.33; fill WAIVED pin-bound (~22-25%).
7 Clock: PASS -- clock_split_km K=8 regional roots on clk_control (v74w measured spread 34/33 TT/FF); io_hold_margin 0.03.
8 Schedule: PRICED -- static; +1 COLL issue edge (uniform: the parent feeds this leaf the uop-pipe d3 word and every other
  COLL child the d4 word; products, controls and all outputs one edge later). Handed to H.STA.BANKLAT.COLL (price record
  results/arch/hbm_coll_mulpipe_1019/price.json). Proofs: tools/run_hbm_coll_mulpipe_proofs_1019.sh (Verilator 5.050,
  ot-epyc8): 20/20 (iter PIPE1 + 3 mutants; shift-equivalence vs v74 on every output bit, NPT1/NPT2 + 5 mutants;
  production 1792 + dense 8192 pairs at E+11+74 + 3 mutants; v74 regression) -- witnesses results/rtl/hbm_coll_mulpipe_1019/proofs_r1.
Critical prefix (ot_hgi_coll_ctl_v5): gate PNGs + these facts go to the coordinator review queue; no REVIEW.json / submit.
