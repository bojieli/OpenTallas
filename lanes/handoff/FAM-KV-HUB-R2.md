# FAM-KV-HUB-R2 handoff (Opus 5.5, successor of FAM-KV-HUB). CURRENT 2026-11-21 05:1x PST
Family: kv3_hub_{C,Ei,Eo,Wi,Wo}, kv3_hroot, kv3_sys_c, kv3_sys_SD_v1. Plan owner KV-PLAN-R4. Representative kv3_hroot.
Work dir: epyc8 /srv/opentallas-scratch2/claude/fam-kv-hub-r2 (tree/, ana/, rows h1_hroot_rows.py, resite2.py).

## Diagnosis (measured, D25d attempt_5 epyc2 kw43-wave-1109/.../KV-D25d/items/kv3_hroot/attempt_5)
- post-CTS TT +2.11 (placement RC); post-GRT TT -753.66 (GRT max 114 pct). 5_global_route.rpt: clk setup skew -532 (fan_c target latency 781 ps on
  clk_t9: clkleafrepg chain), worst max kc rd_bin -> ko[6] -475, cland kvs_ctl ring sd_c -> dsel -429; worst min u_bin kvs_ctl q[927] -> fan_c -248.
- Hops (D25d CTS geom): landing dsel -> u_bin up to 738 (kvpc), 653 (slg), 556 (kvs_ctl); u_st.d -> bout_o_pc 437; fan -> bout_chN 411; relay chain
  stages spaced unevenly (bin and r_c/g_c co-located, then 380 um hops). All logic packed in the E strip.

## Rows (variant A, 0 cycles) = h1_hroot_rows.py on D27d plan + ana/resite_delta.json
- h1 relay_sites per-bit equal-hop re-spacing on the 4 chains: kvpc 738 -> 390, kvs fan 556 -> 273, slg 653 -> 321, esh 437 -> 317 um max hop (all <= 405).
- h2 internal_stations o_kvs_hroot_Q_o_ctl station re-sited to the slg cluster point (1590, 710).
- h3 clock.ring_hold.sender_ps_types.kv3_hroot = -50.
- NOT in A: TAP-GRID-R2 12-west-tap drop (epyc8 tap-grid-r2/hroot/d28-hroot-pending.json renames tap ports; needs collector/raw START regen) = variant B.

## Chain status
- private tree: setup running (setup_tree.log). Next: apply rows, rt_launch_tree on rt/a5603de7c56b, G0 + strict bind/LATCHECK (ot-run epyc8), kit-rtl/gen, run_kit GOAL=route.

## Siblings (wave D25e3, not mine; waiters armed via ot-wait on intel2 client pids)
- hub_Ei attempt_4 route epyc10 (client pid 55902): post-CTS TT +21.74, in GRT.
- hub_Wo attempt_9 route epyc9 (client 2433217): in CTS.   hub_Eo attempt_4 place epyc9 (client 2848185): GPL.
- hub_Wi waits D26 (KV-PLAN-R4); sys_c relaunch on D27c/D27d; hub_C held for bind.
