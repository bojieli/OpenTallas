`timescale 1ns/1ps
// Real HOST parent record face. send_kind is a compiler-owned slot:1 BEGIN,
// 2 AUTH,3 accepted native context. No observed valid chooses a launch cycle.
// Each source codec has one register; final shared pin register adds one.
module qkd_host_record_port(
 input wire ck,rst_n,input wire[1:0]send_kind,
 input wire request_v,input wire[58:0]request_tag,input wire[1:0]request_gen,
 input wire[17:0]request_token,request_position,
 input wire token_epoch_valid,input wire[15:0]token_epoch,
 input wire begin_v,input wire[15:0]begin_epoch,input wire[10:0]expected_pw,input wire[3:0]expected_dw,
 input wire auth_v,input wire[15:0]auth_epoch,input wire[63:0]auth_digest,
 input wire program_ready,input wire[15:0]program_epoch,input wire[63:0]program_digest,
 input wire authorized_footer_valid,input wire[63:0]authorized_footer,
 input wire witness_slot,rx_v,input wire[547:0]rx_record,
 output wire commit_v,installed_valid,installed_fusedcap,
 output wire[15:0]commit_epoch,output wire[63:0]commit_digest,
 output reg tx_v,tx_observed_v,output reg[547:0]tx_record,output wire fault
);
 wire av,ao,af,cv,co,cf,wf;wire[547:0]ar,cr;
 qkd_program_auth_tx u_auth(.ck(ck),.rst_n(rst_n),.send_slot(send_kind==1||send_kind==2),.send_type(send_kind),
 .begin_v(begin_v),.begin_epoch(begin_epoch),.expected_pw(expected_pw),.expected_dw(expected_dw),
 .auth_v(auth_v),.auth_epoch(auth_epoch),.auth_digest(auth_digest),.tx_v(av),.tx_observed_v(ao),.tx_record(ar),.fault(af));
 qkd_host_native_context_tx u_context(.ck(ck),.rst_n(rst_n),.send_slot(send_kind==3),
 .request_v(request_v),.request_tag(request_tag),.request_gen(request_gen),.request_token(request_token),.request_position(request_position),
 .token_epoch_valid(token_epoch_valid),.token_epoch(token_epoch),.program_ready(program_ready),.installed_fusedcap(installed_fusedcap),
 .program_epoch(program_epoch),.program_digest(program_digest),.tx_v(cv),.tx_observed_v(co),.tx_record(cr),.fault(cf));
 qkd_program_witness_rx u_witness(.ck(ck),.rst_n(rst_n),.program_begin_v(begin_v),.receive_slot(witness_slot),.rx_v(rx_v),.rx_record(rx_record),
 .expected_epoch(auth_epoch),.expected_digest(auth_digest),.authorized_footer_valid(authorized_footer_valid),.authorized_footer(authorized_footer),
 .program_commit_v(commit_v),.program_commit_epoch(commit_epoch),.program_commit_digest(commit_digest),
 .program_installed_valid(installed_valid),.installed_fusedcap(installed_fusedcap),.fault(wf));
 assign fault=af|cf|wf;
 always @(posedge ck or negedge rst_n)
 if(!rst_n)begin tx_v<=0;tx_observed_v<=0;tx_record<=0;end
 else begin tx_v<=av|cv;tx_observed_v<=ao|co;tx_record<=cv?cr:ar;end
endmodule
