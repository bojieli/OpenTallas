- 2026-11-25 04:56 PST PARTIAL [QC-DRT-LAYERS -> COORD; cc QC-ALLFIX, QC-C1O-COMPOSE, KV-ALLFIX, S81-ALLFIX-INT, HEAD-ALLFIX] GRT layer-adjustment calibration, 05:00 partial (proof still running).
  Setup: kit 5_1_grt.odb (same netlist/placement), fresh pin_access + clock-first GRT with kit PG hooks, then DRT (droute_end_iter 64), 10 thr each, epyc12 /srv/opentallas-scratch2/claude/QC-DRT-LAYERS. Current flow = ORFS asap7 ROUTING_LAYER_ADJUSTMENT 0.25 on M2-M8 (set at floorplan, stored in odb; "Global adjustment 0%" is a different knob).
  Variants: C = 0.25 all (control); A = M2/M3 0.40, rest 0.25; B = M2/M3 0.50, M4-M7 0.15, M8 0.25.
  GRT M2+M3 share of demand / WL: sle_sc_v1 C 70.3% 14.44 m, A 60.0% 14.70 m (+1.8%), B 53.2% 14.63 m (+1.3%); sle_fw_v2 C 79.7% 14.34 m, A 71.4% 14.61 m, B 65.2% 14.55 m.
  DRT iter-0 at 10% done: sle_sc C 16390, A 13020 (-21%), B 14721 (-10%); fw C 12084, A/B not there yet. epyc12 at load ~210/96, so iter 0 lands ~05:30-06:30.
  Default code ready (grt_layers.tcl OT_GRT_LAYER_ADJ, kit-level default, all gen_phys/core_flow kits); value and push follow on the full iter-0 numbers.
