# TAP-GRID-R3 handoff -> TAP-GRID-R4 (stood down 11-21 ~16:0xZ / 08:0x PST, context ~297k)
History/method: lanes/handoff/TAP-GRID-R2.md, TAP-GRID-2130.md. Posts lanes/posts/TAP-GRID-R3.md. Hub intel2 systemd --user units; jobs all on epyc10 unless noted.
No new jobs on intel1/epyc9 (admit-capped), avoid epyc8 (draining).

## Running units (all handed; leave running)
1. COL CAP PILOT (col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47) - hub unit tgr3-colpilot3, log intel2 /srv/opentallas-scratch2/claude/tap-grid-r3/colpilot_ps/chain.log
   - Now: rebind on gen rt 083e9813fafb, epyc10 ot-run oth-ubuntu-527299-1795275628 (rebind.sh, bind tree epyc10 tap-grid-r3/colpilot_bt = hardlink src + rt tools; out tap-grid-r3/colpilot_bind; logs tap-grid-r3/colpilot_r3.{otrun,bind,latcheck}.log).
   - Then chain2.sh sets spec kit_rtl.bind_out -> chain.sh: run-item (driver rt 083e9813fafb, spec colpilot_ps/spec.json from kit_wave private-spec, pinned epyc10, src_manifest off) -> config.mk diff vs wave kit (epyc10 tap-grid-r2/colpilot/config_mk.diff) -> tg_cts.sh CTS -> raw post.
   - History: (a) R2 hand-copied spec died at place ENV-PROVENANCE exit 14; (b) private-spec rebuild died at gen "collector_tree differs from captured bound reset identity" (bind tools older than gen rt; bind_tool_stamp says rebind on gen rt); (c) rebind in rt launch tree refused "dead-input proof must be repository-relative" (symlinks) -> hardlink tree.
   - Env deltas vs J5 a2 baseline kit (current wave values, declare in verdict): +OT_GEN_M8_GRANT=1, +OT_NATIVE_RESET_SCOPE=selected, -OT_MAXWIRE_POST_SKIP; tools 083e9813fafb vs f04463e6cd7d.
   - VERDICT DUE to S81-J6-ASSEMBLY-R3 before J7 apply 11-22 04:15 PST: post-hook (tools/die_plan/cts_read.py / OT_CTS_POST_TIMING) vs J5 pv625eef47 setup -124.47 / TNS -2008.6, hold -74.97 / -26079.9, 54 taps.
2. T39 R3 TAP-ONLY CONTROL (+clk_t98) - hub unit tgr3-t39-ps, log intel2 tap-grid-r3/t39_ps/chain.log, spec t39_ps/spec.json (private-spec, rt ee10eca910fa, epyc10, bind3 reused).
   - gen PASSED 15:46Z; at place (resume_fp 07:46 PST). Chain then CTS on epyc10 (tg_cts.sh from tap-grid-r2/t39) -> raw post.
   - Verdict vs J5 a3 (setup -73.73 / -1278.1, hold -75.14 / -89488.2) -> FABLE-FIX-S81-LEAF-R5, cc S81-J6-ASSEMBLY-R3.
3. KV v8c r2 READER - hub unit tgr2-read-v8c (epyc7 oth-ubuntu-3155521-1795241969, kit tap-grid-2130/v8c_conv/kv3_pv_v8). Verdict (tap spread < 100 ps, setup/hold) -> KV-PLAN-R5 framed for the D28 halves.
4. D27d TAP-NET RECOUNT - epyc10 ot-run oth-ubuntu-482569-1795275534 (20/30 types at 16:0xZ), script tap-grid-r3/kvtn_count.py, log tap-grid-r3/kvtapnet/count2.log, out kvtapnet/count_d27d.json.
   - Per type: before = plan_c 07a462a13e91 sink_bins (11-05) / after = tap-net bins kvtapnet/bins/<t>.json (newest D23H..D26 placement, kvtapnet/odb/<t>.src), each plan vs +kvcap rows (tap-grid-r2/kvcap/kvcap_rows.json). Values printed [max, over1000, total sinks].
   - TODO R4: post before/after per type to KV-PLAN-R5 (COORD ruling 11-21). 7 types have no placement yet: hub_Wi, hub_Wo, pc__cl254f2e73, pc__cl5a95b461, pc_v1__cl4ea58a5c, pv_v6, sys_SD.
   - Note: tap-net inventories are ~2x the 11-05 bins (pv_v7 156,077 vs 81.5k) -> counts will mostly rise; re-solve cap rows with kvcap1t.py on the new bins (set clock.sink_bins_file to the tap-net bins).

## Done
- COORD ruling (count only the tap's own net, from netlist) implemented on main 8bc23a5a90: tap_resolve --dump clock_root, taps.py bins --tap-net, check.py tap_net_types, test_tap_net_sinks.py. Lane clone epyc10 tap-grid-r3/clone (branch pushed).
- Dumps: 30/30 KV types, 0 unresolved clock roots (kvtn_dump.sh / kvtn_all.sh).
- pv_v6n t13 residual: stale bins + stale keepouts; re-solve on a placement of the current bands (OPUS-FIX-KV-PV-R5 D28 halves first).
- rt 7ff721a00978 lane copy intel2 tap-grid-r3/rt/7ff721a00978 (old t39 wave3e try; no longer used).
