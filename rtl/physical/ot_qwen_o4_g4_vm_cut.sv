`timescale 1ns/1ps
// Route cut for the finite 8-skew-bank Qwen G4 vector memory
// (rtl/physical/ot_qwen_g4_vm_skew_candidate.sv, 32 ot_sram_1r1w_512x128
// macros) with its real producer and capture registers inside the cut, so no
// memory-adjacent path is timed against an assumed port delay.
//
// Producers are the flops that drive the VM in the adopted matvec
// (rtl/hdc/ot_hdc_matvec.sv): the x read request (x_re / x_addr, registered in
// the issue stage) and the second output register (o_we / o_addr / o_mask /
// o_data). The capture is the matvec's MEM_PIPE register mq_x, which samples
// the synchronous macro read one edge after the request edge. The cut adds
// no register the core does not already have: port -> producer and
// capture -> port are the core's own neighbouring stages, which are what
// the block's I/O delay stands for.
module ot_qwen_o4_g4_vm_cut (
    input  wire          clk,
    input  wire          rst_n,
    // producer inputs (the stage before the matvec's registered VM requests)
    input  wire [3:0]    x_re_d,
    input  wire [4*16-1:0] x_addr_d,     // element address: word = [15:4], lane = [3:0]
    input  wire [3:0]    o_we_d,
    input  wire [4*12-1:0] o_addr_d,     // word address
    input  wire [4*16-1:0] o_mask_d,
    input  wire [4*512-1:0] o_data_d,
    // capture outputs (the matvec's mq_x) and status
    output reg  [4*32-1:0] mq_x,
    output reg  [3:0]    mq_xv,
    output wire          fault
);
    reg  [3:0]     x_re;
    reg  [4*16-1:0] x_addr;
    reg  [3:0]     o_we;
    reg  [4*12-1:0] o_addr;
    reg  [4*16-1:0] o_mask;
    reg  [4*512-1:0] o_data;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin x_re <= 4'd0; o_we <= 4'd0; end
        else begin x_re <= x_re_d; o_we <= o_we_d; end
    end
    always @(posedge clk) begin
        x_addr <= x_addr_d; o_addr <= o_addr_d; o_mask <= o_mask_d; o_data <= o_data_d;
    end

    wire [3:0]      rv;
    wire [4*32-1:0] rdata;
    ot_qwen_g4_vm_skew_candidate u_vm (
        .clk(clk), .rst_n(rst_n), .re(x_re), .we(o_we), .raddr(x_addr), .waddr(o_addr),
        .wmask(o_mask), .wdata(o_data), .rv(rv), .rdata(rdata), .fault(fault));

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) mq_xv <= 4'd0;
        else mq_xv <= rv;
    end
    always @(posedge clk) mq_x <= rdata;
endmodule
