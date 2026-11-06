# Private A place continuation — preliminary floorplan witness

Unit `oth-ubuntu-98574-1793981206`, container `4d90405c53b7` (`hbmcore-kit_-99246`), intel2. Run `/srv/opentallas-scratch2/claude/svgr-top-rw-sizing-1106`, log `place_A_critical.otrun.log`, detailed `kit/run_place.log`. Standard ot-run `--crit --hosts localhost --mem 32 --threads 8 --disk 12`; unchanged same-kit official pending-proof reuse, identity `a699928ed074bd0672f23dc88b57f71f9e581a39f32592787af98459b6edca42`, original proof owner `hbmcore-kit_-818575` remains live. No duplicate synthesis or compiler proof. Stock goal `place` stops before CTS.

`floorplan_measure.json` measures actual `2_floorplan.odb`, not final placement. Functional 124066; TAP 16788; SRAM 9. All functional cells remain unplaced at this checkpoint. Functional area 15526.13994 um², nonmacro-core utilization .1107424. Existing row-site capacity 134310.75588 um², after whole-site exclusion of reviewed 4.32 um macro halo union 127516.44672 um², utilization .12175794. No unsupported row direction/height was encountered. Final placed counts and utilization remain PENDING.

No missing/wrong-net POWER/GROUND ITerm. Actual M5 stream_clk pin box [151.152,319.44,151.2,319.92] has zero positive-area intersections with 136 M5 power/ground wire boxes and 141915 M5-touching power/ground via envelopes. This geometric access check does not establish electrical PG continuity. OpenROAD `check_power_grid -floorplanning` is still running; its verdict remains PENDING.

B actual frozen kit remains unlaunched. Current runner has fixed WORK_HOME/FLOW_VARIANT; live cross-kit proof reuse unsupported. Completed transfer currently requires exact freeze identity, incompatible with truthful B geometry differences. Shared-flow owner is reporting the precise capability gap to root. No copied pending markers, substituted freeze, or geometry override.

Remaining: collect actual PG continuity result; final placed functional count <=150000 and post-halo row utilization <=.45; inspect actual placed image; retain compiler verdict independently. No CTS/canonical activation.

Actual `floorplan_actual.png` opened and reviewed: exact nine A SRAM homes and separated 4.32 um halos retained. The clock point is over programme_lo, local (87.346,69.684), 0.804 um inside its top edge; it is not an open-channel pin. Its M5 layer has no macro OBS, and the actual PG shape audit above finds no overlap. Actual CTS via/pin access remains an ordinary later qualification. There are no placed cells in this floorplan image; it is not the required final placement-density image.

OpenROAD `check_power_grid -net VDD -floorplanning` reports `[INFO PSM-0040] All shapes on net VDD are connected.`, Tcl catch 0 / result 1. VSS remains running. This floorplanning connectivity result does not qualify detailed routing, IR, or signal access.

PG connectivity completed for VSS too: `[INFO PSM-0040] All shapes on net VSS are connected.`, Tcl catch 0 / result 1. Full both-net output is retained in `floorplan_pg_check.log`. Both floorplanning connectivity checks PASS; electrical/IR and post-placement/detailed-routing checks remain separate.

Compiler capacity update: shared-flow sole resize owner admitted FULL +32 GiB under admit.lock after other naturally completed jobs released capacity. Original unit oth-ubuntu-818343-1793973397 reservation/meta changed32→64 before scope/Docker64GiB. Exact original container03fdcaeb8d08 remains running; never paused/restarted, proof inputs unchanged. `compiler_live_resize.json` retains the owner receipt. Old29GiB/32GiB pause guard withdrawn by parent after admitted64cap; no blind repeat resize. PLACE unit remains32GiB/8threads separately.

Nearest generated M5 PG shape/via envelope to the stream_clk pin edge is 1.956 um (VDD via envelope x149.076..149.196,y319.525..319.571). Via envelopes conservatively include all via-layer geometry; this separation does not replace detailed signal/clock-via DRC.

Actual global-placement checkpoint (3_3_place_gp.odb): 144222 FUNCTIONAL,16788 TAP,9 SRAM; all functional cells placed. Functional area18069.78132um², nonmacro-core util.12888528, post-halo-row util.14170550. Global placer reported divergence and reverted to iter2052/overflow.194; routability target not reached (best weighted congestion1.4267). No closure claim. Opened global_place_actual.png: dense lower-half controller/port network around programme_lo and cache2/desc_hi, particularly x130..295,y60..310; upper programme region mostly sparse apart from cache4 path and face rows. This is intermediate global placement, not final legalization.

Global checkpoint has65270 null PG ITerms on32635 newly created stdcells; macro PG is bound, and actual clock PG clearance remains1.956um. Final-place binding/census remain pending. The full runtime witness retains all open term names; committed summary records count and sample. Do not interpret the earlier floorplan connectivity pass as post-resize PG continuity.


## Final PLACE and Claude handback

A unit `oth-ubuntu-98574-1793981206` completed exit 0. Final `3_place.odb` measured: 144610 FUNCTIONAL, 16788 TAP, 9 SRAM, 0 unplaced functional. Functional area 18162.72882 um². Nonmacro-core utilization .12954824; post-4.32um-halo row utilization .14243440. Both <=150000 / <=.45 size gates PASS. Actual `final_place_actual.png` opened and reviewed: lower-half concentration and over-programme M5 clock point remain as in global snapshot. DPL reports no placement violations; average displacement .2um, max1.6um. No CTS executed.

Material remaining PG gap: final ODB has 66046 null PG ITerms on 33023 standard-cell instances; no macro PG gap. This is the actual saved final PLACE state, not merely the earlier intermediate snapshot. Do not equate the earlier floorplan all-shapes-connected pass with final resized-cell PG binding. Resolve and capture supply binding before further qualification; active fixture was not edited. M5 clock zero PG overlap and conservative nearest PG/via-envelope distance1.956um persist.

Global placement reported divergence/revert and could not meet routability target (best weighted congestion1.4267). No timing/routing closure claim. Original compiler container03fdcaeb8d08 remains healthy active, admitted64GiB after sole-owner wave resize, no verdict at handback, no restart/pause. Original unit oth-ubuntu-818343-1793973397 and source/proof inputs retained. B actual kit remains frozen/unlaunched on cross-kit proof-transfer capability gap. No new jobs or CTS on Claude handback.

Source-only optional factory c723ac4ead99e17a91e603a4369dc4aa663a546c is published via main22271e4968e2f3416b33902a1430ca9fce2ff17f; no canonical recipe/POR activation. Evidence branch codex/hbm-svgr-top-1106 retains actual A/B kits and reviews.
