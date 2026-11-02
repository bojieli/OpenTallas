# Private SLE outline and pin-budget frontier

Source/data planning only. No GEN, CAD, P&R, STA, proof, physical qualification, source/profile adoption or West geometry alias. Each exact type is independently expanded and allocated. The finite candidate set is not a global geometric optimality certificate.

| Type | Regular std cells | Native regular std area | DATA / auxiliary contacts | Native interior clocks | Selected lattice frame | Nominal free-core fill | Peak /10um/layer |
|---|---:|---:|---:|---:|---|---:|---:|
| sle_stm_v1__cl27746664 | 224247 +4 ROM | 32911.8714 | 18799 / 212 | 71 | [319.68, 630.72] | 20.214962% | 69 WARN |

**sle_stm_v1__cl27746664** per-face DATA: `{'N': 3384, 'S': 1069, 'E': 6852, 'W': 7494}`; independent auxiliary census: `{'INTERIOR-M7': 76, 'N-M7': 12, 'E-M7': 33, 'S-M7': 8, 'INTERIOR-M5': 80, 'W-M7': 3}`. Original clock ports are `clk` and `clk_t1..70`. Frozen type clock metadata has two records, which is not the emitted native port count or a qualified load model.

Finite candidate frontier (target rate, frame, actual canonical peak, nominal free fill):
- 5.95: [336.96, 665.28], peak65/10um, fill17.799269%; fill/aspect FAIL.
- 6.0: [328.32, 656.64], peak66/10um, fill18.650087%; fill/aspect FAIL.
- 6.1: [328.32, 648.0], peak67/10um, fill18.946631%; fill/aspect FAIL.
- 6.25: [319.68, 639.36], peak69/10um, fill19.886706%; fill/aspect FAIL.
- 6.3: [319.68, 630.72], peak69/10um, fill20.214962%; fill/aspect PASS as arithmetic only.
- 6.5: [311.04, 613.44], peak71/10um, fill21.622785%; fill/aspect PASS as arithmetic only.
- 6.75: [302.4, 587.52], peak74/10um, fill23.614833%; fill/aspect PASS as arithmetic only.
- 7.0: [302.4, 570.24], peak77/10um, fill24.507453%; fill/aspect PASS as arithmetic only.

Selected per-face/per-layer exact sliding-window peaks:
- N-M4: 64 at [219.512, 229.512] um.
- N-M5: 66 at [11.0, 21.0] um.
- N-M6: 69 at [231.632, 241.632] um.
- N-M7: 66 at [56.976, 66.976] um.
- S-M5: 65 at [10.952, 20.952] um.
- S-M7: 69 at [13.456, 23.456] um.
- E-M4: 64 at [180.92, 190.92] um.
- E-M6: 69 at [17.552, 27.552] um.
- E-M7: 4 at [420.048, 430.048] um.
- W-M4: 64 at [50.264, 60.264] um.
- W-M6: 69 at [197.072, 207.072] um.
- W-M7: 2 at [387.28, 397.28] um.
| sle_stm_v2__cl55be2264 | 222702 +4 ROM | 32632.2999 | 18281 / 208 | 72 | [319.68, 630.72] | 20.043245% | 67 WARN |

**sle_stm_v2__cl55be2264** per-face DATA: `{'N': 3384, 'S': 1069, 'E': 6593, 'W': 7235}`; independent auxiliary census: `{'INTERIOR-M7': 76, 'N-M7': 12, 'E-M7': 31, 'S-M7': 8, 'INTERIOR-M5': 78, 'W-M7': 3}`. Original clock ports are `clk` and `clk_t1..71`. Frozen type clock metadata has two records, which is not the emitted native port count or a qualified load model.

