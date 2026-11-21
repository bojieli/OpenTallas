# OPUS-FIX-KV-PV-R5 handoff (KV pv family owner; successor of OPUS-FIX-KV-PV-R4)

Written 2026-11-21 06:2x PST. Posts lanes/posts/OPUS-FIX-KV-PV-R5.md. Hub dir intel2 ~/tmp/okpvr5 (chain12.log), /srv/opentallas-scratch2/claude/opus-fix-kv-pv-r5 (mkspec.py, wave_w/spec.json).

## State
- Own tree: epyc8 /srv/opentallas-scratch2/claude/opus-fix-kv-pv-r4/split28/tree5 (rsync copy, NO hardlinks; results/ and physical/ref_tile are
  read-only symlinks to split28/tree). Old split28/tree is hardlinked to kv-plan-r2 (never write in it).
- tree5 tools/die_plan/type_split.py carries the pre-move base-tap fix (raw_premove). compose12.py -> por_split_12_composed (ring
  cl_i_vport_E_N_vo_d2 at (967.68, 241.92) in w; v3e keeps cl_i_vport_E_N_vo_d1, W_N_vo, W_N_vo_d1).
- chain12.sh (ot-run oth-ubuntu-2070916-1795269991, epyc8, from intel2): installs split12 as tree5 plan_of_record (split10 kept as
  por_split_10_installed), r8 = bindgate_4/r8pin2.json, strict bind 5 -> split28/bindgate_5 (+errdiff.txt). If only R8 rows are new:
  ONE r8_refresh (rt/current) from bind-5 bus_groups -> bind 6 (bindgate_6). Accept = errdiff new 0 vs basebind (45 inherited D27b6 rows).
- Next on clean bind: kit_wave run-item /srv/opentallas-scratch2/claude/opus-fix-kv-pv-r5/wave_w/spec.json (dry_gen; wave env of KV-D26
  pv = die_gen_env + item_env kv3_pv_v3 + type_args + flow_tag; asserted in mkspec.py) -> diff config.mk vs wave kit -> run_kit route.
- type_split push: epyc7 lane clone branch claude/opus-fix-kv-pv-r5-tsplit 3a132dd5b5 (R4 b461211ea7 rebased onto main b8c28cb918 +
  raw_premove fix + test; test_type_split.py passes). Push with ot-push-main after a clean bind. S81-SVC-R6 _sidecar fix is already on main (d32d1a542d).
## Cancels (06:01-06:04 PST, kit_wave cancel-rows, struct stop, cls PLAN)
- v1@4 639k/-1103, v2@4 691k/-359, v2n@6 745k/-860, v3@5 489k/-758, v3n@12 472k/-683, v4n@4 456k/-333.
- Left: v4 432k/-345, v5 381k/-915, v5n 422k/-639, v7 394k/-665 (epyc8), v12 445k/-633 (epyc9) - floorplan cells under 450k.
