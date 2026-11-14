# TL-S81PHY (s81 phy__t1) 2026-11-14 04:50
- Why not started: plan flag hard -> wave gen skips; not in only_items. Asked KIT-OPS-3 for hard_wrappers + only_items.
- Private kit: epyc10 /srv/opentallas-scratch2/claude/tl-s81phy (gen.sh: bind kit-rtl + gen.py phys --hard-wrappers on B3v plan_h2_2249 src), log intel2 ~/tl-s81phy-gen.log
## 2026-11-14 06:59
- Wave config done by KIT-OPS-3 (hard_wrappers+only_items). Private kit: gen recipe /srv/opentallas-scratch2/claude/tl-s81phy/gen.sh (epyc10; copy on intel1 w/ run). Patches: bb params (rtl/*_bb.v, orig bb.orig), macro_place.tcl y 0->4.32 (orig gen/macro_place.tcl.orig).
- Result: passes lint/preflight/LEC/floorplan/GP; DPL ok; 3_5 exits 241 deterministically (epyc10+intel1). Blocked on plan: outline growth N side, macro origin y>=4.32, bb params. Posted to DIE-S81-92.
- Next: when plan with growth lands, rerun gen.sh + run_kit.sh route (env OT_NATIVE_RESET_SCOPE=selected OT_PLACE_MAX_FANOUT=64 OT_GRT_NONPORT_HOLD=1 OT_CORE_TAP_REACH_UM=0) on intel1/epyc2; on pass add AUTO-RESIGN row + RESULT.
