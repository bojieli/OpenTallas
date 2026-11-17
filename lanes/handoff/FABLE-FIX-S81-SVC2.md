# FABLE-FIX-S81-SVC2 handoff (Fable owner of the S81 svc family, dp_svc_* types), 2026-11-17 PST
Worker: S81-SVC-SPLIT (Sonnet). Status: STRUCTURAL FORM DECIDED from measurements; NO core kit generated, NO build launched,
NOTHING signed, NO plan rows written yet. The flat lo7 form is closed as a failure (5.69M cells, GPL target density 1.0636).

## Measured (V = read from files by me; W = worker; E = estimate)
- V flat netlist census (epyc8 scratch3 claude/fable-fix-s81-svc2/census/{census.py,census.json}, input lo7 kit 1_synth_odb.v):
  5,688,959 instances; 1,135,302 FFs (95,375 async-reset DFFASRHQN); INVx1 1.14M; 161 macros (64 ot_s81c_attn_hcore, 8 dsdv_svc_sx_hrow, 89 SRAM).
  FF mass: u_irg_07 451,536; u_sms 252,874; 4 x merge (g_m_N) 60.1k each.
- W hierarchical generic sizes (s81-svc-split/size0/h.json, 6,350,726 generic = mapped x 1.116), V port bits (census/ports.py):
  | module | inst | generic cells each | in / out bits | note |
  | ot_hdc_v41x_idx_hslice | 32 | 62,409 | 1157 / 1146 | chain ql_codes->qo_codes 512, k_key->ko_key 544; 8 per dsdv_idx_rg2_chunk PR=1 |
  | ot_s81_su_sml | 16 | 106,819 | 141 / 68 | ot_hdc_v41x_exp 89.6k inside; 4 per dsfd_su_t_smhq |
  | ot_s81_su_smd | 8 | 74,279 | 173 / 34 | 2 per smhq |
  | ot_hdc_v41x_attn_merge_x | 4 | 318,150 | 537 / 529 | 80 qaddf x 3.6k in 5 g[] groups |
  | ot_s81_su_smc | 1 | 57,533 | 516 / 34 | |
  | ot_s81_su_smr | 1 | 36,924 | 586 / 66 | |
  Sum of these 62 instances = 5.67M generic (89 %). Rest (shell) = 0.68M generic = ~0.61M mapped: ot_bind_native x118 164k,
  14 landing rings (ot_dp_clk_landing_cas) 129k, attn_tr_x x4 65k, ot_dp_dly 47k, own 62k, eng_tap 29k, ctrl_rg3 26k, captures 27k, smq 12k.
- V timing: 2_floorplan_final.rpt. The ring path u_cland_unit_i1/u_ring.ctl_w[0] -> lap_ok is MET +178.53 ps (8 stages, 416.5 ps max_delay
  group); it is NOT a long cone. The only failing max groups are reset: clk -44.5 ns and asynchronous -57.5 ns, both through
  INVx1 _8121023_ -> net u_bound.u_u_rsv_14_u_g_smt_u_gw.rst_n fanout 15,395 (64 hcore rst_n pins + flops), unbuffered.
  98,651 failing ends in the unplaced repair_timing vs 95,375 async-reset flops: the failing set is the reset recovery set.
  The GPL -2.57 ns was never traced to a data path (no placed DB). No data-cone pipelining is justified by the numbers so far.
- V prior art, SIGNED and exported (rtx-pro /home/ubuntu/signed-export-1114/s81, AGIdock /archive/opentallas-signed-1114/s81), S81-SVCRS-3 11-10/11:
  ot_s81_su_smc 77.76x259.2, 552 pins (= 516+34+clk+rst of lo7 smc); ot_s81_su_smr 69.12x259.2, 654 pins (= 586+66+2 of lo7 smr);
  ot_s81_svc_idx_hslice_fp 77.76x276.48, 2305 pins (PR pin regs, EL 140; lo7 hslice has 2303 port bits);
  ot_s81_su_sml_fold2 103.68x259.2 / ot_s81_su_smd_fold2 69.12x259.2 / ot_s81_svc_merge_h4 103.68x259.2 (H8 forms, pin counts differ from H16: not reusable as is).
  These were the v2g H8 provider form; H16 (B6c1, S81-SVC-H16 11-14) dropped the providers and went flat. Signed providers sit at ~0.33 std fill.
