# q3_body_ctl OT_Q3CTL_PREACC (DIE-HBM-88-Q3C, 2026-11-07)

Opt-in `ifdef OT_Q3CTL_PREACC in rtl/hbm_accel/cores_split/reform_1105s/q3/ot_hfd_coll_q3_body_ctl.sv.
u_program.data_q (_237833_) is an unconditional no-reset copy of u_fj.u.data_q (clk_program), so the frame-accept
reductions |data_q[255:64] (_027460_, _027468_) and |data_q[63:57] (_027461_, _027469_) are taken one edge early from
u_fj.u.data_q into two registers. vK TT worst path (-55.98, 278+45 endpoints u_program.assembly / metadata) started at
data_q[187] and spent four AND5/AND4 levels in that reduction before the 1600-flop write enable.

- patch_preacc.py: the patch (asserts the copy register and the four assigns textually).
- prove_preacc.py: text identity with the define off + yosys sat miter (seq 8, prove-skip 1, init undef) + 5 mutants.
  Run 2026-11-07 (yosys 0.9): TEXT IDENTICAL, M0 PASS, M1..M5 caught, RESULT PASS.
