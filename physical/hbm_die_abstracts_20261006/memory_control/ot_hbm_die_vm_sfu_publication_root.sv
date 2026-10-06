`timescale 1ps/1fs
`default_nettype none
// Actual native64FP32 result-to-VM parent composition, default OFF.
// Exactly ONE existing publication root (32SRAMs) and ONE result publisher.
// No arithmetic/controller/provider replica; sourceframe/lease are real inputs.
// Prebuild: sfu_result_publication_prebuild.json. Physical/contextclock OPEN.
module ot_hbm_die_vm_sfu_publication_root #(parameter integer ENABLE=0)(
 input wire clk_sm,por_n,warm_req,
 input wire bind_v,output wire bind_r,input wire [72:0] bind_frame,
 input wire [6:0] bind_rank,input wire [31:0] bind_base,bind_span,
 input wire retire_v,output wire retire_r,input wire [72:0] retire_frame,
 output wire [72:0] held_frame,output wire retained,warm_ack,fault,
 input wire activation_wr_v,output wire activation_wr_r,
 input wire [72:0] activation_wr_frame,input wire activation_wr_bank,
 input wire [6:0] activation_wr_addr,input wire [2062:0] activation_wr_data,
 input wire [191:0] activation_wr_owner,
 output wire activation_ACK_v,input wire activation_ACK_r,
 output wire [72:0] activation_ACK_frame,output wire [191:0] activation_ACK_owner,
 input wire activation_rd_v,output wire activation_rd_r,
 input wire [72:0] activation_rd_frame,input wire activation_rd_bank,
 input wire [6:0] activation_rd_addr,input wire [191:0] activation_rd_owner,
 output wire [3:0] tap_v,input wire [3:0] tap_r,
 output wire [4*2063-1:0] tap_data,output wire [4*192-1:0] tap_owner,
 output wire [4*73-1:0] tap_frame,output wire [3:0] tap_source_clk,
 input wire [3:0] tap_ACK_v,output wire [3:0] tap_ACK_r,
 input wire [4*192-1:0] tap_ACK_owner,input wire [4*73-1:0] tap_ACK_frame,
 output wire activation_release,input wire activation_release_r,
 output wire [72:0] activation_release_frame,output wire [191:0] activation_release_owner,
 input wire su_pub_v,output wire su_pub_r,input wire [72:0] su_pub_frame,
 input wire [31:0] su_pub_addr,input wire [1023:0] su_pub_data,
 output wire su_ACK_v,input wire su_ACK_r,
 output wire [31:0] publication_ACK_addr,output wire [72:0] publication_ACK_frame,
 input wire index_read_v,output wire index_read_r,input wire [72:0] index_read_frame,
 input wire [6:0] index_read_rank,input wire [31:0] index_read_addr,
 input wire [5:0] index_read_words,input wire [7:0] index_read_tag,
 output wire index_rsp_v,input wire index_rsp_r,output wire [1023:0] index_rsp_data,
 output wire [7:0] index_rsp_tag,output wire [72:0] index_rsp_frame,
 output wire [6:0] index_rsp_rank ,
 input wire sfu_source_owned,
 input wire sfu_enroll_v,output wire sfu_enroll_r,
 input wire [72:0] sfu_enroll_frame,input wire [31:0] sfu_base_word,sfu_tag,
 input wire sfu_rx_v,output wire sfu_rx_r,input wire [1023:0] sfu_rx_data,
 input wire [72:0] sfu_rx_frame,input wire [3:0] sfu_rx_index,input wire sfu_rx_last,
 output wire sfu_publication_done,output wire sfu_complete_v,input wire sfu_complete_r,
 output wire [72:0] sfu_complete_frame,output wire [31:0] sfu_complete_tag,
 output wire sfu_retained,sfu_drained
);

 wire vm_retained,vm_warm_ack,vm_fault,vm_retire_r,publisher_fault;
 wire vm_bind_r,vm_activation_wr_r,vm_activation_rd_r,vm_su_pub_r,vm_index_read_r;
 wire result_pub_v,result_pub_r,result_ACK_v,result_ACK_r;
 wire [1023:0] result_pub_data;wire [72:0] result_pub_frame;wire [31:0] result_pub_addr;
 // Accepted producer debt must reach SRAM before root warm quarantine closes
 // publication admission. New external offers close immediately on warm.
 wire vm_warm_req=warm_req&&sfu_drained;
 assign fault=vm_fault||publisher_fault;
 assign retained=vm_retained||sfu_retained||fault;
 assign warm_ack=vm_warm_ack&&sfu_drained&&!fault;
 assign retire_r=vm_retire_r&&sfu_drained;
 assign bind_r=vm_bind_r&&!warm_req;
 assign activation_wr_r=vm_activation_wr_r&&!warm_req;
 assign activation_rd_r=vm_activation_rd_r&&!warm_req;
 assign su_pub_r=vm_su_pub_r&&!warm_req;
 assign index_read_r=vm_index_read_r&&!warm_req;
 ot_hbm_vm_publication_parent #(.ENABLE(ENABLE)) u_vm(
 .clk_sm(clk_sm),
 .por_n(por_n),
 .warm_req(vm_warm_req),
 .bind_v(bind_v&&!warm_req),
 .bind_r(vm_bind_r),
 .bind_frame(bind_frame),
 .bind_rank(bind_rank),
 .bind_base(bind_base),
 .bind_span(bind_span),
 .retire_v(retire_v&&sfu_drained),
 .retire_r(vm_retire_r),
 .retire_frame(retire_frame),
 .held_frame(held_frame),
 .retained(vm_retained),
 .warm_ack(vm_warm_ack),
 .fault(vm_fault),
 .activation_wr_v(activation_wr_v&&!warm_req),
 .activation_wr_r(vm_activation_wr_r),
 .activation_wr_frame(activation_wr_frame),
 .activation_wr_bank(activation_wr_bank),
 .activation_wr_addr(activation_wr_addr),
 .activation_wr_data(activation_wr_data),
 .activation_wr_owner(activation_wr_owner),
 .activation_ACK_v(activation_ACK_v),
 .activation_ACK_r(activation_ACK_r),
 .activation_ACK_frame(activation_ACK_frame),
 .activation_ACK_owner(activation_ACK_owner),
 .activation_rd_v(activation_rd_v&&!warm_req),
 .activation_rd_r(vm_activation_rd_r),
 .activation_rd_frame(activation_rd_frame),
 .activation_rd_bank(activation_rd_bank),
 .activation_rd_addr(activation_rd_addr),
 .activation_rd_owner(activation_rd_owner),
 .tap_v(tap_v),
 .tap_r(tap_r),
 .tap_data(tap_data),
 .tap_owner(tap_owner),
 .tap_frame(tap_frame),
 .tap_source_clk(tap_source_clk),
 .tap_ACK_v(tap_ACK_v),
 .tap_ACK_r(tap_ACK_r),
 .tap_ACK_owner(tap_ACK_owner),
 .tap_ACK_frame(tap_ACK_frame),
 .activation_release(activation_release),
 .activation_release_r(activation_release_r),
 .activation_release_frame(activation_release_frame),
 .activation_release_owner(activation_release_owner),
 .su_pub_v(su_pub_v&&!warm_req),
 .su_pub_r(vm_su_pub_r),
 .su_pub_frame(su_pub_frame),
 .su_pub_addr(su_pub_addr),
 .su_pub_data(su_pub_data),
 .su_ACK_v(su_ACK_v),
 .su_ACK_r(su_ACK_r),
 .result_pub_v(result_pub_v),
 .result_pub_r(result_pub_r),
 .result_pub_frame(result_pub_frame),
 .result_pub_addr(result_pub_addr),
 .result_pub_data(result_pub_data),
 .result_ACK_v(result_ACK_v),
 .result_ACK_r(result_ACK_r),
 .publication_ACK_addr(publication_ACK_addr),
 .publication_ACK_frame(publication_ACK_frame),
 .index_read_v(index_read_v&&!warm_req),
 .index_read_r(vm_index_read_r),
 .index_read_frame(index_read_frame),
 .index_read_rank(index_read_rank),
 .index_read_addr(index_read_addr),
 .index_read_words(index_read_words),
 .index_read_tag(index_read_tag),
 .index_rsp_v(index_rsp_v),
 .index_rsp_r(index_rsp_r),
 .index_rsp_data(index_rsp_data),
 .index_rsp_tag(index_rsp_tag),
 .index_rsp_frame(index_rsp_frame),
 .index_rsp_rank(index_rsp_rank));
 ot_hbm_vm_sfu_result_publication #(.ENABLE(ENABLE)) u_publication(
 .clk_sm(clk_sm),.por_n(por_n),.warm_req(warm_req),.warm_ack(),
 .enroll_v(sfu_enroll_v),.enroll_r(sfu_enroll_r),.enroll_frame(sfu_enroll_frame),.enroll_base_word(sfu_base_word),.enroll_tag(sfu_tag),
 .owner_valid(sfu_source_owned&&vm_retained&&!vm_fault),.owner_frame(held_frame),
 .rx_v(sfu_rx_v),.rx_r(sfu_rx_r),.rx_data(sfu_rx_data),.rx_frame(sfu_rx_frame),.rx_index(sfu_rx_index),.rx_last(sfu_rx_last),
 .result_pub_v(result_pub_v),.result_pub_r(result_pub_r),.result_pub_data(result_pub_data),.result_pub_frame(result_pub_frame),.result_pub_addr(result_pub_addr),
 .result_ACK_v(result_ACK_v),.result_ACK_r(result_ACK_r),.result_ACK_frame(publication_ACK_frame),.result_ACK_addr(publication_ACK_addr),
 .publication_done(sfu_publication_done),.complete_v(sfu_complete_v),.complete_r(sfu_complete_r),.complete_frame(sfu_complete_frame),.complete_tag(sfu_complete_tag),
 .retained(sfu_retained),.drained(sfu_drained),.fault(publisher_fault));
endmodule
`default_nettype wire
