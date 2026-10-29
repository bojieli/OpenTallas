DIE-KV-26 2026-10-29 (KV die owner; successor DIE-KV-25 b79712be87; COORD ruling (A) 05:47: drop early core taps, tree c).
Runs intel1:/srv/opentallas-scratch2/claude/die-kv-26-1029. Tools = main 2b90210bd (no die_sta_related/count_align change since; origin/main 83ef222a8).

(0) KV DIE RESET CONTRACT (COORD 06:0x, for the ASTK LEC) -> physical/die_plan/qwen_kvsys/reset_contract.json (+ reset_contract/receipt.txt),
    bench results/die_kv_26_1029/rst. edges 16, assert_edges 20, 30 modules (every event26 hard-core module, incl kv3_astk). [CHECKED-own iverilog]
    Bench on the bound bind26b root chain (kv3_hub_C_part.sv:4771-4772 u_rst_root ot_dp_rsync_s2 -> u_rst_lockq ot_dp_lockq STABLE 16; bind_por_gate PASS)
    -> 8 ot_dp_rrelay -> rgate (run=1) / rsync landing: KVRST_PASS min 20 (rgate) / 22 (landing) locked edges in reset over power-on, 8 mid-run por_n pulses
    0.05..1.94 ns at 8 phases, lock loss inside reset. MUT1 (STABLE 4: 8 edges) and MUT2 (lockq bypass: 0..3 edges) FATAL.
    main lec.reset_contract_gate: kv3_astk used 16; unlisted module refused; request 24 refused. Sink coverage = by reading bind_reset/por_gate (not die-wide sim).

(1) PLAN EVENT event26a (no RTL change): mk_event26a.py sets clock.core_taps early -> internal on 45 types of Codex event26/plan.json (bind26b strict PASS);
    plan_e26a_event.json lists the types + source sha256. Cores keep the partition-internal common latency 250 TT / 202.5 FF (12.3).
    die_trial kit (kit.sh = DIE-KV-21 tree c recipe): 1920 taps / 15296 cells (89 BUFx24 phy tap pads); ctree.v byte-identical to tree c (DIE-KV-25 kit_repc);
    tree.json differs only in 32 repeater site xy (13.56 um slides). ot_clk: tools/clk/configs/kv_e26a.yaml replay IDENTICAL, stage_check PASS (otclk_replay_e26a.log).
(2) DIE GRT0 incl clock (combo GRT M4-M7 signal / M8-M9 clock, 50 it): TT and FF overflow 0, usage 2.37 % [CHECKED-own]. Duty 0 taps outside 45-55, MPW est fail 0.
    In-region spread (128 regions): worst TT 69.8 (hub_Wi) / FF 56.6, 0 regions > 150 -> PASS [CHECKED-own]. (event26 early-tap tree was 414.5.)
(3) DIE STA main die_sta_related, 4 signed views e1/e2/e5/e6 @3e7fccd216, CA = Codex native6/native_bind.json, OCV table + shared droop, HB4 info:
    spice_edge: CA lo TT 104.8 / FF 109.6, fail 0/3595, slot_read 0, guard 0; intra TT setup +315.78; FF hold -112.29 all / real-view -58.23 (4822 pairs) /
      both-real +38.27; kit contract +6.64 PASS (window 80, need 73.36 pv_S_1); seam FF -101.20, kit contract +18.07 PASS.
    spice_cell: CA lo TT 58.6 (90 <100, all pc->pc / pc->hroot) / FF 101.6; intra kit contract -6.69 (pv_S_1); seam kit contract +4.07.
    COORD 10-29 clock-number rule (spice_cell only on paths with BUF cells): in tree c the only BUF cells are the 89 BUFx24 pads on the 32 phy taps.
    Mixed (ca_mixed_e26a.txt): CA worst lo TT 104.8 / FF 109.6, 0 < 100 -> PASS; phy crossings on spice_cell worst 273.5 TT. [STA numbers UNCHECKED: no NUMBER-CHECK]
    START-SKEW: FAIL-CLOSED 1685/1687 "no taps": native6 START stages are clocked from tree nodes (st:h...@t_part__clk), not from die-tree taps, so the
    main CA start-skew check cannot time them. Needs the Codex START timing source (c33d4aedd/57a112ef0/875f89d81, READY root review, NOT on main).
(4) FF HOLD ROOT CAUSE (real-view -58.23): worst pair hg_WS_7 launch e6 real view (clk_t8) -> capture "budget" glue (clk_t3), tap damage 64.55.
    The e6 view has min clock tree path 173.1 ps vs the declared glue latency 202.5 FF: a real core launches ~29 ps earlier than the budget model
    assumes, plus 64.55 tap damage. The same pair with a real capture core (e6->e1) is +38.27. So: unbuilt partition glue, not the die tree.
    Fix variants (NOT BUILT; both need hg partition logic, owned KV-KITS): V1 hg partition kits close hold in-kit against the kit contract (-early 80
    window, +6.64 edge) with the real e1/e6 views; V2 die-level HB4 hold buffers on the glue capture paths (die_sta HB4 model: real-view FF 0.0 after,
    TT setup after +315.78, UNCHECKED plan delay model). DEFAULT V1 (partition-local, no die-top cells).
(5) START native6 provider (estimate only, no placement run): Codex native8_geometry stage rects (after the packed-clock node moves) give
    stage->stage reach max 367.47 um (32 > 350, 2 > 355; 1441 edges, 87 partition-fed). With measured cell-to-stage 8.37 um: max ~384 <= 405;
    with the 25 um full-cell reserve: 2 edges 417.5 > 405. Stage rects are 0.27-um FF slivers, not legal full-cell placement -> physical reach UNVERIFIED.
    Actual all-cell provider placement owner = QC macroPG generic packer (Codex packet). Nearest-tap fallback not started (native6 placement has not failed).
(6) q3: SRAM0 move dropped (COORD 10-29); q3 trial2 -> DRT/sign-off under KV-KITS-20.
=> KV FREEZE GATE: NOT PASS. PASS: strict bind26b, GRT0 TT/FF incl clock, spread, duty, CA lo (mixed rule). FAIL/OPEN: real-view FF hold -58.23
   (partition glue), START skew fail-closed (native6 virtual stages), native6 provider body not placed. Plan clock form for freeze = tree c on event26a.
