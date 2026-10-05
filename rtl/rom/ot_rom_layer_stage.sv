`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// One package of the layer-per-package ROM pipeline.
//
// docs/ANALYTICAL_REPORT.md's redesigned ROM machine keeps one layer's weights
// on one package and pipelines layers across packages: a token's hidden state
// arrives over the package link, the stage reads that layer's selected experts
// from its own striped ROM banks, folds them into the hidden state, and sends
// the result on.  Because a stage reads only its own weights, consecutive
// users occupy consecutive stages with no loss of per-user speed.
//
// Functional stand-ins, stated so they are not mistaken for the model:
//   * expert selection is a fixed function of (token tag, stage), not a router;
//   * the arithmetic is a wrapping sum of each expert word into hidden word
//     (word mod HIDDEN_WORDS), which is order-independent and checkable, not
//     a matrix-vector product;
//   * the message is one flit: {tag, hidden words}.
// What is real is the timing structure: link arrival, a striped-bank read that
// takes k * EXPERT_WORDS / BANKS cycles, accumulate-on-arrival at BANKS words
// per cycle, and the send to the next package.
// ---------------------------------------------------------------------------
module ot_rom_layer_stage #(
    parameter integer STAGE_ID      = 0,
    parameter integer BANKS         = 8,
    parameter integer EXPERTS       = 48,
    parameter integer EXPERT_WORDS  = 64,
    parameter integer MAX_SELECT    = 6,
    parameter integer HIDDEN_WORDS  = 16,
    parameter integer SENSE_LATENCY = 2
) (
    input  wire                              clk,
    input  wire                              rst_n,
    // from the previous package's link
    input  wire                              in_valid,
    output wire                              in_ready,
    input  wire [(HIDDEN_WORDS+1)*32-1:0]    in_msg,     // {hidden, tag}
    // to the next package's link
    output reg                               out_valid,
    input  wire                              out_ready,
    output reg  [(HIDDEN_WORDS+1)*32-1:0]    out_msg,
    output reg  [31:0]                       tokens_done
);
    localparam integer EW = $clog2(EXPERTS);
    localparam integer WW = $clog2(EXPERT_WORDS);
    localparam integer SW = $clog2(MAX_SELECT + 1);

    // Selected experts for (tag, stage): distinct because 5 and EXPERTS are
    // coprime and j < MAX_SELECT < EXPERTS.
    function automatic [EW-1:0] pick(input integer tag, input integer j);
        pick = (tag * 7 + STAGE_ID * 13 + j * 5) % EXPERTS;
    endfunction

    reg [1:0] state;
    localparam [1:0] IDLE = 2'd0, READ = 2'd1, SEND = 2'd2;
    reg [31:0] tag;
    reg [31:0] acc [0:HIDDEN_WORDS-1];
    reg        start;
    reg [MAX_SELECT*EW-1:0] ids;

    wire [BANKS-1:0] lane_valid;
    wire [BANKS*32-1:0] lane_data;
    wire [BANKS*EW-1:0] lane_expert;
    wire [BANKS*WW-1:0] lane_word;
    wire rd_done, rd_busy;
    wire [31:0] rd_cycles, rd_words, rd_conflicts;

    ot_rom_striped_expert_reader #(
        .BANKS(BANKS), .WORD_BITS(32), .EXPERTS(EXPERTS), .EXPERT_WORDS(EXPERT_WORDS),
        .MAX_SELECT(MAX_SELECT), .SENSE_LATENCY(SENSE_LATENCY)
    ) reader (
        .clk(clk), .rst_n(rst_n), .striped(1'b1), .start(start),
        .select_count(MAX_SELECT[SW-1:0]), .select_ids(ids), .busy(rd_busy),
        .lane_valid(lane_valid), .lane_data(lane_data), .lane_expert(lane_expert),
        .lane_word(lane_word), .done(rd_done), .read_cycles(rd_cycles),
        .words_read(rd_words), .bank_conflicts(rd_conflicts)
    );

    assign in_ready = (state == IDLE);

    integer i, b;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; start <= 1'b0; out_valid <= 1'b0; tokens_done <= 0;
            tag <= 0; ids <= 0;
        end else begin
            start <= 1'b0;
            case (state)
                IDLE: if (in_valid) begin
                    tag <= in_msg[31:0];
                    for (i = 0; i < HIDDEN_WORDS; i = i + 1)
                        acc[i] <= in_msg[(i+1)*32 +: 32];
                    for (i = 0; i < MAX_SELECT; i = i + 1)
                        ids[i*EW +: EW] <= pick(in_msg[31:0], i);
                    start <= 1'b1;
                    state <= READ;
                end
                READ: begin
                    // Accumulate every expert word the moment its bank returns it.
                    for (b = 0; b < BANKS; b = b + 1)
                        if (lane_valid[b])
                            acc[lane_word[b*WW +: WW] % HIDDEN_WORDS]
                                = acc[lane_word[b*WW +: WW] % HIDDEN_WORDS] + lane_data[b*32 +: 32];
                    if (rd_done) begin
                        out_msg[31:0] <= tag;
                        for (i = 0; i < HIDDEN_WORDS; i = i + 1)
                            out_msg[(i+1)*32 +: 32] <= acc[i];
                        out_valid <= 1'b1;
                        state <= SEND;
                    end
                end
                SEND: if (out_ready) begin
                    out_valid <= 1'b0;
                    tokens_done <= tokens_done + 1;
                    state <= IDLE;
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
