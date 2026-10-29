`spread_topk_s.py SRC OUT` copies a plan to a fresh OUT and changes only
`selected_line[2367:0]` x coordinates in the TOPK core's pins table. The other
pins, nine clocks, outlines, station coordinates, plan JSON and latency stay
byte-identical. It refuses pin collisions and uses the actual oriented core
origin plus each bit centre for the station reach report.

C25b trial output: 2368 pins now span 568.08 um (87.4% of the S face) at 0.24 um
pitch: peak 84 pins/20 um = 4.2/um, down from 10.45/um. Render personally viewed:
`s_spread_plan.png`; eight SRAM halos and seventeen clock islands are clear.

Verdict remains FAIL FOR P&R. The actual core is MY at root-local (34.56,0),
so its S input y is 0.096 um. The existing selected_line station is at
(469.44,538.92), while its stale endpoint metadata says y=530.261. EVERY one
of the 2368 bits already exceeded 405 um before this candidate (min538.848,
max762.432); the wider S spread has max932.664. Density-only spreading is not
an adequate floorplan fix. DIE-HBM owns the actual face/corridor/station event.
No station is silently moved and no cycle is added by this script.

A zero-cycle alternative estimate (not implemented/adopted): N-facing inputs
at y=499.944 with the station x at the core centre (root-local359.64) would
bound the last hop to about323.016 um. The existing ~1500 N pins require a
coherent pin/layer assignment with the selector partner; this is a die-plan
choice, not a kit-local edit.

The source fix is merged353da5b41. New C25b kit fa7eb9f3007d2cd0 generated on
current main a3d34dd8e, KIT_PREFLIGHT PASS issues0. Tree64 helper is present
and the serial variable write is absent in staged RTL. Source synth+LEC runs
on intel1, unit oth-ubuntu-476300-1793257727, 32GB/8threads, goal synth ONLY:
/srv/opentallas-scratch2/claude/codex-hbm-topk-1028/kits_v4/ot_hbm_idx_topk_link_static_4b8bc21191aa-_tree1028v4
Check run_synth.log, run/logs/.../1_2_yosys.log and lec/lec.json. No place/STA/
route runs are authorized from the failing S-face plan.
