`timescale 1ns/1ps
// Routed SRAM clock/capture context, full G4W16. Still a child, not a full die proof.
module ot_hdc_v41_fh_macro_ctx #(
    parameter integer W  = 16,
    parameter integer G  = 4,
    parameter integer IL = 8,
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer ALAT = 0,
    parameter integer CAPTURE = 0,
    parameter integer RETURN_EXTRA = 2,
    parameter integer PROTECT_SPLIT = 0,
    parameter integer RETIRE = 0,
    parameter integer VM_ENDPOINT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input wire commit_busy,commit_ack_v,
    input wire native_cold_n,native_request_ready,native_reply_capture,native_reply_v,
    input wire [31:0] native_ordinal,
    input wire [46:0] native_request_owner,
    input wire [1266:0] native_checked_reply,
    output wire [2830:0] native_captured_request,native_captured_request_check,
    output wire [1266:0] native_captured_reply,native_captured_reply_check,
    input wire [7:0] commit_ack_id,
    input wire [23:0] commit_ack_word,
    input wire [15:0] commit_ack_mask,
    output wire commit_warm,commit_debt,
    output wire [7:0] commit_id,
    input  wire              s3_v_in,          // the S3 valid that enters the engine's result valid line
    input  wire [1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1-1:0] a_tag_p_in,
    input  wire [G*W*32-1:0] res_in,
    input wire [G-1:0] wr_en,
    input wire [G*AW-1:0] wr_addr,
    input wire [G*W-1:0] wr_mask,
    input wire [G*W*32-1:0] wr_data,
    output wire [G-1:0]      ra_re,
    output wire [G*AW-1:0]   ra_addr,
    input  wire              go_fus,           // a fused op with i_iwe accepted (sets iw_pend)
    input  wire [AW-1:0]     i_iaddr,
    input  wire [4:0]        busy_in,          // active, e_v, s1_v, s1b_v, s2_v (s3_v is s3_v_in)
    input  wire [G-1:0]      o_we1_in,
    input  wire [G*AW-1:0]   o_addr1_in,
    input  wire [G*W-1:0]    o_mask1_in,
    input  wire [G*W-1:0]    leaf_mask_in,
    input  wire [NW-1:0]     leaf_row_in,
    input  wire              tv_in,            // tv[0] input (r_v && r_last && r_amax, as-built)
    input  wire              ov1_in,
    input  wire [NW-1:0]     am_idx_in,
    output wire  [1+1+1+1+1+2+AW+AW+3*(NW+1)+2+AW+3+AW+1-1:0] r_tag,
    output wire               r_v,
    output wire [(1+32+NW)*G*W-1:0] leaf,
    output wire  [G-1:0]      o_we,
    output wire  [G*AW-1:0]   o_addr,
    output wire  [G*W-1:0]    o_mask,
    output wire  [G*W*32-1:0] o_data,
    output wire              fault,
    output wire [G*W*32+G*W+G*AW+G-1:0] result_capture,
    output wire [(1+32+NW)*(G*W/2)-1:0] argmax_level1
);
    wire [G*W*32-1:0] ra_q;
    wire [G*W-1:0] mem_valid,mem_corrected,mem_poison,mem_committed;
    wire memory_fault,child_fault;
    wire [G-1:0] memory_address_fault;
    wire retire_busy,retire_warm_ack,child_warm,child_leaf_v,child_ov;
    wire [159:0] raw_tag;
    wire raw_v;
    wire [G*AW-1:0] raw_addr;
    wire [G*W-1:0] raw_mask;
    wire [G*W*32-1:0] raw_data;
    wire [G-1:0] child_we;
    wire [(1+32+NW)*G*W-1:0] child_leaf;
    ot_hdc_v41_fh_sram_return #(.W(W),.G(G),.AW(AW),.PROTECT_SPLIT(PROTECT_SPLIT)) u_memory (
        .clk(clk),.rst_n(rst_n),.rd_en(ra_re),.rd_addr(ra_addr),.rd_data(ra_q),
        .rd_valid(mem_valid),.corrected(mem_corrected),.poisoned(mem_poison),
        .wr_en(wr_en),.wr_addr(wr_addr),.wr_mask(wr_mask),.wr_data(wr_data),
        .wr_committed(mem_committed),.fault(memory_fault),.address_fault_bits(memory_address_fault));
    ot_hdc_v41_fh_ctx #(.W(W),.G(G),.IL(IL),.AW(AW),.NW(NW),.ALAT(ALAT),
        .CAPTURE(CAPTURE),.RETURN_EXTRA(RETURN_EXTRA),.RETIRE(RETIRE)) u_head (
        .retire_busy(retire_busy),.retire_warm_ack(retire_warm_ack),.warm_emit(child_warm),
        .leaf_valid(child_leaf_v),.result_valid(child_ov),
        .clk(clk),.rst_n(rst_n),.ra_re(ra_re),.ra_addr(ra_addr),.ra_q(ra_q),
        .o_we(child_we),.leaf(child_leaf),.fault(child_fault),
        .s3_v_in(s3_v_in),
        .a_tag_p_in(a_tag_p_in),
        .res_in(res_in),
        .go_fus(go_fus),
        .i_iaddr(i_iaddr),
        .busy_in(busy_in),
        .o_we1_in(o_we1_in),
        .o_addr1_in(o_addr1_in),
        .o_mask1_in(o_mask1_in),
        .leaf_mask_in(leaf_mask_in),
        .leaf_row_in(leaf_row_in),
        .tv_in(tv_in),
        .ov1_in(ov1_in),
        .am_idx_in(am_idx_in),
        .r_tag(raw_tag),
        .r_v(raw_v),
        .o_addr(raw_addr),
        .o_mask(raw_mask),
        .o_data(raw_data));
    wire parent_fault;
    wire native_ack_v,native_fault,native_bounds_fault;
    wire [7:0] native_ack_id;
    wire [23:0] native_ack_word;
    wire [15:0] native_ack_mask;
    generate if(VM_ENDPOINT) begin : g_actual_native_load
`ifndef SYNTHESIS
        initial if(!RETIRE) $fatal(1,"Native endpoint context requires retirement enabled");
