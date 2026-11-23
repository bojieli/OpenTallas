# S81 B2 native SVC3 monitor placement, 2026-11-23

I viewed the native fixed-placement image on E10 at `/srv/opentallas-scratch2/claude/s81-j9-r6/compose/svc3_monitor_codex_1438/native_floorplan_1450/svc3_monitor_native_actual.png`. OpenDB placement unit `oth-ubuntu-4188777-1795474307` and independent ODB readback `oth-ubuntu-34104-1795474385` completed successfully.

All 66 named ASAP7 cells are FIRM, with four flops, an inverter for falling-edge capture, and a retained forwarded-clock buffer per stage. The six distinct M7 endpoint centers match the selected corridor exactly. The two-row width is 3.78 µm. No cell intersects a planned hard box, including the narrow stage 9 gap. The corridor has several over-core legs and requires the upper-metal tracks under actual die reservations. The private zero-delay native RTL test proved the 11 status cycles, 85 matching edges and 76 disagreements with a bypass control.

**PASS-COND for the scoped native corridor route diagnostic.** Evaluate actual native pin escape and segment connectivity in a crop with current hard boxes and the die PG obstruction pattern. Whole-die phase, PG connectivity, complete top clock reservations, TT/FF and sign-off remain release gates.

## Native crop route and extracted timing

- E10 global route `oth-ubuntu-131602-1795474668` connected 69 nets at zero overflow. All 36 long nets are present in the segment export. The longest is `clk_stage8`, 293.55 µm. Fifteen long nets use M8.
- E10 detailed route `oth-ubuntu-280639-1795475010` ran under 270 hard-box and 892 die power rectangles. TritonRoute reduced 12 reported violations to zero. The detailed DEF contains wires on all 69 nets, 580 vias, and a longest net at 293.651 µm. I viewed the actual route image `svc3_monitor_native_drt.png` in the native crop directory above. Stage 9 drops from M8 into the narrow legal opening and its six cells retain distinct accesses.
- The re-opened detailed ODB has an actual wire on every net. OpenRCX and the two Liberty corners completed in E10 `oth-ubuntu-407717-1795475380`. At 833 ps and 60/25 ps uncertainty with propagated clocks, the lowest reported internal TT setup slack is +83.205 ps and the lowest FF hold slack is +111.257 ps. The SPEF and log are `native_extracted.spef` and `scoped_rcx.otrun.log`.
- The separate M4–M9 die-top GRT scope ran in `oth-ubuntu-407585-1795475380`, with 69 nets, zero overflow, and internal placement of wire checks +160.048 ps TT setup and +289.864 ps FF hold using GRT RC. I viewed `svc3_monitor_native_top_grt.png`. The exact upper-layer detailed route is active as `codex-s81-svc3-native-top-drt-1123.service`.
- The full S81 candidate still needs native cell-site integration, die clock reservation replay, physical power connectivity and actual sending/receiving partition boundary timing. The aggregate boot budget of the current SVC3 collector path adds 11 status cycles and zero data cycles.
