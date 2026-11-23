# VIS-DIE-S81 handoff (Opus, started 11-22 23:0x PST by COORD; brief scratchpad visual_brief.txt + visual_brief2.txt)
Scope: whole S81 die floorplan (core placement, channels, pin windows, ft, clock trunk/taps, reset, outline/reticle). Families: VIS-S81-COL (col), LEAF-ROUTE-CBC (leaf), VIS-S81-MISC (rest). Rows -> S81-J6-ASSEMBLY-R5 (J9 cut 11-23 12:00).
Work: epyc9 /srv/opentallas-scratch3/claude/vis-die-s81 (in/plan_j8.json = f65f62779bef copy of epyc10 s81-j6-r5/j8_cut_intake/plan_candidates/j8_v3_c67f_revert2_repriced.json; scripts die_vis.py, wuc.py, wmove.py, es_render.py; matplotlib via ~/.local site path under python3 -I). Outputs mirrored to intel2 /srv/opentallas-scratch2/claude/vis-die-s81/out.
## 11-23 00:0x status
- Renders READ: die_j8_status.png, die_j8_lanes.png, die_j8_edgestrip.png. Verdict in GEOM-REVIEW (00:0x).
- Findings: reticle-bound (Y +19.5 um, X +306 um); EDGE-STRIP 241 types (census lanes/handoff/VIS-DIE-S81-EDGESTRIP-J8.tsv); hub-star ft through leaf.
- Window-off-core die row (wmove.py, col excluded) rejected: 254/524 no free span, rest median 478-um shift. No die-level move row for J9; fix is type re-floor inside outlines (family lanes).
- Offer: svc_lo/svc_hi internal top bands (560/337 um) are the only Y slack in the central column if a family form needs Y growth.
