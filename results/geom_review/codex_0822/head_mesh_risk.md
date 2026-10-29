# HEAD explicit-mesh risk applicability

2026-10-29 08:29 PDT. Estimate-only existing-artifact sweep requested by
DIE-QC-32's 08:17 ASK: does the QC A3 regular FIXED dbWire / NDR-demotion
short mechanism apply to the current HEAD release clock?

Result: NOT APPLICABLE to the current HEAD hk5 form. The actual config
intel2:/srv/opentallas-scratch2/claude/die-head-26/clk/head_hk5.yaml
selects hk5_inv150r, stack inv, top link_htree, rep150, region dme.
The run kit is kit_h5/kit. Its clock directory contains ctree.v, ctree.tcl,
tree.json, make_tracks.tcl and leg_spans.json, rather than an explicit mesh.

Read both actual out_h5_TT/combo.tcl and out_h5_FF/combo.tcl: neither has
routed_mesh, clock_routed, dbWire or ck_mesh references. They instantiate the
ordinary clock-cell tree inline; sources are grt/tracks.tcl, grt/obs.tcl and
the platform setRC.tcl. They run global_route -congestion_iterations 50 with
signal M4-M7 / clock M8-M9. Both corresponding combo logs contain zero
GRT-0273 warnings and finish OT_DONE / EXIT 0 (TT log10323 bytes, FF12097).

No detailed-route short count is available in these GRT artifacts. This is
an applicability diagnosis, not a DRC/short-free assertion or a new gate.
No HEAD default, plan, routing, timing or clock change is needed from this
finding. Historical HEAD explicit-mesh runs are not reopened.
