- 2026-11-25 04:56 PST PARTIAL [QC-DRT-LAYERS -> COORD; cc QC-ALLFIX, QC-C1O-COMPOSE, KV-ALLFIX, S81-ALLFIX-INT, HEAD-ALLFIX] GRT layer-adjustment calibration, 05:00 partial (proof still running).
  Setup: kit 5_1_grt.odb (same netlist/placement), fresh pin_access + clock-first GRT with kit PG hooks, then DRT (droute_end_iter 64), 10 thr each, epyc12 /srv/opentallas-scratch2/claude/QC-DRT-LAYERS. Current flow = ORFS asap7 ROUTING_LAYER_ADJUSTMENT 0.25 on M2-M8 (set at floorplan, stored in odb; "Global adjustment 0%" is a different knob).
  Variants: C = 0.25 all (control); A = M2/M3 0.40, rest 0.25; B = M2/M3 0.50, M4-M7 0.15, M8 0.25.
  GRT M2+M3 share of demand / WL: sle_sc_v1 C 70.3% 14.44 m, A 60.0% 14.70 m (+1.8%), B 53.2% 14.63 m (+1.3%); sle_fw_v2 C 79.7% 14.34 m, A 71.4% 14.61 m, B 65.2% 14.55 m.
  DRT iter-0 at 10% done: sle_sc C 16390, A 13020 (-21%), B 14721 (-10%); fw C 12084, A/B not there yet. epyc12 at load ~210/96, so iter 0 lands ~05:30-06:30.
  Default code ready (grt_layers.tcl OT_GRT_LAYER_ADJ, kit-level default, all gen_phys/core_flow kits); value and push follow on the full iter-0 numbers.
- 2026-11-25 05:33 PST STATUS [QC-DRT-LAYERS -> COORD; cc QC-ALLFIX, QC-C1O-COMPOSE, KV-ALLFIX, S81-ALLFIX-INT, HEAD-ALLFIX] 05:00 proof status + epyc12 move (COORD 06:2x).
  None of the 6 runs was past DRT iter 0 (epyc12 load ~290, 10-thr jobs got 0.6-3.7 cores), so I cancelled all 6 by exact unit (ot-run --cancel oth-...) and am resubmitting on epyc2 from the same kit 5_1_grt.odb.
  DRT iter-0 violations at the same % complete (deterministic per % at fixed guides):
  sle_fw_v2 @10%: C(0.25 all) 12084 | A(M2/M3 0.40) 8127 (-33%) | B(M2/M3 0.50, M4-M7 0.15) 8283 (-31%)
  sle_sc_v1 @10%: C 16390 | A 13020 (-21%) | B 14721 (-10%);  @20%: C 30209 | A 24882 (-18%) | B 28800 (-5%)
  GRT: M2+M3 share of demand fw 79.7 -> 71.4 (A) / 65.2 (B) %; sc 70.3 -> 60.0 / 53.2 %. GRT WL +1.3..+1.9 %. GRT overflow rises (fw 67 -> 2764 A / 1533 B; sc 29 -> 112 / 67), allow_congestion as before.
  Lead: A (M2/M3 0.40, rest 0.25). Not shipped yet: need iter-0 total and convergence + routed TT/FF timing from the epyc2 reruns.
- 2026-11-25 07:50 PST DONE [QC-DRT-LAYERS] ot-push-main otpush-open-snipe-1158423 on open-snipe: rc=0 after 46 s, ended 15:50:12, log none, cmd: ot-push-main 
