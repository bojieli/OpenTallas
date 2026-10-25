module dsdv_svc_f2b_tx #(
    parameter integer W = 2133,                 // word bits {d, v}; odd
    parameter integer MUT = 0
) (
    input  wire                 ck,
    input  wire                 rn,             // die reset, active low: control state only
    input  wire                 v,              // word valid (= word[0])
    input  wire [W-2:0]         d,              // word[W-1:1]
    output wire [(W+1)/2:0]     o,              // {beat, payload[P-1:0]}, P = (W + 1) / 2: the face pin register
    output reg                  fault
);
    localparam integer P = (W + 1) / 2, H = W - P;   // 1067 low (beat 0), 1066 high (beat 1)
    wire [W-1:0] word = {d, v};
    wire [P-1:0] lo_w = word[P-1:0];
    wire [P-1:0] hi_w = {{(P-H){1'b0}}, word[W-1:P]};
    reg owe;                                    // beat 1 owed next cycle
    reg [P-1:0] hold;                           // the half that leaves in the second beat (data, no reset)
    // pin register {beat, payload}: beat (oq_b) and payload[0] (oq_v: v in beat 0) reset (control), the rest data
    reg oq_b, oq_v; reg [P-1:1] oq_d;
    always @(posedge ck) if (v && !owe) hold <= (MUT == 1) ? lo_w : hi_w;
    always @(posedge ck) oq_d <= owe ? hold[P-1:1] : ((MUT == 1) ? hi_w[P-1:1] : lo_w[P-1:1]);
    always @(posedge ck or negedge rn)
        if (!rn) begin owe <= 1'b0; fault <= 1'b0; oq_b <= 1'b0; oq_v <= 1'b0; end
        else begin
            owe <= v && !owe;
            if (v && owe) fault <= 1'b1;        // a word while beat 1 of the previous one is owed: rate violation
            oq_b <= owe;
            oq_v <= owe ? hold[0] : ((MUT == 1) ? hi_w[0] : v);
        end
    assign o = {oq_b, oq_d, oq_v};
endmodule

module dsdv_svc_f2b_rx #(
    parameter integer W = 2133
) (
    input  wire                 ck,
    input  wire                 rn,
    input  wire [(W+1)/2:0]     i,              // {beat, payload[P-1:0]}
    output wire                 v,              // word valid, the cycle after beat 1 reached the pin register
    output wire [W-2:0]         d,              // word[W-1:1]
    output reg                  fault
);
    localparam integer P = (W + 1) / 2, H = W - P;
    // pin register: beat (iq_b) and payload[0] (iq_v: v of beat 0) reset (control), the rest data
    reg iq_b, iq_v; reg [P-1:1] iq_d;
    always @(posedge ck) iq_d <= i[P-1:1];
    wire [P-1:0] iq = {iq_d, iq_v};
    wire bt = iq_b;
    reg exp;                                    // beat 1 expected this cycle (the previous beat 0 carried v = 1)
    reg [P-1:0] lo;                             // beat 0's payload (data, no reset)
    always @(posedge ck) if (!bt) lo <= iq[P-1:0];
    always @(posedge ck or negedge rn)
        if (!rn) begin iq_b <= 1'b0; iq_v <= 1'b0; exp <= 1'b0; fault <= 1'b0; end
        else begin
            iq_b <= i[P]; iq_v <= i[0];
            exp <= !bt && iq[0];
            if (bt && !exp) fault <= 1'b1;      // beat 1 without its beat 0
            if (!bt && exp) fault <= 1'b1;      // beat 0 where beat 1 is owed (missing / reordered beat)
            if (bt && iq[P-1]) fault <= 1'b1;   // beat-1 pad bit (payload[P-1]) must be 0
        end
    wire [W-1:0] word = {iq[H-1:0], lo};
    assign v = bt && exp;                       // word[0] = lo[0] = 1 whenever exp
    assign d = word[W-1:1];
endmodule
