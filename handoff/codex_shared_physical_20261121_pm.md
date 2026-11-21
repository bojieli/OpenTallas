# Shared physical lanes, Nov 21 afternoon

## Timing readers

- Merged ae136503372. The post-place worst-path geometry uses actual instance and port pins, including escaped bus terminal names. QC cbn_q11 on the same placed ODB reads TT −377.04 / TNS −200790.95 before and after. Corrected hop 821.3→62.5 µm, wire path 833.7→128.0 µm and endpoint span 810.5→3.5 µm. Replay epyc8 tap-grid-r4/postplace-pin-diagnostic/replay2.log.
- Merged 9bf23638b0f. The post-place observer reads the populated sibling SDC. CB cf0b exact E2 3_place ODB reproduces −380.66 TT rather than the −659.86 golden-SDC artifact, on the same local macro input path. Replay epyc2 tap-grid-r4/postplace-sdc/replay.log. Timing target, production CTS/GRT SDC and clock period are intact.

## D28 and shared tap grid

- Older KV v8c run completed with TT −8483.95 / hold −690.25 and 215 of 398 outside tap-target tolerance. Reject it as a closure case. Older D28 tap-only G0's twelve errors were legacy cap 1200 gates on pv_v6 and hub_Wo; the separate ≤3000 report passed. That bind needed fresh reset predecessor remap.
- The actual split15 R5 preview d9a9d530060f6 is supported by exact clipped parent tap-net capacity rows on epyc8 tap-grid-r4/split15. Parent placed bins split 83,130 west and 109,052 east. The saved review pictures show legal additions on the populated channels. Same cap 1,200, west 136 taps max 1,159, east 168 max 1,143. Independent optional radius coverage adds four west taps and meets 185.312 µm; the east exploratory arm still has four radius-outlier taps.
- To preserve west old t112 in KV's landing remap, add clk_t136 at (1020.576, 1503.392) on its cap-base rows. Exact pin snap stays at the old site. West max 1,159 remains; 417 sinks attach within 137.168 µm. KV owns applying to its private successor and remapping before bind.
- S81 h9 r0 p3 older col cap pilot gained TT 66.08 and FF WNS 6.58 ps; FF TNS worsened 3821.2 ps, so keep as a trial only. The old t39 t98 tap-only arm regressed and remains held. Same-place t39 pair-span seeded arm differs below 0.1 ps TT WNS and zero FF WNS compared with terminal-only; TT/FF TNS tradeoffs and remaining VP writer load are recorded in TAP-GRID-R4.

## Relay seats and lockups

- FAM COL h9_r1 private TC exact retained 3_3 replay now uses landed ae660 and 83 of 87 groups fit vs zero of zero before. Existing FIT_CHAIN opt-in moves one seat and clears the prior 514.281 µm direct hop. Largest direct hop across fully fitted chains is 397.278 µm. Two remaining over-reach chains need +1 stage at current endpoints. RLYBR and TC routed GRT work remains under FAM-S81-COL-R5 on epyc8.
- The private QC V2 lockup baseline attempt deleted its only gen copy in the old off-hub runner. Main 5f2c571421e repairs the wrapper. QC's approved live official epyc7 V2 baseline already exists, so reuse it. Auto reader qc-lockup-r3-v2-measure.service on epyc7 waits for the sealed route CTS and writes exact hold-end and zero-logic endpoint selection under lockup-station-r3/v2_measure. No restricted proof route armed. S81 p6 lockup proof is still in GRT.

## Global routing

- FLOW-CLKGRT-R2 KV control kv3_hg_v1p2 D26 a3 fails exact geometry with blocked central streets, eleven taps on macros, max tap load 10,009 and 9,082 long register hops. Do not route this cohort without revised actual geometry. Two private inherited place arms are on epyc8 and epyc7. Head hd_spn a5 exact retained 4_cts was visually reviewed and is running separated baseline vs clock-first resistance-aware A/B under epyc7 flow-clkgrt-1121/head_spn. No default change.
- FLOW-OBS-GCELL-R2 hd_host_e v2 retained DRT iteration 60 has twenty-five M7 residual markers, including twenty-two u_epc EOL, then RSZ-0060. HEAD owns fresh LEF-override route. Exact KV hroot net2446 failed M8→M7→M6 via corridor fully lies inside two legacy PGCAP zero-M7 regions. Current wide-spacing PG obstructions cover the otherwise misleading 96 nm gap. Sparse one-net replay uses a different small-layer path with or without the wider guard. This is a mechanism diagnosis; production closure still needs the reviewed congestion A/B in KV's current kit.
