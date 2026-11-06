# Private A place continuation — preliminary floorplan witness

Unit `oth-ubuntu-98574-1793981206`, container `4d90405c53b7` (`hbmcore-kit_-99246`), intel2. Run `/srv/opentallas-scratch2/claude/svgr-top-rw-sizing-1106`, log `place_A_critical.otrun.log`, detailed `kit/run_place.log`. Standard ot-run `--crit --hosts localhost --mem 32 --threads 8 --disk 12`; unchanged same-kit official pending-proof reuse, identity `a699928ed074bd0672f23dc88b57f71f9e581a39f32592787af98459b6edca42`, original proof owner `hbmcore-kit_-818575` remains live. No duplicate synthesis or compiler proof. Stock goal `place` stops before CTS.

`floorplan_measure.json` measures actual `2_floorplan.odb`, not final placement. Functional 124066; TAP 16788; SRAM 9. All functional cells remain unplaced at this checkpoint. Functional area 15526.13994 um², nonmacro-core utilization .1107424. Existing row-site capacity 134310.75588 um², after whole-site exclusion of reviewed 4.32 um macro halo union 127516.44672 um², utilization .12175794. No unsupported row direction/height was encountered. Final placed counts and utilization remain PENDING.

No missing/wrong-net POWER/GROUND ITerm. Actual M5 stream_clk pin box [151.152,319.44,151.2,319.92] has zero positive-area intersections with 136 M5 power/ground wire boxes and 141915 M5-touching power/ground via envelopes. This geometric access check does not establish electrical PG continuity. OpenROAD `check_power_grid -floorplanning` is still running; its verdict remains PENDING.

B actual frozen kit remains unlaunched. Current runner has fixed WORK_HOME/FLOW_VARIANT; live cross-kit proof reuse unsupported. Completed transfer currently requires exact freeze identity, incompatible with truthful B geometry differences. Shared-flow owner is reporting the precise capability gap to root. No copied pending markers, substituted freeze, or geometry override.

Remaining: collect actual PG continuity result; final placed functional count <=150000 and post-halo row utilization <=.45; inspect actual placed image; retain compiler verdict independently. No CTS/canonical activation.

Actual `floorplan_actual.png` opened and reviewed: exact nine A SRAM homes and separated 4.32 um halos retained. The clock point is over programme_lo, local (87.346,69.684), 0.804 um inside its top edge; it is not an open-channel pin. Its M5 layer has no macro OBS, and the actual PG shape audit above finds no overlap. Actual CTS via/pin access remains an ordinary later qualification. There are no placed cells in this floorplan image; it is not the required final placement-density image.

OpenROAD `check_power_grid -net VDD -floorplanning` reports `[INFO PSM-0040] All shapes on net VDD are connected.`, Tcl catch 0 / result 1. VSS remains running. This floorplanning connectivity result does not qualify detailed routing, IR, or signal access.

PG connectivity completed for VSS too: `[INFO PSM-0040] All shapes on net VSS are connected.`, Tcl catch 0 / result 1. Full both-net output is retained in `floorplan_pg_check.log`. Both floorplanning connectivity checks PASS; electrical/IR and post-placement/detailed-routing checks remain separate.
