# S81-TYPE-MEASURE (read-only, 2026-11-14/15)
Plan measured: B3z2 (epyc7 s81-b3-clk/ev/B3z2.json): 395 identities (394 counted + 1), 172 base types (strip __cl/__pv). All 36 signed types are in it (col_h9_r0_p1/p2/p3 x30, col_h10_r0_p1 x6).

## 1. Groups (ids / bases)
ot_s81sl_leaf 75/69; col_h9_r0 60/6; col_h9_r1 60/1; col_h9_r2 60/1; slice_station 46/35; col_h10_r0 12/2; col_h10_r1 12/1; col_h10_r2 12/1; serdes 11/9; dsdv/svc ~40/40; rest 1:1.
## 2. Layout sameness (outline + hard-core module/origin/orient + all bus name/dir/width/face/window + ft_slots + internal_stations)
- Pin sets, windows, faces, outlines are ALREADY identical inside every col base: col_h9_r1 60 ids = 1 layout; col_h9_r2 60 = 1 (2 with clock); col_h10_r1 12 = 1; col_h10_r2 12 = 1; col_h9_r0 60 = 6 layouts (= 6 bases); col_h10_r0 12 = 2. No superset needed: nothing differs.
- What differs between ids: pv = param_set only (43 P_*_INSTANCE strings, "ROM image per instance", i.e. RTL content, not geometry); cl = clock landing_contract (r1: 2 classes; r2: 5 classes with different taps/sink_sites; h10_r1: 2). cland_col_superset.py (step B) already unifies the landing contract for r1.
- Whole die: 395 ids -> 186 distinct physical layouts (194 with clock taps). So ~200 ids (51%) are geometric duplicates; 144 of them are col_h9/h10 r1/r2 (144 ids -> 4 layouts, 6-7 with clock classes).
- Genuinely different: slice_station 44 layouts for 46 ids (t6, t44 differ in outline 1278 vs 1226; cores/ft_slots/taps differ); ot_s81sl_leaf 74/75 (core placement + stations differ per cl). Do not merge.
## 3. Gain
- Builds: if one build per layout class served all ids: -137 col r1/r2/h10 builds, and r0 col -50 (but those are signed). Unsigned only: ~-137 of 359 unsigned ids (38%).
- Wave logs, last 10 h (jobs/*/a*.log, 266 S81 attempts of 488): col_h9_r1 47, r2 30, r0 30, col_h10 30 = 137 attempts (51%); slice_station 48; leaf 78. Failures (rc != 0, not running): col 39 of 102 S81 (38%): r1 13, r2 11, r0 11, h10 4; slice_station 31, leaf 31. Zero S81 attempts finished rc=0 in the window. rc=2 dominates (62); DRT-0255 maze fails and GRT-flagged renders appear. Col failures repeat on the identical layout, so one fix + one build would stand for 60.
## 4. Cost / risk
- Merging ids needs a plan event + bind + LATCHECK + G0 (96-120 GB plan job, current bottleneck) AND an RTL answer: pv ids carry different ROM-image parameters. Whether the netlist (ROM cells inside the partition) is identical across pv is NOT measured; if the ROM image is baked in logic, a single layout cannot be reused without making the ROM content a macro/loadable (RTL/flow change, per-instance LEC). That is the real gate.
- Superset pins: not applicable for col (already identical) so no added congestion. For slice_station/leaf a superset would add pins to types that fail GRT: not recommended.
- Re-sign: none for r1/r2/h10_r1/r2 (no signed type). Touching col_h9_r0 p1-3 / h10_r0_p1 (36 signed) would re-key them: avoid.
- Token latency: col clock cl classes differ in taps/landing; collapsing r2 (5 classes) changes landed contracts (handoff DIE-S81-92: r2 5, h10_r2 4 role-dependent); needs LATCHECK 873 re-run; r1/h10_r1 (step B, B3y) safe.
## Recommendation
PARTIAL pass on col_h9_r1, col_h9_r2, col_h10_r1, col_h10_r2 only (144 ids, unsigned, identical geometry): implement "one physical build per layout+clock class, other pv ids inherit it" (build-level reuse, no layout change) after confirming pv netlist equality; fold into the B4 plan event rather than a separate one. Do NOT touch signed r0 families, slice_station, or leaf (layouts really differ). If pv netlists differ (ROM baked), downgrade to don't.
