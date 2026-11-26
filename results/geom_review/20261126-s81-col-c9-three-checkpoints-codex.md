# S81 COL-C9 retained physical review

Reviewed November 26, 2026. These three private kits retain the typed COL-C9 plan dictionary used by C10b. The review applies to the checkpoints below.

| Kit | Viewed checkpoint | Verdict | Measured placement issues |
| --- | --- | --- | --- |
| E11 `pv8ea75ee5` | Detailed placement, `3_place.odb` `cd6a1f9f6f43` | ISSUES, no route approval | North-edge density 95.3% at (689.3, 1218.4) µm. Worst aggregate T3-to-Y_XA span 809.5 µm. TT setup WNS −16.75 ps. |
| E11 `pv152ea348` | Detailed placement, `3_place.odb` `7b50bf024fce` | ISSUES, no route approval | North-edge density 95.6% at (719.3, 1218.4) µm. Worst aggregate T3-to-Y_XA span 810.1 µm. TT setup WNS −15.81 ps. |
| E9 `pvb2dac3cf` | Detailed placement, `3_place.odb` `ef0e70cb1bd7` | ISSUES, no route approval | Same rendered density and layout as E11 `pv152ea348`, with distinct checkpoint bytes. TT setup WNS −15.814 ps and TNS −312.451 ps. |
| E9 `pvb2dac3cf` | CTS, `4_cts.odb` `e42b7efdab1b` | BAD for further route promotion | Propagated-placement FF worst hold −70.906 ps, with all 50 sampled hold paths negative. The worst sampled setup path is +34.470 ps. |

All three detailed-placement layouts show large macro banks separated by mostly open logic aisles. The density images show the localized north-center boundary strip and small concentrations near the central and south stations. The retained measurements report zero opposing macro pin faces in all three, peak pin-track demand 0.160 and peak inter-macro channel demand 0.134. The worst measured channel is the 6.168 µm horizontal gap between `u_c9_4` and `u_c9_5`. The large T3-to-Y_XA measurement describes aggregate driver and sink spread. It is separate from the narrow north-edge hold cluster.

The E9 CTS path image draws the worst FF paths as a small blue cluster near the north edge toward the west, separate from the north-center density maximum. The route watcher saw 3,237 overflow at GRT iteration 10. The later native log reached extra iteration 49/50 with missing-route diagnostics. That historical log tail carries no final GRT verdict. The CTS failure and GRT observation belong to the exact E9 run. The E11 checkpoints terminate at detailed placement.

Trace the north-edge FF endpoints through the clock and constraint boundary and trace the T3-to-Y_XA links through their actual buffer segments before selecting a form change. Retain the current holds and require a fresh exact placement review for a revised kit.

## Artifacts

The common path on each listed host is `/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT`. The common generated kit prefix is `col_h9_r1__t1__cl49d7a23e__`.

- E11 `col_h9_r1__t1__cl49d7a23e__pv8ea75ee5_1125191156/gen/col_h9_r1__t1__cl49d7a23e__pv8ea75ee5/run/layout_review/place/{layout,density}.png`.
- E11 `col_h9_r1__t1__cl49d7a23e__pv152ea348_1125190641/gen/col_h9_r1__t1__cl49d7a23e__pv152ea348/run/layout_review/place/{layout,density}.png`. DP layout and density SHA prefixes `b56cd59abf82` and `219272c702db` also identify the E9 DP images.
- E9 `col_h9_r1__t1__cl49d7a23e__pvb2dac3cf_1124220314/gen/col_h9_r1__t1__cl49d7a23e__pvb2dac3cf`. CTS `smell_review/pregrt_ff_hold-1126-0016/{floorplan,density}.png` and `smell_review/5_1_grt-1126-0330/{paths.png,summary.txt}` both bind to `4_cts.odb`. Native GRT `run/logs/asap7/dp_col_h9_r1__t1__cl49d7a23e__pvb2dac3cf/base/5_1_grt.tmp.log`.
