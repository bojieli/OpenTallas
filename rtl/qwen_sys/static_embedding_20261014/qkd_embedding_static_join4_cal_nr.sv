// STEWARD-QKd 10-23: RoPE-free join calendar for the release KV die point (OT_KV_ROPE=0 + OT_KV_CTL_NC32=1).
// The release KV die has no RoPE context (the RoPE sweep is the separate OT_KV_ROPE / ROPE_OVL point, qkd_kvs_emb_ctx),
// so this module has no rope_sweep port at all (no tie-off). Body = qkd_embedding_static_join4_cal before deac9e511
// (the only change deac9e511 made was the rope_sweep port, the rope_mode flop and the slot mask).
`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Qwen KV die, KVJ-C3 2026-10-17 (kv_static_join_plan.md item 7, join4 beat_slot): successor of
// qkd_embedding_static_join4 that plays its own compiled beat_slot (glue folded into the join tile beside the d2d KV
// end).  join4 is instantiated unchanged; beat_slot comes from a run-length calendar of 8 boot segments
// {length 8, offset 16} started by the token-run start (d2d kind-15 RESULT engine_result_v, local: the join sits at the
// d2d end).  beat_slot (an output register) is high on edges start pin capture + 2 + [off, off + len) of every segment;
// the calendar ends on the last segment's last edge.  The compiler sets the segments to the edges the four trains' root
// words reach the join4 pins
// (tools/qwen_kv_die/kvjc3_pc_chain.py: 128 code beats, then the scale beat).  No credit, ready or wait.
// Boot word (shared boot bus with qkd_kv_es_fan_root): cfg_data[63:62] = 1, cfg_addr[2:0] = segment,
// cfg_data[23:0] = {len8, off16}; cfg_addr[7:3] / cfg_data[61:24] must be 0 (fault).  Target 0 is the root's.
// Faults (sticky): join4 faults, a start while the calendar runs, a malformed or running-time boot word.
// MUT (bench only): 1 = the last segment's length is one short (the scale beat has no slot).
// ---------------------------------------------------------------------------------------------------------------------
// NATIVE32 uses kept per-segment state/decode controls and six-edge regional reset release.
// PIPE_JOIN independently adds one stream edge in the local low/high/scale join; both default OFF.
module qkd_embedding_static_join4_cal_nr #(parameter integer MUT = 0, parameter integer NATIVE32 = 0, parameter integer PIPE_JOIN = 0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [298:0]  up0, up1, up2, up3,
    input  wire          start,
    input  wire          cfg_we,
    input  wire [7:0]    cfg_addr,
    input  wire [63:0]   cfg_data,
    output wire          word_v,
    output wire [511:0]  word_data,
    output wire [17:0]   word_token,
    output wire [5:0]    word_index,
    output wire          word_scale,
    output wire [15:0]   word_epoch,
    output wire          fault
);
    wire [2:0] reset_root;
    wire [7:0] reset_bank;
    wire [1:0] reset_main;
    generate if(NATIVE32)begin:g_reset
        ot_rst_relay #(.REGIONS(3)) u_root(.clk(ck),.rst_n_in(rst_n),.rst_n(reset_root));
        ot_rst_relay #(.REGIONS(8)) u_bank(.clk(ck),.rst_n_in(reset_root[0]),.rst_n(reset_bank));
        ot_rst_relay #(.REGIONS(2)) u_main(.clk(ck),.rst_n_in(reset_root[1]),.rst_n(reset_main));
    end else begin:g_legacy_reset
        assign reset_root={3{rst_n}};assign reset_bank={8{rst_n}};assign reset_main={2{rst_n}};
    end endgenerate
    reg ss, cw; reg [7:0] ca; reg [63:0] cd;
    always @(posedge ck) begin ca <= cfg_addr; cd <= cfg_data; end
    always @(posedge ck or negedge reset_main[0])
        if (!reset_main[0]) begin ss <= 1'b0; cw <= 1'b0; end else begin ss <= start; cw <= cfg_we; end
    reg [15:0] off [0:7]; reg [7:0] len [0:7];
    reg [15:0] cnt, last; reg act, slot, cf;
    reg [7:0] hit;
    integer k;
    // One same-edge counter per segment bounds comparator fanout. The copies
    // load zero at the existing start edge, so unreset count bits are never
    // observed before initialization; act is reset and qualifies every hit.
    generate if (NATIVE32) begin : g_native32_calendar
        for (genvar segment = 0; segment < 8; segment = segment + 1) begin : g_segment
            (* keep = 1, dont_touch = 1 *) reg [15:0] count_q;
            (* keep = 1, dont_touch = 1 *) reg active_q;
            (* keep = 1, dont_touch = 1 *) reg [1:0] start_count_q;
            (* keep = 1, dont_touch = 1 *) reg start_active_q,cw_off_q,cw_len_q;
            always @(posedge ck or negedge reset_bank[segment])
                if(!reset_bank[segment])begin start_count_q<=0;start_active_q<=0;cw_off_q<=0;cw_len_q<=0;end
                else begin start_count_q<={2{start}};start_active_q<=start;cw_off_q<=cfg_we;cw_len_q<=cfg_we;end
            wire write_off = cw_off_q && cd[63:62] == 2'd1 && ca[2:0] == 3'(segment);
            wire write_len = cw_len_q && cd[63:62] == 2'd1 && ca[2:0] == 3'(segment);
            always @(posedge ck or negedge reset_bank[segment])
                if(!reset_bank[segment])begin off[segment]<=0;len[segment]<=0;end
                else begin if(write_off)off[segment]<=cd[15:0];if(write_len)len[segment]<=cd[23:16];end
            always @(posedge ck or negedge reset_bank[segment])
                if (!reset_bank[segment]) active_q <= 1'b0;
                else if (start_active_q) active_q <= 1'b1;
                else if (act && cnt == last) active_q <= 1'b0;
            wire [15:0] incremented = count_q + 16'd1;
            for(genvar half = 0; half < 2; half = half + 1)begin:g_count_half
                always @(posedge ck)
                    if (start_count_q[half]) count_q[half*8+:8] <= 8'd0;
                    else if (active_q) count_q[half*8+:8] <= incremented[half*8+:8];
            end
            always @(*) hit[segment] = (count_q >= off[segment]) &&
                ({8'd0, count_q} < {8'd0, off[segment]} + {16'd0, len[segment]} -
                 ((MUT == 1 && segment == 1) ? 24'd1 : 24'd0));
        end
    end else begin : g_legacy_calendar
        always @(*) for (k = 0; k < 8; k = k + 1)
            hit[k] = (cnt >= off[k]) && ({8'd0, cnt} < {8'd0, off[k]} + {16'd0, len[k]} - ((MUT == 1 && k == 1) ? 24'd1 : 24'd0));
    end endgenerate
    wire mine = cw && cd[63:62] == 2'd1;
    wire [23:0] configured_end = {8'd0,cd[15:0]}+{16'd0,cd[23:16]};
    wire [15:0] configured_last = 16'(configured_end-24'd1);
    generate if(NATIVE32)begin:g_last
        (* keep=1,dont_touch=1 *)reg [1:0] cw_last_q;
        always @(posedge ck or negedge reset_main[1])
            if(!reset_main[1])cw_last_q<=0;else cw_last_q<={2{cfg_we}};
        for(genvar half=0;half<2;half=half+1)begin:g_half
            always @(posedge ck or negedge reset_main[1])
                if(!reset_main[1])last[half*8+:8]<=0;
                else if(cw_last_q[half] && cd[63:62]==2'd1 && cd[23:16]!=0 && configured_end>{8'd0,last}+24'd1)
                    last[half*8+:8]<=configured_last[half*8+:8];
        end
    end else begin:g_legacy_last
        always @(posedge ck or negedge reset_main[1])
            if(!reset_main[1])last<=0;
            else if(mine && cd[23:16]!=0 && configured_end>{8'd0,last}+24'd1)
                last<=configured_last;
    end endgenerate
    always @(posedge ck or negedge reset_main[0])
        if (!reset_main[0]) begin
            if(!NATIVE32)for (k = 0; k < 8; k = k + 1) begin off[k] <= 16'd0; len[k] <= 8'd0; end
            cnt <= 16'd0; act <= 1'b0; slot <= 1'b0; cf <= 1'b0;
        end else begin
            if (mine) begin
                if(!NATIVE32)begin off[ca[2:0]] <= cd[15:0]; len[ca[2:0]] <= cd[23:16];end
                if (act || ca[7:3] != 5'd0 || cd[61:24] != 38'd0) cf <= 1'b1;
            end
            if (ss) begin if (act) cf <= 1'b1; act <= 1'b1; cnt <= 16'd0; end
            else if (act) begin cnt <= cnt + 16'd1; if (cnt == last) act <= 1'b0; end
            slot <= act && (|hit);
        end
    wire jf;
    qkd_embedding_static_join4 #(.NATIVE32(NATIVE32), .PIPE_JOIN(PIPE_JOIN)) u_join4 (.ck(ck), .rst_n(reset_root[2]), .up0(up0), .up1(up1), .up2(up2), .up3(up3),
        .beat_slot(slot), .word_v(word_v), .word_data(word_data), .word_token(word_token), .word_index(word_index),
        .word_scale(word_scale), .word_epoch(word_epoch), .fault(jf));
    reg cf_q;
    always @(posedge ck or negedge reset_main[0])
        if(!reset_main[0])cf_q<=0;else cf_q<=cf;
    assign fault = jf | (PIPE_JOIN ? cf_q : cf);
endmodule
