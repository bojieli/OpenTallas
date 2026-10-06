// CLAUDE HBM-ABSTRACTS station primitives (tools/hbm_die_station_gen.py).  Default-off by construction: only the
// generated station views (physical/hbm_accel_die_views/stations/<master>/<master>.sv) instantiate them.

// forwarded pass-through slice: falling-edge capture of the received forwarded clock, clock forwarded inverted.
// FDLY kept inverter pairs delay the forwarded clock behind its data (source-synchronous centring): the slice
// launches on the received clock's falling edge and the next station captures half a period later on the falling
// edge of the clock sent here, so clock-to-out of the QN capture flop (+ output inverter and port buffer, ~226 ps
// routed SS) spends the whole T/2 - 0.2 T io budget - 60 ps uncertainty window (190 ps) unless the forwarded
// clock trails the data; the FF hold side of the same arc has ~470 ps to give.  OT_STN_FDLY overrides the default.
`ifndef OT_STN_FDLY
`define OT_STN_FDLY 0
`endif
module ot_hbm_stn_fwd #(parameter integer W = 512, parameter integer FDLY = `OT_STN_FDLY) (
    input wire fclk_i, input wire [W-1:0] d_i, output wire fclk_o, output wire [W-1:0] d_o);
    wire v_unused;
    wire fc0;
    ot_fwd_link_stage #(.W(W), .ENABLE(1)) u_stage (.fclk_i(fclk_i), .rst_n(1'b1), .i_v(1'b1), .i_d(d_i),
                                                    .fclk_o(fc0), .o_v(v_unused), .o_d(d_o));
    genvar k;
    generate for (k = 0; k < 2*FDLY; k = k + 1) begin : g_dly
        wire y;
        if (k == 0) begin : g_first
            ot_fwd_clk_inv u_dly (.a(fc0), .y(y));
        end else begin : g_next
            ot_fwd_clk_inv u_dly (.a(g_dly[k-1].y), .y(y));
        end
    end
    if (FDLY == 0) begin : g_direct
        assign fclk_o = fc0;
    end else begin : g_delayed
        assign fclk_o = g_dly[2*FDLY-1].y;
    end endgenerate
endmodule

// start a forwarded slice from the local clock: posedge registers, forwarded clock = ck through two kept inverters
// (the next station captures on its falling edge, half a period after this launch)
module ot_hbm_stn_launch #(parameter integer W = 512) (
    input wire ck, input wire [W-1:0] d_i, output wire fclk_o, output wire [W-1:0] d_o);
    reg [W-1:0] r;
    always @(posedge ck) r <= d_i;
    wire ckn;
    ot_fwd_clk_inv u_inv0 (.a(ck), .y(ckn));
    ot_fwd_clk_inv u_inv1 (.a(ckn), .y(fclk_o));
    assign d_o = r;
endmodule

// terminate a forwarded slice into ck: write on the forwarded clock's falling edge (kept inverter), mesochronous
// crossing ot_meso_fifo D4 (no backpressure on die links: w_v = r_rdy = 1)
module ot_hbm_stn_meso #(parameter integer W = 512) (
    input wire fclk_i, input wire [W-1:0] d_i, input wire ck, input wire rst_n, output wire [W-1:0] d_o);
    wire wclk;
    ot_fwd_clk_inv u_winv (.a(fclk_i), .y(wclk));
    wire w_rdy, r_v, w_live, r_live, w_fault, r_fault;
    ot_meso_fifo #(.W(W), .DEPTH(4), .OFFSET(2), .GUARD_LO(0), .GUARD_HI(4), .CREDITS(8), .ENABLE(1)) u_fifo (
        .wclk(wclk), .wrst_n(rst_n), .w_v(1'b1), .w_rdy(w_rdy), .w_d(d_i),
        .rclk(ck), .rrst_n(rst_n), .r_v(r_v), .r_rdy(1'b1), .r_d(d_o),
        .w_live(w_live), .r_live(r_live), .w_fault(w_fault), .r_fault(r_fault));
endmodule
