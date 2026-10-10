`timescale 1ns/1ps
`default_nettype none
// Opt-in G25 transport engine. The existing protected inject store contains
// at most PFMAX flits of owned rows (including row-zero padding). Each load
// request asks the frontend to stage the next complete-row chunk before go.
// All M rows are accepted up to M2048; M18/W32 takes two native epochs.
// Frontend obligation: obtain OWNED/M, stage HBM rows and retire only after the
// protected destination store acknowledges every output; this wrapper does not
// pretend those pending generic descriptor/HBM bindings are implemented.
module ot_hgi_coll_row_native #(
 parameter integer ENABLE=0,MUT_ORDER=0,DELCRED=0,NOG=12,PFMAX=512,NPT=8,INJ=2,DEL=4,FW=512,PWT=FW+33
)(
 input wire clk,rst_n,
 input wire start,output wire ready,
 input wire [7:0] rank,group_size,destinations,
 input wire [15:0] slots,row_words,
 output wire load_v, input wire load_r,
 output wire [15:0] load_row,load_rows,
 output wire [INJ*16-1:0] inj_idx,output wire [INJ-1:0] inj_rd,
 input wire [INJ*FW-1:0] inj_data,
 output wire [NPT-1:0] ph_tx_v,output wire [NPT*PWT-1:0] ph_tx_flit,
 input wire [NPT-1:0] sw_cr_ret,ph_rx_v,input wire [NPT*PWT-1:0] ph_rx_flit,
 output wire [NPT-1:0] rx_credit,
 output reg [DEL-1:0] out_v,output reg [DEL*FW-1:0] out_data,
 output reg [DEL*20-1:0] out_row,output reg [DEL*16-1:0] out_word,
 output reg done,output wire fault,output wire [31:0] stat_credit_stall
 ,input wire [DEL-1:0] sink_return
);
 reg [2:0] st;
 reg [7:0] R,G,D,GB;
 reg [15:0] W,PF,remaining,chunk,row_base; reg [19:0] row_bias;reg invalid;
 wire ep_ready,ep_done,ep_fault,map_fault,map_done;
 wire [DEL-1:0] dv;wire [DEL*PWT-1:0] df;
 wire [DEL-1:0] del_permit,del_reserve;wire credit_fault;wire[DEL*8-1:0] credits;
 wire publisher_drained=(DELCRED==0)||(credits=={DEL{8'd128}});
 reg[31:0] publisher_stalls;
 always @(posedge clk or negedge rst_n)if(!rst_n)publisher_stalls<=0;
 else if(DELCRED!=0&&st==2&&del_permit!={DEL{1'b1}})publisher_stalls<=publisher_stalls+1;
 ot_hgi_coll_delivery_credit #(.ENABLE(DELCRED),.DEL(DEL),.CAP(128)) credit(
  .clk(clk),.rst_n(rst_n),.reserve(del_reserve),.credit_return(sink_return),
  .permit(del_permit),.fault(credit_fault),.credits(credits));
 wire [15:0] cap=(row_words==9)?16'(PFMAX/9):(row_words==16)?16'(PFMAX/16):16'(PFMAX/32);
 wire [15:0] first_chunk=slots<cap?slots:cap;
 wire [15:0] next_cap=(W==9)?16'(PFMAX/9):(W==16)?16'(PFMAX/16):16'(PFMAX/32);
 wire [15:0] next_chunk=remaining<next_cap?remaining:next_cap;
 wire [DEL-1:0] mv;wire [DEL*FW-1:0] md;wire [DEL*20-1:0] mr;wire [DEL*16-1:0] mw;
 assign ready=ENABLE!=0 && st==0 && ep_ready && !ep_done && !map_done && publisher_drained;
 assign load_v=ENABLE!=0 && st==1&&!invalid;assign load_row=row_base;assign load_rows=chunk;
 wire launch=(st==1)&&load_r&&ep_ready&&!map_done&&!ep_done&&!invalid;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin st<=0;invalid<=0;R<=0;G<=0;D<=0;GB<=0;W<=0;PF<=0;
 remaining<=0;chunk<=0;row_base<=0;row_bias<=0;out_v<=0;done<=0;end
  else if(ENABLE!=0)begin
   done<=0;out_v<=mv & {DEL{!fault}};out_data<=md;out_word<=mw;
   for(integer l=0;l<DEL;l=l+1)out_row[l*20+:20]<=mr[l*20+:20]+row_bias;
   case(st)
    0:if(start&&ready)begin
     R<=rank;G<=group_size;D<=destinations;W<=row_words;PF<=first_chunk*row_words;
     remaining<=slots;chunk<=first_chunk;row_base<=0;row_bias<=0;
     GB<=group_size==96?0:(rank&~(group_size-8'd1));
     invalid<=slots==0||slots>2048||cap==0||
       !(row_words==9||row_words==16||row_words==32)||
       !(group_size==1||group_size==2||group_size==4||group_size==8||group_size==96)||
       rank>=96||destinations==0||destinations>group_size;
     st<=1;
    end
    1:if(invalid)st<=4;else if(launch)st<=2;
    2:if(ep_fault||map_fault)st<=4;else if(map_done)begin
      remaining<=remaining-chunk;row_base<=row_base+chunk;row_bias<=row_bias+chunk*G;st<=3;
    end
    3:if(ep_ready&&!ep_done&&!map_done&&publisher_drained)begin
      if(remaining==0)begin done<=1;st<=0;end
      else begin chunk<=next_chunk;PF<=next_chunk*W;st<=1;end
    end
    4:;
   endcase
   if(credit_fault)begin st<=4;done<=0;out_v<=0;end
  end
 end
 assign fault=invalid||ep_fault||map_fault||credit_fault;
 ot_hbm_accel_tu_endpoint_psg #(.ENABLE(ENABLE),.DELCRED(DELCRED),.REARM(1),.NOG(NOG),.PFMAX(PFMAX),.NPT(NPT),.INJ(INJ),.DEL(DEL)) ep(
  .clk(clk),.rst_n(rst_n),.pclk(clk),.prst_n(rst_n),.rank(R),.gsz(G==96?4'd3:G==8?4'd3:G==4?4'd2:G==2?4'd1:4'd0),
  .mcast_group_size(G),.mcast_all(G==96),.byp(1'b1),.res_bf16(1'b0),.pf(PF),.go(launch),
  .start_ready(ep_ready),.done_valid(ep_done),.done_ready(map_done),.fault_ack(1'b0),
  .inj_idx(inj_idx),.inj_rd(inj_rd),.inj_data(inj_data),.ph_tx_v(ph_tx_v),.ph_tx_flit(ph_tx_flit),
  .sw_cr_ret(sw_cr_ret),.ph_rx_v(ph_rx_v),.ph_rx_flit(ph_rx_flit),.rx_credit(rx_credit),
  .del_valid(dv),.del_flit(df),.del_permit(del_permit),.del_reserve(del_reserve),.fault(ep_fault),.stat_credit_stall(stat_credit_stall));
 ot_hgi_coll_slot_map #(.ENABLE(ENABLE),.DEL(DEL),.FW(FW),.PWT(PWT),.MUT_ORDER(MUT_ORDER)) map(
  .clk(clk),.rst_n(rst_n),.start(launch),.group_size(G),.group_base(GB),.rank(R),.destinations(D),
  .flits_per_rank(PF),.row_words(W),.in_v(dv),.in_flit(df),.endpoint_done(ep_done),
  .out_v(mv),.out_data(md),.out_row(mr),.out_word(mw),.done(map_done),.fault(map_fault));
endmodule
`default_nettype wire
