`timescale 1ns/1ps
// Literal native xa/xb memory-port slice: full 19-bit scalar address depth.
// Source: selected ot_chip_v41x_tile.sv lines298,618-624. Protection/ownership
// lives in the existing source journals/capture; this port creates no ACK.
// This is behavioral source, NOT a SRAM physical view or clkQ certificate.
module ot_dsrom_wfc_vm_port #(
 parameter VM_AW=19
)(
 input wire clk,
 input wire xa_we,xa_re,
 input wire [VM_AW-5:0]xa_waddr,xa_raddr,
 input wire [511:0]xa_wdata,
 output reg [511:0]xa_rq,
 input wire [3:0]xb_we4,
 input wire [4*(VM_AW-4)-1:0]xb_waddr4,
 input wire [2047:0]xb_wdata4,
 input wire xb_re,
 input wire [VM_AW-5:0]xb_raddr,
 output reg [511:0]xb_rq
);
 reg [31:0]vm[0:(1<<VM_AW)-1];
 integer e,b;
 always @(posedge clk)begin
   for(e=0;e<16;e=e+1)begin
     if(xa_we)vm[{xa_waddr,4'(e)}]<=xa_wdata[32*e+:32];
     for(b=0;b<4;b=b+1)
       if(xb_we4[b])vm[{xb_waddr4[b*(VM_AW-4)+:(VM_AW-4)],4'(e)}]<=xb_wdata4[b*512+32*e+:32];
     if(xa_re)xa_rq[32*e+:32]<=vm[{xa_raddr,4'(e)}];
     if(xb_re)xb_rq[32*e+:32]<=vm[{xb_raddr,4'(e)}];
   end
 end
endmodule

// Only the literal accepted-start capture from selected native core573-574.
// Actual native_idle and fragment_done remain canonical engine signals.
module ot_dsrom_wfc_core_capture(
 input wire clk,native_idle,start,
 input wire [20:0]token,pos,
 input wire [13:0]entry,
 output reg [20:0]tok_r,pos_r,
 output reg [13:0]pc
);
 always @(posedge clk)if(start&&native_idle)begin
   tok_r<=token;pos_r<=pos;pc<=entry;
 end
endmodule
