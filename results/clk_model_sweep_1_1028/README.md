# CLK-MODEL-SWEEP-1 (2026-10-28): DIE-S81-17 stale-stage-model risk sweep, QC / KV / HEAD / HBM (estimate only, no builds)

Method: per routed clock leg, fit n*d0 + k1 L + k2 sum Ls^2 + kf (fanout-1) vs GRT node arrivals (DIE-S81-17 cal_est form);
"before" = the model the builder used; region skew change = max |path-sum of leg residuals| below the LCA per region.
Early label: early_label.py = per-partition nominal early spread on raw taps vs arrival + declared early (arrival - planned target).

| die / tree | builder model | rms/leg before -> fit (TT) | early-ratio double comp | skew report counts planned earliness | worst in-region skew if recalibrated |
|---|---|---|---|---|---|
| QC trial15 (intel2 die-qc23-1028, 12626 legs) | region DME, QC own inv2 cal trial13b (DIE-QC-21); fixed already | 12.03 -> 7.58 (BUFx24 ref 13.54) | no: early 1.0, FF 0.87 = FF/TT unit conv, merge mode | YES: g15 intra skew 562.3 TT is c_*_tf_00 core tap c0; nominal 502.3 raw -> 123.4 TT / 121.4 FF vs target | model-error p50/p90/max 51.5/94.3/123.1 -> 39.9/74.9/126.3 TT (max not model-driven) |
| KV DIE-KV-14 fishbone/link_htree (intel1, 7982 legs) | geometric equal length (balance_legalize), no stage model; --tap-pad from old KV-5 tree | 9.44 -> 7.54 | no ratio, no early taps; BUT pads (96-123 ps) overshoot 30/32 phy regions up to +56 TT | no (no early taps) | 99.2 -> 68.8 TT incl pads; unpadded 80.5 -> 68.8; gate ~157.6 -> ~146 UNCHECKED |
| HEAD die spine_fishbone (intel2 die-head-11 g5_r200, 495 legs) | geometric, no DME | length-only 20.3 -> 13.7 | none (no die early taps) | die: no in-region pairs; tile pair_skew YES 292.5 TT raw vs ~-20 real (UNCHECKED) | 0 (no in-region pairs) |
| HBM trial2b link_htree (intel2 die-hbm-10, 13869 legs) | geometric H-tree, no DME; 461 legs unbalanced after slide (max 3246 um) | group-mean 34.1 -> 19.0 | none; 38 types declare early core taps but link_htree cannot deliver them | no skew_diag run yet | p50 196 -> 128, max 1422 -> 693 TT (hubs; SM regions not model-limited) |
| HBM-RISK-1 k1 (epyc2, placement STA, BUFx24 DME) | STAGE_1X_TT on BUFx24 (matched cell) | 55.1 -> 24.5 | none | n/a | 775 -> 737 |
| PHY_N W/C/E | plan only (one tap per slice), no routed data | - | - | - | - |
