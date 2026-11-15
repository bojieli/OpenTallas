# FABLE-KVRING-HOLD: KV landing-ring cores FF hold -303 / -316 ps (2026-11-14 20:3x PST)

Verdict: the "late 1% of fclk sinks" is a MEASUREMENT ARTIFACT in subtree_balance.tcl (wrong clock edge), triggered by
RTL parameter CONTROL_STATUS_COPY=1. The sinks are not late. No macro, ICG, generated clock, SDC latency or hold buffer
is involved (OVERSIZE-1 guess of hold buffers counted as sinks: ruled out; the outliers exist at 4_cts before any hold repair).

## Kits and DBs
Failing (epyc10, last DB 4_cts.odb; 5_1_grt stopped by OT_HOLD_STRUCTURAL, no GRT DB saved):
- /srv/opentallas-scratch2/claude/oversize-1/rk2/kv_cland_w269_ns_0fea0/kits/kv_cland_w269_ns_0fea0_synth0 (-302.87 ps, 291 delay bufs)
- /srv/opentallas-scratch2/claude/oversize-1/rk/kv3_cland_w257_e_s11/kits/kv3_cland_w257_e_s11_synth0 (-315.56 ps, 299 delay bufs)
Signed siblings (epyc10 rk2/): kv_cland_w259_ns_a43af, kv_cland_w294_ew_a7ae4, kv_cland_w549_ew_bf94f; kv3_hcland_w292_e_s11
(rk/, run dir not on epyc10; logs not read, parameters read from its wrapper .sv).
My what-if (copy of the w269 4_cts.odb, nothing in the kit touched): epyc10 /srv/opentallas-scratch2/claude/fable-kvring-hold/
(q.tcl/q.log sink census, q2.tcl/q2.log balancer report A/B, stb_orig.tcl, stb_edge1.tcl = proposed patch).

## Which sinks, and where the 430 ps comes from (MEASURED, w269 4_cts.odb, FF, placement RC)
The outliers are exactly 16 flops: the two ot_meso_ca_status_copy banks
u_ring.g_control_status_copy.u_guard_status/{written,lap_q}[0..3] and .u_status/{written,lap_q}[0..3]
(2 banks x 2 x DEPTH 4). Netlist census of clock pins:
| class | n | CLK driver | arrival rise | arrival fall |
|---|---|---|---|---|
| fclk DFFLQN (negedge slot/tag/count/wen flops) | 1115 | CTS leaf buffer | 84..88 | 501..506 |
| fclk DFFHQN (status copy) | 16 | own INVx1 below a leaf buffer | 510..512 | 92..93 |
| clk DFFHQN / DFFLQN | 480 / 8 | CTS leaf buffer | 181..191 | 605..616 |
Cause chain: WFALL=1 makes wclk = ~fclk. The slot flops absorb the inverter (yosys maps them to negedge DFFLQN on raw
fclk). ot_meso_ca_status_copy is a (* keep_hierarchy *) module with posedge tclk, so it cannot absorb it: synthesis leaves
posedge DFFHQN behind an inverter (CTS-0041 "Net net759..774 has 1 sinks. Skipping" = these 16). The RTL comment on
ot_meso_wen_ff (DIE-QC-70) describes this exact problem and fixed it there with NEG=1; the status copy never got that form.
stb::arr reads arrival_max_rise on every sink. For the 16 inverted sinks the rise at CLK is launched by the source FALL
at 416.5 ps (half of 833), so they read 416.5 + ~95 = ~511 (GRT 527..546); the 1115 DFFLQN read the source rise, ~86.
"430 ps" = 416.5 half period + ~8 ps inverter + ~6 ps tree. Both groups capture on the SAME source edge (falling fclk):
active-edge arrivals are 501..506 vs 510..512, true skew ~6-11 ps. The balancer then pads 1115 flops by ~430 ps to
match the false target: fclk insertion goes 110 -> 540 ps against d/t_rst_n input delays on ideal fclk and the 16
un-padded status flops -> hold -303/-316 (1040..1093 endpoints). Hold at 4_cts before the balancer: ws -28.5 ps (ordinary).

## Why the signed siblings do not have it (MEASURED)
All four signed cores have no CONTROL_STATUS_COPY (their wrappers: STATUS_REG, GUARD_REG, WFALL, WREG, DSREP, WRITE_CHUNK=16,
RSTREP, +-PLACEREP). No kept status module -> no inverter on the fclk path -> CTS-0041 count 0, OT_STB before fclk spread
8/9/14 ps, 0 delay buffers. Both failing cores have CONTROL_STATUS_COPY=1 (clock_landings.py status_copy opt-in, pv_v1n
vport rings) and 16 CTS-0041 lines each. INFERENCE: every ring core with WFALL=1 and CONTROL_STATUS_COPY=1 (any die;
head_tile_source7_kit.py requires it on HEAD) fails the same way, soft or hard, wherever subtree_balance.tcl runs on it.

## Structural fix (two parts; A alone closes these two cores)
A. Balancer rule STB-EDGE-1 (subtree_balance.tcl source in the kit generator): carry inversion parity down stb::build
   (flip at INV*/CKINV*), and in stb::arr read arrival_max_fall for odd-parity sinks, so every sink is measured from the
   same source edge. 5-line patch = stb_edge1.tcl above (diff vs stb_orig.tcl). MEASURED in report mode on the w269 DB:
   original "fclk p99 511 max 512 spread 428", patched "fclk min 84 p99 93 max 93 spread 9" -> 0 buffers; clk unchanged.
   This is a correction of a wrong measurement, not a new limit. Not audited: pair_skew.tcl, orfs_hold_mm.tcl,
   vclk_measured_hold.tcl also read arrival_max_rise (corners.tcl already folds half a period); check them for the same edge error.
B. RTL (cleaner clock, same cycles): give ot_meso_ca_status_copy the ot_meso_wen_ff form: parameter NEG, negedge of raw
   fclk, instantiated with .tclk(WFALL ? fclk : tclk), .NEG(WFALL). The 16 flops become DFFLQN on the CTS leaf nets,
   the 16 per-flop inverters leave the clock path. Same function (posedge ~fclk == negedge fclk); needs the ring LEC/sim rerun,
   so it belongs in the next RTL event, not in front of A.

## One-build proof
Resume kv_cland_w269_ns_0fea0 from 4_cts (new kit dir or copy+mv of subtree_balance.tcl, never sed -i) with the STB-EDGE-1 file.
Pass = "OT_STB before fclk ... spread <= ~20" and "OT_STB done: 0 delay buffers" (or a handful), no OT_HOLD_STRUCTURAL,
FF hold >= 0 after normal repair, then sign-off. kv3_cland_w257_e_s11 follows with the same file.
OVERSIZE-1 planned A/B (OT_STB_EST=placement) would NOT help: the artifact is 428 ps on placement RC too.
