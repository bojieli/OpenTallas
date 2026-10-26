`timescale 1ns/1ps
`default_nettype none
// Opt-in canonical ILV0/NSTAGE1 successor. A new job latches mode before load;
// every job must reload its independent K or V image. Same34 real SRAMs.
// Fullraw8480 ABI preserved, including FP4 padding. local_codes is physical
// bank order, not a replacement external format. Guards are real640validFF.
module ot_hbm_attn_staging_mode_local #(parameter integer MUT=0)(
 input wire clk,rst_n,mode_set,job_pv,
 input wire[1:0]wr_en,input wire[8:0]wr_addr,input wire[8479:0]wr_data,
 input wire rd_en,input wire[1:0]rd_mask,input wire[8:0]rd_addr,
 output wire[8479:0]rd_data,output wire[8191:0]local_codes,
 output wire[287:0]local_metadata,output reg rd_pv,output reg fault
);
 reg mode_pv;reg[319:0]loaded[0:1];integer l;
 wire load_ok=!mode_set&&(wr_addr<320);
 wire read_ok=rd_en&&!mode_set;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin mode_pv<=0;rd_pv<=0;fault<=0;loaded[0]<=0;loaded[1]<=0;end
  else begin
   if(mode_set)begin
    mode_pv<=job_pv;loaded[0]<=0;loaded[1]<=0;
    if((|wr_en)||rd_en)fault<=1;
   end else begin
    if((|wr_en)&&wr_addr>=320)fault<=1;
    for(l=0;l<2;l=l+1)if(wr_en[l]&&load_ok)loaded[l][wr_addr]<=1;
    if(rd_en)begin
     rd_pv<=mode_pv;
     if(rd_addr>=320)fault<=1;
     else for(l=0;l<2;l=l+1)if(rd_mask[l]&&!loaded[l][rd_addr])fault<=1;
    end
   end
  end
 end
 function automatic[127:0]half_codes(input[255:0]c,input fmt,input odd);
 begin
  if(!fmt||MUT==1)half_codes=odd?c[255:128]:c[127:0];
  else if(odd)half_codes={c[255:200],c[143:136],c[127:64]};
  else half_codes={c[199:144],c[135:128],c[63:0]};
 end endfunction
 function automatic[255:0]join_codes(input[127:0]e,input[127:0]o,input fmt);
 begin
  if(!fmt)join_codes={o,e};
  else join_codes={o[127:72],e[127:72],o[71:64],e[71:64],o[63:0],e[63:0]};
 end endfunction
 genvar t,a,g;
 generate for(t=0;t<32;t=t+1)begin:g_code
  localparam integer KL=t/16,KG=t%16,VG=t/2,ODD=t%2;
  wire[255:0]vpack={half_codes(wr_data[4240+VG*265+:256],wr_data[4240+VG*265+264],ODD!=0),half_codes(wr_data[VG*265+:256],wr_data[VG*265+264],ODD!=0)};
  wire[255:0]wd=mode_pv?vpack:wr_data[KL*4240+KG*265+:256];
  wire[1:0]mask_lanes=MUT==2?{wr_en[0],wr_en[1]}:wr_en;
  wire[255:0]wm=mode_pv?{{128{mask_lanes[1]}},{128{mask_lanes[0]}}}:{256{wr_en[KL]}};
  wire we=load_ok&&(mode_pv?(|wr_en):wr_en[KL]);
  ot_sram_1r1w_1024x256_m2_r2c2 u_codes(.clk(clk),.r_ce_in(read_ok),.r_addr_in({1'b0,rd_addr}),.rd_out(local_codes[t*256+:256]),.w_ce_in(we),.w_addr_in({1'b0,wr_addr}),.wd_in(wd),.w_mask_in(wm),.rr_en(2'b0),.rr_addr(18'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end
 for(a=0;a<2;a=a+1)begin:g_meta
  wire[143:0]m;wire[255:0]q;
  for(g=0;g<16;g=g+1)begin:g_group
   assign m[g*9+:9]=wr_data[a*4240+g*265+256+:9];
   assign rd_data[a*4240+g*265+256+:9]=q[g*9+:9];
   wire fmt=q[g*9+8];
   wire[127:0]ev=local_codes[(2*g)*256+a*128+:128];
   wire[127:0]od=local_codes[(2*g+1)*256+a*128+:128];
   assign rd_data[a*4240+g*265+:256]=(rd_pv&&MUT!=3)?join_codes(ev,od,fmt):local_codes[(a*16+g)*256+:256];
  end
  assign local_metadata[a*144+:144]=q[143:0];
  ot_sram_1r1w_1024x256_m2_r2c2 u_metadata(.clk(clk),.r_ce_in(read_ok),.r_addr_in({1'b0,rd_addr}),.rd_out(q),.w_ce_in(load_ok&&wr_en[a]),.w_addr_in({1'b0,wr_addr}),.wd_in({112'b0,m}),.w_mask_in({256{1'b1}}),.rr_en(2'b0),.rr_addr(18'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
endmodule
`default_nettype wire
