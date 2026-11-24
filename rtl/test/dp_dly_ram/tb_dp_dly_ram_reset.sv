`timescale 1ns/1ps
// DLYRAM-RESET 11-24: reset release through ot_dp_dly_ram, one clock domain per ring, at the six real (W, D) of the
// kv3_pv_v3 PADRAM kit (u_pdram_0..5: 256 x 116, 128 x 121 / 80 / 78 / 47 / 37).  Per domain: a source core register WITH
// reset (0 while held, then random data; bit 0 = valid), the ring, and a consumer core WITH reset released on the same edge
// as the source (Rc - Rs = 0, the worst case: the line has only the hold to flush).  The consumer checks, every cycle after
// its release, that the ring output equals the source value D edges earlier (defined from t = 0: the source resets
// asynchronously at t = 0) and is never X.  Hold H = D + HOFF clocks of running clock (+HOFF=..., default 2).
// Pass: DLYRST bad=0 x=0 in every domain.  Expected FAIL (negative controls): HOFF < 0, or 4-state without
// OT_DLY_RAM_PTR_INIT (X forever: X + 1 = X on wp).
module dom #(parameter integer W = 128, parameter integer D = 37, parameter real HP = 0.4165, parameter integer K = 0) (
    input wire run, output integer bad, output integer xb, output integer chk);
    reg clk = 0;
    always #(HP) if (run) clk = ~clk;
    integer cyc = 0, H, i;
    reg rst_n = 0;
    reg [W-1:0] src;
    reg [W-1:0] hist [0:4095];
    wire [W-1:0] q;
    ot_dp_dly_ram #(.W(W), .D(D)) u_ring (.clk(clk), .d(src), .q(q));
    integer ho;
    initial begin if (!$value$plusargs("HOFF=%d", ho)) ho = 2; H = D + ho; bad = 0; xb = 0; chk = 0; end
    // source core: async reset, clear while held
    always @(posedge clk or negedge rst_n)
        if (!rst_n) src <= {W{1'b0}};
        else for (i = 0; i < W; i = i + 1) src[i] <= $urandom;
    // domain reset: low for H clocks of running clock, synchronous release
    always @(posedge clk) begin cyc <= cyc + 1; rst_n <= (cyc + 1 >= H); end
    // history of what the source drove before each edge (src is 0 from t = 0: rst_n starts low)
    initial src = {W{1'b0}};   // the asynchronous source reset at power-up (rst_n starts low)
    always @(posedge clk) hist[cyc] <= src;
    // consumer core: async reset, same release edge as the source; after release the ring output must be the source
    // value sampled D edges earlier
    reg [W-1:0] acc;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) acc <= {W{1'b0}};
        else begin
            chk = chk + 1;
            if (^q === 1'bx) begin if (xb < 2) $display("DOM%0d X cyc=%0d", K, cyc); xb = xb + 1; end
            else if (cyc >= D && q !== hist[cyc - D]) begin if (bad < 2) $display("DOM%0d MISMATCH cyc=%0d", K, cyc); bad = bad + 1; end
            else if (cyc < D) begin if (bad < 2) $display("DOM%0d EARLY cyc=%0d (line not flushed)", K, cyc); bad = bad + 1; end
            if (q[0]) acc <= acc ^ q;
        end
endmodule

module tb_dp_dly_ram_reset;
    reg run = 1;
    integer hoff = 2;
    integer b[0:5], x[0:5], c[0:5];
    initial if (!$value$plusargs("HOFF=%d", hoff)) hoff = 2;
    dom #(.W(256), .D(116), .HP(0.4165), .K(0)) d0 (.run(run), .bad(b[0]), .xb(x[0]), .chk(c[0]));
    dom #(.W(128), .D(121), .HP(0.4313), .K(1)) d1 (.run(run), .bad(b[1]), .xb(x[1]), .chk(c[1]));
    dom #(.W(128), .D(80),  .HP(0.3907), .K(2)) d2 (.run(run), .bad(b[2]), .xb(x[2]), .chk(c[2]));
    dom #(.W(128), .D(78),  .HP(0.4999), .K(3)) d3 (.run(run), .bad(b[3]), .xb(x[3]), .chk(c[3]));
    dom #(.W(128), .D(47),  .HP(0.3331), .K(4)) d4 (.run(run), .bad(b[4]), .xb(x[4]), .chk(c[4]));
    dom #(.W(128), .D(37),  .HP(0.4447), .K(5)) d5 (.run(run), .bad(b[5]), .xb(x[5]), .chk(c[5]));
    integer k, tb_, tx;
    initial begin
        #(0.5 * 2 * 700);
        run = 0; tb_ = 0; tx = 0;
        for (k = 0; k < 6; k = k + 1) begin
            $display("DLYRST dom=%0d checked=%0d bad=%0d x=%0d", k, c[k], b[k], x[k]);
            tb_ = tb_ + b[k]; tx = tx + x[k];
        end
        $display("DLYRST hoff=%0d bad=%0d x=%0d %s", hoff, tb_, tx, (tb_ == 0 && tx == 0) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
