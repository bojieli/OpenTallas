`timescale 1ns/1ps
// Opt-in physical successor. One slot owns its pin capture, metadata and macro.
// Requests and responses travel in the same direction. The remaining response
// hops exactly compensate each slot's request hops: no global 8:1 data mux.
module ot_qfd_res_slot_tile #(
 parameter integer USE_MACRO=0, MUT=0
)(input wire clk,rst_n,
 input wire me_en,i_ov,i_we,i_last,i_empty,
 input wire [23:0] i_addr,input wire [15:0] i_mask,input wire [511:0] i_data,
 input wire [2:0] slot_id,
 input wire rq_v,input wire [2:0] rq_slot,input wire [5:0] rq_ptr,
 output reg rqf_v,output reg [2:0] rqf_slot,output reg [5:0] rqf_ptr,
 input wire rv,input wire [550:0] rd,
 output reg ov,output reg [550:0] od,
 output reg fault);
 reg pe,po,pw,pl,pz;reg [23:0] pa;reg [15:0] pm;reg [511:0] pd;
 reg cv,cw,cl,cz;reg [23:0] ca;reg [15:0] cm;reg [511:0] cd;
 reg [5:0] wp;
 reg [37:0] meta[0:63];
 wire [511:0] mq;
 reg [2:0] id_q;reg q1_v,r1_v;reg [2:0] q1_s;reg [5:0] q1_p;reg [550:0] r1_d;
 wire hit=rqf_v && rqf_slot==id_q;
 // Every wide capture is unconditional: no me_en pin driving 4.4k enables.
 always @(posedge clk) begin
  id_q<=slot_id;pw<=i_we;pl<=i_last;pz<=i_empty;pa<=i_addr;pm<=i_mask;pd<=i_data;
  cw<=pw;cl<=pl;cz<=pz;ca<=pa;cm<=pm;cd<=pd;
  q1_s<=rq_slot;q1_p<=rq_ptr;rqf_slot<=q1_s;rqf_ptr<=q1_p;r1_d<=rd;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin pe<=0;po<=0;cv<=0;wp<=0;rqf_v<=0;q1_v<=0;r1_v<=0;fault<=0;end
  else begin
   pe<=me_en;po<=i_ov;cv<=pe&&po;q1_v<=rq_v;rqf_v<=q1_v;r1_v<=rv;
   if(cv) begin wp<=wp+1'b1;if(cw&&|ca[23:20]) fault<=1;end
   if(r1_v&&h2) fault<=1;
  end
 end
 always @(posedge clk) if(cv) meta[wp]<={cw,cl,ca[19:0],cm};
 ot_qfd_rs_slotmem #(.DB(64),.LDB(6),.USE_MACRO(USE_MACRO)) u_mem
  (.clk(clk),.re(hit),.raddr(rqf_ptr),.q(mq),.we(cv&&cw),.waddr(wp),.wdata(cd));
 // Two 8:1 metadata levels; row read is separate from request decode.
 reg [37:0] mb[0:7];reg [2:0] sel;reg [37:0] mr;
 reg h1,h2,h3;reg [511:0] cap;
 integer k;
 always @(posedge clk) begin
  for(k=0;k<8;k=k+1) mb[k]<=meta[{rqf_ptr[5:3],3'(k)}];
  sel<=rqf_ptr[2:0];mr<=mb[sel];cap<=mq;
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin h1<=0;h2<=0;h3<=0;ov<=0;end
  else begin
   h1<=hit;h2<=h1;h3<=h2;ov<=r1_v||h2;
  end
 end
 // At h2 the synchronous macro output was captured on the preceding edge;
 // mr belongs to the same request. Bits: used,end,nul,row,mask,data.
 wire used=mr[37] || mr[36];
 always @(posedge clk) begin
  if(h2) od<={used,mr[36],!mr[37],mr[35:16],mr[15:0],MUT!=0 ? cap^512'd1 : cap};
  else od<=r1_d;
 end
endmodule

module ot_qfd_res_tiles_ctl #(parameter integer RS=42,CRB=16)(
 input wire clk,rst_n,me_en,i_ov,o_cr,input wire rv,input wire [550:0] rd,
 output reg rq_v,output reg [2:0] rq_slot,output reg [5:0] rq_ptr,
 output reg o_v,output reg o_end,o_nul,output reg [19:0] o_row,
 output reg [15:0] o_mask,output reg [511:0] o_data,output reg rok,fault);
 reg pe,po,cv;reg [6:0] n;reg [5:0] rp;reg [2:0] slot;
 reg [5:0] cr;reg cpin;reg pin_v;reg [550:0] pin_d;
 wire can=n!=0 && cr!=0;
 wire pop=can && slot==7;
 wire refund=rv && !rd[550];
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin pe<=0;po<=0;cv<=0;n<=0;rp<=0;slot<=0;cr<=CRB;cpin<=0;
   rq_v<=0;o_v<=0;pin_v<=0;rok<=0;fault<=0;end
  else begin
   pe<=me_en;po<=i_ov;cv<=pe&&po;cpin<=o_cr;
   rq_v<=can;pin_v<=rv;
   if(can) begin slot<=slot+1'b1;if(pop) rp<=rp+1'b1;end
   n<=n+8'(cv)-8'(pop);
   cr<=cr+6'(cpin)+6'(refund)-6'(can);
   rok<=(n+8'(cv)+RS+5)<=64;
   o_v<=pin_v&&pin_d[550];
   if((cv&&n==64)||cr>CRB) fault<=1;
  end
 end
 always @(posedge clk) begin pin_d<=rd;rq_slot<=slot;rq_ptr<=rp;
  o_end<=pin_d[549];o_nul<=pin_d[548];o_row<=pin_d[547:528];
  o_mask<=pin_d[548]?16'd0:pin_d[527:512];o_data<=pin_d[511:0];
 end
endmodule

module ot_qfd_res_tiles #(parameter integer USE_MACRO=0,MUT=0,RS=42,CRB=16)(
 input wire clk,rst_n,me_en,i_ov,input wire [7:0] i_we,
 input wire [191:0] i_addr,input wire [127:0] i_mask,input wire [4095:0] i_data,
 output wire o_v,o_end,o_nul,output wire [19:0] o_row,output wire [15:0] o_mask,
 output wire [511:0] o_data,input wire o_cr,output wire rok,fault);
 wire [8:0] qv,rv;wire [26:0] qs;wire [53:0] qp;wire [9*551-1:0] rd;
 wire [7:0] sf;wire cf;
 assign rv[0]=0;assign rd[0+:551]=0;
 ot_qfd_res_tiles_ctl #(.RS(RS),.CRB(CRB)) u_ctl(.clk(clk),.rst_n(rst_n),.me_en(me_en),.i_ov(i_ov),
  .o_cr(o_cr),.rv(rv[8]),.rd(rd[8*551+:551]),.rq_v(qv[0]),.rq_slot(qs[0+:3]),.rq_ptr(qp[0+:6]),
  .o_v(o_v),.o_end(o_end),.o_nul(o_nul),.o_row(o_row),.o_mask(o_mask),.o_data(o_data),.rok(rok),.fault(cf));
 genvar g;
 generate for(g=0;g<8;g=g+1) begin:g_slot
  wire last=(i_we[g] && !(|(i_we >> (g+1)))) || (g==7 && i_we==0);
  ot_qfd_res_slot_tile #(.USE_MACRO(USE_MACRO),.MUT(MUT!=0 && g==1)) u_t(.clk(clk),.rst_n(rst_n),
   .me_en(me_en),.i_ov(i_ov),.i_we(i_we[g]),.i_last(last),.i_empty(i_we==0),
   .i_addr(i_addr[g*24+:24]),.i_mask(i_mask[g*16+:16]),.i_data(i_data[g*512+:512]),.slot_id(3'(g)),
   .rq_v(qv[g]),.rq_slot(qs[g*3+:3]),.rq_ptr(qp[g*6+:6]),
   .rqf_v(qv[g+1]),.rqf_slot(qs[(g+1)*3+:3]),.rqf_ptr(qp[(g+1)*6+:6]),
   .rv(rv[g]),.rd(rd[g*551+:551]),.ov(rv[g+1]),.od(rd[(g+1)*551+:551]),.fault(sf[g]));
 end endgenerate
 assign fault=cf || |sf;
endmodule
