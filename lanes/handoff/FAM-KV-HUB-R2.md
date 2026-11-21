# FAM-KV-HUB-R2 handoff (Opus 5.5). CURRENT 2026-11-21 05:3x PST
STOOD DOWN -> FABLE-FIX-KV-HUB (COORD 05:3x: ~310k context; hroot -753 and hub family repeat-failing). Jobs left running.
Family: kv3_hub_{C,Ei,Eo,Wi,Wo}, kv3_hroot, kv3_sys_c, kv3_sys_SD_v1. D28 rows go to KV-PLAN-R5 (not R4). Lever 8 of FABLE-CLOSURE-STRATEGY (hroot rows + hgi zero-capacity faces).
Work dir: epyc8 /srv/opentallas-scratch2/claude/fam-kv-hub-r2 (tree/, ana/, scripts below). Client logs: intel2 ~/tmp/famkvhubr2/.

## Diagnosis (measured, D25d attempt_5: epyc2 kw43-wave-1109/runs/qwen_kvsys/kit-wave/qwen_kvsys/KV-D25d/items/kv3_hroot/attempt_5)
- TT went from +2.11 post-CTS (placement RC) to -753.66 post-GRT (GRT max 114 pct). 5_global_route.rpt: clk setup skew -532 (fan_c target latency 781 ps on clk_t9 behind a clkleafrepg chain); worst max kc rd_bin[0] -> ko[6] -475 (336 ps on one wire); cland kvs_ctl ring sd_c -> dsel -429; worst min u_bin kvs_ctl q[927] -> fan_c[143] -248 (skew).
- Hops (D25d CTS geometry fable-visual-0030/out/kv_hroot/geom.tsv): landing dsel -> u_bin 738 (kvpc) / 653 (slg) / 556 (kvs_ctl); esh u_st.d -> bout_o_pc 437; fan -> bout_chN 411; kc.ko -> bout_ko 434; all logic packed in the E strip. The relay chains had their stages bunched (bin next to r_c/g_c, then 380-um hops).

## Private delta, variant A (0 added cycles), on D27d (D27c minus pv rows, plan 07a462a13e91) -> plan 3f4e0024a8d1
- ana/resite_delta.json (resite2.py) + h1_hroot_rows.py: h1 per-bit equal-hop relay_sites dsel -> bin -> stage -> stage -> bout: kvpc max hop 738 -> 390, kvs fan 556 -> 273, slg 653 -> 321, esh 437 -> 317 (784 new u_esh.h_c keys; u_st.d spread W over x 1600-1900); h2 o_kvs_hroot_Q_o_ctl station -> (1590, 710); h3 clock.ring_hold.sender_ps_types.kv3_hroot = -50.
- Same rows posted for D28 (e7cb4d9b, redirected to KV-PLAN-R5 at e49d7c0a): lanes/handoff/FAM-KV-HUB-R2-hroot-relay-d28.json + FAM-KV-HUB-R2-h1_hroot_rows.py.
- NOT done: the TAP-GRID-R2 west-tap drop (epyc8 tap-grid-r2/hroot/d28-hroot-pending.json renames the tap ports and needs collector/raw START regen) and +1 station on kvpc/slg to get under 300 um (variant B).
- Tools: rt a5603de7c56b has no hard_boot_prefix_um in its schema; the D27 plan needs kv-plan-r2/d27b/typed_d26_contracts.patch. So the private rt = rtp_a5603de7c56b/ (rt copy + that patch, clean apply), and launch tree = launch_a5603p. Bind and gen BOTH use it. The first unpatched G0 failed on SCHEMA, and its bind was cancelled (rc 143).

## Live units (mine, epyc8; leave them running)
- G0 gate: oth-ubuntu-645507-1795266158 (intel2 client pid 1581880) -> g0gate_a2/gate.out (RC_PRECHECK 0, RC_PRE 0 so far).
- strict bind + LATCHECK: oth-ubuntu-645366-1795266158 (intel2 client pid 1581881) -> bindgate_a2/gate.out (about 2 h).
- Re-arm: timeout 14400 ssh -o ControlPath=none intel2 'export OT_LANE=FABLE-FIX-KV-HUB; ot-wait 1581881 --poll 120'  (same for 1581880), or ot-wait <unit>.

## Next steps (open)
1. When bindgate_a2 shows RC_BIND 0 / BIND_ERRORS 0 / RC_LATCHECK 0 / ALL_DONE: run ot-run --hosts epyc8 --mem 24 --dir W -- bash W/gen_hroot.sh a1 (kit-rtl + gen phys on launch_a5603p, with the BIND-GEN-TOOLSKEW stamp check). Then diff proof/a1/gen/kv3_hroot/config.mk against the D25d attempt_5 config.mk, and run proof/a1/gen/run_kit.sh proof/a1/gen/kv3_hroot route 72 8 through ot-run on epyc7/8/10. Read the post-hook TT (4_cts_post_hook.rpt, tt_setup_measure_grt.log) and the GRT congestion. Watch clk_t9 latency and the kc rd_bin -> ko path.
2. A sign-off build must come from a src_manifest tree, so if the proof passes, KV-PLAN-R5 carries the rows in D28.
3. hgi zero-capacity faces (lever 8): ana/station_core_hg.txt (station_core.py on plan 3f4e0024a8d1, ^kv3_hg). Every hg/hgi type has 476-544 relay_sites inside head*_e2/e4 cores: the kp-station rows u_head{N}_g_t_{8,9,12,13}_u_kst{0,1}.{kp_o[],kpv_o,gf_o} at the core centre column x 186 / 808 (centroid internal_stations core:u_headN_e4/e6.kp_o -> e0.u_kt). hgi_v3 also has ft slots inside cores. Proposed row: move those sites into the streets (y 233-337 / 553-683 / 899-1002, or x streets 294-389 / 605-700) with a margin of at least one gcell, keeping hops <= 300 (the core pins come from pins/kv3_head_eighth_e6_pins_*.json), and put a placement blockage over the core/landing footprint plus one gcell. Proof: hgi_v1 to GRT iteration 10. Coordinate with FABLE-FIX-KV-HGI-R2 / OPUS-FIX-KV-HGI-R3.

## Siblings (wave D25e3 kits, not mine; ot-wait waiters on the intel2 client pids)
- hub_Ei attempt_4 route epyc10 (client 55902): post-hook setup +21.7, in GRT. Its -433 is the port_in seam class (COORD/FABLE-CLOSURE-0600): spend no builds on it.
- hub_Wo attempt_9 route epyc9 (client 2433217): CTS. hub_Eo attempt_4 place epyc9 (client 2848185): GPL.
- hub_Wi waits on D26 (KV-PLAN-R4/R5). sys_c relaunches on D27c/D27d. hub_C is held for the bind.
- Cleanup: tree/physical/die_plan/qwen_kvsys/plan_of_record/bind_of_record.d27d_linked (hardlink copy), the launch_a5603de7c56b and g0gate_a/bindgate_a dirs: ot-delete them when no longer needed.
