
// a W-bit bundle, registered when CUT = 1 (bit 0... the bundle's MSB is the valid, reset to 0), else passed through
// VB >= 0 (fe-push-hphys-1010, opt-in): only bit VB (the bundle's valid) is reset; the data bits are plain flops (a wide
// datapath costs no reset fan-out; validity travels on the reset bit).  VB < 0 (default): every bit reset, as before.
module ot_hdc_w11_cut #(parameter integer W = 1, parameter integer CUT = 0, parameter integer VB = -1) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (CUT && VB < 0) begin : g_r
        reg [W-1:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) r <= {W{1'b0}};
            else r <= d;
        end
        assign q = r;
    end else if (CUT) begin : g_rv
        reg rv;
        reg [W-1:0] rd;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) rv <= 1'b0;
            else rv <= d[VB];
        end
        always @(posedge clk) rd <= d;
        genvar i;
        for (i = 0; i < W; i = i + 1) begin : g_b
            assign q[i] = (i == VB) ? rv : rd[i];
        end
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule
