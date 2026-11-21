// lockstep: ot_s81sl_xs (main, no define) vs ot_s81sl_xs_wc (OT_S81SL_XS_WCOPY); same random pins every edge;
// compares xw_v / xw_d / fault and all 24 macro write ports (w_ce, w_addr, wd, w_mask; data/mask only where w_ce).
module tb_s81sl_xs_wcopy (input wire clk, input wire rst_n, input wire [2:0] g_v, input wire [2:0] g_fam, input wire [20:0] g_idx,
              input wire [3071:0] g_d, input wire is_v, input wire [159:0] is_d, output reg [31:0] mism, output reg [31:0] wr_seen);
    wire xv0, xv1, f0, f1; wire [1100:0] xd0, xd1;
    ot_s81sl_xs    u0 (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d), .is_v(is_v), .is_d(is_d), .xw_v(xv0), .xw_d(xd0), .fault(f0));
    ot_s81sl_xs_wc u1 (.clk(clk), .rst_n(rst_n), .g_v(g_v), .g_fam(g_fam), .g_idx(g_idx), .g_d(g_d), .is_v(is_v), .is_d(is_d), .xw_v(xv1), .xw_d(xd1), .fault(f1));
    genvar s, m;
    wire [23:0] bad, we;
    for (s = 0; s < 3; s = s + 1) begin : g_s
        for (m = 0; m < 8; m = m + 1) begin : g_m
            wire e0 = u0.mw_e[s][m], e1 = u1.mw_e[s][m];
            assign we[8*s+m] = e0;
            assign bad[8*s+m] = (e0 != e1) || (e0 && (u0.mw_a[s][m] != u1.mw_a[s][m] || u0.mw_m[s][m] != u1.mw_m[s][m] ||
                                ((u0.mw_d[s][m] ^ u1.mw_d[s][m]) & u0.mw_m[s][m]) != 256'd0 || u0.mw_d[s][m] != u1.mw_d[s][m]));
        end
    end
    always @(posedge clk) begin
        if (rst_n) begin   // counters never reset (x-initial 0): they span every reset segment
            if (|bad || xv0 != xv1 || f0 != f1 || (xv0 && xd0 != xd1)) mism <= mism + 1;
            wr_seen <= wr_seen + $countones(we);
        end
    end
endmodule
