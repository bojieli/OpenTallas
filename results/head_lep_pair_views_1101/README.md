# HEAD LEP child views

These views come from the existing SIGNED and post-route EQUIVALENT LEP ECO7 core, not a new route. Source: intel2 `/srv/opentallas-scratch2/claude/die-head-46/lep_eco7_kit`; signed receipt `resign_flow-20261030-f-head/signoff/signoff.json` (copied here). Stored sign-off: TT setup +9.29 ps, FF hold +3.92 ps, DRC/antenna 0; routed LEC 69,775/69,775 EQUIVALENT.

The original parent plan named this 777.6 x 492.48 child four times but supplied no LEF/lib. `head_lep_view_delta.apply` adds only those four LEF/lib references. Pins, outline, placement, clocks, reset, RTL and cycles remain unchanged. The actual signed pin-register clock means are TT 452.90 / FF 366.27 ps; `clock_contract.json` binds them to the exact selected TT library. ETM extrema are not used as means.

Export: own copy of the source 6_final ODB/SPEF/SDC, ORFS `do-generate_abstract CORNER=TC CORNERS="tc bc"`, output TT/FF ETMs plus actual abstract LEF. Work: intel2 `/srv/opentallas-scratch2/claude/codex-head-lep-views-1101`; ot-run exit 0, 337 s, peak 3.1 GiB. `_tc.lib` and `_BC.lib` were copied byte-for-byte to `_tt.lib` / `_ff.lib`.

ETMs provide the prototype's macro timing views; parent hold and expanded child-pair qualification still use the real routed child views under the existing flow. This is not a new parent SIGNED or die-G4 claim. No source/frozen plan was edited by this export.
