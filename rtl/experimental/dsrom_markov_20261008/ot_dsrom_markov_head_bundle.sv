`timescale 1ns/1ps
// Opt-in successor minimum bundle. Real B produces n=4*k+q roots; A and
// Markov share released global row identity. Native pre-Markov argmax is unused.
module ot_dsrom_markov_head_bundle #(
 parameter bit ENABLE=0,parameter integer PINREG=0,CACHE_PINREG=0,
 parameter integer VALID_ROWS=128,A_INPUT_STAGES=0,
 parameter [8:0] CUT=511,parameter integer SPLIT9=1,
 parameter integer SK=1+CUT[0]+CUT[1]+CUT[2]+CUT[3]+CUT[4]+CUT[5]+CUT[6]+CUT[7]+CUT[8]+SPLIT9
)(input wire clk,rst_n,input wire start,output wire start_ready,
 input wire[16:0] row0,d_i,input wire[31:0] transaction,
 input wire[255:0] xa,xb,output wire head_go,
 output wire[3:0] joined_valid,output wire[127:0] joined_bits,
 output wire[67:0] joined_row,output reg done,output reg best_valid,
 output reg[16:0] best_row,output reg[31:0] best_bits,output wire fault);
 wire[3:0] sr,er,mg,mv,md,mf,mhave;wire[127:0] mb;wire[67:0] mr;
 wire qr,ev,el,lookup_fault;wire[255:0] ed;wire[3:0] eb;wire[31:0] ei;
 reg busy,control_fault;reg[16:0] base;
 wire accept=start&&start_ready;
 assign start_ready=ENABLE&&!busy&&(&sr)&&qr&&!fault;
 assign head_go=&mg;
 ot_dsrom_markov_embed_rom #(.ENABLE(ENABLE)) lookup(
 .clk(clk),.rst_n(rst_n),.req_valid(accept),.req_ready(qr),.req_token(d_i),.req_id(transaction),
 .out_valid(ev),.out_ready(&er),.out_data(ed),.out_beat(eb),.out_id(ei),.out_last(el),.fault_valid(lookup_fault),.fault_id());
 wire[255:0] xsa,xsb;
 genvar j,q;
 generate for(j=0;j<16;j=j+1)begin:g_sk
  ot_hdc_delay #(.W(16),.D(SK*(j%8))) sa(.clk(clk),.rst_n(rst_n),.d(xa[16*j+:16]),.q(xsa[16*j+:16]));
  ot_hdc_delay #(.W(16),.D(SK*(j%8))) sb(.clk(clk),.rst_n(rst_n),.d(xb[16*j+:16]),.q(xsb[16*j+:16]));
 end endgenerate
 wire bo,bfault;wire[31:0] bd;
 ot_dsrom_head_elem #(.LV(6),.PAD(2),.JOIN(0),.ROWS(128),.CUT(CUT),.SPLIT9(SPLIT9),.INSTANCE("hb"),.SAFE(1)) b(
 .clk(clk),.rst_n(rst_n),.go(head_go),.row0(17'd0),.x(xsb),.b_v(1'b0),.b_d(32'b0),
 .o_v(bo),.o_d(bd),.l_v(),.l_d(),.done(),.best_row(),.best_bits(),.best_key(),.fault(bfault));
 reg[1:0] bq;reg[3:0] bv;reg[31:0] held_b;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin bq<=0;bv<=0;end
 else begin if(head_go)bq<=0;else if(bo)bq<=bq+1;bv<=bo?(4'b1<<bq):0;end
 always @(posedge clk)if(bo)held_b<=bd;
 wire[3:0] af;
 generate for(q=0;q<4;q=q+1)begin:g_a
  localparam integer NVALID=VALID_ROWS<=32*q?0:(VALID_ROWS>=32*(q+1)?32:VALID_ROWS-32*q);
  wire[16:0] driver_row=row0+17'd32*q;wire[16:0] landed_row=base+17'd32*q;
  wire ag,bvalid,hv;wire[16:0] ar;wire[255:0] ax;wire[31:0] ad,hb;
  ot_hdc_delay #(.W(2),.D(A_INPUT_STAGES),.RESET(1)) landing_valid(
   .clk(clk),.rst_n(rst_n),.d({head_go,bv[q]}),.q({ag,bvalid}));
  ot_hdc_delay #(.W(305),.D(A_INPUT_STAGES)) landing_payload(
   .clk(clk),.rst_n(rst_n),.d({landed_row,xsa,held_b}),.q({ar,ax,ad}));
  ot_dsrom_head_elem #(.LV(8),.PAD(0),.JOIN(1),.ROWS(32),.CUT(CUT),.SPLIT9(SPLIT9),.INSTANCE((q==0?"ha0":q==1?"ha1":q==2?"ha2":"ha3")),.SAFE(1)) a(
   .clk(clk),.rst_n(rst_n),.go(ag),.row0(ar),.x(ax),.b_v(bvalid),.b_d(ad),.o_v(),.o_d(),
   .l_v(hv),.l_d(hb),.done(),.best_row(),.best_bits(),.best_key(),.fault(af[q]));
  ot_dsrom_markov_head_driver #(.ENABLE(ENABLE),.PINREG(PINREG),.CACHE_PINREG(CACHE_PINREG),.VALID_ROWS(NVALID),.CUT(CUT),.SPLIT9(SPLIT9),.INSTANCE((q==0?"mk0":q==1?"mk1":q==2?"mk2":"mk3"))) markov(
   .clk(clk),.rst_n(rst_n),.start(accept),.start_ready(sr[q]),.row0(driver_row),.transaction(transaction),
   .embed_valid(ev&&(&er)),.embed_ready(er[q]),.embed_data(ed),.embed_beat(eb),.embed_id(ei),.embed_last(el),
   .head_go(mg[q]),.head_valid(hv),.head_bits(hb),.head_fault(af[q]),
   .joined_valid(joined_valid[q]),.joined_bits(joined_bits[32*q+:32]),.joined_row(joined_row[17*q+:17]),
   .done(md[q]),.best_valid(mhave[q]),.best_row(mr[17*q+:17]),.best_bits(mb[32*q+:32]),.fault(mf[q]));
 end endgenerate
 // Masked first-max: an all-padding A has no candidate, even for negative logits.
 function automatic[31:0] key(input[31:0] v);reg[31:0] z;begin z=(v[30:0]==0)?0:v;key=z[31]?~z:(z^32'h80000000);end endfunction
 function automatic[81:0] pick(input[81:0] u,v);begin
  if(!u[81])pick=v;else if(!v[81])pick=u;
  else pick=(v[80:49]>u[80:49]||(v[80:49]==u[80:49]&&v[48:32]<u[48:32]))?v:u;
 end endfunction
 reg[81:0] c0,c1;wire[81:0] result=pick(c0,c1);reg reduce_valid,reduce_started;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  busy<=0;base<=0;control_fault<=0;done<=0;best_valid<=0;best_row<=0;best_bits<=0;reduce_valid<=0;reduce_started<=0;c0<=0;c1<=0;
 end else begin
  done<=0;reduce_valid<=0;
  if(accept)begin busy<=1;base<=row0;reduce_started<=0;best_valid<=0;end
  if((|mg)&&!(&mg))control_fault<=1;
  if(busy&&(&md)&&!reduce_started&&!fault)begin
   c0<=pick({mhave[0],key(mb[31:0]),mr[16:0],mb[31:0]},{mhave[1],key(mb[63:32]),mr[33:17],mb[63:32]});
   c1<=pick({mhave[2],key(mb[95:64]),mr[50:34],mb[95:64]},{mhave[3],key(mb[127:96]),mr[67:51],mb[127:96]});
   reduce_valid<=1;reduce_started<=1;
  end
  if(reduce_valid&&!fault)begin done<=1;busy<=0;best_valid<=result[81];best_row<=result[48:32];best_bits<=result[31:0];end
 end
 assign fault=lookup_fault|bfault|(|af)|(|mf)|control_fault;
endmodule
