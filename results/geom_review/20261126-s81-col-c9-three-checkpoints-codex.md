# S81 COL-C9 retained physical review

Reviewed November 26, 2026. These three private kits retain the typed COL-C9 plan dictionary used by C10b. The review applies to the checkpoints below.

| Kit | Viewed checkpoint | Verdict | Measured placement issues |
| --- | --- | --- | --- |
| E11 `pv8ea75ee5` | Detailed placement, `3_place.odb` `cd6a1f9f6f43` | ISSUES, no route approval | North-edge density 95.3% at (689.3, 1218.4) µm. Worst aggregate T3-to-Y_XA span 809.5 µm. TT setup WNS −16.75 ps. |
| E11 `pv152ea348` | Detailed placement, `3_place.odb` `7b50bf024fce` | ISSUES, no route approval | North-edge density 95.6% at (719.3, 1218.4) µm. Worst aggregate T3-to-Y_XA span 810.1 µm. TT setup WNS −15.81 ps. |
| E9 `pvb2dac3cf` | Detailed placement, `3_place.odb` `ef0e70cb1bd7` | ISSUES, no route approval | Same rendered density and layout as E11 `pv152ea348`, with distinct checkpoint bytes. TT setup WNS −15.814 ps and TNS −312.451 ps. |
| E9 `pvb2dac3cf` | CTS, `4_cts.odb` `e42b7efdab1b` | BAD for further route promotion | Native FF worst hold −38.934 ps, with 323 residual input-to-register endpoints. The plotted TT hold diagnostic is −70.906 ps. |

All three detailed-placement layouts show large macro banks separated by mostly open logic aisles. The density images show the localized north-center boundary strip and small concentrations near the central and south stations. The retained measurements report zero opposing macro pin faces in all three, peak pin-track demand 0.160 and peak inter-macro channel demand 0.134. The worst measured channel is the 6.168 µm horizontal gap between `u_c9_4` and `u_c9_5`. The large T3-to-Y_XA measurement describes aggregate driver and sink spread. It is separate from the narrow north-edge hold cluster.

The E9 CTS path image draws the worst TT diagnostic hold paths as a small blue cluster near the north edge toward the west, separate from the north-center density maximum. The route watcher saw 3,237 overflow at GRT iteration 10. The later native log reached extra iteration 49/50 with missing-route diagnostics. That historical log tail carries no final GRT verdict. The CTS failure and GRT observation belong to the exact E9 run. The E11 checkpoints terminate at detailed placement.

The hold path attribution below traces the northwest boundary. Trace the T3-to-Y_XA links through their actual buffer segments before selecting a change for that class. Retain the current holds and require a fresh exact placement review for a revised kit.

## Artifacts

The common path on each listed host is `/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/private/S81-ALLFIX-INT`. The common generated kit prefix is `col_h9_r1__t1__cl49d7a23e__`.

- E11 `col_h9_r1__t1__cl49d7a23e__pv8ea75ee5_1125191156/gen/col_h9_r1__t1__cl49d7a23e__pv8ea75ee5/run/layout_review/place/{layout,density}.png`.
- E11 `col_h9_r1__t1__cl49d7a23e__pv152ea348_1125190641/gen/col_h9_r1__t1__cl49d7a23e__pv152ea348/run/layout_review/place/{layout,density}.png`. DP layout and density SHA prefixes `b56cd59abf82` and `219272c702db` also identify the E9 DP images.
- E9 `col_h9_r1__t1__cl49d7a23e__pvb2dac3cf_1124220314/gen/col_h9_r1__t1__cl49d7a23e__pvb2dac3cf`. CTS `smell_review/pregrt_ff_hold-1126-0016/{floorplan,density}.png` and `smell_review/5_1_grt-1126-0330/{paths.png,summary.txt}` both bind to `4_cts.odb`. Native GRT `run/logs/asap7/dp_col_h9_r1__t1__cl49d7a23e__pvb2dac3cf/base/5_1_grt.tmp.log`.

## Northwest hold path attribution

The rendered propagated-placement monitor uses **TT libraries for both setup and hold** (`stage_paths.txt`). Its −70.906 ps and 50 sampled violations are TT results. The native pre-GRT run uses FF libraries for hold and binds the virtual clock to 364.500 ps. It wrote the exact retained `4_cts.odb` after zero-overlap legalization (`pregrt_ff_hold.log`). The file `pregrt_ff_hold_open.tsv` has 323 residuals, all port-to-register: all 322 `frame_int_i0` bits and, separately, `arst_n` at −26.762 ps. FF frame residuals range from −38.934 ps on bit 6 to −22.867 ps on bit 186. There were zero residual same-tap, cross-tap and port-out paths. The native cross-tap worst-slack metric was +43.414 ps and TT setup WNS was +47.158 ps. Before internal repair, the native run saw 2,983 failing cross-tap, 73 same-tap and 1,009 port-out endpoints as well as the same 323 port-in endpoints.

The actual data source is the `fi_W1_p6_r2r1` frame, from `fW1_p6_b2 Y[321]` to `fW1_p6_b1`, with a seven-cycle frame budget and a three-cycle local pad after the receiving `u_bin_frame_int_i0` register. The retained bit 10 full-clock report traces the capture physically from `clk_t18`, through 14 BUFx4 tap-balance cells and four BUFx24 CTS stages, into `q[10]`. The tap-balance chain alone reaches 309.11 ps, and the reported pre-repair TT capture arrival is 460.71 ps (`4_cts_final.rpt`). The retained post-repair TT sampled path reports 471.126 ps capture, +12.500 ps inter-clock uncertainty and +18.379 ps library hold, for 502.005 ps required. Launch is a 450 ps ideal `vclk`, −40 ps input minimum and 21.100 ps receiver data flight, giving 431.100 ps arrival. Reported slack is −70.906 ps. All 50 sampled post-repair min paths start at `frame_int_i0` on `vclk`. The diagnostic witnesses a virtual-boundary launch and a physical capture tree. The native FF open-list gives the exact endpoint census and does not emit a capture-tap field for port paths.

The local FF repair deliberately excludes bulk input hold during repair, then restores the checks for reporting. The kit has the existing opt-in GRT measured-frame hold step, but its retained GRT log has no measured-frame bind receipt. The exact receiver timing establishes the required boundary min-time recovery. A closure decision needs the paired frame sender's early arrival and parent clock insertion at the seam, followed by a scoped receiver correction if that native check still fails. The retained data does not justify broad vclk changes or tap-to-tap hold padding.
