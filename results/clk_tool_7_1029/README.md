# CLK-TOOL-7: HBM street_body clock on ot_clk (OWNER 12.17(2))

Clock of record (COORD 10-29 06:19): Codex street_body, results/codex_hbm_clock_1028/build_street_body.py on
codex/hbm-clock-0300@608e4fa9f, run intel2 codex-hbm-clock-1028/street_body (plan codex-hbm-pins-1028/street4, 3298 taps,
21722 cells). It called die_trial.clock_kit directly with three monkeypatch adapters.

Migration (default off, byte-identical trees when unset):
- body_sites.py -> die_trial --clock-body-sites (clock_site keeps the 1.62x0.27 native body legal) + --chain-hop-max 450
  (chain_ps prices a hop > 450 um as infinite); ot_clk top.body_sites / top.chain_hop_max.
- adaptive_detour_v2.py -> die_trial --detour-adaptive (failed A* retried around the connected macro wall; retries in
  clock/detour_adaptive.json); ot_clk top.detour: adaptive.
- fast_tap_clear.py -> nothing: main schema.tap_clear returns the same site (test_shared_tap_clear_equals_...).
- in-script PHY_N* region copy -> ot_clk inputs.region_fill; inline stage cal -> registry inv2_ndr_hbm_trial2b_early.
- config tools/clk/configs/hbm_street_body.yaml.

Proof (intel2 /srv/opentallas-scratch2/claude/clk-tool-7):
- base0: unmodified build_street_body.py on this branch base (f346d2fe4e) die_trial = byte-identical to Codex
  (tree.json, ctree.v, ctree.tcl, leg_spans.json, meta.json, adaptive_stats.json).
- base1: same script with the three die_trial opt-in globals instead of the monkeypatches (no fast_tap_clear) = byte-identical (all 6 files).
- replay_sb1: ot_clk replay --legacy of hbm_street_body.yaml through die_trial kit: ctree.v + ctree.tcl byte-identical;
  tree.json / leg_spans.json value-identical (json equal), bytes differ only in 180.0/200.0 vs 180/200 (kit CLI parses
  floats; Codex passed ints) -> replay_street_body.json verdict IDENTICAL_EXCEPT_META with diff_keys []. The kit then
  stopped after the clock (rc 1): street4 plan dir has no cores/*canon.json pin sidecars (not a clock issue; a real
  HBM kit needs inputs.pins_rebase or the composed C25c plan).
- Stage check: FAIL closed (the inline cal was fitted on the trial2b routed legs of a clock_rc ndr build; this stack
  is 1x). A new HBM build needs an ot_clk refit on a 1x route, or stack clock_rc ndr.
