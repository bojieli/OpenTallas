`timescale 1ns/1ps
// Literal four-quarter DS ROM hierarchy for separate synthesis. No new state,
// formatter, credits or clock domain. The unchanged chain owns ALL winner,
// line-memory, replay and list-retention state. Query/ref tuples are real caller
// ports; default OFF never grants ready. Source model: hierarchical_parent_join_model.
module ot_dsrom_reindex_hierarchical_parent #(

    parameter integer ENABLE = 0,
    localparam integer Q = 4,        // stacks = select quarters
    parameter integer NPC  = 32,
    parameter integer WB   = 128,
    parameter integer AW   = 28,       // HBM sector address
    parameter integer HW   = 20,
    parameter integer TAGW = 16,
    parameter integer LENW = 4,
    parameter integer BEATW = 4,
    parameter integer DW   = 256,
    parameter integer LBW  = 14,
    parameter integer LMW  = 11,
    parameter integer DF   = 8,
    parameter integer LSW  = 3,        // list slots 2^LSW (>= WIN); 0 = as-built single list
    localparam integer IW = 20,       // position bits
    localparam integer K = 512,
    localparam integer SAW = 8,        // select line-memory words per quarter (log2)
    localparam integer MDROP = 1,
    localparam integer SLW = (LSW > 0) ? LSW : 1,
    localparam integer KW = $clog2(K + 1),
    localparam integer EW = 17 + IW
) (
    input wire clk,
    input wire rst_n,
    input wire [Q-1:0] lw_v,
    input wire [SLW-1:0] lw_slot,
    input wire [LMW-1:0] lw_addr,
    input wire [Q*LBW-1:0] lw_blk,
    input wire start,
    input wire [SLW-1:0] start_slot,
    input wire [IW-1:0] start_pos,
    input wire [KW-1:0] start_k,
    input wire [Q*HW-1:0] start_base,
    input wire [Q*10-1:0] start_skip,
    input wire [Q*(LMW+1)-1:0] start_n,
    input wire [Q*IW-1:0] start_qbase,
    output wire done,
    output wire busy,
    output wire fault,
    output wire [Q*NPC-1:0] req_v,
    input wire [Q*NPC-1:0] req_rdy,
    output wire [Q*NPC*AW-1:0] req_addr,
    output wire [Q*NPC*LENW-1:0] req_len,
    output wire [Q*NPC*TAGW-1:0] req_tag,
    input wire [Q*NPC-1:0] rsp_v,
    output wire [Q*NPC-1:0] rsp_rdy,
    input wire [Q*NPC*TAGW-1:0] rsp_tag,
    input wire [Q*NPC*BEATW-1:0] rsp_beat,
    input wire [Q*NPC*DW-1:0] rsp_data,
    output wire [Q-1:0] out_valid,
    input wire [Q-1:0] out_ready,
    output wire [Q-1:0] out_last,
    output wire [Q*16-1:0] out_lv,
    output wire [Q*16*16-1:0] out_val,
    output wire [Q*16*IW-1:0] out_idx,
    output wire [Q*16-1:0] out_ninf,
    output wire ovf,
    output wire short,
    output wire [3:0] passes,
    output wire [Q*48-1:0] cnt_keys,
    output wire [Q*48-1:0] cnt_beats,
    input wire [Q-1:0] ql_v,
    output wire [Q-1:0] ql_ready,
    input wire [Q*8-1:0] ql_head,
    input wire [Q*512-1:0] ql_codes,
    input wire [Q*32-1:0] ql_sc,
    input wire [Q*16-1:0] ql_w,
    input wire [Q*16-1:0] ks_ref,
    output wire [Q*16-1:0] score_fault,
    output wire [Q-1:0] scorer_protocol_fault
);
    wire [Q-1:0] ks_valid;
    wire [Q-1:0] ks_ready;
    wire [Q*16-1:0] ks_lv;
    wire [Q*16*544-1:0] ks_key;
    wire [Q*16*IW-1:0] ks_idx;
    wire [Q-1:0] ks_last;
    wire [Q-1:0] sc_valid;
    wire [Q-1:0] sc_ready;
    wire [Q*16-1:0] sc_lv;
    wire [Q*16*16-1:0] sc_val;
    wire [Q*16*IW-1:0] sc_idx;
    wire [Q-1:0] sc_last;
    genvar q;
    generate if (ENABLE) begin : enabled
        (* keep_hierarchy = 1 *)
        ot_dsrom_reindex_chain #(
            .OPT_REINDEX_PARENT(1),.Q(Q),.NPC(NPC),.WB(WB),.AW(AW),.HW(HW),
            .TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.DW(DW),.LBW(LBW),
            .LMW(LMW),.DF(DF),.LSW(LSW),.IW(IW),.K(K),.SAW(SAW),.MDROP(MDROP)
        ) u_shared (
            .clk(clk),
            .rst_n(rst_n),
            .lw_v(lw_v),
            .lw_slot(lw_slot),
            .lw_addr(lw_addr),
            .lw_blk(lw_blk),
            .start(start),
            .start_slot(start_slot),
            .start_pos(start_pos),
            .start_k(start_k),
            .start_base(start_base),
            .start_skip(start_skip),
            .start_n(start_n),
            .start_qbase(start_qbase),
            .done(done),
            .busy(busy),
            .fault(fault),
            .req_v(req_v),
            .req_rdy(req_rdy),
            .req_addr(req_addr),
            .req_len(req_len),
            .req_tag(req_tag),
            .rsp_v(rsp_v),
            .rsp_rdy(rsp_rdy),
            .rsp_tag(rsp_tag),
            .rsp_beat(rsp_beat),
            .rsp_data(rsp_data),
            .ks_valid(ks_valid),
            .ks_ready(ks_ready),
            .ks_lv(ks_lv),
            .ks_key(ks_key),
            .ks_idx(ks_idx),
            .ks_last(ks_last),
            .sc_valid(sc_valid),
            .sc_ready(sc_ready),
            .sc_lv(sc_lv),
            .sc_val(sc_val),
            .sc_idx(sc_idx),
            .sc_last(sc_last),
            .out_valid(out_valid),
            .out_ready(out_ready),
            .out_last(out_last),
            .out_lv(out_lv),
            .out_val(out_val),
            .out_idx(out_idx),
            .out_ninf(out_ninf),
            .ovf(ovf),
            .short(short),
            .passes(passes),
            .cnt_keys(cnt_keys),
            .cnt_beats(cnt_beats)
        );
        for (q=0; q<Q; q=q+1) begin : g_quarter
            wire [3:0] last_slices;
            (* keep_hierarchy = 1 *)
            ot_dsrom_reindex_native_quarter #(.ENABLE(1)) u_native (
                .clk(clk),.rst_n(rst_n),
                .ql_v(ql_v[q]),.ql_ready(ql_ready[q]),
                .ql_head(ql_head[q*8 +: 8]),.ql_codes(ql_codes[q*512 +: 512]),
                .ql_sc(ql_sc[q*32 +: 32]),.ql_w(ql_w[q*16 +: 16]),
                .ks_valid(ks_valid[q]),.ks_ready(ks_ready[q]),.ks_last(ks_last[q]),
                .ks_lv(ks_lv[q*16 +: 16]),.ks_ref(ks_ref[q*16 +: 16]),
                .ks_key(ks_key[q*8704 +: 8704]),.ks_idx(ks_idx[q*320 +: 320]),
                .sc_valid(sc_valid[q]),.sc_ready(sc_ready[q]),.sc_last(sc_last[q]),
                .sc_last_slices(last_slices),.sc_lv(sc_lv[q*16 +: 16]),
                .sc_fault(score_fault[q*16 +: 16]),.sc_val(sc_val[q*256 +: 256]),
                .sc_idx(sc_idx[q*320 +: 320]),
                .protocol_fault(scorer_protocol_fault[q])
            );
        end
    end else begin : disabled
        assign done = '0;
        assign busy = '0;
        assign fault = '0;
        assign req_v = '0;
        assign req_addr = '0;
        assign req_len = '0;
        assign req_tag = '0;
        assign rsp_rdy = '0;
        assign out_valid = '0;
        assign out_last = '0;
        assign out_lv = '0;
        assign out_val = '0;
        assign out_idx = '0;
        assign out_ninf = '0;
        assign ovf = '0;
        assign short = '0;
        assign passes = '0;
        assign cnt_keys = '0;
        assign cnt_beats = '0;
        assign ql_ready = '0;
        assign score_fault = '0;
        assign scorer_protocol_fault = '0;
    end endgenerate
endmodule
