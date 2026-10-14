`timescale 1ns/1ps
// Functional integration candidate only. The caller supplies ACTUAL accepted
// SU writes and ACTUAL backing-memory read/write/commit transactions.
// There is no golden-output or current-token KV preload path in this module.
module ot_qwen_tp8_native_services_frontend (
    input wire clk,rst_n,
    input wire epoch_begin,input wire [15:0] epoch,input wire [5:0] layer,input wire [17:0] pos,
    output wire epoch_ready,
    input wire kv_issue_accepted,input wire [1:0] kv_issue_kind,
    input wire [17:0] kv_issue_nout,kv_issue_nin,output wire kv_admit_ready,
    input wire [63:0] kv_we,input wire [1535:0] kv_waddr,input wire [2047:0] kv_wdata,
    output wire formatter_emitted,output wire kv_committed,
    input wire qr_vm_committed,
    output wire q_vm_req_v,input wire q_vm_req_ready,output wire [15:0] q_vm_req_epoch,
    output wire [2:0] q_vm_req_chunk,output wire [23:0] q_vm_req_a0,q_vm_req_a1,
    input wire q_vm_rsp_v,input wire [15:0] q_vm_rsp_epoch,input wire [2:0] q_vm_rsp_chunk,
    input wire [2047:0] q_vm_rsp_data,
    output wire row_v,input wire row_ready,output wire row_kind,
    output wire [15:0] row_epoch,output wire [5:0] row_layer,output wire [17:0] row_pos,
    output wire [1023:0] row_data,
    input wire [3:0] store_ack_v,store_ack_kind,input wire [63:0] store_ack_epoch,
    input wire [23:0] store_ack_layer,input wire [71:0] store_ack_pos,
    output wire [3:0] store_ack_credit,
    input wire native_go,input wire fused_program_capability,
    input wire [23:0] native_xbase,native_obase,
    input wire [17:0] native_nout,native_k,native_pos,
    output wire native_ready,native_idle,output wire [15:0] native_progress,
    output wire native_completed,output wire fault,
    input wire [15:0] active_epoch, input wire [5:0] active_layer,
    output wire attn_vm_valid,input wire attn_vm_ready,
    output wire [23:0] attn_vm_word_addr,output wire [511:0] attn_vm_data,
    output wire [4:0] attn_vm_beat,output wire [15:0] attn_vm_epoch,output wire [5:0] attn_vm_layer,
    input wire attn_commit_valid,input wire [4:0] attn_commit_beat,
    input wire [15:0] attn_commit_epoch,input wire [5:0] attn_commit_layer,
    output wire kernel_request_valid,
    output wire [15:0] kernel_request_epoch, output wire [5:0] kernel_request_layer,
    output wire [17:0] kernel_request_position, output wire kernel_capability,
    output wire kernel_q_valid, output wire [4:0] kernel_q_beat, output wire [511:0] kernel_q_data,
    input wire kernel_ready, kernel_busy, kernel_fault, kernel_done, kernel_q_ready,
    input wire kernel_result_valid, output wire kernel_result_ready,
    input wire [4:0] kernel_result_beat, input wire [511:0] kernel_result_data,
    input wire [15:0] kernel_result_epoch, input wire [5:0] kernel_result_layer
);
    reg [15:0] held_epoch;reg [5:0] held_layer;reg [17:0] held_pos;
    reg descriptor_fault;
    wire provider_fault,provider_epoch_ready,join_fault,join_ready,join_idle;
    wire q_start,q_start_ready,q_valid,q_ready,q_done;
    wire [5:0] q_beat;wire [511:0] q_data;wire [15:0] q_epoch;
    wire [5:0] committed_words;
    wire descriptor_matches = native_xbase==24'd13696 && native_obase==24'd3167 &&
                              native_nout==18'd512 && native_k==18'd128 && native_pos==held_pos;
    assign fault=descriptor_fault||provider_fault||join_fault;
    assign native_ready=join_ready&&descriptor_matches&&!fault;
    assign native_idle=join_idle&&!fault;
    assign native_progress={10'd0,committed_words};
    assign epoch_ready=provider_epoch_ready&&join_idle&&!fault;
    wire accept_epoch=epoch_begin&&epoch_ready;
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin held_epoch<=0;held_layer<=0;held_pos<=0;descriptor_fault<=0;end
        else begin
            if(accept_epoch)begin held_epoch<=epoch;held_layer<=layer;held_pos<=pos;end
            if(epoch_begin&&!epoch_ready)descriptor_fault<=1;
            if(native_go&&!descriptor_matches)descriptor_fault<=1;
            if(q_valid&&q_beat[5])descriptor_fault<=1;
        end
    end
    ot_qfd_native_qkv_provider #(.ENABLE(1)) provider (
        .clk(clk),.rst_n(rst_n),.epoch_begin(accept_epoch),.epoch(epoch),.layer(layer),.pos(pos),
        .epoch_ready(provider_epoch_ready),.kv_issue_accepted(kv_issue_accepted),.kv_issue_kind(kv_issue_kind),
        .kv_issue_nout(kv_issue_nout),.kv_issue_nin(kv_issue_nin),.kv_admit_ready(kv_admit_ready),
        .kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),.formatter_emitted(formatter_emitted),
        .row_v(row_v),.row_ready(row_ready),.row_kind(row_kind),.row_epoch(row_epoch),
        .row_layer(row_layer),.row_pos(row_pos),.row_data(row_data),
        .store_ack_v(store_ack_v),.store_ack_kind(store_ack_kind),.store_ack_epoch(store_ack_epoch),
        .store_ack_layer(store_ack_layer),.store_ack_pos(store_ack_pos),.store_ack_credit(store_ack_credit),
        .kv_committed(kv_committed),.q_start(q_start),.qr_vm_committed(qr_vm_committed),.q_base(24'd13696),
        .q_start_ready(q_start_ready),.vm_req_v(q_vm_req_v),.vm_req_ready(q_vm_req_ready),
        .vm_req_epoch(q_vm_req_epoch),.vm_req_chunk(q_vm_req_chunk),.vm_req_a0(q_vm_req_a0),.vm_req_a1(q_vm_req_a1),
        .vm_rsp_v(q_vm_rsp_v),.vm_rsp_epoch(q_vm_rsp_epoch),.vm_rsp_chunk(q_vm_rsp_chunk),.vm_rsp_data(q_vm_rsp_data),
        .q_v(q_valid),.q_ready(q_ready),.q_beat(q_beat),.q_data(q_data),.q_epoch(q_epoch),
        .q_emitted_done(q_done),.fault(provider_fault));
    ot_qwen_tp8_native_attention_frontend joined (
        .clk(clk),.rst_n(rst_n),.request_valid(native_go&&descriptor_matches),.request_ready(join_ready),
        .fused_program_capability(fused_program_capability),.request_epoch(held_epoch),.request_layer(held_layer),
        .request_position(held_pos),.kv_landing_committed({4{kv_committed}}),.q_reader_idle(q_start_ready),
        .q_reader_start(q_start),.q_valid(q_valid),.q_ready(q_ready),.q_beat(q_beat[4:0]),.q_data(q_data),
        .q_epoch(q_epoch),.q_layer(held_layer),
        .active_epoch(active_epoch),.active_layer(active_layer),
        .vm_valid(attn_vm_valid),.vm_ready(attn_vm_ready),.vm_word_addr(attn_vm_word_addr),.vm_data(attn_vm_data),
        .vm_beat(attn_vm_beat),.vm_epoch(attn_vm_epoch),.vm_layer(attn_vm_layer),
        .commit_valid(attn_commit_valid),.commit_beat(attn_commit_beat),.commit_epoch(attn_commit_epoch),
        .commit_layer(attn_commit_layer),.idle(join_idle),.completed(native_completed),.fault(join_fault),
        .committed_words(committed_words),
        .kernel_request_valid(kernel_request_valid),.kernel_request_epoch(kernel_request_epoch),
        .kernel_request_layer(kernel_request_layer),.kernel_request_position(kernel_request_position),
        .kernel_capability(kernel_capability),.kernel_q_valid(kernel_q_valid),.kernel_q_beat(kernel_q_beat),
        .kernel_q_data(kernel_q_data),.service_ready(kernel_ready),.service_busy(kernel_busy),
        .service_fault(kernel_fault),.service_done(kernel_done),.service_q_ready(kernel_q_ready),
        .result_valid(kernel_result_valid),.result_ready(kernel_result_ready),.result_beat(kernel_result_beat),
        .result_data(kernel_result_data),.result_epoch(kernel_result_epoch),.result_layer(kernel_result_layer));
endmodule
