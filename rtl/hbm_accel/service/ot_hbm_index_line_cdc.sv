`timescale 1ps/1fs
`default_nettype none
// Payload stays SECDED-coded through the crossing and station relay chain.
module ot_hbm_index_coded_pipe #(parameter W=1153,N=24)(
 input wire clk,rst_n,v,input wire[W-1:0]d,
 output wire qv,output wire[W-1:0]q,output reg fault
);
 reg[N-1:0]rv,rv_bar;
 reg[W-1:0]payload[0:N-1];
 wire healthy=rv==~rv_bar;
 assign qv=rv[N-1]&&healthy&&!fault;
 assign q=payload[N-1];
 always@(posedge clk or negedge rst_n)
  if(!rst_n)begin rv<=0;rv_bar<='1;fault<=0;end
  else begin
   rv<={rv[N-2:0],v};rv_bar<={rv_bar[N-2:0],~v};
   if(!healthy)fault<=1;
  end
 always@(posedge clk)begin
  payload[0]<=d;
  for(integer n=1;n<N;n=n+1)payload[n]<=payload[n-1];
 end
endmodule

module ot_hbm_index_line_cdc #(parameter KEYLEG=24,MUT=0)(
 input wire hclk,sclk,rst_n,input wire[8791:0]lines,
 output wire[8791:0]landing_lines,input wire[7:0]landing_credit,
 output wire[7:0]source_credit,output wire fault,output wire corrected
);
 wire[7:0]hf,sf,cf;
 wire[7:0]ce_any;
 assign fault=|hf || |sf || |cf;
 assign corrected=|ce_any;
 for(genvar p=0;p<8;p=p+1)begin:gp
  wire[1152:0]code,received,relayed;
  for(genvar b=0;b<4;b=b+1)begin:data256
   ot_secded_enc #(.K(256),.R(10)) enc(.clk(hclk),.d(lines[p*1099+11+b*256+:256]),.q(code[b*266+:266]));
  end
  ot_secded_enc #(.K(64),.R(8)) enc_tail(.clk(hclk),.d(lines[p*1099+1035+:64]),.q(code[1064+:72]));
  ot_secded_enc #(.K(11),.R(6)) enc_identity(.clk(hclk),.d(lines[p*1099+:11]),.q(code[1136+:17]));
  reg cv,hfault;
  always@(posedge hclk or negedge rst_n)if(!rst_n)cv<=0;else cv<=lines[p*1099];
  wire full_,empty_,wf,rf;wire[2:0]freed;
  wire[1152:0]injected=code ^ ((p==0&&MUT==1)?1153'd1:
   (p==0&&MUT==2)?(1153'd1<<256):(p==0&&MUT==3)?1153'd3:1153'd0);
  wire read_=!empty_&&!rf;
  ot_hbm_accel_cdc_fifo_p2 #(.W(1153),.AW(3)) cross_line(
   .wclk(hclk),.wrst_n(rst_n),.we(cv&&!fault),.wdata(injected),.full(full_),.rd_freed(freed),.w_fault(wf),
   .rclk(sclk),.rrst_n(rst_n),.re(read_),.rdata(received),.empty(empty_),.r_fault(rf));
  always@(posedge hclk or negedge rst_n)if(!rst_n)hfault<=0;else if(cv&&full_)hfault<=1;
  assign hf[p]=hfault||wf;
  wire relay_v,relay_fault;
  ot_hbm_index_coded_pipe #(.W(1153),.N(KEYLEG)) relay(
   .clk(sclk),.rst_n(rst_n),.v(read_),.d(received),.qv(relay_v),.q(relayed),.fault(relay_fault));
  wire[5:0]ov,ce,ue;wire[1087:0]payload;wire[10:0]identity;
  for(genvar b=0;b<4;b=b+1)begin:decode256
   ot_secded_dec #(.K(256),.R(10)) dec(.clk(sclk),.rst_n(rst_n),.v(relay_v),.w(relayed[b*266+:266]),
    .ov(ov[b]),.d(payload[b*256+:256]),.ce(ce[b]),.ue(ue[b]),.n_ce(),.n_ue());
  end
  ot_secded_dec #(.K(64),.R(8)) dec_tail(.clk(sclk),.rst_n(rst_n),.v(relay_v),.w(relayed[1064+:72]),
   .ov(ov[4]),.d(payload[1024+:64]),.ce(ce[4]),.ue(ue[4]),.n_ce(),.n_ue());
  ot_secded_dec #(.K(11),.R(6)) dec_identity(.clk(sclk),.rst_n(rst_n),.v(relay_v),.w(relayed[1136+:17]),
   .ov(ov[5]),.d(identity),.ce(ce[5]),.ue(ue[5]),.n_ce(),.n_ue());
  reg sfault;
  always@(posedge sclk or negedge rst_n)if(!rst_n)sfault<=0;
   else if(rf||relay_fault||(|ue)||((&ov)&&!identity[0]))sfault<=1;
  assign sf[p]=sfault||rf||relay_fault||(|ue);
  assign ce_any[p]=|ce;
  assign landing_lines[p*1099+:1099]={payload,identity[10:1],((&ov)&&identity[0]&&!fault)};
  // Credits are events. A finite queue preserves pulses when the consumer
  // clock is faster; the HBM owner receives at most one pulse per cycle.
  wire cr_v,cr_pipe_fault;wire[1:0]cr_packet;
  ot_hbm_index_coded_pipe #(.W(2),.N(KEYLEG)) credit_relay(
   .clk(sclk),.rst_n(rst_n),.v(landing_credit[p]),.d(2'b01),
   .qv(cr_v),.q(cr_packet),.fault(cr_pipe_fault));
  wire cr_full,cr_empty,cr_wfault,cr_rfault;wire[1:0]cr_received;
  wire cr_read=!cr_empty&&!cr_rfault;
  ot_hbm_accel_cdc_fifo_p2 #(.W(2),.AW(6)) cross_credit(
   .wclk(sclk),.wrst_n(rst_n),.we(cr_v&&!fault),.wdata(cr_packet),.full(cr_full),.rd_freed(),.w_fault(cr_wfault),
   .rclk(hclk),.rrst_n(rst_n),.re(cr_read),.rdata(cr_received),.empty(cr_empty),.r_fault(cr_rfault));
  reg cr_overflow,cr_bad;
  always@(posedge sclk or negedge rst_n)if(!rst_n)cr_overflow<=0;else if(cr_v&&cr_full)cr_overflow<=1;
  always@(posedge hclk or negedge rst_n)if(!rst_n)cr_bad<=0;else if(cr_read&&cr_received!=2'b01)cr_bad<=1;
  assign cf[p]=cr_pipe_fault||cr_wfault||cr_rfault||cr_overflow||cr_bad||(cr_read&&cr_received!=2'b01);
  assign source_credit[p]=cr_read&&cr_received==2'b01&&!fault;
 end
endmodule
`default_nettype wire
