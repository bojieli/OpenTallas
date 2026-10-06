# Qwen slab port group: margin closure (owner margin-first rule 2026-10-06)

## m2 — NOT CLOSED (failed evidence, kept)
OREG 1 + MUL_LAT 9 + ROM lead 3, routed at 770 ps (EPYC1 /srv/opentallas-scratch/claude/qwen-slab-route/m2_slab_lat9_oreg_p770).
Sign-off `tools/w18/corner_sta.py --post-sdc physical/qwen_slab_structural/io_lat_skew90.sdc` (m2/corner_sta_skew90.json):
SS worst -107.0 ps at 770 = **-43.7 at 833.333** (37 violating D pins); FF hold **-109.3** (58 pins). Classes (m2/classes.txt):
- a_q -> u_c5 (decode / zero-detect / LZC / power): 555 ps of logic + 229 ps launch/capture clock skew (22-level tree, 1.0 ns SS insertion).
- u_c1 -> s1_rows: 24-load operand broadcast to the partial-product rows (one 143 ps wire).
- res_in -> res_q setup -56 / hold -109; OREG -> o_* hold -11.6: the boundary flops were NOT at their pins (res_q pin wire up to
  254 ps; res_q SS insertion 818..1,030 ps, the reference res_q[0] an outlier at 1,022) and the flow's boundary SDC (io_wc_skew.sdc)
  used the WC reference arrival as a scalar in every corner, so BC/FF hold of the boundary was never repaired.
- reg -> reg FF hold 8.8..14.8 ps on ~40 endpoints: repaired only to the flow's 20 ps BC margin, below the +15 FF acceptance.

## m3 design
RTL (bit-exact, default-off parameters):
- `ot_hdc_fp32_mul_lat` LAT 10 = new cut C7 in front of S1 (field / zero / non-finite decode | LZC, power). **+1 cycle per ME op**
  (~+0.11 % token, scaled from the +0.34 % recorded for the 3-cycle OREG + LAT 7->9 step).
- `ot_hdc_fp32_mul_lat` KCP 4 (slab `MUL_KCP`): the C1 operand register as 4 kept copies (`ot_hdc_mul_kcp48`, SYNTH_KEEP_MODULES),
  each driving 6 partial products. 0 cycles.
Flow (constraint consistency, no setting sweep):
- `pre_resize_ioanchor.tcl` (PRE_RESIZE): every res_in capture flop and every o_*/ov output flop (+ its output buffer) is moved
  beside its pin before repair_design; DPL legalises. The register stages behind them absorb the wire.
- `io_refpin_skew_m3.sdc` (via pre_cts_skew_m3.tcl / pre_ref_skew_m3.tcl / post_plain_m3.tcl): the skew boundary with
  `-reference_pin res_q[0]/CLK`, so WC setup and BC hold see that corner's arrival (checked on the m3 CTS ODB with both corners:
  WC max launch 988, BC max 642, BC input hold -103 = the single-corner FF value). This OpenSTA reports no WC min path from such an
  input (WC input hold is not a sign-off check). Hold margin 40 ps (FF acceptance +15 with 25 ps uncertainty).
  Rejected on the way (attempt 2, killed after CTS): a generated clock at res_q[0]/CLK -- OpenSTA uses the MIN latency over all
  corners for every hold check, so WC showed fake input hold -445 ps and repair inserted 32,018 hold buffers.
Sign-off unchanged: corner_sta.py + io_lat_skew90.sdc, accept SS >= +40 at 833.333 and FF >= +15.

## m3 benches (m3_bench/)
- W11 multiplier equivalence, 2,000,020 cycles: LAT 3..10, LAT 9 KCP 4, LAT 10 KCP 4 all 0 mismatches. Negative controls: LAT 10
  against the LAT-9 delay 1,671,104 mismatches; one KCP copy's operand corrupted (NEGK) 118 mismatches (both FAIL as required).
- Slab element (tb_qwen_slab_port_group, IN_STAGE/AM_SPLIT/S5_CTL/SCALE_PAIR/OREG 1, LEAD 9): MUL_LAT 10 + MUL_KCP 4 PASS 1,505 results
  bit-exact, 751 argmax tops (m9o reference also PASS). Negative control LEAD 8 (res_in mis-timed): FAIL.
