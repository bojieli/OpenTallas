# G4/W4 Qwen tile: source-pinned CTS diagnostic

Source and focused differential RTL test commit:
`152dc714`. This reduced 16-lane tile keeps the target's four matvec groups
and uses one ROM, four KV SRAM, and four vector SRAM proxy macros. The
independent bank-model test passed across two consecutive loaded addresses:
16 exact output slots of 16 lanes, nonzero data, ingress commits, and clean
drain. The W8 regression passed from the same source. Neither test is a full
Qwen token run.

The retained `cts_artifacts/` log, metrics, and timing report come from a
source-pinned ASAP7 RVT TT route with a 1.5 ns clock, 320 ps maximum
transition, and 60% slew-repair margin. The register clock tree has 22,856
sinks and 22–24 levels. OpenROAD inserted 17,478 hold buffers, then reported
that it could not repair all setup or hold paths. The worst setup endpoint is
`o_data[401]`; the worst hold endpoint is `x_load_data_q[57]/D`.

| Post-CTS, placement-estimated measure | G4/W4 | G4/W8 source-matched CTS |
| --- | ---: | ---: |
| Register clock sinks | 22,856 | 42,084 |
| Register clock depth | 22–24 | 23–26 |
| Setup WNS | −405.282 ps | −419.212 ps |
| Hold WNS | −643.935 ps | −1,151.2 ps |
| Inserted hold buffers | 17,478 | 4,809 |
| Standard-cell area after CTS | 23,039.2 µm² | 39,005.5 µm² |
| Placement violations | 0 | 0 |
| Checkpoint acceptance | **NOT_MET** | **NOT_MET** |

The buffer counts describe **incomplete repair attempts** and are not a
scaling-efficiency result. Halving the matvec lanes reduced clock sinks and
hold deficit but did not close timing at 1.5 ns. The full G4/W4 route is
being evaluated separately. Macro LEF/Liberty views are analytical proxies,
and macro GDS has no internal layout; no full-core or manufacturing claim
follows from this checkpoint.
