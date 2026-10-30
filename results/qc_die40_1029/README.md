# DIE-QC-40 QC-001 native fixed-clock prebuild (2026-10-29 19:07-20:4x PDT)

Base: codex/qc-1847@7adc1c4aa (Codex QC 18:47-19:02, adopted collect-only). Geometry prebuild only: no GRT/CTS/STA, no sign-off/freeze claim.
Run root intel2:/srv/opentallas-scratch2/claude/die-qc40 (ot-run local, 64 GB/4 thr). Numbers from each prov_*/prebuild.json + diag_top.json [CHECKED].

| run | backbone | adapter | top conflicts | native census short/spacing | result |
|---|---|---|---|---|---|
| Codex N1 (prov_R7N1) | R7 | netaware | 233 | 18/6 | FAIL pin-access |
| Codex N2 (prov_R7N2) | R7 | + VIA78 minarea endcaps | 128 | 18/6 | FAIL pin-access |
| RN1J | backbone_native RN1 | indexed (0.032) | - | - | FAIL 18 no_clock_track (driver jog) |
| RN1cJ | RN1c | indexed | - | - | FAIL 283 no_clock_track |
| R7J | R7 | indexed (0.032) | 128 | 18/6 | = N2 (NATIVE_M7 clipped 0 windows) |
| R7F1 | R7 | indexed + F1 shield-aware provider pad, reserve all | - | - | FAIL 7 no_clock_track (trunk M8 y 11016.675) |
| R7F1b | R7 | F1, no pad reserve | 92 | 18/6 | shield class 108 -> 0; +72 M8 pad-vs-later-tree shorts |
| R7F1c | R7 | F1, reserve only moved pads | - | - | FAIL 7 no_clock_track (same trunks as R7F1) |

N2 128 residual classes: 108 = far provider M8 landing pad inside the OWN net's drawn VSS shield (48 nets; shield tie extension of a short same-net stub, e.g. ck_n12 stub 17673.18-17674.44 @11041.0, shield 17664.0-17682.3 @11041.36-.44, provider_clk_00244 pad @11041.316); 18 = clock-cell VIA78 pad vs adjacent-driver jog on the same M8 track (two drivers 0.43 um apart, opposite jogs, e.g. ck_b1162/ck_b329 @19743.0; 4 symmetric H-tree rows); 2 = root M9 vs VDD strap (x 17007.84).

backbone_native RN1 = R7 + 36 former default-window pins; the 89,144 shared records are byte-equal (backbone x, track y). The 36 new records give 0.95-um M7 windows for driver Y pins -> 18 driver jogs have no M8 track.

ROOT CAUSE of the 18/6 native census (CHECKED, all 24 rows): the backbone plan's M6 entry jog is never emitted. `router.stack_backbone_xy` is set by every adapter but has NO consumer in src_pc or origin/main (grep), so stacks/stair shapes stay at the actual pin x. Example ck_b3046/Y: backbone x 23959.136 (M6 jog 0.043, M7 23959.12-.152, 0.032 legal to native pin t_sl_E3_fw__clk M7 23959.184-.216) but the emitted riser is at the pin x 23959.179 (M7 23959.163-.195) -> 0.011-um overlap = real short. Codex 19:01 "legal 0.032" is true for the backbone plan, not for the emitted geometry. Fix (next): emit the M6 jog + VIA67 + M7 riser at backbone_xy in CR.stack_shapes AND CR.routed_tcl (die-local adapter patch), then rerun R7J.

F1b 72 new shorts = 12 nets ck_rn*_1 moved pads landing on the later ck_rn*_2 M8 trunk row (y ~11017.48); reserving them (F1/F1c) blocks those 7 trunks instead. Next F1 form: reserve the ck_rn*_2 trunk rows before far-provider landing selection (or move the pad away from both shield and trunk row).
