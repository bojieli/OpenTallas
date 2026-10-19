// P3 source/destination landing through the EXISTING characterized 1R1W2C
// 16x546 macro. Both native clocks are bound directly, without generated clocks.
`timescale 1ns/1ps
`default_nettype none
module hnx_pl_land_sram #(parameter integer W=2069,D=4,K=2,MUT=0,
 parameter integer AW=$clog2(D))(
 input wire ck_w,ck_r,rsi_w,rsi_r,
 input wire [W-1:0] i,
 output wire [W-1:0] o
);
 localparam integer NB=(W+545)/546;
 localparam integer NG=(W+31)/32;
 reg rq_w,rq_r;
 reg [AW:0] wc,rc;
 wire warm;
 wire [NG-1:0] valid_q;
 reg [D-1:0] v;
 reg [AW:0] epoch[0:D-1];
 wire [AW:0] exp_=rc-K;
 wire [AW-1:0] sel=(MUT==1)?exp_[AW-1:0]+1'b1:exp_[AW-1:0];
 wire [AW-1:0] write_slot=(MUT==2)?wc[AW-1:0]+1'b1:wc[AW-1:0];
 wire [3:0] wa=write_slot;
 wire [3:0] ra=sel;
 wire [NB*546-1:0] wd={{(NB*546-W){1'b0}},i};
 wire [NB*546-1:0] rd;
 wire read_enable=(MUT==3)?1'b1:(warm&&v[sel]);
 always @(posedge ck_w) rq_w<=rsi_w;
 always @(posedge ck_r) rq_r<=rsi_r;
 always @(posedge ck_w) begin
  if(!rq_w) begin wc<=0;v<=0;end
  else begin wc<=wc+1'b1;v[wc[AW-1:0]]<=1'b1;epoch[wc[AW-1:0]]<=wc;end
 end
 always @(posedge ck_r) begin
  if(!rq_r) rc<=0;
  else rc<=rc+1'b1;
 end
 wire [(NG+21)/22-1:0] warm_group;
 assign warm=warm_group[0];
 genvar vg;
 generate for(vg=0;vg<(NG+21)/22;vg=vg+1) begin:g_control
  localparam integer NV=(NG-vg*22>=22)?22:NG-vg*22;
  (* keep=1, dont_touch=1 *) hnx_land_valid_group #(.NC(NV),.D(D),.AW(AW)) u_valid (
   .ck(ck_r),.rq(rq_r),.start(rc==K-1),.vld(v),.sel(sel),
   .warm(warm_group[vg]),.valid_q(valid_q[vg*22+:NV]));
 end endgenerate
 genvar b,g;
 generate for(b=0;b<NB;b=b+1) begin:g_bank
  ot_sram_1r1w2c_16x546_m1 u_mem(.wclk(ck_w),.rclk(ck_r),
   .w_ce_in(rq_w),.w_addr_in(wa),.wd_in(wd[b*546+:546]),.w_mask_in({546{1'b1}}),
   .r_ce_in(read_enable),.r_addr_in(ra),.rd_out(rd[b*546+:546]));
 end
 for(g=0;g<NG;g=g+1) begin:g_valid
  localparam integer BITS=(W-g*32>=32)?32:W-g*32;
  assign o[g*32+:BITS]=rd[g*32+:BITS]&{BITS{valid_q[g]}};
 end endgenerate
`ifndef SYNTHESIS
 reg fault=0;
 always @(posedge ck_r) if(warm&&v[sel]&&epoch[sel]!==exp_&&!fault) begin
  fault<=1;$error("HNXLAND epoch or wrong-bank fault");
 end
 initial if(D>16 || D<4 || (D&(D-1)) || K<1 || K>=D) $fatal(1,"HNXLAND invalid shape");
`endif
endmodule
// Independent kept control groups bound each warm/valid critical fanout to22.
(* keep_hierarchy=1 *) module hnx_land_valid_group #(parameter integer NC=22,D=4,AW=2)(
 input wire ck,rq,start,
 input wire [D-1:0] vld,
 input wire [AW-1:0] sel,
 output reg warm,
 output wire [NC-1:0] valid_q
);
 always @(posedge ck) begin
  if(!rq) warm<=0;
  else if(start) warm<=1;
 end
 genvar g;
 generate for(g=0;g<NC;g=g+1) begin:g_copy
  (* keep=1, dont_touch=1 *) hnx_land_valid_one u_q(.ck(ck),.d(warm&&vld[sel]),.q(valid_q[g]));
 end endgenerate
endmodule
(* keep_hierarchy=1 *) module hnx_land_valid_one(input wire ck,d,output reg q);
 always @(posedge ck) q<=d;
endmodule
`default_nettype wire
