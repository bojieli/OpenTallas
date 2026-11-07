HBM-FORM-SPLIT-13-EXPX 11-06 vC (RE-FORM after vB + vA NOT SIGNED) of ot_hbm_su_pg_lane_exp_x_core.
gen_lane_xc.py REPO OUT -> rtl/: runs ../../die_hbm_1105/expx_vb/gen_lane_xb.py (vB) and post-patches it to MLAT 6 (ot_hdc_fp32_mul_lat LAT 6:
cuts C1+C2+C3) / ALAT 5 (ot_hdc_fp32_add_lat5: cuts A+B) on the lane; SFU seam depths stay 4 / 3 (sfu_s core unchanged).
Measured cause (vA routed, TT): R2R setup in the lane FP stages: u_m2 c1->s1_rows -104, s1_rows->s2_prod -80 (4 CSA levels + 48-bit prefix add in one
stage), sx_y_div face -> u_e1m c1 -68, e1a/ad s1_big|s1_small->s2_val -37/-18 (28-bit sum + normalise in one stage); related-pair clock skew up to 142 ps.
Bench: eq_xc.py = eq_xb.py with T/S as args (T=10, S=6); bench/run_vc.sh MUT...; results bench_results.log:
  MUT 0 PASS (560000 checks, 0 errs); MUT 1..6 (cm delay, co delay, div line, LDCS bit, leaf select, f_e2 align) all FAIL;
  wrong-offset controls T=9 / S=5 FAIL.
PIN CYCLES (core ports, vs the old part-18 exp_x): lane_vm_*/lane_kv_*/lane_ro_*/lane_fault/lane_coll +10 (vB +5);
  sx_v/sx_r/sx_fn out and sx_y_exp/sx_y_div/sx_fault in +6 (vB +3; seam pair moves together, sfu_s unchanged); all other ports 0.
