`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Striped expert banks: read a token's selected experts at the whole die's rate.
//
// docs/ANALYTICAL_REPORT.md credits the redesigned ROM machine with reading the
// experts a token selects in `engaged_bytes / read_bandwidth`, rather than in
// the full-array sweep a dedicated-bank layout implies.  This block is the
// address map and stream schedule that makes that true, in two modes the same
// testbench can compare cycle for cycle:
//
//   STRIPED   expert e's word w lives in bank (w mod BANKS) at row
//             e * EXPERT_ROWS + (w div BANKS).  Every bank serves every expert
//             at a different row range, so one expert row is BANKS words read
//             by all banks in the same cycle: no bank ever sees two requests,
//             and k selected experts take k * EXPERT_ROWS cycles.
//   DEDICATED expert e lives whole in bank (e mod BANKS).  Selected experts
//             that share a bank serialise, and each bank returns one word per
//             cycle, so the read takes max_bank_load * EXPERT_WORDS cycles.
//
// THIS IS NOT A ROM MACRO.  The banks are behavioural arrays with no write
// port, a SENSE_LATENCY pipeline and one read per bank per cycle, which is the
// property the stream schedule depends on.  Bank depth, decoder and mux area,
// wire delay and read energy of deep striped banks are outside this block;
// see docs/ANALYTICAL_REPORT.md section 8.
// ---------------------------------------------------------------------------
module ot_rom_striped_expert_reader #(
    parameter integer BANKS         = 8,
    parameter integer WORD_BITS     = 32,
    parameter integer EXPERTS       = 16,
    parameter integer EXPERT_WORDS  = 64,     // must be a multiple of BANKS
    parameter integer MAX_SELECT    = 6,
    parameter integer SENSE_LATENCY = 2
) (
    input  wire                                  clk,
    input  wire                                  rst_n,
    input  wire                                  striped,      // 1 striped, 0 dedicated

    input  wire                                  start,
    input  wire [$clog2(MAX_SELECT+1)-1:0]       select_count,
    input  wire [MAX_SELECT*$clog2(EXPERTS)-1:0] select_ids,
    output wire                                  busy,

    // One lane per bank.  lane_valid[b] marks that bank b returned a word this
    // cycle; lane_expert / lane_word name which expert word it is.
    output reg  [BANKS-1:0]                      lane_valid,
    output reg  [BANKS*WORD_BITS-1:0]            lane_data,
    output reg  [BANKS*$clog2(EXPERTS)-1:0]      lane_expert,
    output reg  [BANKS*$clog2(EXPERT_WORDS)-1:0] lane_word,
    output reg                                   done,

    output reg  [31:0]                           read_cycles,  // start to done
    output reg  [31:0]                           words_read,
    output reg  [31:0]                           bank_conflicts // dedicated: selected experts serialised behind another in their bank
);
    localparam integer EW   = $clog2(EXPERTS);
    localparam integer WW   = $clog2(EXPERT_WORDS);
    localparam integer SW   = $clog2(MAX_SELECT+1);
    localparam integer EXPERT_ROWS = EXPERT_WORDS / BANKS;
    localparam integer STRIPED_ROWS = EXPERTS * EXPERT_ROWS;
    // Dedicated layout: bank b holds experts b, b+BANKS, ... back to back.
    localparam integer DEDICATED_ROWS = ((EXPERTS + BANKS - 1) / BANKS) * EXPERT_WORDS;
    localparam integer ROWS = (STRIPED_ROWS > DEDICATED_ROWS) ? STRIPED_ROWS : DEDICATED_ROWS;
    localparam integer RW   = $clog2(ROWS);
    localparam integer LAT  = (SENSE_LATENCY < 1) ? 1 : SENSE_LATENCY;

    // The stored value of expert e word w.  A fixed, non-trivial function so a
    // wrong bank, row or order is visible in the data, not only in the counts.
    function automatic [WORD_BITS-1:0] weight_value(input integer e, input integer w);
        weight_value = (e * 32'h9E37_79B1) ^ (w * 32'h85EB_CA77) ^ 32'hC2B2_AE3D;
    endfunction

    // -- the banks: one read port each, no write port anywhere -------------
    reg [WORD_BITS-1:0] striped_cell   [0:BANKS-1][0:STRIPED_ROWS-1];
    reg [WORD_BITS-1:0] dedicated_cell [0:BANKS-1][0:DEDICATED_ROWS-1];
    integer ib, ir, ie, iw;
    initial begin
        for (ie = 0; ie < EXPERTS; ie = ie + 1)
            for (iw = 0; iw < EXPERT_WORDS; iw = iw + 1) begin
                striped_cell[iw % BANKS][ie * EXPERT_ROWS + iw / BANKS] = weight_value(ie, iw);
                dedicated_cell[ie % BANKS][(ie / BANKS) * EXPERT_WORDS + iw] = weight_value(ie, iw);
            end
    end

    // -- request state --------------------------------------------------------
    reg              active;
    reg [SW-1:0]     count;
    reg [EW-1:0]     ids [0:MAX_SELECT-1];
    // Striped: one cursor walks (selected expert, row); every bank reads it.
    reg [SW-1:0]     s_sel;
    reg [WW:0]       s_row;
    // Dedicated: each bank walks its own queue of selected experts.
    reg [SW-1:0]     d_sel  [0:BANKS-1];   // next index into ids for this bank
    reg [WW:0]       d_word [0:BANKS-1];
    reg              d_done [0:BANKS-1];

    // Sense pipeline per bank.
    reg              p_valid  [0:BANKS-1][0:LAT-1];
    reg [WORD_BITS-1:0] p_data [0:BANKS-1][0:LAT-1];
    reg [EW-1:0]     p_expert [0:BANKS-1][0:LAT-1];
    reg [WW-1:0]     p_word   [0:BANKS-1][0:LAT-1];

    reg              issuing;
    reg [31:0]       inflight_drain;

    assign busy = active;

    // Next selected expert index at or after `from` that maps to bank b in the
    // dedicated layout; `count` if none.  Reads the latched ids.
    function automatic [SW-1:0] next_for_bank(input integer b, input integer from);
        integer j;
        begin
            next_for_bank = count;
            for (j = MAX_SELECT - 1; j >= 0; j = j - 1)
                if (j >= from && j < count && (ids[j] % BANKS) == b)
                    next_for_bank = j[SW-1:0];
        end
    endfunction

    // The same search over the request inputs, for the cycle the request lands.
    function automatic [SW-1:0] first_for_bank(input integer b);
        integer j;
        begin
            first_for_bank = select_count;
            for (j = MAX_SELECT - 1; j >= 0; j = j - 1)
                if (j < select_count && (select_ids[j*EW +: EW] % BANKS) == b)
                    first_for_bank = j[SW-1:0];
        end
    endfunction

    // Selected experts that share a dedicated bank with an earlier selection:
    // each one is a full expert read that cannot overlap its predecessor.
    function automatic [31:0] serialised_experts(input integer dummy);
        integer j, k;
        reg shared;
        begin
            serialised_experts = 0;
            for (j = 0; j < MAX_SELECT; j = j + 1) begin
                shared = 1'b0;
                for (k = 0; k < MAX_SELECT; k = k + 1)
                    if (k < j && j < select_count
                        && (select_ids[k*EW +: EW] % BANKS) == (select_ids[j*EW +: EW] % BANKS))
                        shared = 1'b1;
                if (shared) serialised_experts = serialised_experts + 1;
            end
        end
    endfunction

    integer b, s;
    reg any_live;
    reg [31:0] delivered;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 1'b0; done <= 1'b0; issuing <= 1'b0;
            read_cycles <= 0; words_read <= 0; bank_conflicts <= 0;
            lane_valid <= 0; lane_data <= 0; lane_expert <= 0; lane_word <= 0;
            count <= 0; s_sel <= 0; s_row <= 0; inflight_drain <= 0;
            for (b = 0; b < BANKS; b = b + 1) begin
                d_sel[b] <= 0; d_word[b] <= 0; d_done[b] <= 1'b1;
                for (s = 0; s < LAT; s = s + 1) p_valid[b][s] <= 1'b0;
            end
        end else begin
            done <= 1'b0;
            if (start && !active) begin
                active <= 1'b1; issuing <= 1'b1;
                count <= select_count;
                for (s = 0; s < MAX_SELECT; s = s + 1)
                    ids[s] <= select_ids[s*EW +: EW];
                s_sel <= 0; s_row <= 0;
                read_cycles <= 0; words_read <= 0;
                bank_conflicts <= striped ? 32'd0 : serialised_experts(0);
                for (b = 0; b < BANKS; b = b + 1) begin
                    d_word[b] <= 0;
                    d_sel[b]  <= first_for_bank(b);
                    d_done[b] <= (first_for_bank(b) >= select_count);
                end
                inflight_drain <= 0;
            end else if (active) begin
                read_cycles <= read_cycles + 1;
                for (b = 0; b < BANKS; b = b + 1) p_valid[b][0] <= 1'b0;
                // ---- issue: one read per bank per cycle, never more ----
                if (issuing) begin
                    if (striped) begin
                        if (s_sel < count) begin
                            for (b = 0; b < BANKS; b = b + 1) begin
                                p_valid[b][0]  <= 1'b1;
                                p_data[b][0]   <= striped_cell[b][ids[s_sel] * EXPERT_ROWS + s_row];
                                p_expert[b][0] <= ids[s_sel];
                                p_word[b][0]   <= s_row * BANKS + b;
                            end
                            if (s_row + 1 == EXPERT_ROWS) begin
                                s_row <= 0; s_sel <= s_sel + 1;
                            end else s_row <= s_row + 1;
                        end else issuing <= 1'b0;
                    end else begin
                        any_live = 1'b0;
                        for (b = 0; b < BANKS; b = b + 1)
                            if (!d_done[b]) begin
                                any_live = 1'b1;
                                p_valid[b][0]  <= 1'b1;
                                p_data[b][0]   <= dedicated_cell[b][(ids[d_sel[b]] / BANKS) * EXPERT_WORDS + d_word[b]];
                                p_expert[b][0] <= ids[d_sel[b]];
                                p_word[b][0]   <= d_word[b][WW-1:0];
                                if (d_word[b] + 1 == EXPERT_WORDS) begin
                                    d_word[b] <= 0;
                                    d_sel[b]  <= next_for_bank(b, d_sel[b] + 1);
                                    d_done[b] <= (next_for_bank(b, d_sel[b] + 1) >= count);
                                end else d_word[b] <= d_word[b] + 1;
                            end
                        if (!any_live) issuing <= 1'b0;
                    end
                end
                // ---- sense pipeline ----
                for (b = 0; b < BANKS; b = b + 1)
                    for (s = 1; s < LAT; s = s + 1) begin
                        p_valid[b][s]  <= p_valid[b][s-1];
                        p_data[b][s]   <= p_data[b][s-1];
                        p_expert[b][s] <= p_expert[b][s-1];
                        p_word[b][s]   <= p_word[b][s-1];
                    end
                // ---- deliver ----
                delivered = 0;
                for (b = 0; b < BANKS; b = b + 1) begin
                    lane_valid[b] <= p_valid[b][LAT-1];
                    lane_data[b*WORD_BITS +: WORD_BITS] <= p_data[b][LAT-1];
                    lane_expert[b*EW +: EW] <= p_expert[b][LAT-1];
                    lane_word[b*WW +: WW] <= p_word[b][LAT-1];
                    if (p_valid[b][LAT-1]) delivered = delivered + 1;
                end
                words_read <= words_read + delivered;
                if (!issuing) begin
                    inflight_drain <= inflight_drain + 1;
                    if (inflight_drain == LAT) begin
                        active <= 1'b0; done <= 1'b1;
                    end
                end
            end
        end
    end
endmodule
