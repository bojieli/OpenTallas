# TYPE-HDCORE-ELEMAB handoff (started 2026-11-14)
- Goal: rebuild ot_s81hd_elemA_cv / elemB_cv as NEW signed records, same pins as signed LEF (results/head_core_clockfreeze_release/elem{A,B}_signed), R-MINIMAL + LEC.
- Work dir: epyc9 /srv/opentallas-scratch2/claude/type-hdcore-elemab/repo = shared clone of hbm-vsn-xtap/src_x11 checked out at d6231262f (signed src commit; 6ddb210f73 also present). Hub git has all commits.
- Chain to replay: hd_elemA_rebuild.py (--elem A|B) -> head_elemB_island_kit.py style island patch (infra_island_kit_patch/v2/v3q, quadA_v4.json in results/head_core_lat_r5_1026/elemB/kit_inputs) -> head_core_r14_rebuild.sh (plan tree) -> route -> head_post_route_eco.sh -> signoff + LEC. Pins: A ft_mstrap_i centre (159.84,159.84); B (144.72,146.16); io.tcl must be regenerated from the signed LEF.
- Modern hold hooks: tools/die_plan/pregrt_ff_hold.py + OT_PREGRT_FF_HOLD in wave src /srv/opentallas-scratch2/claude/wave-src/20261113/s81_head (epyc9).
- Status: setting up work tree (11-14).
