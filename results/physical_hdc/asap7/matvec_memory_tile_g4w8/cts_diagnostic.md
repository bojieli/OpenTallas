# G4/W8 Qwen tile: source-pinned CTS diagnostic

Source and differential RTL test commit:
`e1e7a00ad990fa469da8cded05877ce00c5e8652`. The run uses the reduced
32-lane matvec tile with two ROM, four KV SRAM and four vector SRAM proxy
macros, ASAP7 RVT TT, a 1.5 ns clock, a 320 ps transition limit, and 60%
slew-repair margin. It is a **CTS checkpoint**, not a full route signoff.

The default CTS log, metrics and timing report are retained in
`cts_default_artifacts/`. OpenROAD built a separate register clock tree for
42,084 register sinks, with 23–26 clock-buffer levels. Its critical ingress
flop clock arrives at approximately 1.49 ns. The worst setup endpoint is
`o_mask[7]`; the worst hold endpoint is `x_load_data_q[53]/D`. OpenROAD
explicitly reported that it could not repair all setup or hold paths.

The second record, `cts64.json`, comes from the same clean source commit with
`--cts-cluster-size 64 --pnr-stop-after cts`. This is a controlled change to
the clock sink cluster limit. OpenROAD still limited register clusters to 32
sinks based on buffer capacitance; the resulting tree remained 23–26 levels.

| Post-CTS, placement-estimated measure | Default | Requested cluster 64 |
| --- | ---: | ---: |
| Setup WNS | −419.212 ps | −419.212 ps |
| Hold WNS | −1,151.2 ps | −1,151.2 ps |
| Setup / hold violating endpoints | 1,464 / 1,527 | 1,464 / 1,527 |
| Inserted hold buffers | 4,809 | 4,809 |
| Setup / hold skew | 210.318 / 252.919 ps | 210.318 / 252.919 ps |
| Standard-cell area after CTS | 39,005.5 µm² | 39,005.5 µm² |
| Placement violations | 0 | 0 |
| Checkpoint acceptance | NOT_MET | NOT_MET |

The identical results show that this cluster-size knob did not change the
effective clock topology. The 4,809 buffers are a **failed hold-repair
checkpoint**, not a savings against the earlier W4/G2 tile, whose passing
route had 18,810 hold buffers. A full G4/W8 route is still being evaluated
separately. The analytical macro LEF/Liberty views and empty macro-internal
GDS remain model-grade; this checkpoint says nothing about full-core closure
or manufacturability.
