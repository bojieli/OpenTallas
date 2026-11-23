# COL ROM-in LAG diagnostic geometry review

Reviewed the two actual 3_place renders for col_h9_r1__t1__cl49d7a23e__pv0a45e191, R2L bind 808b37ec0b73, 3_5_place_dp.odb SHA1 290012e26db968d88cc0. Files are intel2:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/18a2688b741/private/OPUS-FIX-S81-COL-RANKSEAT-R2/col_h9_r1__t1__cl49d7a23e__pv0a45e191_1123060921/gen/col_h9_r1__t1__cl49d7a23e__pv0a45e191/run/layout_review/place/{layout,density}.png.

PASS for one CTS latch-to-ROM diagnostic. The ROM rows have continuous east-west spaces above and below the main arrays. The middle delay-cell columns leave north-south escapes on both sides, with small pockets at the southern I/O landing and the east-center n12 through n15 row. The two measured placement flags were 807.1 um fanout spread and 88.9% local density. Keep NO-LAG as the compose default until the ROM-in and ROM-out timing measurements support LAG.

The inherited finish spec continued at 08:21 with OT_PROBE_THROUGH. Its automatic geometry report stopped after the 600 s preview and measured 4,164 sinks on one tap, 645.73 µm worst register leg and vertical channel utilization 1.676. The finish continuation exceeds this CTS-only review. Keep it as historical diagnostic output and retain NO-LAG. A new finish requires a revised kit and a fresh exact review.
