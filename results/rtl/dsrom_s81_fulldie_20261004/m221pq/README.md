# S81 m221pq layer1 die (current physical basis, CLAUDE S81-DIE 2026-10-07)

1,792 pairs a die (mapping 2d811aafb: HALF 120 stages / 480 dies, FULL 98 / 392), mixed221 frames (4 BF full-width +
10 q half-width = 9 rows a region, q frame 221.4 um, frame 2,646 um), 1,728 um hub columns, PQ placement
(`--pq-place`): a 164.16 um root row on top of tier channels 0-5 (ret_root_r128 132.192 x 133.92 between two 8.64 um
return stations, centred in the 142.56 um return strip), PQ core slab 449.28 um tall after the VM with its 3 ROMs.
Options: `options.txt`; generator `tools/dsrom_s81_fulldie.py` (branch claude/s81-die-20261007); q abstract
`physical/s81_die_views/q_elem_qs5f` (routed QS5 FH221.4; FF hold open in its own job).

- plan/: floorplan.json (python legality 0 / 0, 0 pin clashes, field round trip 167 + 2 PQ stations), DEF, SVG
- clock/: die clock plan validated by clock-only CTS (tools/budgets/clock_plan.py): 167 regions, 69,979 synchronous
  pairs, max intra-region bound 58.5 ps (0 violations), 1 inter-region pair over 150 ps (ctrl_SW/cks <-> svc_SW/ck,
  197.2 ps, the hbm_read pair resolved inside the slabs by the abutting ctrl_pc / svc_pc tiles)
- OpenROAD real case (EPYC3 m221pq/a_real): 56,119 instances, 0 overlaps, 0 outside, on-track PASS, pin access 0 errors

Budgets (not views) on this die: PQ root (ret_root_r128 outline from results/uarch/s81_pq_root_cam_20261007), PQ core
slab, return stations (generated glue), hub slabs without a closed tile composition; marked "interim" in the die STA kit.
