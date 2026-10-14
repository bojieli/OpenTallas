`timescale 1ns/1ps
// Fixed parameter hardened bank family. Each accepted view binds exactly one name/parameter set.
`ifdef OT_FENCE_BANK_HARD
(* blackbox *) module ot_hbm_native_fence_bank128(
`else
module ot_hbm_native_fence_bank128(
`endif
 input wire clk,rst_n,input wire [127:0] din,input wire [1:0] write_next,read_next,
 output wire [255:0] slots,output wire [1:0] read_select);
`ifndef OT_FENCE_BANK_HARD
 ot_hbm_native_fence_fifo_bank #(.W(128),.S(2)) u_local(.clk(clk),.rst_n(rst_n),.din(din),.write_next(write_next),.read_next(read_next),.slots(slots),.read_select(read_select));
`endif
endmodule
`ifdef OT_FENCE_BANK_HARD
(* blackbox *) module ot_hbm_native_fence_bank32(
`else
module ot_hbm_native_fence_bank32(
`endif
 input wire clk,rst_n,input wire [31:0] din,input wire [1:0] write_next,read_next,
 output wire [63:0] slots,output wire [1:0] read_select);
`ifndef OT_FENCE_BANK_HARD
 ot_hbm_native_fence_fifo_bank #(.W(32),.S(2)) u_local(.clk(clk),.rst_n(rst_n),.din(din),.write_next(write_next),.read_next(read_next),.slots(slots),.read_select(read_select));
`endif
endmodule
`ifdef OT_FENCE_BANK_HARD
(* blackbox *) module ot_hbm_native_fence_bank18(
`else
module ot_hbm_native_fence_bank18(
`endif
 input wire clk,rst_n,input wire [17:0] din,input wire [1:0] write_next,read_next,
 output wire [35:0] slots,output wire [1:0] read_select);
`ifndef OT_FENCE_BANK_HARD
 ot_hbm_native_fence_fifo_bank #(.W(18),.S(2)) u_local(.clk(clk),.rst_n(rst_n),.din(din),.write_next(write_next),.read_next(read_next),.slots(slots),.read_select(read_select));
`endif
endmodule
`ifdef OT_FENCE_BANK_HARD
(* blackbox *) module ot_hbm_native_fence_bank9(
`else
module ot_hbm_native_fence_bank9(
`endif
 input wire clk,rst_n,input wire [8:0] din,input wire [1:0] write_next,read_next,
 output wire [17:0] slots,output wire [1:0] read_select);
`ifndef OT_FENCE_BANK_HARD
 ot_hbm_native_fence_fifo_bank #(.W(9),.S(2)) u_local(.clk(clk),.rst_n(rst_n),.din(din),.write_next(write_next),.read_next(read_next),.slots(slots),.read_select(read_select));
`endif
endmodule
`ifdef OT_FENCE_BANK_HARD
(* blackbox *) module ot_hbm_native_fence_bank8(
`else
module ot_hbm_native_fence_bank8(
`endif
 input wire clk,rst_n,input wire [7:0] din,input wire [1:0] write_next,read_next,
 output wire [15:0] slots,output wire [1:0] read_select);
`ifndef OT_FENCE_BANK_HARD
 ot_hbm_native_fence_fifo_bank #(.W(8),.S(2)) u_local(.clk(clk),.rst_n(rst_n),.din(din),.write_next(write_next),.read_next(read_next),.slots(slots),.read_select(read_select));
`endif
endmodule
`ifdef OT_FENCE_BANK_HARD
(* blackbox *) module ot_hbm_native_fence_bank1(
`else
module ot_hbm_native_fence_bank1(
`endif
 input wire clk,rst_n,input wire [0:0] din,input wire [1:0] write_next,read_next,
 output wire [1:0] slots,output wire [1:0] read_select);
`ifndef OT_FENCE_BANK_HARD
 ot_hbm_native_fence_fifo_bank #(.W(1),.S(2)) u_local(.clk(clk),.rst_n(rst_n),.din(din),.write_next(write_next),.read_next(read_next),.slots(slots),.read_select(read_select));
`endif
endmodule
