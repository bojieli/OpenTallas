HBM-FORM-SPLIT-14-SUX 2026-11-06 18:10 PST: RE-FORM of the shared SU lane cores ot_hbm_su_pg_lane_exp_x_core / ot_hbm_su_pg_lane_full_x_core.
Measured cause (routed exp_x vC, vD and full_x vB, TT SPEF + FF): every R2R setup and every R2R FF hold violation passes at ZERO skew
(worst zero-skew setup slack +27.4 / +16.1 / -1.1 ps; hold all >= 0 but one vD endpoint -9.6); related-pair skew 195-224 ps.  The tree is
tight with a CTS-intrinsic late tail in branches that detour around the six SRAMs (vD NE corner through a 100-um wire repeater).
Form (both cores): sux_latbal.tcl = post-CTS subtree latency balance to the latest sink (delay stages at the highest node whose whole
subtree is early, re-measured per round; SRAM CLK pins balanced too; same ports/flops/cycles) + ONE plain TritonCTS tree.
Offline replay on the 4_cts.odb of the routed kits (placement RC): latbal_replay/{xD,xC,fB}.log (vD p1..p99 159 -> 30 ps, vC 84 -> 22,
full_x vB 56 -> 22).
vB adds RTL gen_lane_xd.py: lane multiplier MLAT 7 = C1+C2+C3+C5 (existing bit-identical cut; C5 cuts the face sx_y_* -> e1m input
stage) and fixes the E1-add fault alignment of gen_lane_xb.py (2 dM - dA, was dM: wrong whenever dM != dA; vB/vC had dM == dA).
Bench (EXPX lock-step method, old part-18 splitx composition vs the new core; bench/run_xd.sh, bench/run_fx.sh, mk_bench_fx.py):
  exp_x  T=14 S=8: MUT 0 PASS 560000 checks; MUT 1-6 FAIL; controls T=13 and S=7 FAIL.
  full_x T=14 S=8 side +8: MUT 0 PASS 640000 checks; MUT 1/3/6 FAIL; side-return control SIDE_D 6 (+7) FAIL; S=7 FAIL.
  Before the E1-add fix MUT 0 FAILED (95 lane_fault mismatches, NaN epochs only): bench_before_e1a_fix.log.
PIN CYCLES (vB only; vA = RTL unchanged, 0): write side lane_vm_*/lane_kv_*/lane_ro_*/lane_fault/lane_coll +14; SFU seam sx_v/sx_r/sx_fn
  out + sx_y_exp/sx_y_div/sx_fault in +8; full_x side pipe lane_side_v/lane_side_x out + lane_side_y in +8; all others 0 (vs part-18).
Kits (mk_kits.sh; epyc2 /srv/opentallas-scratch2/claude/hbm-form-split-14-sux/kits): exp_x _vE (vA) / _vF (vB), full_x _vC (vA) / _vD (vB).
