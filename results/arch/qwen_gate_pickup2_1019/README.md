# Qwen existing-gate pickup, 2026-10-19 12:43 PT

D2D SAFE5 is **not safe for release**. Both completed gates failed fill, and the independent actual post-CTS all-driver census now finds **268 non-clock roots above 32 loads** in each: 74 combinational (maximum491),194 flop (maximum194). Inputs2492/max10,macro548/max1,tie1425/max1. Kept140 kff and112 kffr instances do not certify their downstream transparent cones. The low-fill diagnostic cannot be waived into qualification. Preserve original FAIL; create a structural source successor before another route.

| Existing gate | TT setup ps | FF hold ps | TT/FF boundary spread ps | TT launch/capture ps | Fill | GRT |
|---|---:|---:|---|---|---|---|
| sf5 |131.034|13.124|69.9/64.0|121.834/100.715|22%|0 overflow|
| sf5w|140.957|28.836|39.2/35.8|114.663/82.291|25%|0 overflow|

Timing is a read-only post-CTS placement-RC diagnostic, at its own measured clock reference; it is not routed extraction or parent-neighbor qualification. FF uses the actual FF standard-cell and 64x137 macro libraries, not TT macro data. Native libraries and logical-pin rows are compressed here with SHA256 in timing summaries. Original gate source-binding manifests remain embedded in gate_result.json. Neither kit was modified or submitted. Probe fleet units2150275/2150294-1792438865 both exited0; ep5 was selected only for locality of the existing ODBs.

Worst native roots include `_30942_/Y`491, `u_core.g_eb[1].u_eb/q.../QN`194, `_37518_/Y`150 actual RESETN pins, `g_cal_seg_rx_k[0].../QN`71. The census follows native BUF/INV/HB outputs transparently, deduplicates terminal logical pins, includes every input/FF/comb/macro/tie driver, and excludes clock endpoints. Rows are uncapped. It directly queries ODB pin directions, without a sampled role filter or guessed macro-pin library parser.

## Checklist and remaining physical evidence

1. Registered I/O: explicit RTL PR=1; native timing model has zero combinational input/output arcs. Reset2 capture is claimed in source. Full source-to-native reset ancestry/first-use proof is not certified by this packet.
2. Reach: not certified. The README claim that345.6x216 alone guarantees405um Manhattan is insufficient. Exact stage-pair/pin geometry must be measured; no clock or data falsepath waiver.
3. Fanout: **FAIL268 roots**, including150-load reset. Source and physical copying require a full actual-netlist lineage proof, not module counts.
4. Depth: gate mapped490.1ps. Timing positive at placement RC, subject to structural repair and priced cycles.
5. Storage: four64x137 macros, one-kilobit calendar tables; ten-deep1-bit delay chains have only an existing prose waiver, no new owner waiver here.
6. Geometry: sf5 four macros on43.2um origins,57.912x45.672each, side229pins/0.192pitch claimed5.23/um; external3668 signal/clock pin geometries pass track access. Actual PG via/contact/OBS and macro lead electrical calibration are **not certified** here. sf5 outline345.6x216, sf5w388.8x172.8. Fill fails22/25%; North occupancy93/83% is a possible scoped pin-bound argument, conditional on complete native/parent fit. Parent slot/binding fit not supplied.
7. Clock: N center-fed, measured spreads pass, io_hold_margin0.03. Actual parent/neighbour reference/landed boundary and final routed electrical/contact/timing proof remain open. Max-slew/capacitance reports in the diagnostic logs have no printed violations; this does not supersede the explicit fanout failure.
8. Schedule: source equivalence200kcycles and real35-layer pair bench already committed in99cbdd49d lineage; current candidate claims0 addededges. Any source successor must preserve them or price schedule changes before building.

Floorplan PNGs were viewed by this collector and sent to ROOT for personal review; no REVIEW.json was authored. The existing placed sf5 layout is preserved for future exact geometry audit.

## Other collected jobs

SYSFACEbc2 andbc2c terminal synthesis2700s timeout, no layout, no textbook verdict. Logs are immutable evidence here. bc2l long-cap original remains LIVE on ep8 `/srv/opentallas-scratch/claude/ref_gate/qfd_sys_face_bc2l-20261019-114348`, advancing Yosys1_2 at12:39; no relaunch. The separate historical generic roundtrip ep7 PID3282231 also still consumesCPU; do not duplicate or discard it.

Native59 safe3/3b/3c original clients452733/452734/1087840 remain LIVE. At12:39 safe3 on ep7 global placement,3b ep7 resizing,3c ep6 global placement. Their zero-byte local logs are buffered, not dead jobs. safe3 and3b share005f source knownland45loads; diagnostic only unless actualnativeproof disproves that. Only3c uses56landcopies/source3c51edcae; uncapped source/actualnative/reset/readiness and currentrule checks must precede submit. Q-ready age20 remains uncertified. No native59 submission was attempted.
