# QC-MESH-PILOT-2 (2026-10-28 PDT): detailed-route proof of the QC-MESH-PILOT-1 A0-quad mesh, by clips

Basis: QC-MESH-PILOT-1 claude/qc-mesh-pilot-1-1028@058de253f4 (trials tA3 = c_E3_bf_11 adj 0.4, tA2 = c_E3_bf_11 adj 0.7,
tB = c_W2_bn_01 adj 0.4; plan ev_qc23pg). Die-local scripts only; no shared tool changed (default flow byte-identical).
**All numbers UNCHECKED** -> NUMBER-CHECK.

## Why clips
The full 3.23-mm2 region sat in DRT "Init gr pin query" for > 2 h (21:26-23:29, and > 45 min in the earlier runs);
containers qcmp-tA2/tA3/tB were killed 23:29 (log line appended to each run.log). Per the COORD ruling the region is
routed as slices; routed arrivals are composed analytically (AGENTS: simulate the minimum component):
- `mid` = middle band, full width (root port -> R -> A x2 -> B x4 inputs, root -> E0), 0.23 mm2
- `c0..c3` = one tap column each, +-80 um around its M9 strap, full height (B_i -> P -> C -> D -> 8 mesh drivers)
- `core` = centre channel (E0 -> Q -> E1 -> A0 core-tap loads, off-mesh branch)
Each clip carries the mesh straps inside it as FIXED 4W wiring of a regular net (DEF NDR CK4W), so DRT must route
every driver Y and tap A pin stack onto the strap (pin-stack DRC is part of the proof; PILOT-1 left them unrouted as
special-net pins). Rects snap to 8.64 um (all track/site grids align). A clip entry gets an M9 port at the nearest PG
gap (the incoming leg's stack); DRC markers within 3 um of it are clip-harness artifacts (`drc_summary.json`).
Clip pin-access init takes seconds (vs > 2 h for the full region).

## Files
- `pilot_clip.py build|compose|merge`, `clip_sta.sh` (TT/FF re-time of each routed clip with the composed entry slew,
  then compose), `clip_render.py` (full DEF path parser incl. via chains), `test_pilot_clip.py` (2 tests: every
  tree net in exactly one clip, cells inside, 8.64 grid, fixed mesh wiring; compose reproduces the full tree exactly).
  Tests 5/5 PASS with QC-MESH-PILOT-1's 3.

## Results so far (23:30)
- Clip method vs the full-region GRT (clip GRT arrivals composed, TT late, 156 pins): tA3 -0.42..+0.63 ps (exact);
  tA2 -3.8..+15.2 ps; tB -32.8..+0.5 ps. The +-80 um clip window keeps GRT from the long x-jogs onto the core edge
  that PILOT-1 found (render VIEWED): tB's worst full-region jog (D2uu) is 33 ps faster in the clip. So for tA2/tB the
  clip numbers are the window-constrained routing = close to PILOT-1 condition (1) "reserved tree-leg M9 track".
- DRT finished: mid (3 trials), core (3), c0 (tA2, tB): **0 design DRC**; residual = 2 Min Step at the root/entry
  M9 port (+2 shorts where the a2/a3 c0 entry port lands on the strap gap) = harness only. Iteration-0 counts
  (e.g. c3 2571: tree-leg Metal Spacing/Min Step on M8/M9 next to the core edge) fall to 23-41 by iteration 3.
- Pending (DRT still converging, 10-27 markers, stubborn-tile iterations): c1, c2, c3 of all three trials
  (intel1 a3/, epyc2 a2/ b/); c0 of a3. Render of tB partial (mid+c0+core) VIEWED: tree legs on M9 along the strap
  column, one M9 x-jog over the u_t02 core edge in c0, core branch straight on M9 in the centre channel.

## Collect (successor)
1. When every `*/run.log` in intel1:/srv/opentallas-scratch2/claude/qc-mesh-pilot-2/a3 and
   epyc2:/srv/opentallas-scratch2/claude/qc-mesh-pilot-2/{a2,b} ends `EXIT 0`:
   `cd /srv/opentallas-scratch2/claude/qc-mesh-pilot-2 && bash clip_sta.sh a3 ../qc-mesh-pilot-1/tA3` (intel1),
   `bash clip_sta.sh a2 ../qc-mesh-pilot-1/tA2; bash clip_sta.sh b ../qc-mesh-pilot-1/tB` (epyc2);
   `python3 pilot_clip.py merge X mrg_X` for X = a3/a2/b.
2. Copy `X/tree_drt_{TT,FF}.txt` + `mrg_X/{drt.def,drc.rpt,drc_summary.json}` to intel2
   /srv/opentallas-scratch2/claude/qc-mesh-pilot-2/t{A3,A2,B}d/ (hosts do not resolve each other: relay via localhost).
3. intel2, in that dir: `bash <wt>/results/qc_mesh_pilot_1/pilot_chain.sh tA3d drt` (and tA2d, tBd) -> pair_drt.json;
   `python3 <wt>/results/qc_mesh_pilot_1/pilot_summary.py drt hb_est23.json summary_drt.json tA3d tA2d tBd`
   (two-trial stability tA3d~tA2d = same template, different GRT adjust); `clip_render.py tXd tXd render_drt.png` + VIEW.
4. Verdict: DRT glue pair U <= 61 ps TT/FF (incl. MC 3 sigma + gradient) -> DIE-QC-24 adopts for the 192 A0 quad
   regions; else W180 hold buffering. Also report DRT-minus-clip-GRT per pin (`compose ... grt` vs `drt`).
