`timescale 1ns/1ps
// Explicit opt-in physical top: native SRAM staging, identical external cycles.
module dsdv_rowx_xm_sram #(parameter integer MUT = 0, parameter integer D = 16) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          cfg_v,
    input  wire [63:0]   cfg_d,          // [3:0] POS [4] head [5] tail [6] HB [22:7] XOFF [38:23] BC_OFF [50:39] NS [61:51] NR [62] PK
    input  wire          hdr_v,
    input  wire [511:0]  hdr_d,          // the ROWS PK2 header word for this half's ingress
    input  wire          go,
    input  wire          x_v,            // export words of this half (from the entry P.V lane / pvrd)
    input  wire [512:0]  x_d,
    input  wire          ri_v,           // reduce partial from POS - 1
    input  wire [1023:0] ri_d,
    output reg           ro_v,           // reduce partial to POS + 1
    output reg  [1023:0] ro_d,
    input  wire          bi_v,           // broadcast from POS + 1
    input  wire [1023:0] bi_d,
    output reg           bo_v,           // broadcast to POS - 1
    output reg  [1023:0] bo_d,
    output reg           e_v,            // to the svc entry q (ROWS PK2 frame)
    output reg  [511:0]  e_d,
    output wire          fault,
    output wire [7:0]    fcode
);
    dsdv_rowx_xm #(.MUT(MUT),.D(D),.USE_SRAM(1)) u_xm (
        .clk(clk), .rst_n(rst_n), .cfg_v(cfg_v), .cfg_d(cfg_d), .hdr_v(hdr_v), .hdr_d(hdr_d), .go(go), .x_v(x_v), .x_d(x_d), .ri_v(ri_v), .ri_d(ri_d), .ro_v(ro_v), .ro_d(ro_d), .bi_v(bi_v), .bi_d(bi_d), .bo_v(bo_v), .bo_d(bo_d), .e_v(e_v), .e_d(e_d), .fault(fault), .fcode(fcode));
endmodule
