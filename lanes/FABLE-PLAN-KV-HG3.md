# FABLE-PLAN-KV-HG3: structural review of KV plan event HG3 (2026-11-16 21:1x PST)

Plan 006e38e15a71 (epyc10 kv-r/hg2f/plan_c_hg3.json), tree D11 src_kv_pin_eb1e73448bd0_hg3_006e38e1_d11
(manifest b3846f5bbf72). Base HG2c fac383f38bc4 (D10, manifest 3fbbcd9f69fc). Read only; all numbers below are
measured by me from the two plan JSONs and the trees unless marked INFERENCE. The bind belongs to KV-R (not started when
I read: no hg3 gate dir; the HG2c bind was still running, 29 CPU-min).

## Verdict: PASS, no block. One fold recommendation (F1) with measured numbers.

## 1. Do both changes land exactly? YES
- Full deep diff HG2c -> HG3: 13 changed leaves, nothing else.
  11 in clock.cohort (the object equals rows_cohort_e6a.json sha b043c6e92991, byte check of file sha on epyc10 and epyc7),
  2 in partition_types.kv3_hub_Wo.clock.landing_raw_branches: [52] fs_o_idsrc_WN_y stages[1] x 535.976 -> 545.6 and
  [63] fs_o_seq__g_fan_N__u_fan_kc_d1 stages[1] x 535.21 -> 550.5; y 669.3 on both, unchanged.
- D11 vs D10 manifests: 323,676 files each, 1 file differs (plan_c.json), 695 overlay entries, 1 differs.

## 2. Cohort vs rows B / C and tap budgets: CONSISTENT
- Cohort: id kv_hg2_e6a, tree dc4842b75b69, ctree 24bfec154b8f, 11,571 taps / 42,509 cells. Both hashes match the files at the
  named source today (epyc7 fable-die-kv/hg2/runs/e6a/kit/clock tree.json, ctree.v), and match kv-r/hg2c_receipt.json.
- Rows C in the HG3 plan: 6,129 per-port windows, max 202, mean 72.4, 0 over 208.25; seam_ps 170. Rows B: 51 types,
  19,309 reserved rects. Same as the KV-CLK-R2 handoff. No tap, window, seam or reserved-site leaf changed in HG3.
- Budgets unchanged: insertion 250 +-40, neighbour 80.
- Advisory (KV-CLK-R2): (a) cohort.island_ft.rule still says "tree_kv58" twice (the island_ft_check line covers it; text only).
  (b) cohort.source is a scratch path on a fleet host; export tree.json + ctree.v off fleet before cleanup reaches it.
  (c) instance-weighted per-port windows sum to 11,204 against 11,571 taps (367 apart); I did not reconcile this
  (INFERENCE: taps in types without per-port rows); KV-CLK-R2 can state it in one line.

## 3. Hops and comb at the new spot: PASS
- Hops (same y, Manhattan = Euclid): WN_y 905.188 -> 545.6 = 359.6, 545.6 -> 166.764 = 378.8;
  kc_d1 904.805 -> 550.5 = 354.3, 550.5 -> 165.615 = 384.9. All <= 405. (The KV-HUB-WO text says <= 382; the real worst is 384.9.)
  Worst raw-branch hop in hub_Wo is 403.9 on an unchanged branch (fs_o_kvs_emb_px_tok_d1). R-REACH-4 inputs (taps, forwarded
  pins) are not in the diff; HG2 measured 0 over, worst 404.6.
- Comb, from the HG3 plan's own ft bit sites of kv3_hub_Wo: last ft column in rows y 667-671.5 is x 542.16 (cell to 543.24).
  Window 1 = x 543.44-547.76, window 2 = x 548.34-552.66: 0 ft cells in either, 15 of 15 rows fit, 45 slots each at the 1.188 fit
  width (need: 2 flops). Clearances: 0.20 um to the comb, 0.58 um between the two windows, 0.52 um to the tapcell column at
  553.176. Nearest rows-B reserved rect 25.8 / 21.2 um from the window edges. No hard core, station or other raw stage inside.
