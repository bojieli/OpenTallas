// TOPK5 unbound arithmetic transport pilot. See guarded_mux_model.json.
// Every payload bit is captured at the boundary, transported once, then merged.
// Copies are structural and retained by the actual ot_keep_regs synthesis hook.
module ot_s81ph_native_guarded_mux #(
    parameter integer W = 148,
    parameter integer CHUNK = 12,
    parameter integer MUT = 0
) (
    input wire clk, rst_n,
    input wire [W-1:0] a, b,
    input wire [1:0] sel,
    output reg [W-1:0] y
);
    localparam integer NC = (W+CHUNK-1)/CHUNK;
    initial begin
        if (W < 1 || W > 148 || CHUNK < 1 || CHUNK > 12 || NC > 15)
            $fatal(1, "guarded mux shape exceeds modeled reset/control budget");
    end
    (* keep = 1 *) reg rst_l0, rst_l1;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin rst_l0 <= 1'b0; rst_l1 <= 1'b0; end
        else begin rst_l0 <= 1'b1; rst_l1 <= rst_l0; end
    end
    reg [W-1:0] a0, b0, a1, b1;
    (* keep = 1 *) reg [1:0] s0;
    (* keep = 1 *) reg [1:0] s1 [0:NC-1];
    always @(posedge clk) begin
        a0 <= a; b0 <= b;
        a1 <= a0; b1 <= b0;
    end
    always @(posedge clk or negedge rst_l1) begin
        if (!rst_l1) s0 <= 2'b00;
        else s0 <= sel;
    end
    genvar c;
    generate for (c=0; c<NC; c=c+1) begin : g_chunk
        localparam integer N = ((W-c*CHUNK) < CHUNK) ? (W-c*CHUNK) : CHUNK;
        always @(posedge clk or negedge rst_l1) begin
            if (!rst_l1) s1[c] <= 2'b00;
            else s1[c] <= s0;
        end
        wire ca = (MUT == 1 && c == 0) ? s1[c][1] : s1[c][0];
        wire cb = (MUT == 2 && c == NC-1) ? 1'b0 : s1[c][1];
        always @(posedge clk)
            y[c*CHUNK +: N] <= (a1[c*CHUNK +: N] & {N{ca}}) |
                                (b1[c*CHUNK +: N] & {N{cb}});
    end endgenerate
endmodule
