DIE-KV-13 2026-10-28 11:02 PDT dcal write-group rule (COORD TOK-ALL-13r, coord 1d570d046).
Problem: dcal bcfg write port: rx_we/tx_we (L1433/L1434) landed 1 edge before addr/data (L1431/L1432): main table 55 vs 56,
DIE-KV-8 RT20 table 82 vs 83 -> STALE boot-config write, native calendar FAIL (Codex codex/qk-native-1351 sim).
Cause: R8 keeps the as-built relative offset of a bus; the historical as-built reference had WE at 5 stages vs addr/data 6,
but the producer (boot dispatch DSTG1) emits the four on ONE source edge (Codex source_event_contract.json, 0/0/0/0).
Rule (one generator rule, die-local, no per-lane hand pad): physical/die_plan/qwen_kvsys/r8/r8_write_groups.py
  prep : every member of a declared write group (r8/write_groups.json: en + addr + data of one sink write port) gets ONE
         as-built reference = the latest stage in the group (its source event); the raw value is kept as
         asbuilt_lane_stages (member ids kept); generic r8.py pads then lands the group on one edge.
  check: every write group lands on ONE edge in an R8 landing table (fails closed: missing / partial / unequal).
  Wired into run_v39f.sh (prep after r8_rebase, check after the table) and the KV-13 R8 regen r8_13.sh.
Results [CHECKED, own runs]:
  main r8 table: r8.py pads on main r8/bus_groups.json reproduces the main table 5537/5537; with prep exactly 2 members
    change: bcfg_rx_we / bcfg_tx_we pad 2 -> 3, landed 55 -> 56 (= addr/data 56); pad_flops 34397 -> 34399 (+2 FF).
    r8.py check PASS (0 unequal, 0 inversions) on the prepped groups + new table; write-group check: old FAIL, new PASS.
    check.py G0 on the plan: the same 20 ERRORs before and after (cuts 13, core_pin_form 7; pre-existing, none R8).
  DIE-KV-8 RT20 table (bind_s2, latest strict-bind R8): r8_13.sh regen -> 5655/5655 ids, exactly 2 diffs: WE 82 -> 83
    (pad 3); r8 check --strap-pads RC 0; write-group check RC 0 -> qwen_kvsys_r8_landing_rt20_wg.json.
  test_r8_write_groups.py 3/3 PASS (generic R8 lands WE early and check catches it; prep lands one edge with ids kept;
    a partial group fails closed).
Cost: +2 FF, +1 boot strobe edge, 0 layer/token cycles (boot-only strobe lanes; no token-path lane changes).
