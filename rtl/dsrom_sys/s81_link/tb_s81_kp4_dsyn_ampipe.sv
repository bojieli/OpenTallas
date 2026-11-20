`timescale 1ns/1ps
// tb_s81_kp4_dsyn_ampipe (FABLE-FIX-S81-SERDES 11-19): ot_s81_kp4_dsyn AMPIPE=1 (OT_S81_KP4_AMOK_PIPE, am_ok cut by one
// register) equals AMPIPE=0 delayed by exactly one clock on every output (x_q, k_v, k_lo, k_L, k_any, lock, n_relock),
// on an encoded KP4 stream with AM corruptions (misses, drops, relocks) and p_v gaps.  MUT_B=1 (a mutant that does NOT
// delay the word: x0 <= p_d) must FAIL.  With OT_S81_KP4_AM_FACE3 the AM counts come from ot_s81_kp4_am_face3 on a
// face register, as in the kit.  PASS line: TB_S81_KP4_DSYN_AMPIPE PASS.
module tb_s81_kp4_dsyn_ampipe;
    parameter integer NB = 6000, MUT_B = 0;
    reg clk = 0, rst_n = 0;
    always #0.41667 clk = ~clk;
    reg tx_v = 0; reg [511:0] tx_d = 0;
    wire e_v; wire [543:0] e_d; wire efault;
    ot_s81_kp4_enc u_e (.clk(clk), .rst_n(rst_n), .tx_v(tx_v), .tx_d(tx_d), .p_v(e_v), .p_d(e_d), .fault(efault));
    reg [543:0] c_d; reg c_v; reg [11:0] flip;
    always @(posedge clk) begin c_v <= e_v; c_d <= e_d ^ {flip, 532'b0}; end
`ifdef OT_S81_KP4_AM_FACE3
    reg [543:0] f_d; reg f_v; wire [8:0] am3;
    always @(posedge clk) begin f_d <= c_d; f_v <= c_v; end
    ot_s81_kp4_am_face3 u_f (.clk(clk), .p_d(c_d), .parts(am3));
    `define AMF , .am_face3(am3)
`else
    wire [543:0] f_d = c_d; wire f_v = c_v;
    `define AMF
`endif
    wire [543:0] xa, xb; wire [3:0] kva, kvb; wire [309:0] kla, klb; wire [4:0] kLa, kLb; wire kya, kyb, la, lb; wire [31:0] na, nb;
    ot_s81_kp4_dsyn #(.AMPIPE(0)) u_a (.clk(clk), .rst_n(rst_n), .p_v(f_v), .p_d(f_d), .x_q(xa), .k_v(kva), .k_lo(kla), .k_L(kLa),
        .k_any(kya), .lock(la), .n_relock(na) `AMF);
    ot_s81_kp4_dsyn #(.AMPIPE(MUT_B ? 0 : 1)) u_b (.clk(clk), .rst_n(rst_n), .p_v(f_v), .p_d(f_d), .x_q(xb), .k_v(kvb), .k_lo(klb), .k_L(kLb),
        .k_any(kyb), .lock(lb), .n_relock(nb) `AMF);
    reg [930:0] a_dl;
    integer cyc = 0, bad = 0, locks = 0, lost = 0, kv = 0; reg la_q = 0;
    always @(posedge clk) begin
        a_dl <= {xa, kva, kla, kLa, kya, la, na};
        if (rst_n) begin
            cyc = cyc + 1;
            if (la && !la_q) locks = locks + 1;
            if (!la && la_q) lost = lost + 1;
            la_q = la;
            if (|kva) kv = kv + 1;
            if (cyc > 40 && {xb, kvb, klb, kLb, kyb, lb, nb} !== a_dl) begin
                bad = bad + 1; if (bad < 4) $display("ERR mismatch cycle %0d", cyc);
            end
        end
    end
    integer b;
    initial begin
        flip = 0;
        repeat (6) @(posedge clk); rst_n = 1;
        repeat (3) @(posedge clk);
        for (b = 0; b < NB; b = b + 1) begin
            @(negedge clk);
            tx_v = 1;
            tx_d = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                    $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
            // AM corruption bursts: frames 150..200 lose their AM (drop + relock), sparse 1..3-bit flips elsewhere
            flip = (b >= 1500 && b < 2000) ? 12'hFFF : (($urandom % 37) == 0 ? (12'h1 << ($urandom % 12)) : 12'h0);
        end
        @(negedge clk); tx_v = 0; flip = 0;
        repeat (60) @(posedge clk);
        $display("TB_S81_KP4_DSYN_AMPIPE cycles %0d mismatches %0d locks %0d losses %0d k_valid %0d", cyc, bad, locks, lost, kv);
        if (bad == 0 && locks >= 2 && lost >= 1 && kv > 20) $display("TB_S81_KP4_DSYN_AMPIPE PASS");
        else $display("TB_S81_KP4_DSYN_AMPIPE FAIL");
        $finish;
    end
endmodule
