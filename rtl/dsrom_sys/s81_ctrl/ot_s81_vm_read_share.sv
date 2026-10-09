`timescale 1ns/1ps
// Opt-in arbitration on ONE EXISTING native NP8 read port (documented slot1).
// No new master port and no native ready signal. Hop has32 reserved responses;
// HC owns one request through its real return. VM must preserve this port's
// request order and share the common reset/quiescence fence. Other NP8 owners
// and same-bank schedule capacity remain integration obligations.
module ot_s81_vm_read_share #(parameter integer ENABLE=0)(
 input wire clk,rst_n,
 input wire hop_re,input wire[13:0] hop_row,
 output wire hop_rsp_valid,output wire[511:0] hop_rsp_data,
 input wire hc_req_valid,output wire hc_req_ready,input wire[13:0] hc_req_row,
 output wire hc_rsp_valid,output wire[511:0] hc_rsp_data,
 output wire vm_re,output wire[13:0] vm_row,
 input wire vm_rsp_valid,input wire[511:0] vm_rsp_data,input wire vm_fault,
 output reg fault
);
 reg[27:0] hop_rows[0:31];reg[27:0] hc_row_q;
 reg[1:0] owners[0:63];
 reg[4:0] hp,ht,hp_n,ht_n;
 reg[5:0] hc,hc_n,hop_owned,hop_owned_n;
 reg[5:0] op,ot,op_n,ot_n;reg[6:0] oc,oc_n;
 reg hc_owned,hc_owned_n,hc_pending,hc_pending_n,turn,turn_n;
 wire control_ok=(hp_n==~hp)&&(ht_n==~ht)&&(hc_n==~hc)&&
  (hop_owned_n==~hop_owned)&&(op_n==~op)&&(ot_n==~ot)&&(oc_n==~oc)&&
  (hc_owned_n==!hc_owned)&&(hc_pending_n==!hc_pending)&&(turn_n==!turn)&&
  (hc<=32)&&(hop_owned<=32)&&(oc<=33);
 wire owner_ok=(oc!=0)&&(owners[op][1]==!owners[op][0]);
 wire safe=ENABLE&&!fault&&control_ok&&!vm_fault;
 wire take_rsp=safe&&vm_rsp_valid&&owner_ok;
 wire hop_return=take_rsp&&!owners[op][0];
 wire hc_return=take_rsp&&owners[op][0]&&hc_owned;
 assign hop_rsp_valid=hop_return;assign hop_rsp_data=vm_rsp_data;
 assign hc_rsp_valid=hc_return;assign hc_rsp_data=vm_rsp_data;
 wire hop_push=safe&&hop_re&&((hop_owned<32)||hop_return);
 assign hc_req_ready=safe&&!hc_owned;
 wire hc_push=hc_req_valid&&hc_req_ready;
 wire choose_hc=hc_pending&&((hc==0)||turn);
 wire head_ok=choose_hc?(hc_row_q[27:14]==~hc_row_q[13:0]):
                                   (hop_rows[hp][27:14]==~hop_rows[hp][13:0]);
 wire issue=safe&&((hc!=0)||hc_pending)&&head_ok&&((oc<33)||take_rsp);
 assign vm_re=issue;assign vm_row=choose_hc?hc_row_q[13:0]:hop_rows[hp][13:0];
 wire hop_pop=issue&&!choose_hc;
 wire[4:0] hp_next=hp+hop_pop,ht_next=ht+hop_push;
 wire[5:0] hc_next=hc+hop_push-hop_pop;
 wire[5:0] ho_next=hop_owned+hop_push-hop_return;
 wire[5:0] op_next=op+take_rsp,ot_next=ot+issue;
 wire[6:0] oc_next=oc+issue-take_rsp;
 wire hco_next=hc_push?1'b1:hc_return?1'b0:hc_owned;
 wire hcp_next=hc_push?1'b1:(issue&&choose_hc)?1'b0:hc_pending;
 wire turn_next=issue?!choose_hc:turn;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   hp<=0;ht<=0;hc<=0;hop_owned<=0;op<=0;ot<=0;oc<=0;
   hp_n<=~5'd0;ht_n<=~5'd0;hc_n<=~6'd0;hop_owned_n<=~6'd0;
   op_n<=~6'd0;ot_n<=~6'd0;oc_n<=~7'd0;
   hc_owned<=0;hc_owned_n<=1;hc_pending<=0;hc_pending_n<=1;turn<=0;turn_n<=1;fault<=0;
  end else if(!fault)begin
   if(!control_ok||vm_fault||(!ENABLE&&(hop_re||hc_req_valid))||
      (hop_re&&!hop_push)||
      (vm_rsp_valid&&(!owner_ok||(owners[op][0]&&!hc_owned)||(!owners[op][0]&&hop_owned==0)))||
      (((hc!=0)||hc_pending)&&!head_ok))fault<=1;
   else begin
    hp<=hp_next;hp_n<=~hp_next;ht<=ht_next;ht_n<=~ht_next;
    hc<=hc_next;hc_n<=~hc_next;hop_owned<=ho_next;hop_owned_n<=~ho_next;
    op<=op_next;op_n<=~op_next;ot<=ot_next;ot_n<=~ot_next;oc<=oc_next;oc_n<=~oc_next;
    hc_owned<=hco_next;hc_owned_n<=!hco_next;hc_pending<=hcp_next;hc_pending_n<=!hcp_next;
    turn<=turn_next;turn_n<=!turn_next;
    if(hop_push)hop_rows[ht]<={~hop_row,hop_row};
    if(hc_push)hc_row_q<={~hc_req_row,hc_req_row};
    if(issue)owners[ot]<={!choose_hc,choose_hc};
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