`endif
        ot_hdc_v41_fh_vm_endpoint_ctx #(.ENABLE(1)) u_native (
            .fast_clk(clk),.cold_n(native_cold_n),
            .request_accept((|o_we)&&native_request_ready),.request_warm(commit_warm),
            .checked_reply_capture(native_reply_capture),.published_reply_v(native_reply_v),
            .native_ordinal(native_ordinal),.request_owner(native_request_owner),.request_id(commit_id),
            .head_we(o_we),.head_addr(o_addr),.head_mask(o_mask),.head_data(o_data),
            .checked_reply(native_checked_reply),.bounds_fault(native_bounds_fault),.endpoint_fault(native_fault),
            .captured_request(native_captured_request),.captured_request_check(native_captured_request_check),
            .captured_reply(native_captured_reply),.captured_reply_check(native_captured_reply_check),
            .head_ack_v(native_ack_v),.head_ack_id(native_ack_id),.head_ack_word(native_ack_word),.head_ack_mask(native_ack_mask));
    end else begin : g_no_native_load
        assign native_ack_v=0;assign native_ack_id=0;assign native_ack_word=0;assign native_ack_mask=0;
        assign native_fault=0;assign native_bounds_fault=0;
        assign native_captured_request=0;assign native_captured_request_check=0;
        assign native_captured_reply=0;assign native_captured_reply_check=0;
    end endgenerate
    assign fault=RETIRE?parent_fault:(child_fault||memory_fault);
`ifndef SYNTHESIS
    initial if(RETURN_EXTRA!=2+PROTECT_SPLIT) $fatal(1,"Protected SRAM return and head latency mismatch");
`endif
    generate if(RETIRE) begin : g_retirement
        localparam integer PW=5512;
`ifndef SYNTHESIS
        initial if(G!=4||W!=16||AW!=24||NW!=16) $fatal(1,"RETIRE requires full G4W16 physical context");
