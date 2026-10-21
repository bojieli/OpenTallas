HBM-OWN/SU 10-21: one source file carrying BOTH closed cxport_ij halves for the die bind.
- ij_s module text == origin/main (closed view hbm_su_cx_ijs_1018-n1-2682c59ac, OBR=1).
- ij_q module + ot_hbm_cxijq_sel_copy text == 5a6486280 (closed view hbm_su_cx_ijq_1019t-t1-5a6486280, SAFE_GATHER=1).
- wrappers ot_hbm_su_static_cxport_ij / _split gain SAFE_GATHER (default 0 = previous behaviour) passed to u_q / u_ij.
Benches (Verilator 5.050, ot-epyc5, cxij_benches.sh): hub lockstep OBR=1+SAFE=1 QID2 PASS 24183 checks, QID0/B39 PASS,
default OBR=0/SAFE=0 PASS; MUT4 FAIL (errors 36033) as expected; cxijq_safe SD0 PASS 13365 / MUT6 FAIL as expected.
(MUT1 only perturbs the legacy ctl path, so it is not a negative for SAFE=1.) Die instantiates with OBR=1, SAFE_GATHER=1.
