`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// KV-BIND5-OBS 10-19: HOST observation window = the real reader of the KV-die HOST root's observation-only outputs
// (bind v2 OUTPUT_OPEN class c: hc / marker / issued / landed / participant_* / program_auth_* / admission certificates,
// the host fault / abort levels) and of the die observation outputs dcal adm_done / cal_ready / running / layer and the
// D2D end's recovery_cycles.
//
// Placement: between the HOST AXI4-Lite packet master (u_packet.u_axi, the ot_host_if handshake: ONE transaction at a
// time) and the control CSR slave (u_control, qkd_host_sys_csr_service) inside qkd_host_control_packet_admission.  Every
// address outside the window passes through unchanged (combinational, as the CSR's own [12] split); the window is the
// unused part of the CSR's 4 KB system region:
//   0x1800  OBS_CTRL  W: [0] CAPTURE (snapshot every obs bit + the sticky flt vector in one edge)
//                        [1] CLEAR   (sticky fault vector <- current levels; never masks a still-active fault)
//                     R: {8'h0B, 8'(NW), 16'(capture count)}
//   0x1804  OBS_NB    R: {16'(NF), 16'(NB)}
//   0x1900 + 4 i      R: shadow word i, i < NW = ceil((NB + NF) / 32): bits [NB-1:0] = live obs, [NB +: NF] = sticky flt
//   (other window addresses read 0, writes are accepted and ignored: AXI-Lite OKAY, as the CSR's default)
// Storage: the obs pin registers ARE the snapshot (load-enable = the registered CAPTURE, replicated per 32-bit slice:
// one flop per observed bit, no second bank; the snapshot is the obs value 1 edge after the OBS_CTRL write);
// flt has a live pin register, the sticky vector and its snapshot (3 flops per fault bit).
// Static timing (no runtime stall on any token path: this is the off-die HOST boundary, where the AXI handshake is the
// existing protocol): the snapshot is taken on the CAPTURE write edge (obs: the pin value; flt: sticky | live pin reg), a window read returns its data a FIXED 3 edges after the AR handshake (idx register -> 8 registered
// 8:1 group muxes -> registered 8:1 -> R).  Off the token schedule: no die calendar edge, no STATUS edge (STATUS 1989 of
// 1998 unchanged); the HOST CSR read of a window word costs 4 ck_csr edges vs 2 for a CSR register.
// MUT (bench only): 1 capture never loads the shadow, 2 window read returns word i+1, 3 flt not sticky (live level),
//                   4 pass-through read data replaced by the window mux (reads of the CSR break)
// ---------------------------------------------------------------------------------------------------------------------
module qkd_host_obs_csr #(
    parameter integer NB = 64,
    parameter integer NF = 8,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [NB-1:0] obs,
    input  wire [NF-1:0] flt,
    // upstream: from the packet AXI master
    input  wire          u_awvalid, output wire u_awready, input wire [12:0] u_awaddr,
    input  wire          u_wvalid,  output wire u_wready,  input wire [31:0] u_wdata, input wire [3:0] u_wstrb,
    output wire          u_bvalid,  input  wire u_bready,  output wire [1:0] u_bresp,
    input  wire          u_arvalid, output wire u_arready, input wire [12:0] u_araddr,
    output wire          u_rvalid,  input  wire u_rready,  output wire [31:0] u_rdata, output wire [1:0] u_rresp,
    // downstream: to the CSR slave
    output wire          d_awvalid, input  wire d_awready, output wire [12:0] d_awaddr,
    output wire          d_wvalid,  input  wire d_wready,  output wire [31:0] d_wdata, output wire [3:0] d_wstrb,
    input  wire          d_bvalid,  output wire d_bready,  input  wire [1:0] d_bresp,
    output wire          d_arvalid, input  wire d_arready, output wire [12:0] d_araddr,
    input  wire          d_rvalid,  output wire d_rready,  input  wire [31:0] d_rdata, input wire [1:0] d_rresp
);
    localparam integer NT = NB + NF;
    localparam integer NW = (NT + 31) / 32;
    localparam integer NWP = 64;                         // padded to 8 groups x 8 words
    initial if (NW > NWP || NB < 1 || NF < 1) $fatal(1, "qkd_host_obs_csr: NB + NF must fit 64 words");

    // ---- pin registers + sticky fault vector
    reg [NB-1:0] obs_q;                                  // pin register = snapshot (enable CAPTURE)
    reg [NF-1:0] flt_q, flt_st, flt_snap;
    reg [15:0]   ncap;
    wire [NWP*32-1:0] shadow = {{(NWP*32-NT){1'b0}}, flt_snap, obs_q};
    // ---- window decode
    wire aw_win = u_awaddr[12] && u_awaddr[11:9] == 3'b100;
    wire ar_win = u_araddr[12] && u_araddr[11:9] == 3'b100;
    reg  o_bvalid, o_rvalid, rd_busy, d_rpend, d_wpend;
    reg  [2:0] rd_ph;                                     // 3-edge fixed read pipeline
    reg  [31:0] o_rdata;
    reg  alive;
    always @(posedge clk or negedge rst_n) if (!rst_n) alive <= 1'b0; else alive <= 1'b1;
    // a window transaction starts only with no pass-through transaction outstanding (and vice versa): one at a time
    wire o_wr_go = alive && u_awvalid && u_wvalid && aw_win && !o_bvalid && !d_wpend;
    wire o_rd_go = alive && u_arvalid && ar_win && !o_rvalid && !rd_busy && !d_rpend;
    assign d_awvalid = u_awvalid && !aw_win && !o_bvalid;
    assign d_wvalid  = u_wvalid && !aw_win && !o_bvalid;
    assign d_awaddr  = u_awaddr;
    assign d_wdata   = u_wdata;
    assign d_wstrb   = u_wstrb;
    assign d_bready  = u_bready;
    assign d_arvalid = u_arvalid && !ar_win && !o_rvalid && !rd_busy;
    assign d_araddr  = u_araddr;
    assign d_rready  = u_rready;
    assign u_awready = aw_win ? o_wr_go : (d_awready && !o_bvalid);
    assign u_wready  = aw_win ? o_wr_go : (d_wready && !o_bvalid);
    assign u_bvalid  = o_bvalid | d_bvalid;
    assign u_bresp   = o_bvalid ? 2'b00 : d_bresp;
    assign u_arready = ar_win ? o_rd_go : (d_arready && !o_rvalid && !rd_busy);
    assign u_rvalid  = o_rvalid | d_rvalid;
    assign u_rdata   = (MUT == 4) ? o_rdata : (o_rvalid ? o_rdata : d_rdata);
    assign u_rresp   = o_rvalid ? 2'b00 : d_rresp;

    wire wr_ctrl = o_wr_go && u_awaddr[8:2] == 7'd0 && u_wstrb[0];
    wire cap = wr_ctrl && u_wdata[0];
    wire clr = wr_ctrl && u_wdata[1];
    // CAPTURE / CLEAR are registered once and the capture enable is REPLICATED per 32-bit slice (kept copies: each
    // drives <= 32 snapshot flops; SAFE-DESIGN 3): the snapshot is taken 1 edge after the OBS_CTRL write handshake
    localparam integer NCP = (NT + 31) / 32;
    (* keep = 1, dont_touch = 1 *) reg [NCP-1:0] cap_q;
    reg clr_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            cap_q <= 0; clr_q <= 0; flt_q <= 0; flt_st <= 0; ncap <= 0;
        end else begin
            cap_q <= {NCP{cap && MUT != 1}};
            clr_q <= clr;
            flt_q <= flt;
            flt_st <= (MUT == 3) ? flt_q : (clr_q ? flt_q : (flt_st | flt_q));
            if (cap) ncap <= ncap + 16'd1;
        end
    genvar gc;
    generate for (gc = 0; gc < NT; gc = gc + 1) begin : g_snap
        if (gc < NB) begin : g_o
            always @(posedge clk or negedge rst_n)
                if (!rst_n) obs_q[gc] <= 1'b0; else if (cap_q[gc / 32]) obs_q[gc] <= obs[gc];
        end else begin : g_f
            always @(posedge clk or negedge rst_n)
                if (!rst_n) flt_snap[gc - NB] <= 1'b0;
                else if (cap_q[gc / 32]) flt_snap[gc - NB] <= (MUT == 3) ? flt_q[gc - NB] : (flt_st[gc - NB] | flt_q[gc - NB]);
        end
    end endgenerate

    // ---- fixed 3-edge window read pipeline (kept per-group select copies: <= 32 selects per copy register)
    reg  [6:0] idx_r;                                    // [6] = data region (0x1900+), [5:0] word
    (* keep = 1, dont_touch = 1 *) reg [2:0] wsel_g0, wsel_g1, wsel_g2, wsel_g3, wsel_g4, wsel_g5, wsel_g6, wsel_g7;
    reg  [2:0] gsel_r;
    reg        data_r;
    reg  [31:0] grp_r [0:7];
    reg  [31:0] ctl_r;
    wire [6:0] idx_in = {u_araddr[8], u_araddr[7:2] + ((MUT == 2) ? 6'd1 : 6'd0)};
    function [31:0] wsel(input [2:0] s, input [2:0] g);
        wsel = shadow[32 * (8 * g + s) +: 32];
    endfunction
    integer gi;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            idx_r <= 0; rd_ph <= 0; rd_busy <= 0; o_rvalid <= 0; o_rdata <= 0; o_bvalid <= 0;
            gsel_r <= 0; data_r <= 0; ctl_r <= 0; d_rpend <= 0; d_wpend <= 0;
            wsel_g0 <= 0; wsel_g1 <= 0; wsel_g2 <= 0; wsel_g3 <= 0; wsel_g4 <= 0; wsel_g5 <= 0; wsel_g6 <= 0; wsel_g7 <= 0;
            for (gi = 0; gi < 8; gi = gi + 1) grp_r[gi] <= 0;
        end else begin
            // pass-through outstanding trackers (one transaction at a time on each channel)
            if (d_arvalid && d_arready) d_rpend <= 1'b1;
            if (d_rvalid && d_rready) d_rpend <= 1'b0;
            if (d_awvalid && d_awready) d_wpend <= 1'b1;
            if (d_bvalid && d_bready) d_wpend <= 1'b0;
            if (o_bvalid && u_bready) o_bvalid <= 1'b0;
            if (o_wr_go) o_bvalid <= 1'b1;
            if (o_rvalid && u_rready) o_rvalid <= 1'b0;
            rd_ph <= {rd_ph[1:0], o_rd_go};
            if (o_rd_go) begin
                rd_busy <= 1'b1; idx_r <= idx_in;
                {wsel_g0, wsel_g1, wsel_g2, wsel_g3} <= {4{idx_in[2:0]}};
                {wsel_g4, wsel_g5, wsel_g6, wsel_g7} <= {4{idx_in[2:0]}};
            end
            // edge 2: eight registered 8:1 group muxes + the control-register word
            grp_r[0] <= wsel(wsel_g0, 3'd0); grp_r[1] <= wsel(wsel_g1, 3'd1);
            grp_r[2] <= wsel(wsel_g2, 3'd2); grp_r[3] <= wsel(wsel_g3, 3'd3);
            grp_r[4] <= wsel(wsel_g4, 3'd4); grp_r[5] <= wsel(wsel_g5, 3'd5);
            grp_r[6] <= wsel(wsel_g6, 3'd6); grp_r[7] <= wsel(wsel_g7, 3'd7);
            gsel_r <= idx_r[5:3]; data_r <= idx_r[6];
            ctl_r <= (idx_r[5:0] == 6'd0) ? {8'h0B, 8'(NW), ncap} :
                     (idx_r[5:0] == 6'd1) ? {16'(NF), 16'(NB)} : 32'd0;
            // edge 3: registered final 8:1 -> R
            if (rd_ph[1]) begin
                o_rvalid <= 1'b1; rd_busy <= 1'b0;
                o_rdata <= data_r ? grp_r[gsel_r] : ctl_r;
            end
        end
endmodule
