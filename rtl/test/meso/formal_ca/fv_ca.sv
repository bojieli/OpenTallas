// MESO-COUNT-1 formal harness for ot_dp_clk_landing_ca (SymbiYosys, multiclock on, abc pdr).
// Global time = $global_clock steps; one clock period P = 8 steps.  tclk rises at t = 0 mod 8, rclk at t = PH mod 8
// (PH anyconst: every static phase at 1/8 period resolution).  The sender start (count origin) is released after SR
// tclk edges, the receiver's after RR rclk edges (anyconst): together with PH they span every whole-cycle offset in
// L = t(receiver origin edge) + K*P - t(sender origin edge) (the lag of every word) from -2 P to +7 P.
// Metastability / STA bound: a slot read within 0..3 steps (< P/2) of its write, or a guard sample taken at the write
// instant, returns an ARBITRARY value (fv_any, anyseq).
//   A_SAFE  (every PH, SR, RR; no window assumption): ready && !fault -> q == the word the sender presented at count
//           (receiver count - 1 - K), i.e. latency is exactly K+1 receiver cycles or the crossing is not ready.
//   A_NOFLT (L in the guard window [5,27] steps): fault never rises.
//   A_LIVE  (L in the window): ready by step 600 (75 cycles).
// Together: for every static phase in the window the latency is the same fixed K, the crossing comes up, and outside
// it the crossing fails closed.
module fv_ca #(parameter integer K = 2, parameter integer LMIN = 5, parameter integer LMAX = 27) (
    input wire [1:0] d,
    input wire [5:0] fv_any
);
    localparam integer D = 4, P = 8;
    (* anyconst *) reg [2:0] PH;
    (* anyconst *) reg [2:0] SR;
    (* anyconst *) reg [2:0] RR;
    (* anyconst *) reg [4:0] N;          // watched sender word (mod 32)
    always @* begin assume(SR >= 1 && SR <= 5); assume(RR >= 1 && RR <= 6); end
    reg [2:0] tick = 0;
    reg [9:0] t = 0;                       // saturating global time
    wire tclk = (tick < 3'd4);
    wire [2:0] rt = tick - PH;
    wire rclk = (rt < 3'd4);
    // clk2fflogic: a flop clocked at step s+1 samples its D at step s.  All harness state is global-clock state
    // updated at the step BEFORE an edge (tn / rn), so it changes exactly like a tclk / rclk flop.
    wire tn = (tick == 3'd7);              // tclk rises at the next step
    wire [2:0] tick1 = tick + 3'd1;
    wire rn = (tick1 == PH);               // rclk rises at the next step
    reg [2:0] te = 0, re = 0; reg t_rst_n = 0, rst_n = 0;
    reg [4:0] sc = 0, rc = 0; reg [1:0] cap = 0; reg capv = 0;
    reg [9:0] tw0 = 0, tr0 = 0; reg w0 = 0, r0 = 0;
    wire wr = tn && t_rst_n;               // a word is written at the next step, slot sc[1:0]
    always @($global_clock) begin
        tick <= tick + 1'b1; if (t != 10'h3ff) t <= t + 1'b1;
        if (tn) begin
            if (te != 3'd7) te <= te + 1'b1;
            t_rst_n <= t_rst_n || ({1'b0, te} + 4'd1 >= {1'b0, SR});   // sticky release (te saturates at 7)
            if (t_rst_n) begin
                sc <= sc + 1'b1;
                if (sc == N) begin cap <= d; capv <= 1'b1; end
                if (!w0) begin w0 <= 1'b1; tw0 <= t + 1'b1; end
            end
        end
        if (rn) begin
            if (re != 3'd7) re <= re + 1'b1;
            rst_n <= rst_n || ({1'b0, re} + 4'd1 >= {1'b0, RR});
            if (rst_n) begin
                rc <= rc + 1'b1;
                if (!r0) begin r0 <= 1'b1; tr0 <= t + 1'b1; end
            end
        end
    end
    wire lknown = w0 && r0;
    wire signed [11:0] L = $signed({2'b0, tr0}) + K * P - $signed({2'b0, tw0});
    wire inwin = lknown && L >= LMIN && L <= LMAX;
    // metastability / STA bound (values seen by a flop clocked at the NEXT step): the slot is written at the next step
    // (wnext: coincident sample) or was written 0..2 steps ago (age): read lag 0..3 steps -> arbitrary data.
    reg [2:0] age [0:D-1];
    integer i;
    initial for (i = 0; i < D; i = i + 1) age[i] = 3'd7;
    wire [D-1:0] wnext, recent;
    genvar g;
    for (g = 0; g < D; g = g + 1) begin : gw
        assign wnext[g] = wr && (sc[1:0] == g);
        always @($global_clock) age[g] <= wnext[g] ? 3'd0 : ((age[g] == 3'd7) ? 3'd7 : age[g] + 1'b1);
        assign recent[g] = wnext[g] || (age[g] <= 3'd2);
    end
    wire [1:0] q; wire ready, fault;
    ot_dp_clk_landing_ca #(.W(2), .DEPTH(D), .K(K)) dut (
        .fclk(tclk), .t_rst_n(t_rst_n), .clk(rclk), .rst_n(rst_n), .d(d), .q(q), .ready(ready), .fault(fault),
        .fv_recent(recent), .fv_now(wnext), .fv_any(fv_any));
    wire [4:0] idx = rc - 5'd1 - 5'(K);
    always @* begin
        if (ready && !fault && rc != 0 && idx == N) A_SAFE: assert (capv && q == cap);
        if (inwin) A_NOFLT: assert (!fault);
        if (t >= 10'd600 && inwin) A_LIVE: assert (ready);
    end
`ifdef FV_REACH
    always @* A_REACH: assert (!(ready && inwin));
`endif
`ifdef FV_COVER
    always @* begin
        C_WIN_LO: cover (inwin && L == LMIN && ready);
        C_WIN_HI: cover (inwin && L == LMAX && ready);
        C_OUT_LO: cover (lknown && L == LMIN - 2 && fault);
        C_OUT_HI: cover (lknown && L == LMAX + 2 && fault);
    end
`endif
endmodule
