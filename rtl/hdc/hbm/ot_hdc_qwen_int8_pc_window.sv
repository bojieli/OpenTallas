`timescale 1ns/1ps
// Bounded INT8 weight-HBM supply for the Qwen O4 core. A code word is G*W
// signed bytes; each PC owns every PCS-th 32-byte sector of each word. The
// scale image is a distinct region of packed W*BF16 words at the SAME ISA
// addresses. An op is issued only after its code and useful scales reside in
// the local banks. The matvec's one-cycle ROM latency is then preserved.
//
// This is a supply window, not an HBM controller: the external controller
// returns {tag,data} in any order on each PC and arbitrates KV traffic. The
// caller splits ops to at most WIN_WORDS; longer descriptors fault closed.
module ot_hdc_qwen_int8_pc_window #(
    parameter integer G = 4,
    parameter integer W = 16,
    parameter integer AW = 24,
    parameter integer HAW = 28,
    parameter integer NW = 16,
    parameter integer PCS = 2,
    parameter integer WIN_WORDS = 32,
    parameter integer SCALE_WORDS = 128,
    parameter integer SB = 256,
    parameter integer TAGW = 16
) (
    input  wire clk, rst_n,
    input  wire load,
    input  wire [AW-1:0] op_base,
    input  wire [NW-1:0] op_words,
    input  wire [NW-1:0] op_nout,
    input  wire [HAW-1:0] code_base_sector, scale_base_sector,
    output reg  ready, fault,
    // The independent synchronous core ROM ports.
    input  wire code_re,
    input  wire [AW-1:0] code_addr,
    output reg  [G*W*8-1:0] code_q,
    input  wire scale_re,
    input  wire [G*AW-1:0] scale_addr,
    output reg  [G*W*16-1:0] scale_q,
    // One request/response lane per pseudo-channel. Response tags echo the
    // issued tag; sector payload and addresses are 32-byte units.
    output reg  [PCS-1:0] rq_v,
    input  wire [PCS-1:0] rq_rdy,
    output reg  [PCS*HAW-1:0] rq_addr,
    output reg  [PCS*TAGW-1:0] rq_tag,
    input  wire [PCS-1:0] rsp_v,
    input  wire [PCS*TAGW-1:0] rsp_tag,
    input  wire [PCS*SB-1:0] rsp_data
);
    localparam integer CODE_BYTES = G*W;
    localparam integer SECTORS = CODE_BYTES/(SB/8);
    localparam integer SPC = SECTORS/PCS;
    localparam integer SCALE_SECTORS = (SCALE_WORDS+PCS-1)/PCS;
    localparam integer CODE_BANK_DEPTH = WIN_WORDS*SPC;
    localparam integer DATA_TAG_BITS = (CODE_BANK_DEPTH > SCALE_SECTORS) ?
                                       $clog2(CODE_BANK_DEPTH+1) : $clog2(SCALE_SECTORS+1);
    initial begin
        if (G*W*8 % SB != 0 || SECTORS % PCS != 0 || TAGW < DATA_TAG_BITS+1 || HAW < 28)
            $fatal(1, "unsupported Qwen HBM PC-window geometry");
    end
    localparam [1:0] IDLE=0, CODE=1, SCALE=2, DONE=3;
    reg [1:0] state;
    reg [AW-1:0] base_r;
    reg [NW-1:0] words_r;
    reg [NW-1:0] scales_r;
    reg [31:0] issued [0:PCS-1];
    reg [31:0] received [0:PCS-1];
    reg [SB-1:0] code_bank [0:PCS-1][0:CODE_BANK_DEPTH-1];
    reg [SB-1:0] scale_bank [0:PCS-1][0:SCALE_SECTORS-1];
    integer p, g, s, idx, off, bank, slot;
    integer code_count;
    reg all_issued, all_received;
    always @(*) begin
        code_count = words_r*SPC;
        all_issued = 1'b1;
        all_received = 1'b1;
        rq_v = 0; rq_addr = 0; rq_tag = 0;
        for (integer q=0; q<PCS; q=q+1) begin
            if (state == CODE || state == SCALE) begin
                if (issued[q] < ((state == CODE) ? code_count : (scales_r+PCS-1-q)/PCS)) begin
                    rq_v[q] = 1'b1;
                    if (state == CODE)
                        rq_addr[q*HAW +: HAW] = code_base_sector +
                            ((base_r + issued[q]/SPC)*SECTORS + (issued[q]%SPC)*PCS + q);
                    else
                        rq_addr[q*HAW +: HAW] = scale_base_sector + base_r + issued[q]*PCS + q;
                    rq_tag[q*TAGW +: TAGW] = {(state == SCALE), issued[q][TAGW-2:0]};
                end
                if (issued[q] < ((state == CODE) ? code_count : (scales_r+PCS-1-q)/PCS)) all_issued = 1'b0;
                if (received[q] < ((state == CODE) ? code_count : (scales_r+PCS-1-q)/PCS)) all_received = 1'b0;
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; ready <= 0; fault <= 0;
            base_r <= 0; words_r <= 0; scales_r <= 0;
            for (p=0; p<PCS; p=p+1) begin issued[p]<=0; received[p]<=0; end
        end else begin
            if (load) begin
                ready <= 0;
                if (state != IDLE && state != DONE) fault <= 1;
                else if (op_words == 0 || op_words > WIN_WORDS ||
                         (op_nout+W-1)/W > SCALE_WORDS) fault <= 1;
                else begin
                    fault <= 0; state <= CODE;
                    base_r <= op_base; words_r <= op_words;
                    scales_r <= (op_nout+W-1)/W;
                    for (p=0; p<PCS; p=p+1) begin issued[p]<=0; received[p]<=0; end
                end
            end else if (state == CODE || state == SCALE) begin
                for (p=0; p<PCS; p=p+1) begin
                    if (rq_v[p] && rq_rdy[p]) issued[p] <= issued[p]+1;
                    if (rsp_v[p]) begin
                        if (rsp_tag[p*TAGW + TAGW-1] != (state == SCALE) ||
                            rsp_tag[p*TAGW +: TAGW-1] >= ((state == CODE) ? code_count : (scales_r+PCS-1-p)/PCS))
                            fault <= 1;
                        else begin
                            if (state == CODE)
                                code_bank[p][rsp_tag[p*TAGW +: TAGW-1]] <= rsp_data[p*SB +: SB];
                            else
                                scale_bank[p][rsp_tag[p*TAGW +: TAGW-1]] <= rsp_data[p*SB +: SB];
                            received[p] <= received[p]+1;
                        end
                    end
                end
                if (all_issued && all_received && !fault) begin
                    for (p=0; p<PCS; p=p+1) begin issued[p]<=0; received[p]<=0; end
                    if (state == CODE) state <= SCALE;
                    else begin state <= DONE; ready <= 1; end
                end
            end
            if (code_re) begin
                if (!ready || code_addr < base_r || code_addr >= base_r + words_r) fault <= 1;
                else for (s=0; s<SECTORS; s=s+1) begin
                    code_q[s*SB +: SB] <= code_bank[s%PCS][(code_addr-base_r)*SPC + s/PCS];
                end
            end
            if (scale_re) begin
                if (!ready) fault <= 1;
                else for (g=0; g<G; g=g+1) begin
                    if (scale_addr[g*AW +: AW] < base_r ||
                        scale_addr[g*AW +: AW] >= base_r + scales_r)
                        scale_q[g*W*16 +: W*16] <= 0;
                    else begin
                        off = scale_addr[g*AW +: AW] - base_r;
                        scale_q[g*W*16 +: W*16] <= scale_bank[off%PCS][off/PCS];
                    end
                end
            end
        end
    end
endmodule
