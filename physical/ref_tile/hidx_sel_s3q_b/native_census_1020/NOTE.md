# s3q native32 census (HBM-IDX5 10-20)
Mapped netlist of the s3q_b gate @415f8381b (ot-epyc6 ref_gate/hidx_sel_s3q_b-20261019-234422, 1_2_yosys.v), origin/main
tools/ref_tile/native_census.py: FAIL, 497 drivers > 32, max 1788 (u_f0/u_f1 fill copies -> S5 barrel rotate).
s3q_a/s3q_b gates CANCELLED 02:25 (2.5 h in congested trial GRT; a census FAIL is a gate FAIL). s3c_a: FAIL 2 (d_go 61, u_rr.rst_n 115).
Offender classes (summary_s3q_b.json / classify_s3q_b.txt): fill copies fq0/fq1 (<=1788, comb rotate nets <=644), sel_line pack
decode (138 nets <=49, seq <=102), nf/fill (349), lane copies gl[].u_lc (89 drivers <=75: one bit -> 37-bit line enables),
hist copies gh/gha (<=56), rawr (<=63), last_id (<=49), s1_pass (172), s2_v/s3_v/comp_started, reset leaf (117).
Redesign owed (structural, not a squeeze): registered one-hot destination selects for pack and rotate (per slot-quarter
kept copies), quarter-lane (<=10 b) enable copies, regional reset leaves (<=32), per-consumer rawr/thr copies; re-time the
calendar (sel_in / choose) and rerun run_selector_s3.sh + lp lockstep before any gate.
