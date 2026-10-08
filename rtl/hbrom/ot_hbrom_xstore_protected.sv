`timescale 1ns/1ps
// Fixed full AR leaf storage. Enabled only by the opt-in protected leaf.
// Independent ingress beat codewords preserve all original partial-write masks.
// Read response is three edges after SRAM request (original capture +2).
// Write lands three edges after input (original input register +2 encode).
module ot_hbrom_xstore_protected #(parameter integer SP=0)(
 input wire clk,rst_n,
 input wire read_en,input wire[6:0] read_addr,
 input wire write_en,input wire[6:0] write_addr,
 input wire[1:0] write_oh,input wire[2047:0] write_data,
 output wire read_valid,output wire[787:0] read_data,
 output wire corrected,output wire fault,
 output wire write_pending);
 import ot_gpu_w6_secded_pkg::*;
 import ot_hbrom_secded_pipeline_pkg::*;
 localparam integer N0=(SP==3)?8:9;
 localparam integer N1=(SP==3)?6:4;
 localparam integer NW=N0+N1;
 localparam integer LEN0=(SP==3)?452:532;
 // A beat1 vector contains leaf3's last80 quant bits followed by BF16256.
 function automatic integer leaf_bit(input integer w,input integer k);
  integer t;
  begin
   t=(w<N0)?w*64+k:(w-N0)*64+k;
   if(w<N0) leaf_bit=(t<LEN0)?t:-1;
   else if(SP==3) leaf_bit=(t<336)?452+t:-1;
   else leaf_bit=(t<256)?532+t:-1;
  end
 endfunction
 function automatic integer ingress_bit(input integer b);
  integer f;
  begin
   if(b<532) f=SP*532+b;
   else f=2128+SP*256+b-532;
   ingress_bit=f%2048;
  end
 endfunction
 reg[2:0] wv;
 reg[6:0] wa0,wa1,wa2;
 reg[1:0] wo0,wo1,wo2;
 wire[1023:0] ram_out,ram_in,ram_mask;
 wire[NW-1:0] ue,ce;
 wire[NW*64-1:0] decoded;
 reg[3:0] rv;
 reg fault_q;
 (* keep = "true", dont_touch = "yes" *) reg[2:0] wv_shadow;
 (* keep = "true", dont_touch = "yes" *) reg[3:0] rv_shadow;
 (* keep = "true", dont_touch = "yes" *) reg[6:0] wa0_shadow,wa1_shadow,wa2_shadow;
 (* keep = "true", dont_touch = "yes" *) reg[1:0] wo0_shadow,wo1_shadow,wo2_shadow;
 (* keep = "true", dont_touch = "yes" *) reg fault_shadow;
 wire control_bad=(wv_shadow!==~wv)||(rv_shadow!==~rv)||
   (wa0_shadow!==~wa0)||(wa1_shadow!==~wa1)||(wa2_shadow!==~wa2)||
   (wo0_shadow!==~wo0)||(wo1_shadow!==~wo1)||(wo2_shadow!==~wo2)||
   (fault_shadow!==~fault_q);
 wire stop=fault_q||control_bad;
 // Metadata companions are compared before any SRAM side effect.
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   wv_shadow<=3'b111;rv_shadow<=4'b1111;fault_shadow<=1;
   wa0_shadow<=7'h7f;wa1_shadow<=7'h7f;wa2_shadow<=7'h7f;
   wo0_shadow<=2'b11;wo1_shadow<=2'b11;wo2_shadow<=2'b11;
  end else begin
   wv_shadow<={wv_shadow[1:0],~(write_en&&!stop)};
   rv_shadow<={rv_shadow[2:0],~(read_en&&!stop)};
   wa0_shadow<=~write_addr;wa1_shadow<=wa0_shadow;wa2_shadow<=wa1_shadow;
   wo0_shadow<=~write_oh;wo1_shadow<=wo0_shadow;wo2_shadow<=wo1_shadow;
   if(control_bad||(rv[3]&&(|ue)))fault_shadow<=0;
  end
 assign fault=stop;
 assign read_valid=rv[3]&&!stop&&!(|ue);
 assign corrected=read_valid&&(|ce);
 assign write_pending=|wv;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin wv<=0;rv<=0;fault_q<=0;end
  else begin
   wv<={wv[1:0],write_en&&!stop};
   rv<={rv[2:0],read_en&&!stop};
   if(control_bad||(rv[3]&&(|ue)))fault_q<=1;
  end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin wa0<=0;wa1<=0;wa2<=0;wo0<=0;wo1<=0;wo2<=0;end
  else begin
  wa0<=write_addr;wa1<=wa0;wa2<=wa1;
  wo0<=write_oh;wo1<=wo0;wo2<=wo1;
  end
 end
 genvar w,k,m;
 generate for(w=0;w<NW;w=w+1)begin:g_word
  wire[63:0] payload;
  for(k=0;k<64;k=k+1)begin:g_bit
   localparam integer B=leaf_bit(w,k);
   if(B>=0)begin
    assign payload[k]=write_data[ingress_bit(B)];
    assign read_data[B]=decoded[w*64+k];
   end else assign payload[k]=1'b0;
  end
  reg[63:0] raw0;
  reg[71:0] enc1,enc2,read0;
  reg[79:0] dec1;reg[65:0] dec2;
  always @(posedge clk)begin
   raw0<=payload;
   enc1<=encode64(raw0)&{1'b0,{71{1'b1}}};enc2<={^enc1[70:0],enc1[70:0]};
   read0<=ram_out[w*72+:72];
   dec1<={check72(read0),read0};dec2<=correct72(dec1[71:0],dec1[79:72]);
  end
  assign ram_in[w*72+:72]=enc2;
  assign ram_mask[w*72+:72]={72{wo2[(w<N0)?0:1]}};
  assign decoded[w*64+:64]=dec2[63:0];
  assign ce[w]=dec2[64];assign ue[w]=dec2[65];
 end
 if(NW*72<1024)begin
  assign ram_in[1023:NW*72]=0;
  assign ram_mask[1023:NW*72]=0;
 end
 for(m=0;m<4;m=m+1)begin:g_macro
  ot_sram_1r1w_128x256_m1_r2c2 u_x(
   .clk(clk),.r_ce_in(read_en&&!stop),.r_addr_in(read_addr),.rd_out(ram_out[m*256+:256]),
   .w_ce_in(wv[2]&&!stop&&(|ram_mask[m*256+:256])),.w_addr_in(wa2),
   .wd_in(ram_in[m*256+:256]),.w_mask_in(ram_mask[m*256+:256]),
   .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
endmodule