- V area: core 4,262,791 um2, fixed 3,124,339, free 1,138,452 um2. E new cores at 0.60 fill: hslice 12.0k x32, sml 20.6k x16, smd 14.3k x8,
  merge_x 61k x4, + signed smc 20.2k + smr 17.9k = ~1.11M um2, +10 % channels, + shell 0.61M cells at 0.5 = 0.16M -> ~1.38M um2 needed:
  E outline 1442.88 -> ~1598.4 x 2980.8 (+155.52 X; die Y spare is 19.5 um per S81-SVC-H16, die X spare 755 um). With the signed 0.33-fill
  hslice_fp donor instead of a compact hslice: +~300k um2 more (another ~+100 um X).

## Decision (structural form "H16 providers")
1. Hard cores, one master each, H16 params, never reshape hcore/hrow/SRAM: ot_hdc_v41x_idx_hslice x32 (or signed ot_s81_svc_idx_hslice_fp if
   the worker proves pin/param/latency identity), ot_s81_su_sml x16, ot_s81_su_smd x8, ot_hdc_v41x_attn_merge_x x4 (parallel fallback form:
   one core per g[] group, x20, ~64k), ot_s81_su_smc x1 + ot_s81_su_smr x1 REUSED signed if source/params identical, else rebuilt.
2. Pipeline: none on data cones (ring path met). Core pins registered (pin_audit_core.py); where a port is not registered add pin
   registers in the core wrapper (cycles pre-approved, report latency rows).
3. Reset: keep the kit's relay tree (bound_reset.json, reset_tree.tcl, depth 12); leaves reach core rst pins; each new core carries its own
   reset entry register (ot_reset_sync / 64-edge S81 reset contract). The 15,395-fanout net goes away with the cores (its sinks are inside them).
4. Shell after cores ~0.61M mapped E: over 400k. Next cut in order: landing rings -> cland ring macros (129k), then attn_tr_x x4 (16k each).
5. Outline: +155.52 um X estimate, to be fixed from built core outlines; rows to S81-DIE-R3 for the event after D6x/D7x.

## Worker tasks posted (W1..W5, see lanes/posts/FABLE-FIX-S81-SVC2.md)
W1 reuse proof smc/smr/hslice_fp; W2 core kits with the normal generator (r588 shared kit files); W3 builds via ot-run to R-MINIMAL;
W4 shell recount with cores black-boxed; W5 census of the other svc types (hi3, t6, pvso).

## Not done / next for the owner
- Read W1-W5 results; fix outlines; write plan rows (type contents + outline + latency rows) and hand to S81-DIE-R3.
- Shell kit (cores as macros) build after cores sign; R-MINIMAL sign-off; export AGIdock + rtx-pro.
- GPL -2.57 ns data path still unmeasured; measure on the first placed shell.
No job of mine running. No kit patched. Nothing deleted. Old kit E8 scratch3 fable-fix-s81-svc/lo7_floorplan_fix1117 kept as evidence (FLEET-OPS may reclaim results/*.odb, 30 GB, once the worker no longer needs 1_1_yosys_canonicalize.rtlil).

## UPDATE 11-17 ~14:0x PST (COORD message)
- Scope of the form = whole svc family, svc_hi included (hi3 dp_svc_hi_dsdv_svc_rs__t3, 4.20M std cells + 140 macros flat). W5 (census of hi3/t6/pvso for the same masters) is REQUIRED before plan rows, not optional.
- hi3 flat run (S81-TYPES-R3, E8 unit 3543253, container dpkit-svc_hi_dsdv_svc_rs__t3-3543364, in CTS final report, 56 GB; CTS detailed placement 10,052 s) keeps running to GRT as a data point only: I take its GRT congestion map, overflow and frame TT (plus the worst DATA path start/end/stage count from 4_cts_final.rpt) into the form. It is not the release path and I do not wait for its sign-off; S81-TYPES-R3 keeps owning the job.
- COORD relayed W1-W5 to S81-SVC-SPLIT (my SendMessage did not reach it).
- NOT YET READ by me: hi3 4_cts_final.rpt (the first placed svc timing; it answers the open -2.57 ns data-path question for the family).
