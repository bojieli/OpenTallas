# hbm_hc_tail_child_k5 -- HC Sinkhorn tail child MAIN (HBMc/HC-TAIL 10-22)

Successor of k4 (gate ep9 ref_gate/hbm_hc_tail_child_k4-20261021-181829). The k4 CTS odb, timed at TT 833.333 with a
propagated clock and placement RC, gives WNS -177.3 / TNS -141.8k over 1,175 reg2reg endpoints, 1,146 of them in the
Sinkhorn. Each endpoint was traced back to its RTL origin by replaying the cloner on folded_k4f:
(1) the step-0 B quotient (SUBN 1) Q2 cone, about 1,000 endpoints at -177..-96 ps: a_xm/a_tm compare -> E -> subnormal shift
amount -> the 24/27-bit shifts, plus the 53-bit product CPA;
(2) the A-step flt endpoint (X3 -> sk_norm -> a_bad_sum), -156 ps;
(3) steady add P / Q1 cones that start behind the exponent==0 decode of st, -44 / -31 ps;
(4) tail exp Horner add (fp32_add_lat4i), -55 ps. No cycles added for this class (10-22 freeze): route repair/upsizing, LVT on <=~2% of cells if still a near miss; NEXT-RELEASE (XLA 5, +8 edges) only if TT < 0 after that.
The fix is ot_hdc_sinkhorn_cp SC2 (tail SKP 3):
- a QS cut in the B quotients (ot_hdc_skc_quot CUTS 1);
- an A-normalise / a_bad cut;
- decoded state registers sd_e/sd_m/sd_z, written with st.
The steady D stays 16, so SDIV 17, CAP 699 and L 989 are unchanged. The root uses TSKP 3 / TSDIV 17 / TE 495 (same latency
as k4).
MAIN keeps the k4 floorplan, pins and default CTS.

Source: rtl/hbm_accel/generic/peers/static_hc/native/ot_hbm_hc_tail_child_static_k5.v, sha256 in
results/rtl/hbm_hc_root_safe_1020/tail_child_hc11/k5_netlist.sha256. Recipe: nl.sh there (`nl.sh k5 17 1 3 495 1040`):
- 48,340 flops, 7,214 clones, 545k cells;
- max loads 24.
Benches (Verilator 5.050, ot-epyc5):
- RTL lockstep PASS 48 (+495);
- MUT1 FAIL 44/48;
- SDIV 16 (offset 453) FAIL 48/48;
- native lockstep: tailc_k5_native_m0_run.log.
