`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Fixed-NCOL wrappers for ot_compute_unit_gemm, one synthesis top each.
//
// These exist because tools/run_abi3_physical.py --param NCOL=N makes Yosys 0.68
// re-derive ot_mac_tile after it has already been derived for the default
// parameterisation and it aborts:
//
//   ERROR: Assert `modules_.count(module->name) == 0' failed in kernel/rtlil.cc:1231
//
// A wrapper carries no logic of its own -- every port is a straight pass-through,
// so the routed netlist is the unit's and nothing is added to the critical path or
// the area. It is the same pattern rtl/abi3/ot_probe_packed8_bf16.sv uses to
// characterise one parameterisation of a parameterised leaf.
// ---------------------------------------------------------------------------
`define OT_GEMM_PROBE(NAME, N)                                               \
module NAME (                                                                \
    input  wire                clk,                                          \
    input  wire                rst_n,                                        \
    input  wire                start,                                        \
    input  wire [8:0]          cfg_k,                                        \
    input  wire [7:0]          cfg_scale,                                    \
    output wire                busy,                                         \
    output wire                done,                                         \
    input  wire                wr_en,                                        \
    input  wire [7:0]          wr_addr,                                      \
    input  wire [255:0]        wr_data,                                      \
    input  wire                act_we,                                       \
    input  wire [7:0]          act_waddr,                                    \
    input  wire [16*N-1:0]     act_wdata,                                    \
    input  wire                refill_valid,                                 \
    output wire                refill_ready,                                 \
    output wire                stalled,                                      \
    input  wire [3:0]          res_sel,                                      \
    output wire [40*N-1:0]     res_data,                                     \
    output wire [16*N-1:0]     dropped_mask                                  \
);                                                                           \
    ot_compute_unit_gemm #(.LANES(16), .ACC_W(40), .K_MAX(256), .NCOL(N)) u ( \
        .clk(clk), .rst_n(rst_n), .start(start), .cfg_k(cfg_k),              \
        .cfg_scale(cfg_scale), .busy(busy), .done(done),                     \
        .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data),                 \
        .act_we(act_we), .act_waddr(act_waddr), .act_wdata(act_wdata),       \
        .refill_valid(refill_valid), .refill_ready(refill_ready),            \
        .stalled(stalled), .res_sel(res_sel), .res_data(res_data),           \
        .dropped_mask(dropped_mask));                                        \
endmodule

`OT_GEMM_PROBE(ot_probe_gemm_unit_n2, 2)
`OT_GEMM_PROBE(ot_probe_gemm_unit_n4, 4)
`OT_GEMM_PROBE(ot_probe_gemm_unit_n8, 8)
