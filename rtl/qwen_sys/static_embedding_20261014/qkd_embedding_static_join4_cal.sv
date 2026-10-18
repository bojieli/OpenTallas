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
module qkd_embedding_static_join4_cal #(parameter integer MUT = 0) (
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
    reg ss, cw; reg [7:0] ca; reg [63:0] cd;
    always @(posedge ck) begin ca <= cfg_addr; cd <= cfg_data; end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin ss <= 1'b0; cw <= 1'b0; end else begin ss <= start; cw <= cfg_we; end
    reg [15:0] off [0:7]; reg [7:0] len [0:7];
    reg [15:0] cnt, last; reg act, slot, cf;
    reg [7:0] hit;
    integer k;
    always @(*) for (k = 0; k < 8; k = k + 1)
        hit[k] = (cnt >= off[k]) && ({8'd0, cnt} < {8'd0, off[k]} + {16'd0, len[k]} - ((MUT == 1 && k == 1) ? 24'd1 : 24'd0));
    wire mine = cw && cd[63:62] == 2'd1;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            for (k = 0; k < 8; k = k + 1) begin off[k] <= 16'd0; len[k] <= 8'd0; end
            cnt <= 16'd0; last <= 16'd0; act <= 1'b0; slot <= 1'b0; cf <= 1'b0;
        end else begin
            if (mine) begin
                off[ca[2:0]] <= cd[15:0]; len[ca[2:0]] <= cd[23:16];
                if (cd[23:16] != 8'd0 && {8'd0, cd[15:0]} + {16'd0, cd[23:16]} > {8'd0, last} + 24'd1)
                    last <= 16'(({8'd0, cd[15:0]} + {16'd0, cd[23:16]}) - 24'd1);
                if (act || ca[7:3] != 5'd0 || cd[61:24] != 38'd0) cf <= 1'b1;
            end
            if (ss) begin if (act) cf <= 1'b1; act <= 1'b1; cnt <= 16'd0; end
            else if (act) begin cnt <= cnt + 16'd1; if (cnt == last) act <= 1'b0; end
            slot <= act && (|hit);
        end
    wire jf;
    qkd_embedding_static_join4 u_join4 (.ck(ck), .rst_n(rst_n), .up0(up0), .up1(up1), .up2(up2), .up3(up3),
        .beat_slot(slot), .word_v(word_v), .word_data(word_data), .word_token(word_token), .word_index(word_index),
        .word_scale(word_scale), .word_epoch(word_epoch), .fault(jf));
    assign fault = jf | cf;
endmodule
