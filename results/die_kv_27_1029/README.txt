DIE-KV-27 2026-10-29 (KV die owner; successor DIE-KV-26 ccbdfd831a; plan event26a FROZEN 12.17(1)). Tools = main e256f6799c.
Runs intel1:/srv/opentallas-scratch2/claude/die-kv-27-1029 (inputs read-only: die-kv-26-1029 kit_e26a/out_e26a_*/clk_e26a, Codex codex-kv-25-1029 native6/native8_geometry/event26).

(1) START TIMING SOURCE: Codex c33d4aedd/57a112ef0/875f89d81 (+f4e8d6ba1) are ALREADY ON MAIN as 9c98002e2/56ae35898/c901fabaa/71f845628
    (in 2b90210bd) -> no pick needed. Real cause of DIE-KV-26 START-skew fail-closed 1685/1687 'no taps': the DIE-KV-26 proof used the old
    land-kv-1027 copy of trial_tap_arrivals.py (collapsed geometric paths, 8441 nodes, max depth 52) while the native6 bind keys stages by
    physical cell paths (15424 nodes, depth 176). MAIN trial_tap_arrivals.py on the same arrivals -> 15424 node paths = Codex proof key set
    exactly; all 3126 START stage endpoints resolve (proof.sh). Next fail-closed reason was 1445 fall-edge stages without measured node fall
    arrivals -> OT_EDGES v1 readout (Codex codex-clock-components-1028 read_*.tcl, LEFs from the e26a combo.tcl) on the e26a GRT SDF (edges_run.sh):
    T rows equal the DIE-KV-26 arrivals (max |d| 0.015 ps), 15296 M + 1920 F rows -> proofE (fall on all 1920 taps / 15424 nodes).
(2) DIE STA main die_sta_related on proofE (gate.sh = DIE-KV-26 recipe, 4 signed views, native6 bind, plan_e26a) [STA UNCHECKED, NUMBER-CHECK REQ]:
    spice_edge: START-skew 0/1687 FAIL TT and FF (worst skew hi 77.7 TT / 54.7 FF vs limit 92.4; stage pins = virtual_tap MODEL: measured node
      arrival + median tap leg, flops not built); CA lo TT 104.8 / FF 109.6, 0/3595 <100 -> COUNT-ALIGN TT/FF PASS.
      intra TT +314.30, FF hold all -114.93, real-view -50.98 (3083 neg pairs; worst still hg_WS_7 e6 real launch -> budget glue capture,
      damage 64.61), both-real +37.97, kit contract +6.64 PASS; seam FF -103.65, kit contract +18.19 PASS.
    spice_cell: START-skew 0/1687; CA lo TT 58.6 (90 <100 = pc->pc inverter-only paths, spice_edge applies per COORD clock rule) / FF 101.6.
    Under the COORD clock-number rule (spice_edge on inverter-only incl. all START stages, spice_cell only on the 32 phy BUFx24-pad crossings,
    DIE-KV-26 ca_mixed): CA/START PASS.
(3) native6 PROVIDER REACH (main start_provider_plan.py, conservative corner-to-corner on legal emitted FF row rects of Codex
    native8_geometry/source_check_stages.json, 1528 stages/1772 edges, boundary pins from event26/plan_native_pins.json):
    0 errors, max hop 367.47 um <= 405, max clock access 9.99 um (provider_reach_native_pins.json). physical_qualified=false: 12141 comb
    relay cells are not placed (all-cell pack = QC macroPG packer). With the event26a plan pins (old cland_tstart pins) 331 boundary
    edges 582..3213 um -> the native pin sites are required in the frozen plan (event26a lacks them; event26/plan_native_pins.json has them).
(4) ASK-C PLAN DELTA event27 (COORD 06:14 YES, gate-failure fix KV-007/KV-008; mk_event27.py, event27/):
    qkd_kvs_pc R0+fMX pins r27: pc__land_es[287:0] S face -> W face y 288..343 directly below the chain block (fi/fo/ki/ko/x__est
      unchanged at 343.75..360.6); i_prev/o_next/o_prev re-spread 0.192 um (4 M4 tracks) y 2.5..267; W 1736 pins (4.8/um). Chain c[F_V]
      (6.5,357) -> land_es now <= ~75 um (was >= 608). 23 hard_cores repointed (19 R0 + 3 fMX file users + ahub). h_head_p unchanged.
      Partition side: land_es -> hsl soft logic now leaves at the W face (kvpc W faces face each other, 69 um channel): pc partition kit
      must re-check that hop (<=405).
    qkd_ahub pins r27: ck[3] S-W (150,50), ck[4] S-E (450,50), ck[5] E-S (580,110), ck[6] E-N (580,330) interior M5 (kit may slide <=20 um
      off macros); hub_C clock taps ahub.ck[3..6] at hub_C (366,1095.44)/(666,1095.44)/(796,1155.44)/(796,1375.44), 250 TT/202.5 FF.
      RTL: qkd_ahub ck[2:0] -> ck[6:0], same clock; sinks S band x<300 -> ck[3], x>=300 -> ck[4], E column y<220 -> ck[5], else ck[6],
      centre stays ck[0]; ck[1]/ck[2] zh clocks unchanged -> KV-KITS-21. Die tree c unchanged (partition-internal leaves).
    Pin render event27/pins_e27.png VIEWED. Strict bind of event27 waits the ahub RTL port widening (kvs_pc part is pins-only).
(5) HOLD: V1 (hg kits close hold in-kit vs 80 ps, real e1/e6 views) = KV-KITS-21 (waits FLOW-HOLD-1). V2 estimate (die_sta HB4 plan model,
    UNCHECKED, BOUND = every hard-core data pin): hg+hgi partitions 2.78M HB4 = 0.284 mm2 (die-wide all 6.33M / 0.646 mm2); hg_WS_7 alone
    69.8k. The cells sit inside hg/hgi partitions (no die-top path) -> V2 can only be built as an hg kit variant (pre-CTS HB4 k=3 on e6 output
    -> glue capture nets), not at die level; run in parallel with V1 inside KV-KITS-21 if COORD wants both.
=> KV freeze gate on event26a: PASS = bind26b, GRT0 TT/FF incl clock, spread 69.8, duty, CA (mixed rule), START-skew 0/1687 (MODEL stage pins).
   OPEN = real-view FF hold -50.98 (unbuilt hg glue; V1/V2 in kits), seam FF -103.65 conservative (kit contract PASS), START provider comb
   cells unplaced, KV kit sign-offs.
