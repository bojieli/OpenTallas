`timescale 1ns/1ps
// Static sharing of ONE existingNP8 read1; ordinaryFIFO/credits only.
// Native responses follow actualportorder. No extraVMports, readlease,
// complementarycontrolstate, authorization or resetepoch hardware.
module ot_s81_vm_read_share #(parameter integer ENABLE=0)(
 input wire clk,rst_n,input wire hop_re,input wire[13:0] hop_row,
 output wire hop_rsp_valid,output wire[511:0] hop_rsp_data,
 input wire hc_req_valid,output wire hc_req_ready,input wire[13:0] hc_req_row,
 output wire hc_rsp_valid,output wire[511:0] hc_rsp_data,
 output wire vm_re,output wire[13:0] vm_row,
 input wire vm_rsp_valid,input wire[511:0] vm_rsp_data,input wire vm_fault,output reg fault
);
 reg[13:0] hop_rows[0:31],hc_row_q;reg owners[0:63];
 reg[4:0] hp,ht;reg[5:0] hc,hop_owned,op,ot;reg[6:0] oc;
 reg hc_owned,hc_pending,turn;
 wire safe=ENABLE&&!fault&&!vm_fault;
 wire take_rsp=safe&&vm_rsp_valid&&oc!=0;
 wire hop_return=take_rsp&&!owners[op],hc_return=take_rsp&&owners[op]&&hc_owned;
 assign hop_rsp_valid=hop_return;assign hop_rsp_data=vm_rsp_data;
 assign hc_rsp_valid=hc_return;assign hc_rsp_data=vm_rsp_data;
 wire hop_push=safe&&hop_re&&((hop_owned<32)||hop_return);
 assign hc_req_ready=safe&&!hc_owned;wire hc_push=hc_req_valid&&hc_req_ready;
 wire choose_hc=hc_pending&&((hc==0)||turn);
 wire issue=safe&&((hc!=0)||hc_pending)&&((oc<33)||take_rsp);
 assign vm_re=issue;assign vm_row=choose_hc?hc_row_q:hop_rows[hp];
 wire hop_pop=issue&&!choose_hc;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin hp<=0;ht<=0;hc<=0;hop_owned<=0;op<=0;ot<=0;oc<=0;
   hc_owned<=0;hc_pending<=0;turn<=0;fault<=0;end
  else if(!fault)begin
   if(vm_fault||(!ENABLE&&(hop_re||hc_req_valid))||(hop_re&&!hop_push)||
     (vm_rsp_valid&&(oc==0||(owners[op]&&!hc_owned)||(!owners[op]&&hop_owned==0))))fault<=1;
   else begin
    hp<=hp+hop_pop;ht<=ht+hop_push;hc<=hc+hop_push-hop_pop;
    hop_owned<=hop_owned+hop_push-hop_return;op<=op+take_rsp;ot<=ot+issue;oc<=oc+issue-take_rsp;
    if(hc_push)hc_owned<=1;else if(hc_return)hc_owned<=0;
    if(hc_push)hc_pending<=1;else if(issue&&choose_hc)hc_pending<=0;
    if(issue)turn<=!choose_hc;
    if(hop_push)hop_rows[ht]<=hop_row;if(hc_push)hc_row_q<=hc_req_row;
    if(issue)owners[ot]<=choose_hc;
   end
  end
 end
endmodule

// Exact existing two-slot adapter facade. Actual hard master still has NP8:
// bind these words to slots0/1 only under the selected scheduler reservation.
// ENABLE=0 keeps the historical write0/read1 adapter byte-for-byte behavior.
module ot_s81_vm_shared_adapter #(parameter integer ENABLE=0)(
 input wire clk,rst_n,input wire we,input wire[13:0] wa,input wire[511:0] wd,
 input wire re,input wire[13:0] ra,output wire rq_v,output wire[511:0] rq,
 input wire hc_req_valid,output wire hc_req_ready,input wire[13:0] hc_req_row,
 output wire hc_rsp_valid,output wire[511:0] hc_rsp_data,
 output wire[1:0] i_v,output wire[1:0] i_we,output wire[27:0] i_row,
 output wire[31:0] i_mask,output wire[1023:0] i_d,
 input wire[1:0] o_v,input wire[1023:0] o_d,input wire vm_fault,output wire fault
);
 generate if(ENABLE)begin:g_share
  wire vr;wire[13:0] va;
  ot_s81_vm_read_share #(.ENABLE(1)) share(.clk(clk),.rst_n(rst_n),
   .hop_re(re),.hop_row(ra),.hop_rsp_valid(rq_v),.hop_rsp_data(rq),
   .hc_req_valid(hc_req_valid),.hc_req_ready(hc_req_ready),.hc_req_row(hc_req_row),
   .hc_rsp_valid(hc_rsp_valid),.hc_rsp_data(hc_rsp_data),
   .vm_re(vr),.vm_row(va),.vm_rsp_valid(o_v[1]),.vm_rsp_data(o_d[512+:512]),
   .vm_fault(vm_fault||o_v[0]),.fault(fault));
  assign i_v={vr,we};assign i_we=2'b01;assign i_row={va,wa};
  assign i_mask={16'd0,16'hffff};assign i_d={512'd0,wd};
 end else begin:g_legacy
  ot_s81_vm_adapter legacy(.clk(clk),.rst_n(rst_n),.we(we),.wa(wa),.wd(wd),
   .re(re),.ra(ra),.i_v(i_v),.i_we(i_we),.i_row(i_row),.i_mask(i_mask),.i_d(i_d),
   .o_v(o_v),.o_d(o_d),.vm_fault(vm_fault),.rq_v(rq_v),.rq(rq),.fault(fault));
  assign hc_req_ready=0;assign hc_rsp_valid=0;assign hc_rsp_data=0;
 end endgenerate
endmodule
