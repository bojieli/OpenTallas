// Experimental registered fork, NOT a closed tile or adopted die master.
// Input A/B/cl/q/e pieces must arrive on the same clock edge. Outputs are
// independent registered copies, and preserve t/e alignment for both heads.
// A transport insertion requires the ectl score/tag/nb latency contract and
// the end-to-end bench to be updated/proved; this module alone proves neither.
module qfd_ectl_word_fork_candidate #(
    parameter integer MUT_ROW_SWAP = 0
) (
    input wire ck,
    input wire rst_n,
    input wire [511:0] row_a,
    input wire [511:0] row_b,
    input wire [15:0] cl,
    input wire [518:0] q,
    input wire [15:0] e0,
    input wire [15:0] e1,
    output wire [1558:0] t0,
    output wire [1558:0] t1,
    output wire [15:0] eo0,
    output wire [15:0] eo1
);
    wire [1558:0] word_in = MUT_ROW_SWAP ?
        {q, cl[15:4], row_a, row_b, cl[3:0]} :
        {q, cl[15:4], row_b, row_a, cl[3:0]};
    // Physical realization must verify two independent 1,575-Q banks survive
    // synthesis. These attributes express that requirement; they are no proof.
    (* keep = "true", dont_touch = "true" *) reg [1574:0] bank0;
    (* keep = "true", dont_touch = "true" *) reg [1574:0] bank1;
    always @(posedge ck) begin
        if (!rst_n) begin
            bank0 <= 1575'd0;
            bank1 <= 1575'd0;
        end else begin
            bank0 <= {e0, word_in};
            bank1 <= {e1, word_in};
        end
    end
    assign {eo0, t0} = bank0;
    assign {eo1, t1} = bank1;
endmodule
