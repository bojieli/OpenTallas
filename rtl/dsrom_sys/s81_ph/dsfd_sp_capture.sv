`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_sp_capture -- S81 die view top (CLAUDE S81-PH contract results/rtl/s81_ph_20261006/capture/contract.json).
// f_gather = the gather's t_capture (per root {fp32, row, pos, e, v} x 128 | control word {d159, v} | {live, busy,
// fault}); t_vm (serial domain) = per root {row1 {data32, addr19}, v1, row0 {data32, addr19}, v0} x 128 | status 64.  ck/rst stream, ckv/rsv serial.
// Every die input is captured in a flop at the pin; every die output is launched from a flop.
// ---------------------------------------------------------------------------------------------------------------
// CORE 2 (default, redesign pass 2026-10-06): the tiled capture ot_s81ph_cap_t (8 x dsfd_capt_grp + dsfd_capt_ctl,
// ot_s81ph_cap_tile.sv); the die places the tiles and this module is the composition reference.  CORE 0/1: the
// single-view cores (dsfd_sp_capture_v1).
`ifdef S81PH_CAP_CORE1
module dsfd_sp_capture #(parameter integer LD = 4, parameter integer CORE = 1) (
`elsif S81PH_CAP_SAFE
module dsfd_sp_capture #(parameter integer LD = 4, parameter integer CORE = 3) (
`else
module dsfd_sp_capture #(parameter integer LD = 4, parameter integer CORE = 2) (
`endif
    input wire [0:0] ck,
    input wire [0:0] rst,
    input wire [0:0] ckv,
    input wire [0:0] rsv,
    input wire [6946:0] f_gather,
    output wire [13375:0] t_vm
);
    generate if (CORE == 2 || CORE == 3) begin : g_t
        ot_s81ph_cap_t #(.SAFE(CORE == 3 ? 1 : 0), .NT(8), .LD(LD)) u_t (.ck(ck[0]), .rst(rst[0]), .ckv(ckv[0]), .rsv(rsv[0]),
            .f_gather(f_gather), .t_vm(t_vm));
    end else begin : g_v
        dsfd_sp_capture_v1 #(.LD(LD), .CORE(CORE)) u_v (.ck(ck), .rst(rst), .ckv(ckv), .rsv(rsv), .f_gather(f_gather),
            .t_vm(t_vm));
    end endgenerate
endmodule

module dsfd_sp_capture_v1 #(parameter integer LD = 4, parameter integer CORE = 1) (
    input wire [0:0] ck,
    input wire [0:0] rst,
    input wire [0:0] ckv,
    input wire [0:0] rsv,
    input wire [6946:0] f_gather,
    output wire [13375:0] t_vm
);
    localparam integer NR = 128;
    // reset synchronisers; rst_s[1] is the margin SDC's rst_mcp2 cell name (release allowed 2 cycles)
    reg [1:0] rst_s, rv_q;
    always @(posedge ck[0] or negedge rst[0]) if (!rst[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    always @(posedge ckv[0] or negedge rsv[0]) if (!rsv[0]) rv_q <= 2'b00; else rv_q <= {rv_q[0], 1'b1};
    wire rs_n = rst_s[1], rv_n = rv_q[1];
    // pin register: no reset (CORE 1: the core's own valid/state flops are reset; the gather's outputs are 0 one
    // cycle into reset, and reset is held >= 3 cycles)
    reg [6946:0] fq;
    generate if (CORE != 0) begin : g_fq
        always @(posedge ck[0]) fq <= f_gather;
    end else begin : g_fq0
        always @(posedge ck[0] or negedge rs_n) if (!rs_n) fq <= 6947'd0; else fq <= f_gather;
    end endgenerate
    wire [NR-1:0] rv; wire [NR*52-1:0] rd;
    genvar g;
    generate for (g = 0; g < NR; g = g + 1) begin : g_u
        assign rv[g] = fq[53*g];
        assign rd[52*g +: 52] = fq[53*g + 1 +: 52];
    end endgenerate
    wire [2*NR-1:0] wv; wire [NR*102-1:0] wd; wire [63:0] st;
    generate if (CORE != 0) begin : g_p
        // margin-first core (cap_m1 of the rd64 core: -3.0 ns post-CTS): ot_s81ph_cap_p
        ot_s81ph_cap_p #(.NR(NR), .LD(LD)) u_c (.clk(ck[0]), .rst_n(rs_n), .ckv(ckv[0]), .rsv_n(rv_n),
            .row_v(rv), .row_d(rd), .ctl_v(fq[6784]), .ctl_d(fq[6785 +: 159]), .g_fault(fq[6944]), .g_busy(fq[6945]),
            .g_live(fq[6946]), .w_v(wv), .w_d(wd), .st(st));
    end else begin : g_rd64
        ot_s81ph_capture #(.NR(NR), .LD(LD)) u_c (.clk(ck[0]), .rst_n(rs_n), .ckv(ckv[0]), .rsv_n(rv_n),
            .row_v(rv), .row_d(rd), .ctl_v(fq[6784]), .ctl_d(fq[6785 +: 159]), .g_fault(fq[6944]), .g_busy(fq[6945]),
            .g_live(fq[6946]), .w_v(wv), .w_d(wd), .st(st));
    end endgenerate
    generate for (g = 0; g < NR; g = g + 1) begin : g_o
        assign t_vm[104*g +: 104] = {wd[102*g + 51 +: 51], wv[2*g + 1], wd[102*g +: 51], wv[2*g]};
    end endgenerate
    assign t_vm[13312 +: 64] = st;
endmodule
