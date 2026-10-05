`timescale 1ns/1ps
// Single-outstanding, generation-tagged packed-attention descriptor gate.
// L0_ONLY permits the first executable layer (128 window rows, no CKV).
// The storage service owns row contents; this gate owns readiness and replay.
module ot_chip_v41x_attn_desc_lifecycle #(
    parameter integer AW = 30,
    parameter integer NW = 21,
    parameter integer NL = 4,
    parameter integer USERW = 10,
    parameter integer GENW = 16,
    parameter bit L0_ONLY = 1,
    parameter [GENW-1:0] RESET_GEN = '0
) (
    input  wire clk, rst_n,
    input  wire desc_v,
    input  wire [USERW-1:0] desc_user,
    input  wire [NW-1:0] desc_pos, desc_tiles, desc_k, desc_nout,
    input  wire [AW-1:0] desc_wbase, desc_ts, desc_ks, desc_js,
    input  wire [1:0] desc_hg,
    input  wire desc_mmode,
    output wire desc_accept,
    output wire [GENW-1:0] desc_gen,
    output wire [10:0] desc_rows,
    input  wire stage_v,
    input  wire [GENW-1:0] stage_gen,
    input  wire [10:0] stage_rows,
    input  wire beat_v, beat_ready,
    input  wire [GENW-1:0] beat_gen,
    input  wire [NL-1:0] beat_mask,
    input  wire issue_v,
    input  wire engine_idle,
    input  wire service_fault,
    input  wire wrap_drained,
    output wire issue_ok,
    output reg  done,
    output reg  fault,
    output reg  [3:0] fault_code,
    output wire [10:0] beats_accepted
);
    localparam [2:0] IDLE=0, STAGE=1, READY=2, ARM=3, STREAM=4, DRAIN=5, FAULT=6;
    localparam [3:0] F_SHAPE=1, F_CHANGED=2, F_STAGE=3, F_TAG=4,
                     F_COUNT=5, F_MASK=6, F_EARLY=7, F_EXTRA=8,
                     F_SOURCE=9, F_WRAP=10;
    reg [2:0] state;
    reg [GENW-1:0] last_gen, active_gen;
    reg [USERW-1:0] active_user;
    reg [NW-1:0] active_pos, active_tiles, active_k, active_nout;
    reg [AW-1:0] active_wbase, active_ts, active_ks, active_js;
    reg [1:0] active_hg;
    reg active_mmode;
    reg [10:0] active_rows, beat_count;
    wire [NW-1:0] incoming_rows = (desc_ks == {{(AW-1){1'b0}},1'b1}) ? desc_nout : desc_k;
    wire wrap_needed = last_gen == {GENW{1'b1}};
    wire [GENW-1:0] next_gen = wrap_needed ?
        {{(GENW-1){1'b0}},1'b1} : last_gen + 1'b1;
    wire desc_same = desc_user == active_user && desc_pos == active_pos &&
        desc_tiles == active_tiles && desc_k == active_k && desc_nout == active_nout &&
        desc_wbase == active_wbase && desc_ts == active_ts &&
        desc_ks == active_ks && desc_js == active_js &&
        desc_hg == active_hg && desc_mmode == active_mmode;
    wire [10:0] total_beats = (active_rows + NL - 1) / NL;
    wire [10:0] rows_left = active_rows - beat_count * NL;
    reg [NL-1:0] expected_mask;
    integer l;
    always @(*) for (l=0; l<NL; l=l+1) expected_mask[l] = (rows_left > l);
    assign desc_accept = state == IDLE && desc_v;
    assign desc_gen = state == IDLE ? next_gen : active_gen;
    assign desc_rows = state == IDLE ? incoming_rows[10:0] : active_rows;
    assign issue_ok = state == READY && !fault;
    assign beats_accepted = beat_count;

    task automatic fail(input [3:0] code);
        begin state <= FAULT; fault <= 1'b1; fault_code <= code; end
    endtask
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; last_gen <= RESET_GEN; active_gen <= '0;
            active_user <= '0; active_pos <= '0; active_tiles <= '0;
            active_k <= '0; active_nout <= '0; active_wbase <= '0;
            active_ts <= '0; active_ks <= '0; active_js <= '0;
            active_hg <= '0; active_mmode <= 1'b0;
            active_rows <= '0; beat_count <= '0;
            done <= 1'b0; fault <= 1'b0; fault_code <= '0;
        end else begin
            done <= 1'b0;
            if (service_fault) fail(F_SOURCE);
            else case (state)
                IDLE: begin
                    if (stage_v || (beat_v && beat_ready)) fail(F_STAGE);
                    else if (desc_v) begin
                        if (wrap_needed && !wrap_drained) fail(F_WRAP);
                        else if (!desc_mmode || incoming_rows == 0 || incoming_rows > 640 ||
                            (L0_ONLY && (incoming_rows != 128 || desc_pos < 127)))
                            fail(F_SHAPE);
                        else begin
                            state <= STAGE; last_gen <= next_gen; active_gen <= next_gen;
                            active_user <= desc_user; active_pos <= desc_pos;
                            active_tiles <= desc_tiles; active_k <= desc_k;
                            active_nout <= desc_nout; active_wbase <= desc_wbase;
                            active_ts <= desc_ts; active_ks <= desc_ks;
                            active_js <= desc_js; active_hg <= desc_hg;
                            active_mmode <= desc_mmode;
                            active_rows <= incoming_rows[10:0]; beat_count <= '0;
                        end
                    end
                end
                STAGE: begin
                    if (desc_v && !desc_same) fail(F_CHANGED);
                    else if (beat_v && beat_ready) fail(F_EARLY);
                    else if (stage_v) begin
                        if (stage_gen != active_gen) fail(F_TAG);
                        else if (stage_rows < ((active_rows < NL) ? active_rows : NL) ||
                                 stage_rows > active_rows) fail(F_COUNT);
                        else state <= READY;
                    end
                end
                READY: begin
                    if (desc_v && !desc_same) fail(F_CHANGED);
                    else if (stage_v) fail(F_STAGE);
                    else if (beat_v && beat_ready) fail(F_EARLY);
                    else if (issue_v) state <= ARM;
                end
                ARM: begin
                    if (desc_v || stage_v || issue_v) fail(F_CHANGED);
                    else if (beat_v && beat_ready) fail(F_EARLY);
                    else if (!engine_idle) state <= STREAM;
                end
                STREAM: begin
                    if (desc_v) fail(F_CHANGED);
                    else if (stage_v) fail(F_STAGE);
                    else if (engine_idle) fail(F_EARLY);
                    else if (beat_v && beat_ready) begin
                        if (beat_gen != active_gen) fail(F_TAG);
                        else if (beat_count >= total_beats) fail(F_EXTRA);
                        else if (beat_mask != expected_mask) fail(F_MASK);
                        else begin
                            beat_count <= beat_count + 1'b1;
                            if (beat_count + 1'b1 == total_beats) state <= DRAIN;
                        end
                    end
                end
                DRAIN: begin
                    if (desc_v) fail(F_CHANGED);
                    else if (stage_v) fail(F_STAGE);
                    else if (beat_v && beat_ready) fail(F_EXTRA);
                    else if (engine_idle) begin state <= IDLE; done <= 1'b1; end
                end
                default: state <= FAULT;
            endcase
        end
    end
endmodule
