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

## 2. Proof (one kit): t39 on plan e + R8 lever + TAPHOLD rows = plan f (th_delta.py --slots)
- Tools: main 255a1cf9cd3b (my push 03:46): ft_slots[].hold_hb4 = HOLDFORM-1 for ft slots (N kept HB4 per bit in front of station 0; gen_rtl + bind + kit dont_touch count + schema + tests). buses[].hold_hb4 existed (in-buses only). Lane clone epyc7 L/clone. NOTE: `bind.py verify` (transport proof) fails on any hold_hb4 plan: it parses the cells with SYNTHESIS and has no HB4xp67 cell (pre-existing, also the bus form); gates here use elab + bind + LATCHECK, as R10's.
- th_delta.py (plan e a0a696072693 -> f): r8_t39_delta.py --ver unchanged (vsw R0, sw / swr re-site, relay site, VER bank) + hold_hb4 3 on leafdn_i0 (bus) and ft2 / ft3 / ft4 (slots) = all 2,578 port ends (3 x ~38 ps FF vs ws -97) + clock.ft_hop_lockup {types [t39], hops {t39: {ft2: [2], ft3: [3]}}} + type clock.pregrt_hold_guard_ps 100. tap_reset_affinity NOT used (walks 4 buffer stages; reset bit has 11; no CK skew at GRT RC).
- Tree: epyc7 L/src_f = ot-tree-fork of the local J7 event tree kw45/src_s81_pin_3c913dbdfb23_d8j7_1117_work (54 GB, nlink 1); th_bind.sh swaps in tools of rt $TH_RT (J7 tools kept as tools.j7), moves the J7 bind out to native_bind/out.j7 and binds into a fresh native_bind/out; plan e staged as L/plan_e.json, regrid netlist 6017c662 as L/die_netlist.base.v (VER edit LF_CS_VER_D on u_s_4S applied by the script).
- GATE F GREEN 07:17 (plan f 0e99c3d82aa6, tree src_f, rt 255a1cf9cd3b): ELAB 0, strict BIND 0, LATCHECK PASS 873/873 with lane deltas vs gate e = {} (identical), G0 0 new errors vs gate e (7 = 7), PLAN-GATE-PRE PASS findings 0. Logs epyc7 L/gate_f/, client log intel2 L/gate_f.otrun.log.
- GATE G GREEN 07:20 (A/B: plan g f48cee737776 = plan f with EVERY ft station hop latched, th_delta2.py --slots --allhops; tree src_g; th_bind2.sh with TH_TREE=src_g TH_GATE=gate_g TH_DELTA_ARGS=--allhops): same verdicts. Logs epyc7 L/gate_g/.
- KITS RUNNING (epyc7, goal finish = sign-off + routed LEC, wave env + OT_GRT_CONG_ITERS=50 only, no port-hold keys):
  - k1 (plan f): chain intel2 L/spec/k1.chain.log, spec L/spec/k1/spec.json, run-item log L/spec/k1/run_item.log; kit epyc7 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/18a2688b741/private/FABLE-FIX-S81-LEAF-TAPHOLD/ot_s81sl_leaf__t39_1122071812/gen/ot_s81sl_leaf__t39
  - k2 (plan g, all hops): intel2 L/spec/k2.chain.log, L/spec/k2/; kit .../ot_s81sl_leaf__t39_1122072106/gen/ot_s81sl_leaf__t39
  - chains are nohup on intel2 (th_chain.sh k1 / th_chain2.sh k2 with TH_TREE=src_g); if they die, re-run `python3 -I /srv/opentallas-scratch2/claude/rt/255a1cf9cd3b/tools/autopilot/kit_wave.py run-item L/spec/<k>/spec.json`.
  - Read at CTS: run_route.log OT_CTS_POST_TIMING, pregrt_ff_hold.log class lines (expect port_in ~2 = arst_n + cland_tstart_in), OT_HOLDPAD (7722 cells), OT_RELAY_SITES (25 seats now matched?), tt_setup_keep.log. At GRT: th_probe.sh / th_tt2.sh on the final 5_1_grt.odb only.
- Tools also on main: 71c5a1ca59d3 (kit pad-count hook reads the kit RTL; needed for family rows where a bound lane is narrower than its plan bus / slot). k1 / k2 gen on 255a1cf9cd3b (plan-width range; t39 fits exactly: 7722 in 7722..7734).
- station_rule.py rows on plan f predicts 0 cross-tap ft hops for t39 (plan tap grid != as-built tap assignment): family hop rows need a measured CTS DB per type, or the type-level form (every hop).

## 3. Family rows (not handed yet; wait for the proof read)
- th_family.py rows PLAN OUT / apply PLAN ROWS OUT (intel2 L): plan-derived, per leaf type: hold_hb4 3 on every plain (not in clock.landing_contract.bands) in-bus and ft slot + pregrt_hold_guard_ps 100. On plan e: 80 types, 158,455 pad bits, 475k cells, max 14,085 cells in one type (t28). Needs J8 tools >= 255a1cf9cd3b.
- R8 kit note: OT_RELAY_SITES placed 0 of 25 seats (keys unmatched; RELAY-NORM fix came later), so its reset relays and the crr_vsw seat were unseated; the new kit (tools >= RELAY-NORM) will seat them. Plan e also turns on OT_S81SL_VP_CFX for t39 (cf written from yrow_d[0], not from the dodd mux): expect the dodd class to shrink to dodd -> yrow_d[0].

## 4. Open
- dodd_q -> yrow_d[0] and the lpad q[594] reset bit (TT) have no row; decide after the new kit's CTS / GRT read (seat via relay_sites key = flop name below u_bound without the cell suffix; relay_split for a per-cluster copy).
- Internal core-output cross-tap ends (455 under margin, 142 violating): only the pre-GRT guard so far; structural cause = FF tap-mean spread 83 ps (glue taps padded at TT run late at FF vs core-internal trees) + core tap window.
- The two LOCKUP-STATION jobs were cancelled by S81-DIE-R5 02:37 (setup < -300, GRT not converging; its note: lockup forms crowd the leaf clock trees). FAIL-CLASS 958ddd525b is ACKed here (03:05).