`endif
        wire rv,rw,retired_warm_payload,retired_ov,retired_leaf_v;
        wire [PW-1:0] packet={child_leaf,child_we,raw_addr,raw_mask,raw_data,
            raw_tag,raw_v,child_ov,child_leaf_v,child_warm};
        wire [PW-1:0] retired;
        wire [63:0] veto;
        wire [3:0] write_veto,retired_we;
        wire [3135:0] retired_leaf;
        ot_hdc_v41_fh_retire_parent #(.ENABLE(1),.PAYLOAD_BITS(PW)) u_parent (
            .clk(clk),.rst_n(rst_n),.packet_v(raw_v||child_ov||(|child_we)||child_warm||child_leaf_v),
            .warm(child_warm),.packet(packet),.warm_word(raw_addr[23:0]),.warm_mask(raw_mask[15:0]),
            .poison(mem_poison),.address_fault(memory_address_fault),.arithmetic_fault(child_fault||native_fault),
            .sink_busy(commit_busy),.ack_v(VM_ENDPOINT?native_ack_v:commit_ack_v),.ack_id(VM_ENDPOINT?native_ack_id:commit_ack_id),
            .ack_word(VM_ENDPOINT?native_ack_word:commit_ack_word),.ack_mask(VM_ENDPOINT?native_ack_mask:commit_ack_mask),
            .retired_v(rv),.retired_warm(rw),.retired_packet(retired),.retired_id(commit_id),
            .lane_veto(veto),.write_veto(write_veto),.busy(retire_busy),.warm_ack(retire_warm_ack),
            .fault(parent_fault),.warm_debt(commit_debt));
        assign {retired_leaf,retired_we,o_addr,o_mask,o_data,r_tag,r_v,
            retired_ov,retired_leaf_v,retired_warm_payload}=retired;
        assign o_we=rv?(retired_we&~write_veto):4'b0;
        assign commit_warm=rw&&(|o_we);
        for(genvar l=0;l<64;l=l+1) begin : g_local_veto
            assign leaf[l*49+:49]={retired_leaf[l*49+48]&&!veto[l],retired_leaf[l*49+:48]};
        end
    end else begin : g_original
        assign {r_tag,r_v,o_addr,o_mask,o_data}={raw_tag,raw_v,raw_addr,raw_mask,raw_data};
        assign o_we=fault?{G{1'b0}}:child_we;
        for(genvar l=0;l<G*W;l=l+1) begin : g_leaf_fault
            localparam integer CW=1+32+NW;
            assign leaf[l*CW+:CW]={child_leaf[l*CW+CW-1]&&!fault,child_leaf[l*CW+:CW-1]};
        end
        assign parent_fault=0;assign retire_busy=0;assign retire_warm_ack=0;
        assign commit_warm=0;assign commit_id=0;assign commit_debt=0;
    end endgenerate
    // Actual result-port receiving registers and the first existing argmax
    // tree level bound this child. They add loads, not production stages.
    generate if(VM_ENDPOINT) begin : g_native_result_observe
        wire [95:0] captured_head_addr;
        for(genvar g=0;g<4;g=g+1) begin : g_addr_observe
            assign captured_head_addr[g*24+:24]={9'b0,native_captured_request[2640+(g+1)*15+:15]};
        end
        // Observe the existing native receiving registers; do not keep a
        // second fictitious result receiver after adding the real endpoint.
        assign result_capture={native_captured_request[2716+:4],captured_head_addr,
            native_captured_request[16+:64],native_captured_request[592+:2048]};
    end else begin : g_legacy_result_observe
        reg [G*W*32+G*W+G*AW+G-1:0] captured;
        always @(posedge clk) captured <= {o_we,o_addr,o_mask,o_data};
        assign result_capture=captured;
    end endgenerate
    for(genvar p=0;p<G*W/2;p=p+1) begin : g_argmax_consumer
        localparam integer CW=1+32+NW;
        wire [CW-1:0] x0=leaf[CW*(2*p)+:CW];
        wire [CW-1:0] x1=leaf[CW*(2*p+1)+:CW];
        wire x0_wins=x0[CW-1]&&(!x1[CW-1]||x0[CW-2-:32]>x1[CW-2-:32]||
            (x0[CW-2-:32]==x1[CW-2-:32]&&x0[NW-1:0]<x1[NW-1:0]));
        reg [CW-1:0] c;
        always @(posedge clk) c<=x0_wins?x0:x1;
        assign argmax_level1[CW*p+:CW]=c;
    end
endmodule
