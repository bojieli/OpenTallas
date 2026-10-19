# XDIE step co-sim re-run on current main (L2H-TOK, 10-19)

Source: origin/main b317080134 (git archive), rtl/hbm_accel/generic/collective/xdie/run_xdie_hbm_step.sh all, Verilator 5.050,
ot-epyc7 unit oth-ubuntu-336877. Build uses the die-bound COLL parameters of the GEN2e die (hb_coll_NE
ot_hfd_coll_q2_hard_v8g #(NLINK 1, TP 192), default AR_ITER 0 / ROWS 64).

Result XDIE3_GATE rc=0, every config bit-exact (faults/sched_fail/rx_bad 0), E = first VM request -> last delivery (d0/d1):
qw_ag64 307/301, qw_ag32 235/229, qw_ag16 199/193, qw_rs4 190/184, ds_ag48 600/594, ds_rs4 519/513 -- identical to
XDIE-HBM3 (results/rtl/xdie_hbm_1019/step_cosim). Mutants m_vmstep, m_flip, m_early, m_rsrc REJECTED.
The single XDIE2_SCHED_FAIL line in run_all.log is a stage-A probe (assumed constants), not a pass stage.

Open: production RS48/RS144 need ROWS>=128/256 + AR_ITER 1 (step_cosim4/5/6), which the GEN2e die does NOT bind yet;
the SW parent ot_hfd_coll_q3_hard_v8x (NLINK 2) has no step co-sim.
