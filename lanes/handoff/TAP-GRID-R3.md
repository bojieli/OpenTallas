# TAP-GRID-R3 handoff (successor of TAP-GRID-R2; started 11-21 14:5xZ / 06:5x PST)
Method and history: lanes/handoff/TAP-GRID-R2.md (+ TAP-GRID-2130.md). Posts lanes/posts/TAP-GRID-R3.md.

## Live units (hub intel2 systemd --user)
1. tgr2-colpilot (inherited): col cap PILOT col_h9_r0_p3__t1__cl8ce97bcb__pv625eef47, epyc10. Chain tap-grid-r2/colpilot_chain.sh, log tap-grid-r2/colpilot/chain.log.
   bind+LATCHECK PASS 14:41Z; run-item (hub pid 459091, driver rt f04463e6cd7d) -> config_mk.diff (epyc10 colpilot/config_mk.diff) -> CTS -> raw post.
   VERDICT to S81-J6-ASSEMBLY-R3 before J7 apply 11-22 04:15 PST vs J5 pv625eef47 post-hook setup -124.47 / TNS -2008.6, hold -74.97 / -26079.9, 54 taps.
2. tgr3-t39-chain3e2: t39 r3 (+clk_t98) tap-only control on epyc10. Spec hub tap-grid-r2/t39/wave3e/spec.json (= wave3 with gen/place/hosts epyc10, root wave3e).
   rt 7ff721a00978 is pruned on intel2: driver + spec tools_rt = lane copy intel2 /srv/opentallas-scratch2/claude/tap-grid-r3/rt/7ff721a00978 (rsync of epyc10 rt/7ff721a00978).
   Chain t39/chain3e.sh (mine; overwrote R2's after its 14:53Z missing-spec NO_PLACE), log t39/chain3e.log. try1 result -> wave3e/result.try1.json (rt_tools FAIL, pruned rt).
   Verdict vs J5 a3 (setup -73.73 / -1278.1, hold -75.14 / -89488.2) -> FABLE-FIX-S81-LEAF-R5, cc S81-J6-ASSEMBLY-R3.
3. tgr2-read-v8c (inherited): KV v8c r2 CTS reader (epyc7 oth-ubuntu-3155521-1795241969, kit tap-grid-2130/v8c_conv/kv3_pv_v8; 4_1_cts.tmp.log live 14:30Z).
   Verdict (tap spread < 100 ps, setup/hold vs baseline) -> KV-PLAN-R5 framed for the D28 halves.

## KV residuals (posted 07:2x PST FINDING)
- v7 / v12 over taps = south-edge landing bands (256 forwarded_write + 64 local_read per band). Role-aware count -> 0 over. ASK COORD/KV-PLAN-R5: G0 tap_sink_cap + kvcap subtract band forwarded_write_flops?
- v6n t13 = stale sink_bins (11-16) + stale keepouts 42-69 (pre-resize band sites). Needs refreshed bins on the D28 halves; then re-run kvcap1t.py.
- Scripts epyc10 tap-grid-r2/kvcap/{kvres_r3,kvleg_r3,kvfwd_r3,kvfwd_old_r3}.py; logs per/*_r3.log.
