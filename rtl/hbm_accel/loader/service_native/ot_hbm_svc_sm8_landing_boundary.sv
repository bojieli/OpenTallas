// Opt-in pin boundary. Two-entry HBM elasticity is admission-safe with registered ready.
// No production master changes. Native reset release takes two edges in each domain.
`default_nettype none
(* keep_hierarchy = "yes" *) module ot_hbm_landing_pin_segment #(parameter integer W=16)(
 input wire clk,rst_n,push,pop,input wire [W-1:0] data_in,output wire [W-1:0] data_out);
 (* keep = "true" *) reg wp,rp,push_q;
 reg [W-1:0] pin_data;
 reg [W-1:0] slot0,slot1;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin wp<=0;rp<=0;push_q<=0;end
  else begin
   pin_data<=data_in;push_q<=push;
   if(push_q)begin if(wp)slot1<=pin_data;else slot0<=pin_data;wp<=!wp;end
   if(pop)rp<=!rp;
  end
 end
 assign data_out=rp?slot1:slot0;
endmodule

module ot_hbm_svc_sm8_landing_boundary #(
 parameter [2:0] BANK=0, parameter integer RESPONSE_DEPTH=8,LBANKS=4,FMUT=0,
 parameter integer BMUT=0,LB=(LBANKS>2)?2:1,IW=283+LB
)(
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire in_v,output reg in_ready,input wire [IW-1:0] in_data,output reg overflow,
 input wire reserve_v,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,
 input wire [11:0] reserve_total,input wire stop,
 output reg complete_v,output reg [LB-1:0] complete_bank,output reg fault,
 input wire read_v,input wire [LB-1:0] read_bank,input wire [5:0] read_row,
 output reg [255:0] read_data
);
 (* async_reg = "true" *) reg [1:0] hr,sr;
 always @(posedge hbm_clk or negedge hbm_rst_n)
  if(!hbm_rst_n)hr<=0;else hr<={hr[0],1'b1};
 always @(posedge stream_clk or negedge stream_rst_n)
  if(!stream_rst_n)sr<=0;else sr<={sr[0],1'b1};
 wire hreset=hr[1],sreset=sr[1];
 wire core_ready,core_overflow,core_complete,core_fault;
 wire [LB-1:0] core_bank;
 wire [255:0] core_data;
 wire [IW-1:0] head;
 reg [1:0] used;
 reg ingress_fault,pending;
 wire push=in_v&&in_ready;
 wire pop=(used>{1'b0,pending})&&core_ready;
 wire [1:0] used_next=used+{1'b0,push}-{1'b0,pop};
 always @(posedge hbm_clk or negedge hreset)begin
  if(!hreset)begin used<=0;pending<=0;in_ready<=0;ingress_fault<=0;overflow<=0;end
  else begin
   used<=used_next;pending<=push;
   // BMUT=1 deliberately omits occupancy reservation; bench must catch loss.
   in_ready<=BMUT==1?core_ready:(used_next<2);
   if(in_v&&!in_ready)ingress_fault<=1;
   overflow<=ingress_fault||core_overflow;
  end
 end
 genvar g;
 generate for(g=0;g<(IW+15)/16;g=g+1)begin:g_pin
  localparam integer W=(IW-16*g>=16)?16:IW-16*g;
  (* keep_hierarchy = "yes" *) ot_hbm_landing_pin_segment #(.W(W)) u_segment(
   .clk(hbm_clk),.rst_n(hreset),.push(push),.pop(pop),
   .data_in(in_data[16*g+:W]),.data_out(head[16*g+:W]));
 end endgenerate
 reg rv_q,stop_q,read_q;
 reg [LB-1:0] rb_q,readb_q;
 reg [15:0] re_q;
 reg [11:0] rt_q;
 reg [5:0] row_q;
 always @(posedge stream_clk or negedge sreset)begin
  if(!sreset)begin
   rv_q<=0;stop_q<=1;read_q<=0;rb_q<=0;readb_q<=0;re_q<=0;rt_q<=0;row_q<=0;
   complete_v<=0;complete_bank<=0;fault<=0;read_data<=0;
  end else begin
   rv_q<=reserve_v;rb_q<=reserve_bank;re_q<=reserve_epoch;rt_q<=reserve_total;
   stop_q<=stop;read_q<=read_v;readb_q<=read_bank;row_q<=read_row;
   complete_v<=core_complete;complete_bank<=core_bank;
   fault<=core_fault;read_data<=core_data;
  end
 end
 ot_hbm_svc_sm8_landing_bank_sram285 #(.BANK(BANK),.RESPONSE_DEPTH(RESPONSE_DEPTH),
  .LBANKS(LBANKS),.FMUT(FMUT),.LB(LB),.IW(IW)) u_core(
  .hbm_clk(hbm_clk),.hbm_rst_n(hreset),.stream_clk(stream_clk),.stream_rst_n(sreset),
  .in_v(pop),.in_ready(core_ready),.in_data(head),.overflow(core_overflow),
  .reserve_v(rv_q),.reserve_bank(rb_q),.reserve_epoch(re_q),.reserve_total(rt_q),.stop(stop_q),
  .complete_v(core_complete),.complete_bank(core_bank),.fault(core_fault),
  .read_v(read_q),.read_bank(readb_q),.read_row(row_q),.read_data(core_data));
endmodule
`default_nettype wire
