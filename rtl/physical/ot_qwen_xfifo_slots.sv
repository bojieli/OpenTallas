`timescale 1ns/1ps
// Qwen ROM TP8 IO credit-CDC leaf. W1024 preserves the earlier partition; the die-approved native partition
// uses W546 for partial and SerDes records, with514-bit UCIe result records zero-padded32 bits. The native region
// places10 leaves (UCIeP/R and3 SerDes pairs) with separate writer/reader clock entries; it has no parent cells or
// clock tree. Exact placements/port maps: physical/qwen_romio_slots/xf_native_partition_1013.json.
// ot_qwen_die_cdc_ch is unchanged: kept input capture, registered credit and faults, output pin station.
// OT_XF_MUT (bench only) exchanges output data bits5 and517.
module qfd_xf_ch #(parameter integer W = 1024, parameter integer IBUF = 4, OCRED = 4, IBMEM = 0) (
    input  wire          wck,
    input  wire          rck,
    input  wire          rst_n,
    input  wire          i_v,
    input  wire [W-1:0] i_d,
    output wire          i_cr,
    output wire          w_fault,
    output wire          o_v,
    output wire [W-1:0] o_d,
    input  wire          o_cr,
    output wire          r_fault
);
    wire [W-1:0] od;
    ot_qwen_die_cdc_ch #(.W(W), .IBUF(IBUF), .OCRED(OCRED), .IBMEM(IBMEM), .PIPE(2)) u_ch (
        .wclk(wck), .wrst_n(rst_n), .i_v(i_v), .i_d(i_d), .i_cr(i_cr), .w_fault(w_fault),
        .rclk(rck), .rrst_n(rst_n), .o_v(o_v), .o_d(od), .o_cr(o_cr), .r_fault(r_fault));
`ifdef OT_XF_MUT
    localparam integer MUTBIT = (W > 517) ? 517 : W-7;
    assign o_d = {od[W-1:MUTBIT+1], od[5], od[MUTBIT-1:6], od[MUTBIT], od[4:0]};
`else
    assign o_d = od;
`endif
endmodule
