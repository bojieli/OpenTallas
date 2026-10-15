`timescale 1ns/1ps
// Compiler-owned use of the EXISTING HCP tail 4x4096x72 parameter ROM port.
// Addresses0..343 remain coefficient parameters;512..831 main finalgain,
//832..1151 M2 finalgain. No new storage macro and no ready/credit scheduling.
// A valid command reads320 consecutive256-bit words and writes320512-bit VM
// rows. The physical parent must reserve the ROM/VM ports for this entire job.
module ot_s81_head_gain_stream #(parameter integer WL=4,MUT_GAIN=0)(
 input wire clk,rst_n,start,draft,
 input wire [13:0] vm_base_row,
 output wire rom_ce, output wire [11:0] rom_addr,
 input wire [255:0] rom_data,
 output wire wq_v,output wire [13:0] wq_row,
 output wire [15:0] wq_mask,output wire [511:0] wq_d,
 input wire wq_commit,
 output reg busy,done,fault
);
 localparam integer CYCLES=322+WL;
 reg[8:0]word_idx;reg[13:0]base,row_q;reg mode,rv;
 reg[15:0]age,commits;reg[WL-1:0]due;
 assign rom_ce=busy && word_idx<320;
 assign rom_addr=12'd512+(mode?12'd320:12'd0)+word_idx;
 assign wq_v=rv;
 assign wq_row=row_q;
 assign wq_mask=16'hffff;
 for(genvar lane=0;lane<16;lane=lane+1)begin:g_expand
  assign wq_d[32*lane+:32]={rom_data[16*lane+:16],16'd0} ^ ((MUT_GAIN && lane==0)?32'h00010000:32'd0);
 end
 always@(posedge clk or negedge rst_n)begin
  if(!rst_n)begin busy<=0;done<=0;fault<=0;word_idx<=0;base<=0;mode<=0;rv<=0;row_q<=0;age<=0;commits<=0;due<=0;end
  else begin
   done<=0;rv<=rom_ce;
   due<=WL'( (due<<1)|wq_v );
   if(wq_commit!=due[WL-1])fault<=1;
   if(wq_commit)commits<=commits+1'b1;
   if(rom_ce)begin word_idx<=word_idx+1'b1;row_q<=base+word_idx;end
   if(start)begin
    if(busy||rv||due!=0||vm_base_row>14'd16064)fault<=1;
    else begin busy<=1;word_idx<=0;base<=vm_base_row;mode<=draft;age<=0;commits<=0;end
   end
   if(busy)begin
    age<=age+1'b1;
    if(age+1==CYCLES)begin
     busy<=0;done<=1;
     if(commits!=320||word_idx!=320||rv||due!=0)fault<=1;
    end
   end
  end
 end
 initial if(WL<1)$fatal(1,"gainstream requires fixed positive VM commit latency");
endmodule
