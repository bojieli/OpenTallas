// CLAUDE HBM-ABSTRACTS station primitives (tools/hbm_die_station_gen.py).  Default-off by construction: only the
// generated station views (physical/hbm_accel_die_views/stations/<master>/<master>.sv) instantiate them.

// forwarded pass-through slice: falling-edge capture of the received forwarded clock, clock forwarded inverted.
// FDLY kept inverter pairs delay the forwarded clock behind its data (source-synchronous centring): the slice
// launches on the received clock's falling edge and the next station captures half a period later on the falling
// edge of the clock sent here, so clock-to-out of the QN capture flop (+ output inverter and port buffer, ~226 ps
// routed SS) spends the whole T/2 - 0.2 T io budget - 60 ps uncertainty window (190 ps) unless the forwarded
// clock trails the data; the FF hold side of the same arc has ~470 ps to give.  Measured on the worst r1 view
// hfd_stn_r21 (SS setup, routed): FDLY 0 -28.34 ps, 1 +7.54 ps, 2 +21.73 ps, 3 +35.18 ps (FF hold 478 ps throughout);
// default 6 under the owner margin rule (accept SS >= +40 ps at 833.333 after an over-constrained route; ~13.7 ps a
// pair, the worst FDLY 2 view hfd_stn_r3 was +3.3 ps).
// OT_STN_FDLY overrides the default.
`ifndef OT_STN_FDLY
`define OT_STN_FDLY 6
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
// (the next station captures on its falling edge, half a period after this launch).  LDLY further kept inverter
// pairs make the forwarded clock trail its data as FDLY does for a forward slice (launch clock-to-out of the QN
// register spends the T/2 window: routed hfd_gath_r24 SS +25.16 ps at LDLY 0); default 3 under the margin rule.
`ifndef OT_STN_LDLY
`define OT_STN_LDLY 3
`endif
module ot_hbm_stn_launch #(parameter integer W = 512, parameter integer LDLY = `OT_STN_LDLY) (
    input wire ck, input wire [W-1:0] d_i, output wire fclk_o, output wire [W-1:0] d_o);
    reg [W-1:0] r;
    always @(posedge ck) r <= d_i;
    wire ckn, ck2;
    ot_fwd_clk_inv u_inv0 (.a(ck), .y(ckn));
    ot_fwd_clk_inv u_inv1 (.a(ckn), .y(ck2));
    genvar k;
    generate for (k = 0; k < 2*LDLY; k = k + 1) begin : g_dly
        wire y;
        if (k == 0) begin : g_first
            ot_fwd_clk_inv u_dly (.a(ck2), .y(y));
        end else begin : g_next
            ot_fwd_clk_inv u_dly (.a(g_dly[k-1].y), .y(y));
        end
    end
    if (LDLY == 0) begin : g_direct
        assign fclk_o = ck2;
    end else begin : g_delayed
        assign fclk_o = g_dly[2*LDLY-1].y;
    end endgenerate
    assign d_o = r;
endmodule

// terminate a forwarded slice into ck: write on the forwarded clock's falling edge (kept inverter), mesochronous
// crossing ot_meso_fifo D4 (no backpressure on die links: w_v = r_rdy = 1).  ot_meso_fifo takes wrst_n synchronous
// to wclk and rrst_n synchronous to rclk, so the station's one quasi-static rst_n is resynchronised into each domain
// (two flops each); its DOWN/ALIGN/READY/RUN handshake already tolerates any release order between the two sides.
// Without this the single rst terminal fans out to every flop of both domains under the 0.2 T input budget and,
// into the write side, under the 356.667 ps crossing bound (measured r2_hfd_meso_r32: SS -214.6 ps on rst).
// RI=1 (generator --margin): the slice is captured at the face pins on the write clock before the FIFO (+1 cycle), so
// the FIFO's own crossing no longer shares its placement with the pin-to-FIFO wire.  RDREG=1 (--margin): ot_meso_fifo
// registers its data-ring readout next to the one-hot select (+1 cycle), so the crossing arc ends at that flop.
// NOBP=1 (--margin): a station never back-pressures (r_rdy = 1), so the FIFO's receive buffer and its W-wide output
// select (a 512-load control net: M1_hfd_meso_r1 SS +38.1 ps) go; same latency.  The no-backpressure invariant
// is enforced here: the FIFO's r_rdy is tied 1'b1 below (ot_meso_fifo NOBP comment has the argument).  CRDREG=1
// (--margin): the credit-ring readout is registered too (N1_hfd_meso_r32: credit crossing SS +35.0 ps).
module ot_hbm_stn_meso #(parameter integer W = 512, parameter integer RI = 0, parameter integer RDREG = 0, parameter integer NOBP = 0, parameter integer CRDREG = 0) (
    input wire fclk_i, input wire [W-1:0] d_i, input wire ck, input wire rst_n, output wire [W-1:0] d_o);
    wire wclk;
    ot_fwd_clk_inv u_winv (.a(fclk_i), .y(wclk));
    wire [W-1:0] w_d;
    generate if (RI) begin : g_ri
        reg [W-1:0] ri;
        always @(posedge wclk) ri <= d_i;
        assign w_d = ri;
    end else begin : g_direct
        assign w_d = d_i;
    end endgenerate
    reg [1:0] wrs, rrs;
    always @(posedge wclk) wrs <= {wrs[0], rst_n};
    always @(posedge ck) rrs <= {rrs[0], rst_n};
    wire w_rdy, r_v, w_live, r_live, w_fault, r_fault;
    ot_meso_fifo #(.W(W), .DEPTH(4), .OFFSET(2), .GUARD_LO(0), .GUARD_HI(4), .CREDITS(8), .ENABLE(1), .RDREG(RDREG), .NOBP(NOBP), .CRDREG(CRDREG)) u_fifo (
        .wclk(wclk), .wrst_n(wrs[1]), .w_v(1'b1), .w_rdy(w_rdy), .w_d(w_d),
        .rclk(ck), .rrst_n(rrs[1]), .r_v(r_v), .r_rdy(1'b1), .r_d(d_o),
        .w_live(w_live), .r_live(r_live), .w_fault(w_fault), .r_fault(r_fault));
endmodule
