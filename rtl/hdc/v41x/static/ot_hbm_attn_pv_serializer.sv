`timescale 1ns/1ps
`default_nettype none
// Candidate source-preserving transpose store. Capture is the literal H16/TD32
// PV output: word[tile*16+head], dim=tile*16+capture_dim. Drain emits64
// head-major FP32 words, i.e. eight canonical256-bit sectors. Actual VM output
// ownership, station ages and fault/status binding remain parent obligations.
module ot_hbm_attn_pv_serializer (
 input wire clk,rst_n,
 input wire capture_v,capture_epoch,input wire[3:0]capture_dim,
 input wire[16383:0]capture_data,input wire[511:0]capture_flags,
 input wire drain_v,drain_epoch,input wire[3:0]drain_head,
 input wire[2:0]drain_block,input wire[15:0]drain_base_sector,
 output reg write_v,output reg[2047:0]write_data,
 output reg[63:0]write_flags,output reg[15:0]write_base_sector,
 output reg fault
);
 function automatic integer perm(input integer c);
  perm=(c&3)|((c&12)<<2);
 endfunction
 wire[127:0]bank_q[0:127];wire[3:0]flag_q[0:127];
 reg[15:0]seen[0:1];reg dv,ep;reg[3:0]head;reg[2:0]block_;
 reg[15:0]sector;
 genvar b,a;
 generate for(b=0;b<128;b=b+1)begin:g_bank
  // For each absolute capture phase the XOR is a bijection, so every bank
  // receives one128-bit write. For a64dimension drain block, only64distinct
  // banks are read; this combinational decode selects its one real read port.
  wire[6:0]source_index=7'(b)^7'(perm(int'(capture_dim)));
  wire[4:0]tile=source_index[6:2];wire[1:0]hg=source_index[1:0];
  wire[127:0]data_in=capture_data[(int'(tile)*16+int'(hg)*4)*32+:128];
  wire[3:0]flags_in=capture_flags[int'(tile)*16+int'(hg)*4+:4];
  reg read_bank;reg[3:0]read_c;
  always @*begin
   read_bank=0;read_c=0;
   for(integer d=0;d<64;d=d+1)
    if((((int'(drain_block)*4+d/16)*4+int'(drain_head)/4)^perm(d%16))==b)begin
     read_bank=drain_v;read_c=4'(d%16);
    end
  end
  wire[4:0]ra={drain_epoch,read_c};wire[127:0]flags_by_addr;
  ot_sram_1r1w_32x128_m1 u_data(.clk(clk),.r_ce_in(read_bank),.r_addr_in(ra),.rd_out(bank_q[b]),
   .w_ce_in(capture_v),.w_addr_in({capture_epoch,capture_dim}),.wd_in(data_in),.w_mask_in({128{1'b1}}));
  // Explicit status flops, not an inferred behavioral payload RAM. Two physical
  // clock roots are required for the16384flagFFs; mapped clock closure is open.
  for(a=0;a<32;a=a+1)begin:g_status
   reg[3:0]f;
   always @(posedge clk)if(capture_v&&{capture_epoch,capture_dim}==5'(a))f<=flags_in;
   assign flags_by_addr[a*4+:4]=f;
  end
  reg[3:0]fq;always @(posedge clk)if(read_bank)fq<=flags_by_addr[ra*4+:4];
  assign flag_q[b]=fq;
 end endgenerate
 integer d,which;
 always @*begin
  write_data=0;write_flags=0;
  for(d=0;d<64;d=d+1)begin
   which=(((int'(block_)*4+d/16)*4+int'(head)/4)^perm(d%16));
   write_data[d*32+:32]=bank_q[which][head[1:0]*32+:32];
   write_flags[d]=flag_q[which][head[1:0]];
  end
 end
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  seen[0]<=0;seen[1]<=0;dv<=0;write_v<=0;fault<=0;ep<=0;head<=0;block_<=0;sector<=0;write_base_sector<=0;
 end else begin
  dv<=drain_v;write_v<=drain_v;
  if(capture_v)begin
   if(capture_dim==0)seen[capture_epoch]<=16'h0001;
   else begin
    if(seen[capture_epoch][capture_dim]||!seen[capture_epoch][capture_dim-1])fault<=1;
    seen[capture_epoch][capture_dim]<=1;
   end
  end
  if(drain_v)begin
   if(seen[drain_epoch]!=16'hffff||drain_base_sector[2:0]!=0||
      (capture_v&&capture_epoch==drain_epoch))fault<=1;
   ep<=drain_epoch;head<=drain_head;block_<=drain_block;
   sector<=drain_base_sector+16'(int'(drain_head)*64+int'(drain_block)*8);
   write_base_sector<=drain_base_sector+16'(int'(drain_head)*64+int'(drain_block)*8);
  end
 end
endmodule
`default_nettype wire
