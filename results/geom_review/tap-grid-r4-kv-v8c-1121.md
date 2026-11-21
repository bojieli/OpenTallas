# KV v8c converge2 post-CTS geometry

Reviewed the exact retained `4_1_cts.odb` render in epyc7 scratch2 `claude/tap-grid-2130/v8c_conv/cts_failure_read/{layout,density}.png`. The four macro columns pinch the vertical center street. Placement heatmap shows the street from north edge to row two close to full and a crowded crossing between the middle joins. The 744,632-instance DB exceeds the renderer's connectivity threshold, so the PNG cannot establish individual tap or lane reach.

The existing post-hook `4_cts_final.rpt` gives TT −8483.95 ps and FF −690.25 ps. The worst TT path is `u_bound.u_pd8_i_pvw_u_ctl_cmd_1_t_10.r[6]` to its terminal `q`, both on `clk_t11`. Its final `net282621` wire contributes 6084.26 ps and 19.26 ns D slew. The run reports 568,597 non-tap cells against the 400k cap.

**FAIL.** Use the D28 split successor. The old control's layout and timing are retained as evidence.
