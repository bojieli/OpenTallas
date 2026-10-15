`timescale 1ns/1ps
// tb_mtp_lane_io (mtp-colllane-1011): one die's MTP side of tb_s81ph_coll_sys TB_MTP.  The head-die sequencer's
// transmitters (ot_dsrom_mtp_ltx, the sequencer's own link pair) send NTOK token-return flits, NSEED seeds and NACC
// accept events across the REAL hub chain into the slab (FWD stations forward, RET back: head631 + MTPL slab 9 / 9), and the
// far die's received token / seed reach two consumers (ot_dsrom_mtp_lrx_rtt over CF / CR stations) whose ready follows
// MSTALL.  Checks: every received token / seed / accept equals the partner die's sent stream, in order, nothing extra.
//   MSTALL 0 random stalls | 1 seed consumer stalled forever (HOL: tokens must still all arrive) | 2 both consumers
//   stalled forever (collective traffic must still complete, unchanged) | 3 no stalls (rate / class RTT) | 4 long
//   windows from cycle 1,200 (link up ~1,100; token to 15,000, seed to 20,000: class credits, receiver grants and
//   buffers run full)
module tb_mtp_relay #(parameter integer W = 1, parameter integer HOPS = 0) (
    input wire clk, rst_n, input wire [W-1:0] i, output wire [W-1:0] o);
    generate if (HOPS == 0) begin : g0 assign o = i; end
    else begin : gp
        reg [W-1:0] p [0:HOPS-1]; integer j;
        always @(posedge clk) begin
            if (!rst_n) for (j = 0; j < HOPS; j = j + 1) p[j] <= '0;
            else begin p[0] <= i; for (j = 1; j < HOPS; j = j + 1) p[j] <= p[j-1]; end
        end
        assign o = p[HOPS-1];
    end endgenerate
endmodule

module tb_mtp_lane_io #(parameter integer DIE = 0, parameter integer NTOK = 300, parameter integer NSEED = 80,
                        parameter integer NACC = 24, parameter integer MSTALL = 0, parameter integer FWD = 9,
                        parameter integer RET = 9, parameter integer CF = 5, parameter integer CR = 5,
                        parameter integer TGAP = 0) (
    input  wire          clk, rst_n,
    input  wire [31:0]   cyc,
    output wire [647:0]  f_mtp,
    input  wire [1:0]    t_mtp,
    input  wire [512:0]  t_mrt,
    output wire          f_mrt,
    input  wire [77:0]   t_mrs,
    output wire          f_mrs,
    input  wire [56:0]   t_macc,
    output integer       tok_rx, seed_rx, acc_rx, tok_tx, seed_tx, acc_tx, errs,
    output integer       tok_first_tx, tok_first_rx, tok_last_rx, tok_mid_rx
);
    localparam integer SW = 77, AW = 57, PEER = DIE ^ 1;
    function automatic [511:0] tok(input integer die, input integer n);
        integer k; begin for (k = 0; k < 16; k = k + 1) tok[32*k +: 32] = (32'h9e3779b9 * (n + 1)) ^ (32'h01010101 * k) ^ (32'h7f4a7c15 * (die + 1)); end
    endfunction
    function automatic [SW-1:0] seed(input integer die, input integer n);
        reg [95:0] w; begin w = {32'hc2b2ae35 * (n + 3), 32'h85ebca6b * (n + 7) ^ die, 32'h27d4eb2f * (die + n + 1)}; seed = w[SW-1:0]; end
    endfunction
    function automatic [AW-1:0] accw(input integer die, input integer n);
        reg [63:0] w; begin w = {32'h165667b1 * (n + 5), 32'hd3a2646c ^ (n * 977 + die)}; accw = {1'b0, 1'b1, w[AW-3:0]}; end
    endfunction
    // ---------------- sender side: the sequencer's ltx pair, FWD / RET stations
    // TGAP > 0: the sequencer's fastest emission -- valid held until granted, at most one token per TGAP cycles
    integer last_t = -1000;
    wire tv_c = rst_n && tok_tx < NTOK && (TGAP == 0 ? (cyc % 97) < 70 : (cyc - last_t) >= TGAP);
    wire sv_c = rst_n && seed_tx < NSEED && (cyc % 53) < 12;
    wire tr_c, sr_c, tl_v, sl_v, tg_l, sg_l; wire [511:0] tl_d; wire [SW-1:0] sl_d;
    ot_dsrom_mtp_ltx #(.W(512)) u_tt (.clk(clk), .rst_n(rst_n), .c_valid(tv_c), .c_ready(tr_c), .c_data(tok(DIE, tok_tx)),
        .l_valid(tl_v), .l_ready(tg_l), .l_data(tl_d));
    ot_dsrom_mtp_ltx #(.W(SW)) u_ts (.clk(clk), .rst_n(rst_n), .c_valid(sv_c), .c_ready(sr_c), .c_data(seed(DIE, seed_tx)),
        .l_valid(sl_v), .l_ready(sg_l), .l_data(sl_d));
    reg [AW-1:0] acc_q;
    wire acc_go = rst_n && acc_tx < NACC && cyc > 200 && (cyc % 307) == 11;
    always @(posedge clk) acc_q <= acc_go ? accw(DIE, acc_tx) : {AW{1'b0}};
    tb_mtp_relay #(.W(1 + 512 + 1 + SW + AW), .HOPS(FWD)) u_f (.clk(clk), .rst_n(rst_n), .i({acc_q, sl_d, sl_v, tl_d, tl_v}), .o(f_mtp));
    tb_mtp_relay #(.W(2), .HOPS(RET)) u_r (.clk(clk), .rst_n(rst_n), .i(t_mtp), .o({sg_l, tg_l}));
    // ---------------- receiver side: consumers over CF / CR stations
    wire rt_v, rs_v, rt_g, rs_g, ct_v, cs_v; wire [511:0] rt_d, ct_d; wire [SW-1:0] rs_d, cs_d;
    reg ct_r, cs_r;
    tb_mtp_relay #(.W(513), .HOPS(CF)) u_cf (.clk(clk), .rst_n(rst_n), .i(t_mrt), .o({rt_d, rt_v}));
    tb_mtp_relay #(.W(78), .HOPS(CF)) u_sf (.clk(clk), .rst_n(rst_n), .i(t_mrs), .o({rs_d, rs_v}));
    tb_mtp_relay #(.W(2), .HOPS(CR)) u_cr (.clk(clk), .rst_n(rst_n), .i({rs_g, rt_g}), .o({f_mrs, f_mrt}));
    ot_dsrom_mtp_lrx_rtt #(.W(512), .D(CF + CR + 4), .ENABLE_RTT(1), .FORWARD_HOPS(CF), .RETURN_HOPS(CR)) u_ct (
        .clk(clk), .rst_n(rst_n), .l_valid(rt_v), .l_ready(rt_g), .l_data(rt_d), .c_valid(ct_v), .c_ready(ct_r), .c_data(ct_d));
    ot_dsrom_mtp_lrx_rtt #(.W(SW), .D(CF + CR + 4), .ENABLE_RTT(1), .FORWARD_HOPS(CF), .RETURN_HOPS(CR)) u_cs (
        .clk(clk), .rst_n(rst_n), .l_valid(rs_v), .l_ready(rs_g), .l_data(rs_d), .c_valid(cs_v), .c_ready(cs_r), .c_data(cs_d));
    always @(negedge clk) begin
        case (MSTALL)
            1: begin ct_r = (cyc % 7) != 0; cs_r = 1'b0; end
            2: begin ct_r = 1'b0; cs_r = 1'b0; end
            3: begin ct_r = 1'b1; cs_r = 1'b1; end
            4: begin ct_r = !(cyc >= 1200 && cyc < 15000) && (cyc % 7) != 0; cs_r = !(cyc >= 1200 && cyc < 20000) && (cyc % 5) != 0; end
            default: begin ct_r = (cyc % 7) != 0 && !((cyc % 500) >= 400); cs_r = (cyc % 5) != 0 && !((cyc % 700) >= 500); end
        endcase
    end
    initial begin tok_rx = 0; seed_rx = 0; acc_rx = 0; tok_tx = 0; seed_tx = 0; acc_tx = 0; errs = 0;
                  tok_first_tx = -1; tok_first_rx = -1; tok_last_rx = -1; tok_mid_rx = -1; end
    always @(posedge clk) if (rst_n) begin
        if (tv_c && tr_c) begin if (tok_first_tx < 0) tok_first_tx <= cyc; tok_tx <= tok_tx + 1; last_t <= cyc; end
        if (sv_c && sr_c) seed_tx <= seed_tx + 1;
        if (acc_go) acc_tx <= acc_tx + 1;
        if (ct_v && ct_r) begin
            if (tok_rx >= NTOK || ct_d !== tok(PEER, tok_rx)) begin errs = errs + 1; if (errs < 10) $display("MTP DIE %0d token %0d mismatch", DIE, tok_rx); end
            if (tok_first_rx < 0) tok_first_rx = cyc;
            tok_last_rx = cyc; tok_rx = tok_rx + 1;
            if (tok_rx == NTOK / 2) tok_mid_rx = cyc;
        end
        if (cs_v && cs_r) begin
            if (seed_rx >= NSEED || cs_d !== seed(PEER, seed_rx)) begin errs = errs + 1; if (errs < 10) $display("MTP DIE %0d seed %0d mismatch", DIE, seed_rx); end
            seed_rx = seed_rx + 1;
        end
        if (t_macc[AW-1]) begin errs = errs + 1; if (errs < 10) $display("MTP DIE %0d lane / adapter FAULT", DIE); end
        if (t_macc[AW-2]) begin
            if (acc_rx >= NACC || t_macc !== accw(PEER, acc_rx)) begin errs = errs + 1; if (errs < 10) $display("MTP DIE %0d accept %0d mismatch", DIE, acc_rx); end
            acc_rx = acc_rx + 1;
        end
    end
endmodule