- The same model on HG2c gives 0 slots / 0 of 15 rows for both old windows (45 and 30 ft cells inside): it reproduces the failure.

## 4. Core reshaped? NO
No outline_um, hard_cores, origin or orient leaf is in the 13-leaf diff.

## 5. Latency: UNCHANGED
No bus, ft_slot, internal_station, pipeline or contents leaf changed; the two branches keep 4 and 3 stages. lane_asbuilt_latency.py
and bind.py do not read clock.cohort. So the HG3 LATCHECK must equal HG2c's row for row. HG2c's own LATCHECK had not finished
when I read (PRE PASS, G0 PASS 0 errors); KV-R: diff the two latcheck.tsv files, expect 0 lines.

## 6. Hold records (r424 terms): nothing releases on HG3
kit_wave qwen_kvsys is still on event KV-HG1, plan 08d352df7ef0, tree D5. 15 records:
- 13 with event_adopt:KV-HG1 (43 keys) and 1 with result:KV-R:kv-pc-delta (1 key): not tied to HG3.
- kv-hg1-pilot-cts: 31 keys, term proof:kv-hg1-pilot-cts, bound to plan 08d352df7ef0, not follow_plan. After the switch it keeps
  holding 31 keys and audits as HOLD-SUPERSEDED. KV-R: rebind it to 006e38e15a71 (or follow_plan) in the same switch.
- pilot-qwen_kvsys-7a4761d359fa ('*', follow_plan) names the D5 tree; the switch must issue the D11 one (b3846f5bbf72).
  kv3_hub_Wo is in no other record, so its relaunch waits only on that GEN pilot.
- planned_events has no KV-HG2/HG2c/HG3. Under r424 a new event_adopt:KV-HG3 term is refused until the event is declared. KV-R.

## 7. What else should ride on this event
- F1 (measured; owner KV-HUB-WO for the proof, KV-R for the fold). Same failure family, second type. Sweep of all 5,170
  raw-stage windows in 49 types against each type's ft bit sites: after HG3, 2 windows still have 0 fitting slots:
  kv3_hgi_v8 fs_ft11_o stage 1 (1213.92, 762.408), 45 ft cells inside, and stage 2 (1213.92, 375.684), 43 ft cells inside
  (ft comb x 1209.6-1239.8, y 749.8-771.1 and 369.9-391.0). No other window has under 4 slots. kv3_hgi_v8 has never reached
  place (it fails at GEN, class c21781975f), so this is a prediction; the model has the 2 hub_Wo windows as its only
  calibration and ignores tapcells and non-ft cells.
  Candidate moves that keep every hop <= 400 and clear ft cells, reserved rects, hard cores and other raw windows in the model:
  stage 1 -> (1215.0, 771.048) and stage 2 -> (1215.0, 391.074); hops 379.2 and 380.0 (were 386.7). An x-only move needs
  33-36 um and breaks 405 Manhattan (422).
  Recommendation: fold these two moves into HG3 before the bind starts (plan re-make + tree copy, no new event later);
  if KV-R's bind is already past G0 when this is read, let HG3 run and carry the two moves on the next KV event (HG2d / B2).
  Not a correctness block on HG3: HG3 is right as composed.
- Lever 7.2 (die_sta_related drops the 27 non-edge pairs): tool change, not plan; no need to ride.
- Lever 7.3 (5 child cores): registered as view candidates by KV-CLK-R2 19:48 (a4f5f64b5208); no plan row needed.
- Lever 7.4 (hub_Wo band): this event closes it; the INFERENCE in the strategy (band predates e6a) was wrong, cause is the ft comb.
- B2 (534 reserved rects in 5 signed types) stays a separate later event as KV-CLK-R2 planned; it re-signs types.

## Not checked
HG3 bind / LATCHECK results (not started); a real landing dry pass on a D11 hub_Wo kit (KV-HUB-WO proof was on the 7yhr
attempt_4 kit copy, 0 BAND FAIL, 70,435 cells placed; the ft sites I used are HG3's own); kv3_hgi_v8 in a real kit.
