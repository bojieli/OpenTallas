`timescale 1ns/1ps
`default_nettype none
// Real result SRAM, metadata queue and issue credits; no row output flops.
module ot_hgi_qw_ovr #(
    parameter integer LQ = 16
) (
    input  wire          clk,
    input  wire          rst_n,
    // lane-group leaves
    // lane-group leaves, one port set a leaf row (each on the face toward its row; the write data has one kept copy a row)
    input  wire [7:0]        l_wcr0, l_wcr1, l_wcr2, l_wcr3,
    // control head
    input  wire              c_mw_v,
    input  wire [5:0]        c_mw_a,
    input  wire [14:0]       c_mw_sec,
    input  wire [2:0]        c_mw_n,
    input  wire              c_wg,        // control head: busy && write grant, registered
    output reg               d_wf,
    output reg               d_bad,
    // decoder tiles (parent level)
    input  wire              d_vo,
    input  wire              d_f,
    input  wire              d_df,
    input  wire [511:0]      d_y,
    output wire row_rst_n,
    output reg wm_v, output reg [14:0] wm_sec, output reg [2:0] wm_n,
    output wire [511:0] row_y
);
    localparam integer OD = 64, OW = 6;         // = SRAM words
    localparam integer CW = $clog2(LQ + 1);
    reg f_rst; always @(posedge clk) f_rst <= rst_n;
    wire [2:0] rr_n;                            // 0 control, 1 counters / relays, 2 decoder tiles
    ot_rst_relay #(.REGIONS(3)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    function automatic [31:0] lanes(input [4:0] l0, input [2:0] nn);
        lanes = 0;
        for (integer j = 0; j < 4; j = j + 1) if (j < nn) lanes[5'(l0 + j)] = 1'b1;
    endfunction
    // ---------------------------------------------------------------- seam RX from the control head
    reg wg_ok, mw_v; reg [OW-1:0] mw_a; reg [14:0] mw_sec; reg [2:0] mw_n;
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin wg_ok <= 0; mw_v <= 0; end
        else begin wg_ok <= c_wg; mw_v <= c_mw_v; end       // x_v = the one-head 'launch'
    always @(posedge clk) begin mw_a <= c_mw_a; mw_sec <= c_mw_sec; mw_n <= c_mw_n; end   // x_hd = gh[6]
    // ---------------------------------------------------------------- result capture, SRAM FIFO
    reg yc_v, yc_f, yc_df; reg [511:0] yc;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) begin yc_v <= 0; yc_f <= 0; yc_df <= 0; end
        else begin yc_v <= d_vo; yc_f <= d_vo && d_f; yc_df <= d_df; end
    always @(posedge clk) yc <= d_y;
    reg [14:0] mq_sec [0:OD-1]; reg [2:0] mq_n [0:OD-1];
    reg [31:0] mq_ln [0:OD-1];
    reg [OW-1:0] od_h, od_t; reg [OW:0] od_n;
    // write credits (take last cycle's hit vector)
    reg [31:0] ev_wcr, hit_w; reg [CW-1:0] wcr [0:31];
    always @(posedge clk or negedge rr_n[1])
        if (!rr_n[1]) begin ev_wcr <= 0; for (integer b = 0; b < 32; b = b + 1) wcr[b] <= LQ[CW-1:0]; end
        else begin
            ev_wcr <= {l_wcr3, l_wcr2, l_wcr1, l_wcr0};
            for (integer b = 0; b < 32; b = b + 1) wcr[b] <= wcr[b] + CW'(ev_wcr[b]) - CW'(hit_w[b]);
        end
    // write head lookahead: hd_* = meta of entry od_h, re-read every edge for the next od_h.  Exact: an entry counts in od_n
    // only after its gather/decode/capture pipeline (>= 5 edges after its meta write), so mq is settled when hd reads it.
    reg [14:0] hd_sec; reg [2:0] hd_n; reg [31:0] hd_ln;
    wire [14:0] w_sec0 = hd_sec; wire [2:0] w_n = hd_n;
    reg [31:0] w_ok_l;
    always @* for (integer b = 0; b < 32; b = b + 1) w_ok_l[b] = wcr[b] > CW'(hit_w[b]);
    wire w_cr_ok = &(~hd_ln | w_ok_l);
    wire w_fire = !d_bad && wg_ok && od_n != 0 && w_cr_ok;   // wg_ok implies busy
    // Independent current/next reads: fire selects after the read mux.
    wire [OW-1:0] od_next=od_h+1'b1;
    wire [14:0] cur_sec=mq_sec[od_h],next_sec=mq_sec[od_next];
    wire [2:0] cur_n=mq_n[od_h],next_n=mq_n[od_next];
    wire [31:0] cur_ln=mq_ln[od_h],next_ln=mq_ln[od_next];
    always @(posedge clk) begin
        hd_sec <= (cur_sec & {15{!w_fire}}) | (next_sec & {15{w_fire}});
        hd_n <= (cur_n & {3{!w_fire}}) | (next_n & {3{w_fire}});
        hd_ln <= (cur_ln & {32{!w_fire}}) | (next_ln & {32{w_fire}});
        if(mw_v)begin mq_sec[mw_a]<=mw_sec;mq_n[mw_a]<=mw_n;mq_ln[mw_a]<=lanes(mw_sec[4:0],mw_n);end
    end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin od_h <= 0; od_t <= 0; od_n <= 0; hit_w <= 0; d_bad <= 0; d_wf <= 0; end
        else begin
            hit_w <= w_fire ? hd_ln : 32'd0; d_wf <= w_fire;
            if (yc_v) begin od_t <= od_t + 1'b1; if (yc_f) d_bad <= 1'b1; end
            if (yc_df) d_bad <= 1'b1;
            od_n <= od_n + (OW+1)'(yc_v) - (OW+1)'(w_fire);
            if (w_fire) od_h <= od_h + 1'b1;
        end
    // registered SRAM read issue (next to u_od): rf_* = w_fire / od_h / head meta one edge later
    reg rf_v; reg [OW-1:0] rf_a; reg [14:0] rf_sec; reg [2:0] rf_n;
    always @(posedge clk) begin rf_a <= od_h; rf_sec <= w_sec0; rf_n <= w_n; end
    wire [511:0] od_rd;
    ot_sram_1r1w_64x512_m1_r2c2 u_od (.clk(clk), .r_ce_in(rf_v), .r_addr_in(rf_a), .rd_out(od_rd),
        .w_ce_in(yc_v), .w_addr_in(od_t), .wd_in(yc), .w_mask_in({512{1'b1}}),
        .rr_en(2'b00), .rr_addr(12'd0), .cr_en(2'b00), .cr_sel(18'd0));
    // Macro output and existing metadata stage -> four real row capture leaves.
    assign row_y=od_rd;
    assign row_rst_n=rr_n[1];
    always @(posedge clk)begin wm_sec<=rf_sec;wm_n<=rf_n;end
    always @(posedge clk or negedge rr_n[1])
        if(!rr_n[1])begin rf_v<=0;wm_v<=0;end
        else begin rf_v<=w_fire;wm_v<=rf_v;end
    initial if ((LQ & (LQ - 1)) != 0) $fatal(1, "ot_hgi_qw_ovd: LQ");
endmodule
`default_nettype wire
