// Additive real source wrapper: observation guard precedes BOTH effects. Original
// source is unchanged. No hierarchical reads of original protected state.
module ot_hbm_credit_source_session #(parameter integer ENABLE=0)(
 input wire clk,rst_n,cold_link_start,input wire[23:0]link_epoch,
 input wire reserve_valid,output wire reserve_ready,
 input wire grant_valid,output wire grant_ready,input wire[71:0]grant_word,
 output wire ack_valid,input wire ack_ready,output wire[71:0]ack_word,
 output wire debt_zero,initial_ack_seen,fault
);
 wire allow,srr,sgr,sf,df,ofault;
 assign reserve_ready=srr&&allow&&!fault;assign grant_ready=sgr&&allow&&!fault;
 ot_hbm_credit_source #(.ENABLE(ENABLE)) source(clk,rst_n,cold_link_start,link_epoch,
 reserve_valid&&allow&&!fault,srr,grant_valid&&allow&&!fault,sgr,grant_word,ack_valid,ack_ready,ack_word,sf);
 ot_hbm_credit_source_debt #(.ENABLE(ENABLE)) debt(clk,rst_n,cold_link_start,link_epoch,
 reserve_valid&&reserve_ready,grant_valid&&grant_ready,grant_word,allow,debt_zero,df);
 ot_hbm_initial_credit_ack_observer #(.ENABLE(ENABLE)) initial_ack(clk,rst_n,link_epoch,
 ack_valid,ack_ready,ack_word,initial_ack_seen,ofault);
 assign fault=sf||df||ofault;
endmodule
