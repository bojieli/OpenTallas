PL-BK 10-18 ~08:10: lp.py MUT 4 (one child's reset run 1 edge longer) on dsdv_bk_sel_x_lp is NOT visible to the generic
random lockstep for ANY reset child tried: u_rs (default), u_g (spec mut_child, 06:5x), u_c and u_q0 (these trials,
ot-epyc5, Verilator): MUT 0 PASS, MUT 1/2 FAIL, MUT 4 PASS. The selector children's reset state is fully re-written
before the lockstep's warm-up window ends, so MUT 4 is an equivalent mutant here. Kept spec mut_child u_g; the reset
alignment witness must come from the golden sel bench on the landed parent (run_bk_bench.sh LP=1) with an LP reset
mutant, or a fail_witness_waiver citing these logs.
