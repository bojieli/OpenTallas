DIE-HBM-77-EXPX 11-05 vB form of ot_hbm_su_pg_lane_exp_x_core (registered faces, self-contained deeper pipeline).
gen_lane_xb.py REPO OUT  -> rtl/ (lane_xb, pinreg_xb, exp_x core MLAT 5 / ALAT 4 with SFU seam depths 4 / 3).
eq_xb.py: lock-step bench vs the part-18 splitx composition (old exp_x + sfu_s) ; bench/run.sh MUT...; results bench_results.log
  MUT 0 PASS; MUT 1 cm delay, 2 co delay, 3 div line not shifted, 4 LDCS bit, 5 leaf bank select, 6 f_e2 alignment: all FAIL.
PIN CYCLES (core ports): lane_vm_*/lane_kv_*/lane_ro_*/lane_fault/lane_coll +5; sx_v/sx_r/sx_fn out and sx_y_exp/sx_y_div/sx_fault in +3
  (seam pair moves together, sfu_s core unchanged); all other ports 0.
