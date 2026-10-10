`timescale 1ns/1ps
`default_nettype none
// Opt-in G25 transport engine. The existing protected inject store contains
// M rows (including OWNED's row-zero padding), in slot order, before start.
// Frontend obligation: obtain OWNED/M, stage HBM rows and retire only after the
// protected destination store acknowledges every output; this wrapper does not
// pretend those pending generic descriptor/HBM bindings are implemented.
module ot_hgi_coll_row_native #(
 parameter integer ENABLE=0,MUT_ORDER=0,PFMAX=512,NPT=8,INJ=2,DEL=4,FW=512,PWT=FW+33
)(
 input wire clk,rst_n,
 input wire start,output wire ready,
 input wire [7:0] rank,group_size,destinations,
 input wire [15:0] slots,row_words,
 output wire [INJ*16-1:0] inj_idx,output wire [INJ-1:0] inj_rd,
 input wire [INJ*FW-1:0] inj_data,
 output wire [NPT-1:0] ph_tx_v,output wire [NPT*PWT-1:0] ph_tx_flit,
 input wire [NPT-1:0] sw_cr_ret,ph_rx_v,input wire [NPT*PWT-1:0] ph_rx_flit,
 output wire [NPT-1:0] rx_credit,
 output wire [DEL-1:0] out_v,output wire [DEL*FW-1:0] out_data,
 output wire [DEL*20-1:0] out_row,output wire [DEL*16-1:0] out_word,
 output wire done,output wire fault,output wire [31:0] stat_credit_stall
);
 reg [1:0] st;
 reg [7:0] R,G,D,GB;
 reg [15:0] W,PF; reg invalid;
 wire ep_ready,ep_done,ep_fault,map_fault,map_done;
 wire [DEL-1:0] dv;wire [DEL*PWT-1:0] df;
 wire [31:0] span=slots*row_words;
 assign ready=ENABLE!=0 && st==0 && ep_ready && !ep_done && !map_done;
 wire launch=(st==1)&&ep_ready&&!invalid;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin st<=0;invalid<=0;R<=0;G<=0;D<=0;GB<=0;W<=0;PF<=0;end
  else if(ENABLE!=0)begin
   case(st)
    0:if(start&&ready)begin
     R<=rank;G<=group_size;D<=destinations;W<=row_words;PF<=span[15:0];
     GB<=group_size==96?0:(rank&~(group_size-8'd1));
     invalid<=slots==0||span==0||span>PFMAX||
       !(row_words==9||row_words==16||row_words==32)||
       !(group_size==1||group_size==2||group_size==4||group_size==8||group_size==96)||
       rank>=96||destinations==0||destinations>group_size;
     st<=1;
    end
    1:if(invalid)st<=3;else if(launch)st<=2;
    2:if(ep_fault||map_fault)st<=3;else if(map_done)st<=0;
    3:;
   endcase
  end
 end
 assign done=map_done&&!fault;
 assign fault=invalid||ep_fault||map_fault;
 ot_hbm_accel_tu_endpoint_psg #(.ENABLE(ENABLE),.REARM(1),.PFMAX(PFMAX),.NPT(NPT),.INJ(INJ),.DEL(DEL)) ep(
  .clk(clk),.rst_n(rst_n),.pclk(clk),.prst_n(rst_n),.rank(R),.gsz(G==96?4'd3:G==8?4'd3:G==4?4'd2:G==2?4'd1:4'd0),
  .mcast_group_size(G),.mcast_all(G==96),.byp(1'b1),.res_bf16(1'b0),.pf(PF),.go(launch),
  .start_ready(ep_ready),.done_valid(ep_done),.done_ready(map_done),.fault_ack(1'b0),
  .inj_idx(inj_idx),.inj_rd(inj_rd),.inj_data(inj_data),.ph_tx_v(ph_tx_v),.ph_tx_flit(ph_tx_flit),
  .sw_cr_ret(sw_cr_ret),.ph_rx_v(ph_rx_v),.ph_rx_flit(ph_rx_flit),.rx_credit(rx_credit),
  .del_valid(dv),.del_flit(df),.fault(ep_fault),.stat_credit_stall(stat_credit_stall));
 ot_hgi_coll_slot_map #(.ENABLE(ENABLE),.DEL(DEL),.FW(FW),.PWT(PWT),.MUT_ORDER(MUT_ORDER)) map(
  .clk(clk),.rst_n(rst_n),.start(launch),.group_size(G),.group_base(GB),.rank(R),.destinations(D),
  .flits_per_rank(PF),.row_words(W),.in_v(dv),.in_flit(df),.endpoint_done(ep_done),
  .out_v(out_v),.out_data(out_data),.out_row(out_row),.out_word(out_word),.done(map_done),.fault(map_fault));
endmodule
`default_nettype wire
