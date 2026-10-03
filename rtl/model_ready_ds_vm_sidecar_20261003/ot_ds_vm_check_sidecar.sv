`timescale 1ns/1ps
// Additive source-prepared component, disabled by default. 32 actual native
// SRAM macros provide 8 check bits per64data, two64check halves per128word.
// This is a raw paired-parity port, NOT checked VM publication/retirement.
// Caller holds accepted ownership and prohibits reset until positively drained.
module ot_ds_vm_check_sidecar #(parameter integer ENABLE=0)(
 input wire clk,rst_n,
 input wire rd_v,input wire [14:0] rd_base_word,input wire [227:0] rd_owner,
 output wire rd_accept_v,output wire rd_out_v,
 output reg [255:0] rd_checks,output wire [227:0] rd_out_owner,
 input wire wr_v,input wire [14:0] wr_word,input wire [63:0] wr_checks,
 input wire [227:0] wr_owner,output wire wr_accept_v,
 output wire wr_ack_v,output wire [14:0] wr_ack_word,
 output wire [227:0] wr_ack_owner,output wire fault,corrected_command
);
 import ot_gpu_w6_secded_pkg::*;
 reg [287:0] rq [0:4];reg [359:0] wq [0:3];reg [71:0] fq;
 reg [255:0] checks0,checks1;
 wire [255:0] rr [0:4];wire [319:0] ww [0:3];
 wire [19:0] rue,rcorrected;wire [19:0] wue,wcorrected;
 wire [65:0] fd=decode64(fq);
 wire any_bad=(|rue)||(|wue)||padding_bad;
 wire padding_bad;
 wire [127:0] parity [0:3][0:7];
 wire [255:0] rawR={12'b0,rd_owner,rd_accept_v,rd_base_word};
 wire [319:0] rawW={12'b0,wr_accept_v,wr_owner,wr_checks,wr_word};
 assign fault=fd[65] || (|fd[63:2]) || fd[0] || any_bad;
 assign corrected_command=fd[64] || fd[1] || (|rcorrected) || (|wcorrected);
 assign rd_accept_v=(ENABLE!=0)&&rst_n&&!fault&&rd_v&&(rd_base_word[1:0]==0);
 assign wr_accept_v=(ENABLE!=0)&&rst_n&&!fault&&wr_v;
 assign rd_out_v=(ENABLE!=0)&&rst_n&&!fault&&rr[4][15];
 assign rd_out_owner=rr[4][243:16];
 assign wr_ack_v=(ENABLE!=0)&&rst_n&&!fault&&ww[3][307];
 assign wr_ack_word=ww[3][14:0];assign wr_ack_owner=ww[3][306:79];
 wire [8:0] pad_bad;
 generate for(genvar t=0;t<5;t=t+1)begin:g_rd_code
  for(genvar c=0;c<4;c=c+1)begin:g_word
   wire [65:0] d=decode64(rq[t][c*72+:72]);
   assign rr[t][c*64+:64]=d[63:0];assign rue[t*4+c]=d[65];assign rcorrected[t*4+c]=d[64];
  end
  assign pad_bad[t]=|rr[t][255:244];
 end
 for(genvar t=0;t<4;t=t+1)begin:g_wr_code
  for(genvar c=0;c<5;c=c+1)begin:g_word
   wire [65:0] d=decode64(wq[t][c*72+:72]);
   assign ww[t][c*64+:64]=d[63:0];assign wue[t*5+c]=d[65];assign wcorrected[t*5+c]=d[64];
  end
  assign pad_bad[t+5]=|ww[t][319:308];
 end endgenerate
 assign padding_bad=|pad_bad;
 // Explicit source W6 command registers protect address, ownership, validity
 // and the parity write value. Decoder correction is before any macro use.
 always @(posedge clk)begin
  if(!rst_n)begin
   fq<=encode64(0);checks0<=0;checks1<=0;rd_checks<=0;
   for(integer i=0;i<5;i=i+1)rq[i]<=0;
   for(integer i=0;i<4;i=i+1)wq[i]<=0;
  end else begin
   fq<=encode64({62'b0,corrected_command,
       fault || ((ENABLE!=0)&&rd_v&&(rd_base_word[1:0]!=0))});
   for(integer c=0;c<4;c=c+1)rq[0][c*72+:72]<=encode64(rawR[c*64+:64]);
   for(integer c=0;c<5;c=c+1)wq[0][c*72+:72]<=encode64(rawW[c*64+:64]);
   for(integer i=1;i<5;i=i+1)rq[i]<=rq[i-1];
   for(integer i=1;i<4;i=i+1)wq[i]<=wq[i-1];
   for(integer b=0;b<4;b=b+1)
    checks0[b*64+:64]<=parity[b][rr[1][14:12]][rr[1][11]*64+:64];
   checks1<=checks0;rd_checks<=checks1;
  end
 end
 generate for(genvar b=0;b<4;b=b+1)begin:g_bank
  for(genvar p=0;p<8;p=p+1)begin:g_pair
   wire read_en=(ENABLE!=0)&&rst_n&&!fault&&rr[0][15]&&(rr[0][14:12]==p);
   wire write_en=(ENABLE!=0)&&rst_n&&!fault&&ww[1][307]&&(ww[1][1:0]==b)&&(ww[1][14:12]==p);
   wire [127:0] data=ww[1][11]?{ww[1][78:15],64'b0}:{64'b0,ww[1][78:15]};
   wire [127:0] mask=ww[1][11]?{64'hffffffffffffffff,64'b0}:{64'b0,64'hffffffffffffffff};
   ot_sram_1r1w_512x128_m4_r2c2 u_sram(
    .clk(clk),.r_ce_in(read_en),.r_addr_in(rr[0][10:2]),.rd_out(parity[b][p]),
    .w_ce_in(write_en),.w_addr_in(ww[1][10:2]),.wd_in(data),.w_mask_in(mask),
    .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(14'b0));
  end
 end endgenerate
endmodule
