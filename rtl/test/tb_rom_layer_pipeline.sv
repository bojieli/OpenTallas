`timescale 1ns/1ps
// Four-package layer pipeline: link -> stage -> link -> stage ... -> sink.
//
// Injects TOKENS tokens back to back, each a different user, and checks every
// token's final hidden state against a reference model of the same folding.
// Prints one TOKEN line per token with its latency and arrival cycle, and a
// SUMMARY; tools/rtl_rom_layer_pipeline_campaign.py checks the latency law and
// the pipelined arrival interval.
module tb_rom_layer_pipeline;
    localparam integer STAGES = 4, TOKENS = 8;
    localparam integer BANKS = 8, EXPERTS = 48, EXPERT_WORDS = 64, MAX_SELECT = 6;
    localparam integer HIDDEN = 16, LAT = 2, CH = 60;
    localparam integer MW = (HIDDEN + 1) * 32;

    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;    // 1 GHz
    integer cycle = 0;
    always @(posedge clk) cycle <= cycle + 1;

    // Links feed stages; link s carries the message into stage s, link STAGES
    // carries the last stage's output to the sink.
    wire [STAGES:0]  l_in_valid, l_in_ready, l_out_valid, l_out_ready, l_out_last;
    wire [MW-1:0]    l_in_msg  [0:STAGES];
    wire [MW-1:0]    l_out_msg [0:STAGES];
    wire [31:0]      l_stalls  [0:STAGES];
    wire [31:0]      s_done    [0:STAGES-1];

    reg src_valid = 0;
    reg [MW-1:0] src_msg = 0;
    assign l_in_valid[0] = src_valid;
    assign l_in_msg[0] = src_msg;
    assign l_out_ready[STAGES] = 1'b1;

    genvar g;
    generate
        for (g = 0; g <= STAGES; g = g + 1) begin : link
            ot_rom_pkg_link #(.FLIT_BYTES(MW/8), .TX_STAGES(2), .CHANNEL_CYCLES(CH),
                              .RX_STAGES(2), .CREDITS(16)) u (
                .clk(clk), .rst_n(rst_n), .in_valid(l_in_valid[g]), .in_ready(l_in_ready[g]),
                .in_data(l_in_msg[g]), .in_last(1'b1), .out_valid(l_out_valid[g]),
                .out_ready(l_out_ready[g]), .out_data(l_out_msg[g]), .out_last(l_out_last[g]),
                .credit_stalls(l_stalls[g]));
        end
        for (g = 0; g < STAGES; g = g + 1) begin : stage
            wire out_valid;
            wire [MW-1:0] out_msg;
            ot_rom_layer_stage #(.STAGE_ID(g), .BANKS(BANKS), .EXPERTS(EXPERTS),
                                 .EXPERT_WORDS(EXPERT_WORDS), .MAX_SELECT(MAX_SELECT),
                                 .HIDDEN_WORDS(HIDDEN), .SENSE_LATENCY(LAT)) u (
                .clk(clk), .rst_n(rst_n), .in_valid(l_out_valid[g]), .in_ready(l_out_ready[g]),
                .in_msg(l_out_msg[g]), .out_valid(out_valid), .out_ready(l_in_ready[g+1]),
                .out_msg(out_msg), .tokens_done(s_done[g]));
            // A stage offers its result once; the link accepts it when it has credit.
            assign l_in_valid[g+1] = out_valid;
            assign l_in_msg[g+1] = out_msg;
        end
    endgenerate

    // ---- reference model ------------------------------------------------
    function automatic [31:0] weight_value(input integer e, input integer w);
        weight_value = (e * 32'h9E37_79B1) ^ (w * 32'h85EB_CA77) ^ 32'hC2B2_AE3D;
    endfunction
    function automatic [31:0] initial_word(input integer tag, input integer i);
        initial_word = tag * 32'h0101_0101 + i * 32'h1000_0001;
    endfunction
    reg [31:0] ref_h [0:TOKENS-1][0:HIDDEN-1];
    integer t, s, j, w, i, e;
    initial begin
        for (t = 0; t < TOKENS; t = t + 1) begin
            for (i = 0; i < HIDDEN; i = i + 1) ref_h[t][i] = initial_word(t, i);
            for (s = 0; s < STAGES; s = s + 1)
                for (j = 0; j < MAX_SELECT; j = j + 1) begin
                    e = (t * 7 + s * 13 + j * 5) % EXPERTS;
                    for (w = 0; w < EXPERT_WORDS; w = w + 1)
                        ref_h[t][w % HIDDEN] = ref_h[t][w % HIDDEN] + weight_value(e, w);
                end
        end
    end

    // ---- source: inject tokens back to back ------------------------------
    // The source is faster than the pipeline, so later tokens queue in the
    // first link's buffer; the first token's latency is the unloaded path.
    integer sent_at [0:TOKENS-1];
    integer next_tok = 0;
    always @(posedge clk) if (rst_n) begin
        if (src_valid && l_in_ready[0]) begin
            sent_at[next_tok] = cycle;
            next_tok = next_tok + 1;
        end
        src_valid <= (next_tok < TOKENS);
    end
    always_comb begin : fill_message
        integer k;
        src_msg[31:0] = next_tok;
        for (k = 0; k < HIDDEN; k = k + 1)
            src_msg[(k+1)*32 +: 32] = initial_word(next_tok, k);
    end

    // ---- sink: scoreboard -------------------------------------------------
    integer got = 0, errors = 0, prev_arrival = -1, tag;
    always @(posedge clk) if (l_out_valid[STAGES]) begin
        tag = l_out_msg[STAGES][31:0];
        for (i = 0; i < HIDDEN; i = i + 1)
            if (l_out_msg[STAGES][(i+1)*32 +: 32] !== ref_h[tag][i]) errors = errors + 1;
        $display("TOKEN tag=%0d latency=%0d arrival=%0d interval=%0d", tag, cycle - sent_at[tag],
                 cycle, prev_arrival < 0 ? 0 : cycle - prev_arrival);
        prev_arrival = cycle;
        got = got + 1;
        if (got == TOKENS) begin
            $display("SUMMARY tokens=%0d errors=%0d", got, errors);
            $finish;
        end
    end

    initial begin
        repeat (3) @(posedge clk);
        rst_n = 1;
    end
    initial begin #200000; $display("SUMMARY tokens=%0d errors=timeout", got); $finish; end
endmodule
