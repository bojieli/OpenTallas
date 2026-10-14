`timescale 1ns/1ps
// Explicit flat {stack,local_byte} -> existing stack2/sector34 port.
// Invalid alignment/capacity holds the request and latches a fault. No aperture.
module ot_hbm_accel_loader_addr_to_service #(
 parameter integer ENABLE=0, ADDR_W=32, STACK_W=0, SECTOR_W=34,
 parameter [63:0] STACK_BYTES=0
)(input wire clk,rst_n,input wire in_v,output wire in_rdy,
 input wire[ADDR_W-1:0] in_addr,input wire in_we,
 input wire[255:0] in_data,input wire[31:0] in_strb,input wire[15:0] in_tag,
 output wire out_v,input wire out_rdy,output wire[1:0] out_stack,
 output wire[SECTOR_W-1:0] out_sector,output wire out_we,
 output wire[255:0] out_data,output wire[31:0] out_strb,output wire[15:0] out_tag,
 output reg fault);
 localparam integer LOCAL_W=ADDR_W-STACK_W;
 initial if(ADDR_W<32||ADDR_W>64||STACK_W<0||STACK_W>2||SECTOR_W<LOCAL_W-5||STACK_BYTES>(65'h1<<LOCAL_W))$fatal(1,"lossless loader address geometry");
 wire[LOCAL_W-1:0] local_addr=in_addr[LOCAL_W-1:0];
 wire bad=|local_addr[4:0] || (STACK_BYTES!=0 && 65'(local_addr)+65'd32>STACK_BYTES);
 assign out_v=ENABLE&&in_v&&!bad;assign in_rdy=ENABLE&&out_rdy&&!bad;
 assign out_stack=ENABLE?2'(in_addr>>LOCAL_W):2'b0;
 assign out_sector=ENABLE?SECTOR_W'(local_addr>>5):'0;
 assign out_we=ENABLE&&in_we;assign out_data=ENABLE?in_data:'0;
 assign out_strb=ENABLE?in_strb:'0;assign out_tag=ENABLE?in_tag:'0;
 always @(posedge clk or negedge rst_n)if(!rst_n)fault<=0;else if(ENABLE&&in_v&&bad)fault<=1;
endmodule
