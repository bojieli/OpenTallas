module ot_s81sl_ve_dly #(parameter integer W = 32, D = 1, MUT = 0, ZERO_LOW = 0) (
    input wire clk, input wire [W-1:0] d, input wire [W-1:0] d2, output wire [W-1:0] q, output wire [W-1:0] q2);
    generate if (D >= 3) begin : g_ring
        ot_s81sl_ve_ring #(.W(W), .D(D), .MUT(MUT), .ZERO_LOW(ZERO_LOW)) u (clk, d, q, q2);
    end else if (D == 0) begin : g_w
        assign q = d;
        assign q2 = d2;
    end else begin : g_sh
        // r4b: both chains are kept registers (ot_hdc_delay's unkept flops folded into the kept copy chain)
        (* keep *) reg [W-1:0] p [0:D-1];
        (* keep *) reg [W-1:0] c [0:D-1];
        integer i;
        always @(posedge clk) begin
            p[0] <= d;
            c[0] <= d2;
            for (i = 1; i < D; i = i + 1) begin p[i] <= p[i - 1]; c[i] <= c[i - 1]; end
        end
        assign q = p[D - 1];
        assign q2 = c[D - 1];
    end endgenerate
endmodule

module ot_s81sl_ve_ring #(parameter integer W = 32, D = 3, MUT = 0, ZERO_LOW = 0) (
    input wire clk, input wire [W-1:0] d, output wire [W-1:0] q, output wire [W-1:0] q2);
    localparam integer N = D - 2;
    localparam integer K = (N <= 2) ? 1 : $clog2(N);
    localparam [K-1:0] LAST = N - 1;
    localparam integer S = (W + 7) / 8;
    // Opt-in, caller-declared constant BF16 lanes. The selected ve_m input
    // expands BF16 with literal low16 zeroes; physical synthesis already
    // folds these lanes. Keep their RTL startup meaning explicit.
    localparam [W-1:0] DATA_MASK = {W{1'b1}} << ZERO_LOW;
    reg [W-1:0] din;
    (* keep *) reg [W-1:0] dout;                 // r4b: kept like dout2
    (* keep *) reg [W-1:0] dout2;                // VE4: kept copy of the output register (same D)
    reg [K-1:0] wptr;
    wire [K-1:0] wnext = (wptr >= LAST) ? {K{1'b0}} : wptr + 1'b1;
    reg  [N-1:0] oh_d, oh_late;
    integer r;
    always @* for (r = 0; r < N; r = r + 1) begin
        oh_d[r] = (wnext == r[K-1:0]);
        oh_late[r] = (wptr == r[K-1:0]);
    end
    always @(posedge clk) begin din <= d & DATA_MASK; wptr <= wnext; end
    genvar sl, i;
    generate for (sl = 0; sl < S; sl = sl + 1) begin : g_s
        localparam integer LO = 8 * sl;
        localparam integer SW = (W - LO) < 8 ? (W - LO) : 8;
        (* keep = "true" *) reg [N-1:0] oh;          // this slice's row select copy
        always @(posedge clk) oh <= oh_d;
        // MUT 3 (bench only): slice 1 READS one row late (a uniformly rotated select would still be exact)
        reg [N-1:0] ohr;
        always @(posedge clk) ohr <= (MUT == 3 && sl == 1) ? oh_late : oh_d;
        wire [N-1:0] rsel = (MUT == 3) ? ohr : oh;
        wire [SW*N-1:0] sel;
        for (i = 0; i < N; i = i + 1) begin : g_r
            reg [SW-1:0] row;
            always @(posedge clk) if (oh[i]) row <= din[LO +: SW];
            assign sel[SW*i +: SW] = row & {SW{rsel[i]}};
        end
        reg [SW-1:0] rd;
        integer j;
        always @* begin rd = {SW{1'b0}}; for (j = 0; j < N; j = j + 1) rd = rd | sel[SW*j +: SW]; end
        always @(posedge clk) dout[LO +: SW] <= rd & DATA_MASK[LO +: SW];
        always @(posedge clk) dout2[LO +: SW] <= rd & DATA_MASK[LO +: SW];
    end endgenerate
    assign q = dout;
    assign q2 = dout2;
`ifndef SYNTHESIS
    initial wptr = {K{1'b0}};
`endif
endmodule
