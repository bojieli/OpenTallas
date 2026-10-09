`timescale 1ns/1ps
// One real 4096-token W1 bank: eight 4096x266 macros, replicated38 times
// for the released151936x256 INT8 table. Scale16 occupies two spare8bit
// fields. No ROM ECC, parity or synthetic table. Finite one-read lease.
module ot_qwen_dspark_w1_bank #(parameter integer ENABLE=0,BANK=0)(
 input wire clk,rst_n,input wire i_v,output wire i_r,
 input wire [17:0] i_token,input wire [63:0] i_id,
 output reg o_v,input wire o_r,output wire [511:0] o_codes,
 output wire [15:0] o_scale,output wire [1:0] o_quarter,
 output wire [63:0] o_id,output wire o_last,output reg fault
);
 reg busy,req;
 reg [11:0] row;
 reg [63:0] lease;
 reg [2:0] pipe;
 reg [1:0] quarter;
 reg [2047:0] captured;
 reg [15:0] scale;
 wire [2127:0] macro_q;
 wire fire=i_v&&i_r;
 wire bound_ok=(i_token<151936)&&(i_token[17:12]==6'(BANK));
 assign i_r=(ENABLE!=0)&&!busy&&!fault;
 assign o_codes=captured[quarter*512+:512];
 assign o_scale=scale;assign o_quarter=quarter;assign o_id=lease;
 assign o_last=o_v&&quarter==3;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin busy<=0;req<=0;pipe<=0;quarter<=0;o_v<=0;fault<=0;end
  else begin
   req<=fire&&bound_ok;
   pipe<={pipe[1:0],fire&&bound_ok};
   if(fire)begin
    if(!bound_ok)fault<=1;
    else begin busy<=1;row<=i_token[11:0];lease<=i_id;quarter<=0;end
   end
   if(pipe[2])o_v<=1;
   if(o_v&&o_r)begin
    if(quarter==3)begin o_v<=0;busy<=0;end
    else quarter<=quarter+1'b1;
   end
  end
 end
 for(genvar g=0;g<8;g=g+1)begin : banks
  `ifdef SYNTHESIS
  ot_rom_4096x266_m8 macro_inst(
  `else
  ot_rom_4096x266_m8 #(.INSTANCE($sformatf("qwen_w1_b%0d_c%0d",BANK,g))) macro_inst(
  `endif
   .clk(clk),.ce_in(req),.addr_in(row),.rd_out(macro_q[g*266+:266]));
  // Real sole-pin capture: no mux or dequantisation before this register.
  always @(posedge clk)captured[g*256+:256]<=macro_q[g*266+:256];
 end
 always @(posedge clk)scale<={macro_q[266+256+:8],macro_q[256+:8]};
endmodule
