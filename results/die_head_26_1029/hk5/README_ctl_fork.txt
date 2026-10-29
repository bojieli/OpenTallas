DIE-HEAD-26 fork, 2026-10-29: hk5_ctl plan event (estimate first, then generator).  Own numbers, UNCHECKED by NUMBER-CHECK.
Base: hk4 plan_spine_raw_rx_tx (main a4453d400 tools/die_plan; base G0 PASS 0 err / 22 warn).

(1) CROP + FT STRIP (no neighbour pin moves). Core = type-frame SW rect that keeps every window it already touches.
type     slot             core            area     synth (std+SRAM)        total fill  strips (type: rect, slots)
hd_ctl   1442.88x1226.88  587.52x518.40   304,571  17,214+53,294 = 70,508  0.232       hd_ctl_n 1296.00x708.48 (w3u/w3d moved, 5 st; 5 ctl W buses -> core N face, 1-3 st)
                                                                                       hd_ctl_e 855.36x103.68 (n_tx/n_rx, 3 st)
hd_host  1442.88x1226.88  1296.00x570.24  739,031  153,593 (std ~29.6k)    0.208       hd_host_n 1442.88x656.64 (au/ad/bu/bd moved; h_tx/h_rx 2 st)
hd_mesh  1442.88x1226.88  604.80x1226.88  742,017  150,990 (std ~27.0k)    0.203       hd_mesh_e 838.08x86.40 (m_tx/m_rx 3 st), 3 inst MY/MX/R180
Stations = ceil(route/364) (G0C hop <= 0.9x405).  Latency (Plan.lane_latency): host_tx/rx 38->40, m0S_tx 49->52, m0S_rx 51->54,
m7S_tx 46->49, m7S_rx 47->50, m7N_tx 6->12, m7N_rx 7->13, lepf/unit_lep 2->3, ctrl_lep/head_lep_fault_return 2->4,
head_lep_landing 2->5 (all priced by the static schedule, 12.15c; regen_constants needed downstream).
G0 on plan_hk5_ctl.json: PASS 0 errors, 24 warnings (22 base + 2 new "crossing ~1002 um" WARN on ctl_n slots: generic bbox
estimate; the exact hop check passes).  Only hd_ctl/host/mesh changed + 4 new types; only mesh7N/mesh7S core origins moved
(mirrored instances keep their far-corner core in place); 6 new parts; 10 freed rects -> die.channels.  Clock die_islands outside
the cores: 2 (ctl) + 11 (mesh) dropped (now die channel), reset local taps clipped to the core.  Regions: new strips join their
parent's region (spine_regions_hk5_ctl.json).  Render hk5_ctl_zoom.png (viewed).
Strips are near-empty ft channels (fill << 1 %) -> GEOM template-strip rule, as for the hk4 strips.
Files: gen_hk5_ctl.py, plan_hk5_ctl.json, hk5_ctl_report.json, spine_regions_hk5_ctl.json, g0_hk5/, render.py, hk5_ctl_zoom.png
