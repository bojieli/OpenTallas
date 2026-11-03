# HEAD LEP child views

These views come from the existing SIGNED and post-route EQUIVALENT LEP ECO7 core, not a new route. Source: intel2 `/srv/opentallas-scratch2/claude/die-head-46/lep_eco7_kit`; signed receipt `resign_flow-20261030-f-head/signoff/signoff.json` (copied here). Stored sign-off: TT setup +9.29 ps, FF hold +3.92 ps, DRC/antenna 0; routed LEC 69,775/69,775 EQUIVALENT.

The original parent plan named this 777.6 x 492.48 child four times but supplied no LEF/lib. `head_lep_view_delta.apply` adds only those four LEF/lib references. Pins, outline, placement, clocks, reset, RTL and cycles remain unchanged. The actual signed pin-register clock means are TT 452.90 / FF 366.27 ps; `clock_contract.json` binds them to the exact selected TT library. ETM extrema are not used as means.

Export: own copy of the source 6_final ODB/SPEF/SDC, ORFS `do-generate_abstract CORNER=TC CORNERS="tc bc"`, output TT/FF ETMs plus actual abstract LEF. Work: intel2 `/srv/opentallas-scratch2/claude/codex-head-lep-views-1101`; ot-run exit 0, 337 s, peak 3.1 GiB. `_tc.lib` and `_BC.lib` were copied byte-for-byte to `_tt.lib` / `_ff.lib`.

ETMs provide the prototype's macro timing views; parent hold and expanded child-pair qualification still use the real routed child views under the existing flow. This is not a new parent SIGNED or die-G4 claim. No source/frozen plan was edited by this export.

## 2026-11-03 abstract re-export (DH56-LEP, class C PDN-0006)

`ot_s81hd_lep_pair.lef` is now the detailed-upper-layer form of the SAME signed 6_final.odb (no re-route): the blanket `-bloat_occupied_layers` OBS on M6/M7 hid every M5 PG pin from the parent M6 straps (`[ERROR PDN-0006] VSS on M5 is blocked by obstructions on M6, M7`). `tools/die_plan/abstract_detail.py splice` keeps the signed view byte-for-byte except the M6/M7 OBS, which come from `write_abstract_lef -bloat_factor 1` of that ODB; pins, SIZE, PG pins and M1-M5 OBS are unchanged (`check` PASS, the detailed export's PIN section equals the signed one). hd_lep0N PDN probe PASS: 98/98 macro PG terms connected, 178/178 M5 PG strips per u_pair net touched, 0 strap/OBS overlaps. Evidence: `abstract_detail_1103.json`. Libs, clock contract and sign-off are unchanged.