Finite candidate frontier (target rate, frame, actual canonical peak, nominal free fill):
- 5.95: [319.68, 639.36], peak65/10um, fill19.717777%; fill/aspect FAIL.
- 6.0: [319.68, 639.36], peak66/10um, fill19.717777%; fill/aspect FAIL.
- 6.1: [319.68, 630.72], peak67/10um, fill20.043245%; fill/aspect PASS as arithmetic only.
- 6.25: [311.04, 613.44], peak69/10um, fill21.439109%; fill/aspect PASS as arithmetic only.
- 6.3: [302.4, 604.8], peak69/10um, fill22.591402%; fill/aspect PASS as arithmetic only.
- 6.5: [302.4, 587.52], peak71/10um, fill23.414235%; fill/aspect PASS as arithmetic only.
- 6.75: [302.4, 570.24], peak74/10um, fill24.299274%; fill/aspect PASS as arithmetic only.
- 7.0: [302.4, 552.96], peak77/10um, fill25.253847%; fill/aspect PASS as arithmetic only.

Selected per-face/per-layer exact sliding-window peaks:
- N-M4: 62 at [225.08, 235.08] um.
- N-M5: 63 at [6.728, 16.728] um.
- N-M6: 67 at [235.92, 245.92] um.
- N-M7: 67 at [13.456, 23.456] um.
- S-M5: 63 at [10.904, 20.904] um.
- S-M7: 67 at [19.728, 29.728] um.
- E-M4: 62 at [186.824, 196.824] um.
- E-M6: 67 at [58.832, 68.832] um.
- E-M7: 4 at [420.048, 430.048] um.
- W-M4: 62 at [51.608, 61.608] um.
- W-M6: 67 at [15.632, 25.632] um.
- W-M7: 2 at [387.28, 397.28] um.

The two selected candidates happen to have the same 319.68×630.72 frame after separate source/count/pin expansion: v1 target6.3 and v2 target6.1 yield different canonical windows and peaks69/67. This is not aliasing either native type. Next larger tested319.68×639.36 fails20% fill for both. Smaller alternatives trade higher local pin pressure for more free fill.

Arithmetic uses actual regular mapped ASAP7 area only: std_area / (((W−8.64)×(H−8.64))−4×121.848×62.952). Core inset4.32um each edge is a planning convention to be verified by any future actual GEN; old placed area including physical-only cells is never substituted. No assumed future clock/physical-only area credit. The v2 nominal margin above20% is only0.043245 percentage points.

Contact packing uses the unchanged canonical schema.pin_positions allocator and PART_PG_BANDS. Existing M4/M6 E/W and M5/M7 N/S contracts remain. Both end guards are core-rim4.32+extra2.16um; inter-bundle gap0.96um. A tiny flt_ctl_i window originally had zero usable M7 tracks; its interval is extended on the existing0.016um grid until canonical allocation succeeds. Scalar edge contacts retain face/layer and are separately assigned existing PG-free free tracks with contact-width clearance. All data/scalar allocations are PG-clear; no scalar failure. Six pins/um/layer is a WARN budget; the listed exact10um peaks are not disguised as a strict6 pass.

Native original interior auxiliary contacts remain UNALLOCATED in compact geometry: v1 76 interiorM7 (71clocks+arst_n/start_i/rst_o_0/start_o_0/cland_tstart_in) plus80M5; v2 76 interiorM7 (72clocks+arst_n/start_i/rst_o_0/start_o_0) plus78M5. No clock identity, insertion, source root/edge, reset topology or stage count is modified or qualified.

Render shows a candidate original2×2 ROM topology: spacing155.52×95.04um, dimensions121.848×62.952um, origin4.32-lattice plus native y-offset0.012. Selected common origins [21.6,237.612],[177.12,237.612],[21.6,332.652],[177.12,332.652]. All4.32halos fit; usable left/right streets12.96/12.072um, inter-column gap25.032um and inter-row gap23.448um. These are geometric openings, not proven escape/PG/channel or native consumer reach. Publication/capture/FT/collector/reset windows and parent context still require type-specific planning and owner review. No generic boundary register, new pipeline stage or cycle change.

Source source-normalized match evidence remains stm_capacity_reuse_packet1131.json. Retained original native io contacts are compressed below; closure source d90 PRE-D13 stays exact. Native ROM MIF/programme/asset qualification remains independently held. Parent may LOOK at this finite tradeoff; no PLACE is authorized by this packet.
