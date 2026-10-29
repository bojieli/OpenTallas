# DIE-HBM-21 (HBM die owner, 2026-10-29 15:05-17:3x PDT)

Plan candidate **d21** = d16k_q2L (0b7b966cbaf2) + EP B4r + qcore Q2d + sfustore/cp_rxs SRAM-edge rule.
intel1:/srv/opentallas-scratch2/claude/die-hbm-21/plan/d21 (die_plan 510f3e209486, core_macros 000a42968308, see d21_sha256.txt).
G0 PASS 0 errors; G0C = the 8 inherited errors of epB4, 0 new (g0*_d21_summary.json). CHECKED.
Built as: `epb_plan.py d16k_q2L ep_r B4r_plan_pins.json 427.68 246.24 dh21b4r "[220.32, 25.92]"` ->
`mkvar.py ep_r d21 spec21q.json` (qcore 267.84x250.56, Q2d macros, origin shift 8.64, stations not re-sited) ->
`sfu_s1.py d21` -> `rxs_rb.py d21`.

All probes = place-only on the kit synth (run_place.sh), judged by AUTO-GEOM (review.sh -> geom_check.sh, GRT 50 it).
Per-probe verdict lines: probes.tsv.

| item | probe | result (CHECKED) |
|---|---|---|
| hfd_ep_static channel_h 1.081 | B4s S band +4.32 | FAIL channel_h 2.861 (1-um fragment window), fill 0.088 |
| | B4m mid channel +4.32 | FAIL channel_h 1.095 |
| | B4p / B4p2 E/W pin columns raised | FAIL 1.143 / 1.183 |
| | **B4r** SerDes S pins 0.192 pitch, sd_rx centred under mid channel | **PASS**, channel_h 0.845, GRT 0, r2r 320.0 |
| qcore V3a channel_h 1.004 | Q1w mb x 10.8 | channel_h 0.84 but pin_reg_max FAIL 154.1 |
| | **Q2d** mb down 4.32 (y 40.668) | **PASS**, channel_h 0.98, GRT 0, r2r 336.1 |
| sfustore (vA GRT 13, relay 7) | **S1** cols R0/MY/R0 | GRT 0, relay 0, channel_h 0.675; r2r 504.85 (10) = u_fcore.fault -> E u_bout_fault (vA kit predates plan fr17 re-face) |
| | S3 cols MY/MY/R0 | GRT 0, r2r 509.17 (12) |
| host_cp_rxs (GEOM-65 FAIL: GRT 28377, channel_h 1.677) | RD one W column MY | GRT 0; r2r 671.6 (455), channel_v 1.126, clock_reach 298.9 FAIL |
| | **RB** 2x3 S half, rd_out to a 58.9-um centre channel | GRT 0, channel_h 0.407, relay 0; remaining FAIL fill 0.035 / empty 0.78 (outline 434.8x480 for ~5k um2 of cells) + r2r 557.6 (331: 329 are fanout of ONE reset flop u_fcore.u_rr.rst_n, 2 data codec q_pin) |

SRAM-edge rule: cxport_ij_q has no SRAMs (N/A). whatif.py = placement-held what-if on geom.tsv (estimate);
hotnets.py = nets crossing a cut window.
