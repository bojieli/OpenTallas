# DS ROM selected S81 macro/PG/track preparation under Maxwell

Selection is Claude `73851317fd9b4fb86c56f6ff760e29981ec610f2`: 81 stages, 2,417 active pairs per rank die, BF519, ragged retained RD64, indexer wk/wq_b replicated on all four ranks. Model screen 839.239 mm2 (839.24 rounded), 18.761 mm2 margin; 324 layer-rank dies and 368 total. S82/S73/RD16 are not selected. The screen is not a placed-fit verdict.

Maxwell's source-pinned S81 inventory input gives 9,668 weight macros/rank die and 3,132,432 across the layer-rank dies. This is a decision-derived inventory target, not a fabricated placed-instance census. As of Maxwell's 2026-10-04T00:52:18Z handoff, actual S81 frame LEFs/netlist/DEF, full inventory, stage/rank map and native power grid are absent. Arendt owns generation with --stages 81 --pairs 2417 --bf 519 and explicit every-rank indexer addressing/compute/service. Do not use the S82 address API's 9552/2388/512 constants. Maxwell owns placement composition, native PDN/IR and GRT; this tool only prepares actual pin/PG and channel inputs.

The four retained actual LEF objects are pinned by SHA256 against Maxwell's 31-object kit. Their grades are kept: failed routed Rcap0 Q is NOT selected; weight/configuration ROM LEFs require source/track binding; PHY is an assumed licensed-IP proxy. No v2 substitution, macro generation or source mutation was performed.

Concrete placement constraints from the retained LEFs:

| Master | Orientation | Preferred-track origin constraint | Joint site/row constraint |
|---|---|---|---|
| weight/config ROM | R0/MY | Y = 0 mod 48 nm | Y = 0 mod 2160 nm |
| weight/config ROM | MX/R180 | Y = 42 mod 48 nm | Y = 810 mod 2160 nm |
| PHY proxy | R0/MX | X = 0 mod 48 nm | X = 0 mod 432 nm |
| PHY proxy | MY/R180 | X = 24 mod 48 nm | X = 216 mod 432 nm |

These are legal pin-centre lattices, not actual selected placement. Mirroring the retained ROM while snapping to origin0 puts pins 6nm off M4. Pin rectangle area576nm2 is below the2000nm2 tech minimum: routing patches/access must be counted, not removed. Failed Q also reports same-layer OBS spacing concerns. Legal pin centres alone do not close pin access or routing.

`preparation_r2.json` preserves every native supply rectangle by layer/local bbox. Weight/configuration and PHY contacts are M4. The retained Q has contacts on M1/M2/M6/M7, all kept rather than reduced to synthetic load pins. Maxwell's hierarchy must connect actual macro landings upward (M4->M5->M6->M7->M8, or M7->M8), prove VDD/VSS connectivity first, then use the actual S81 instance power map, bump sources, via/PG shapes, RC and clock-C exclusions for IR. The historical204W map is not S81 power. Supply access inside blocked layers cannot be skipped by attaching current sources to invented M1 pins.

Actual channel counting unions PG, clock/shield and macro-obstruction intervals without double-counting a track. There is no guessed signal-share percentage. Long-haul M3/M5 remains excluded; actual registered stage distance must be <=430um with added cycles charged by the parent model. Corridor geometry, signal count and track exclusions remain unknown until Maxwell supplies selected objects, so channel capacity and selected-die fit are unqualified.

Mapped RD64 node evidence is also carried unchanged: 4,706 ragged nodes projected at FF50 imply75.293688mm2 full-node body, versus31.548mm2 storage-only return in the analytical screen. Maxwell/Claude must reconcile existing residual containment; do not blindly add the difference or silently delete it. No alternate stage or return-depth lever was opened.

Replay without physical tools:

```sh
python3 tools/dsrom_s81_macro_track_prep.py --out /tmp/s81-preparation.json
python3 tools/dsrom_s81_macro_track_check.py
```

When selected placement/channel objects exist, optional JSON inputs to --placements/--channels must declare stages81 and exact selection_commit73851317f..., and contain instances/channels respectively. Placement records carry actual instance/master/origin_nm/orientation (R0/MX/etc); channel records carry actual layer/axis/low_nm/high_nm/required_tracks plus pg_intervals_nm/clock_shield_intervals_nm/obstruction_intervals_nm. The tool transforms real supply shapes and tests actual pin centres; it does not place or route. Source binding stays open until Maxwell matches these objects to the selected netlist/inventory.

Validation in check.log covers S81 binding, legal joint lattices, overlapping PG/clock track debits, and refusal of S82. No new build, P&R, sweep, inference or HBM work. Maxwell-reported existing live jobs are preserved as owner-reported state, not claimed freshly verified by this worker.
