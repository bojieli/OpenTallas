# FABLE-FIX-S81-LEAF-TAPHOLD handoff (Fable fix lane, started 2026-11-22 02:4x PST; pairs with OPUS-FIX-S81-LEAF-R10; rows to R10 + S81-J6-ASSEMBLY-R5, due 14:00, J8 cut 16:00)

NOTHING IS SIGNED. Brief: intel2 ~/coord/lanes/FABLE-CLOSURE-0235.md section 3. Lane dir (both hosts): /srv/opentallas-scratch2/claude/fable-fix-s81-leaf-taphold (L). Local scratch copies of every script: session scratchpad taphold/.

## 1. Measured cause (posted 03:2x, hub 2dbc51597d): the lpad -> bin tap-skew inference is NOT confirmed
DB: R8 proof kit (epyc7 kw43-wave-1109n/.../private/FABLE-FIX-S81-LEAF-R8/ot_s81sl_leaf__t39_1121220439/gen/ot_s81sl_leaf__t39) 5_1_grt.prerepair.odb, FF, GRT RC, kit hold frame (postcts_gate frame + hold_gate overlay). No final 5_1_grt.odb exists (the kit is still in its GRT hold repair).
- 4,169 ends under +30: port_in 2,578 (all < 0, ws -97.1 at bound vclk 364.5, -75.7 at measured 385.95), cross_tap 1,454 (152 < 0, ws -56.1), same_tap 107 (1 < 0), port_out 30 (0).
- port_in: launch = input PORT (vclk, in_min -40), no launch flop. ft4_i 1,105 / leafdn_i0 596 / ft3_i 598 / ft2_i 277. Capture CK p10/p50/p90 382/393/401. slack + CK = 314.7: fixed by the seam contract, not tap skew. Sign-off: port-only hold = PASS + parent obligation (signoff.evaluate port_only_hold).
- internal by kind (under +30 / < 0): ft_hop 751 / 6 (ft3 3->4 540, ft2 2->3 204; launch tap t29 FF 333, capture t23 407), core_out->glue 241 / 118, core_out->cst 214 / 24, cst->cst 234 / 5, other 121 / 0. Internal ends under margin: <0 153, <10 394, <20 905, <30 1,561.
- lpad_leafdn_i0 -> captures: 6 ends, 0 violating.
- Stall cause: R8 A/B key OT_GRT_PORT_HOLD_PORTS=1 put the 2,578 port ends in the GRT ECO repair (1.8 buffers per 25 s iteration; 201 buffers / 2,573 s per chunk).
- FF tap table (probe1b.otrun.log on intel2 L): tap mean 333 (t29) .. 416 (t6), spread 83 ps; in-tap up to 100 ps (t20 332-434); t6 5,701 sinks, t41 4,210, t7 1,393 (cap 1,000).
- TT same DB: wns -116.6, 227 viol, 66 under -42: dodd_q -> vp_cf / yrow_d / src 51 (-116.6; launch CK 443, capture 363 at CTS), u_rrl_303 -> cland_fstart_ft4_o 1 (-111; plan e raw-reset class), lpad q[594] reset bit -> vp u_rr / cst_vni 14 (-77.7; 11 buffer stages, ~700 um).
- Files: epyc7 L/probe1/th_ends_bound.tsv, th_tt_ends.tsv; intel2 L/probe1*.otrun.log. Probes: th_probe.tcl (+ TH_SKIP_CENSUS=1 = tap table only), th_tt.tcl; run through ot-run --stage KIT (kit mounted ro). PathEnd objects die after any pin arrival query: read all path ends first.

## 2. Proof (one kit): t39 on plan e + R8 lever + TAPHOLD rows = plan f 74606bec6930
- th_delta.py (plan e a0a696072693 -> f): r8_t39_delta.py --ver unchanged (vsw R0, sw / swr re-site, relay site, VER bank) + clock.ft_hop_lockup {types [t39], hops {t39: {ft2: [2], ft3: [3]}}} (launch-side latch on the two measured cross-tap station hops) + type clock.tap_reset_affinity true + clock.pregrt_hold_guard_ps 75. Schema-valid on rt c54215ce9245.
- Tree: epyc7 L/src_f = ot-tree-fork of intel2 fable-fix-s81-leaf-r9/g68b_src (gate-e tree, J7 + plan e); tools replaced by rt c54215ce9245 (>= floor 6d2e187f0d; J7 tools kept as tools.j7).
- Gate f: th_bind.sh (elab + strict bind + LATCHECK + G0 + PRE; out L/bind_f, logs L/gate_f; markers THF_* / TH_GATE_F_DONE). Then kit_wave private-spec (--tree src_f --bind-out bind_f --rt c54215ce9245, wave env, NO port-hold A/B keys) + run-item + run_kit.sh route.
- station_rule.py rows on plan f predicts 0 cross-tap ft hops for t39 (plan tap grid != as-built tap assignment): family hop rows need a measured CTS DB per type, or the type-level form (every hop).

## 3. Open
- Family rows (74 types) not written. Port-in hold: structural options = hold_hb4 pad rows (bus form exists; ft slots need a tools change in bind.py / gen_rtl.py) or early capture tap for the input rank + latch on its outgoing hop (no early-tap key exists). Not decided.
- dodd_q fanout and the lpad q[594] reset bit (TT) have no row yet; tap_reset_affinity walks only 4 buffer stages, check OT_TAP_RESET lines in the new kit.
- The two LOCKUP-STATION jobs (pids 278006, 338136) ended before 02:50 (not by me).
