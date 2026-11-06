# h9b WQDIAG: diagonal age bit masked (HBM-FORM-TIMING-12-H9B, 2026-11-06)

Kit LEC of svc_pc_ctrl_leaf_cfg_h9b (Codex pg6 kit, vB form) was NOT EQUIVALENT: the 32 diagonal bits
wq_older[p*WQ+p] of the write-queue age matrix are never reset and are written 0 on every push of slot p,
so they only carry their X power-up value. Synthesis ties them to constant 0 (TIELO, even with keep), and the
LEC from the free power-up state cannot prove wab/wab_oh/wcrd (37 differs on vBk, which already keeps s1k/s2k).

Change (rtl/ot_hbm_r14_stream_pc_strap_h9.sv, one line): pwin[ai] masks the diagonal bit
(`& ~(WQ'(1) << ai)`). This is the function synthesis already built; the 32 diagonal flops are unused.
No cycle change, PIN CYCLES 0. rtl/ = the full kit RTL set (cfg = h9b_stkreg vB form with ENQREG=1 default).
Kit side: config.mk `override export OT_KEEP_WIRES = s1k s2k` (merged s1k/s2k copies stay flops).

Proof (proof/, yosys in openroad/orfs:asap7lock, full cfg top, SRAM everted): gold = captured strap
(sha256 484262ce...) with proc; flatten; opt_dff (resolves the X power-up of the never-reset diagonal to the
only value ever written, as synthesis does) vs new: equiv_make/struct/simple/induct -seq 2,
equiv_status -assert: 16125/16125 proven. Mutant (mask the neighbour bit) 32 unproven, FAIL as required.
See proof/result.txt.
