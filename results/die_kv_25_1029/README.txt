DIE-KV-25 2026-10-29 (KV die owner; successor DIE-KV-24 + Codex KV reset packet 05:03). Runs intel1:/srv/opentallas-scratch2/claude/die-kv-25-1029.
Tools = main 2b90210bd (die_trial / die_sta_related / fit_dme_stage_cal); clock build path = tools/clk/ot_clk.py (12.17(2)):
configs/kv_e26.yaml + registry entry inv_ndr_kv21_treeb; ot_clk replay of kv_e26 = IDENTICAL to the die_trial kit_e26 (otclk_replay_e26.log).
Input plan = Codex event26/plan.json (strict bind26b PASS 160 parts/56 types/2545 crossings/430554 bits, 0 errors: bind_report read CHECKED).

(1) event26 vs tree-c plan hm_r26q15c: partition origins, ports, lanes, type outlines/buses/face pins identical; BUT 45/56 types now declare
    clock.core_taps = "early" (v5.0 early taps), so main die_trial builds 3549 taps (1920 partition + 1629 hard-core taps), 21191 cells
    (89 BUFx24 + 21102 CKINVDCx16), not tree c (1920 taps / 15296 cells) on which bind b, CA, Codex native6 graph and the packed clock body were made.
(2) Die GRT0 incl clock (combo GRT, M4-M7 signal / M8-M9 clock, 50 it) on event26: TT/FF overflow 0, usage 2.38 %; duty 0 taps outside 45-55,
    MPW est fail 0 (all variants) [CHECKED-own]. repc (tree-c recipe on hm_r26q15c) reproduces KV-21 kit_c ctree.v byte-identical.
(3) In-region spread <=150 (TT/FF): e26 (DME pv_S_6/7) hub_Wi 414.5/367.0, pv_S_5 155.6 -> FAIL; e26b (DME pv_S_5/6/7+hub_Wi, kv21 cal)
    hub_Wi 159.6 TT / 136.8 FF -> FAIL by 9.6 ps TT (only region >150); c26/d26 (own-leg refit cal, more DME regions) WORSE (hub_Wi 184.1, pv_S_7 178.3) -> stopped.
    Cause (hub_Wi): early core taps c1/c7/c8 arrive up to ~157 ps before the partition taps; tree c was 69.8.
(4) Die STA (main die_sta_related, 4 signed views e1/e2/e5/e6 @3e7fccd216, CA = Codex native6/native_bind.json) on e26 proof:
    spice_edge: intra TT +211.98 / FF hold -389.75 (real-view -81.58, kit contract -352.07 FAIL); seam FF -130.29 (contract -10.42 FAIL);
    landed CA lo TT -14.0 / FF 12.9 FAIL (bind planned on tree-c arrivals); core_insertion FAIL: 733 of 1629 early core taps have no signed view.
    spice_cell (gate number for BUF paths): intra FF -407.14, landed lo TT -53.1 / FF 1.8 FAIL. Status UNCHECKED (no NUMBER-CHECK).
=> KV freeze gate: GRT0 PASS; clock check FAIL (spread hub_Wi, CA on the early-tap tree, missing core views, hold); START physical (native6 provider body) not placed.
Tests: tools/clk/test_ot_clk.py 2 FAIL in the sparse WT only because results/die_qc21_1028 and s81_head pin files are not checked out (not touched here).
