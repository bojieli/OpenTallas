`timescale 1ns/1ps
// hfd_host_ingest (stream ingest 2026-10-08, coverage T3): the HBM accelerator die's GPU-prefill KV-ingest master =
// ot_rom_host_ingest (QKV_EN 0, RMW_EN 0: ROWS for window / compressed rows, RAW for packed index keys) + ot_hbm_ingest_xlat
// (linear ingest sectors -> the DS-V4.1 decode KV layout of ot_hbm_accel_dskv_wb, on the stack write-request port format
// wq_*).  The wq_* port shares the die's HBM write fabric with the per-token write-back (decode first) and the loader
// (mtp-die wiring); eop_v / eop_d carry the BOOT_END marker (loader boot check).  Clocks as ot_rom_host_ingest.
module hfd_host_ingest #(parameter integer IQ = 4) (
    input  wire          rst_n,
    input  wire          clk_h,
    input  wire          h_v,
    input  wire [1:0]    h_cls,
    input  wire [511:0]  h_d,
    output wire [4:0]    h_crn,
    output wire          t_v,
    output wire [63:0]   t_d,
    input  wire          t_cr,
    input  wire          clk_i,
    input  wire          ck,
    output wire          wq_v,
    output wire [1:0]    wq_stack,
    output wire [4:0]    wq_pc,
    output wire [4:0]    wq_bank,
    output wire [18:0]   wq_row,
    output wire [4:0]    wq_col,
    output wire [255:0]  wq_data,
    input  wire          wq_r,
    output wire          eop_v,
    output wire [63:0]   eop_d,
    output wire          fault
);
    wire o_v, o_we, o_cr, f_hi, f_x;
    wire [31:0] o_addr;
    wire [255:0] o_d;
    wire rn_c;
    ot_reset_sync u_rs (.clk(ck), .async_rst_n(rst_n), .sync_rst_n(rn_c));
    ot_rom_host_ingest #(.KVHMAX(1), .HDMAX(16), .QKV_EN(0), .RMW_EN(0), .OCRED(IQ)) u_hi (
        .rst_n(rst_n), .clk_h(clk_h), .h_v(h_v), .h_cls(h_cls), .h_d(h_d), .h_crn(h_crn), .t_v(t_v), .t_d(t_d),
        .t_cr(t_cr), .clk_i(clk_i), .ck(ck), .o_v(o_v), .o_we(o_we), .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr),
        .i_rv(1'b0), .i_rd(256'd0), .fault(f_hi));
    ot_hbm_ingest_xlat #(.IQ(IQ)) u_x (
        .ck(ck), .rst_n(rn_c), .o_v(o_v), .o_we(o_we), .o_addr(o_addr), .o_d(o_d), .o_cr(o_cr),
        .wq_v(wq_v), .wq_stack(wq_stack), .wq_pc(wq_pc), .wq_bank(wq_bank), .wq_row(wq_row), .wq_col(wq_col),
        .wq_data(wq_data), .wq_r(wq_r), .eop_v(eop_v), .eop_d(eop_d), .fault(f_x));
    assign fault = f_hi | f_x;
endmodule
