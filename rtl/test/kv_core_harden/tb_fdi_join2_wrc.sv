`timescale 1ns/1ps
// DIE-KV-93 11-08: ot_fdi_join2 RP_COPIES=16 + WR_COPIES=16 (registered one-hot write enables, +1 input cycle) vs the
// original (RP_COPIES=1, WR_COPIES=0).  Random a/b valid streams with lane skew (bursts, gaps, resets): every flit the
// original pops at edge k is popped by the new form at edge k+1 with the same o_d, in order, and no other pops (a flit
// in flight across a reset is flushed by both).  -DKV93_WRC_MUT (one enable copy, slice 5, writes the wrong entry at
// random) must FAIL.
module tb_fdi_join2_wrc;
    localparam integer WA = 522, WB = 521, DEPTH = 16, W = WA + WB;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0, a_v = 0, b_v = 0; reg [WA-1:0] a_d = 0; reg [WB-1:0] b_d = 0;
    wire ov0, ov1; wire [W-1:0] od0, od1;
    ot_fdi_join2 #(.WA(WA), .WB(WB), .DEPTH(DEPTH), .RP_COPIES(1)) u_a (.clk(clk), .rst_n(rst_n), .a_v(a_v), .a_d(a_d),
        .b_v(b_v), .b_d(b_d), .o_v(ov0), .o_d(od0));
    ot_fdi_join2 #(.WA(WA), .WB(WB), .DEPTH(DEPTH), .RP_COPIES(16), .WR_COPIES(16)) u_b (.clk(clk), .rst_n(rst_n),
        .a_v(a_v), .a_d(a_d), .b_v(b_v), .b_d(b_d), .o_v(ov1), .o_d(od1));
`ifdef KV93_WRC_MUT
    always @(negedge clk) if (rst_n && u_b.g_wrc.wa_c[5] != 0 && ($urandom % 5) == 0)
        u_b.g_wrc.wa_c[5] = {u_b.g_wrc.wa_c[5][DEPTH-2:0], u_b.g_wrc.wa_c[5][DEPTH-1]};
`endif
    reg [W-1:0] exp_d [0:63];
    integer exp_e [0:63];
    integer hd = 0, tl = 0, i, k, mism = 0, edges = 0, pops0 = 0, pops1 = 0, matched = 0;
    initial begin
        repeat (4) @(posedge clk);
        #0.1 rst_n = 1;
        for (i = 0; i < 20000; i = i + 1) begin
            #0.1;
            if (i % 5000 == 4999) rst_n = 0; else rst_n = 1;
            a_v = ($urandom % 3 != 0) && (u_a.an < DEPTH - 1);
            b_v = ($urandom % 3 != 0) && (u_a.bn < DEPTH - 1);
            for (k = 0; k < 17; k = k + 1) begin a_d[32*k +: 32] = $urandom; b_d[32*k +: 32] = $urandom; end
            @(posedge clk); #0.05;
            edges = edges + 1;
            if (!rst_n) begin hd = 0; tl = 0; end      // both forms flush
            else begin
                if (ov1) begin
                    pops1 = pops1 + 1;
                    if (hd == tl || exp_e[hd % 64] != edges - 1 || exp_d[hd % 64] !== od1) begin
                        mism = mism + 1; if (mism < 4) $display("MISMATCH edge %0d (queue %0d)", edges, tl - hd);
                    end else matched = matched + 1;
                    if (hd != tl) hd = hd + 1;
                end else if (hd != tl && exp_e[hd % 64] < edges - 1) begin
                    mism = mism + 1; if (mism < 4) $display("MISSING pop edge %0d", edges); hd = hd + 1;
                end
                if (ov0) begin pops0 = pops0 + 1; exp_d[tl % 64] = od0; exp_e[tl % 64] = edges; tl = tl + 1; end
            end
        end
        if (mism == 0 && matched > 1000) $display("PASS fdi_join2_wrc edges=%0d pops0=%0d pops1=%0d matched=%0d mismatches=0", edges, pops0, pops1, matched);
        else $display("FAIL fdi_join2_wrc edges=%0d pops0=%0d pops1=%0d matched=%0d mismatches=%0d", edges, pops0, pops1, matched, mism);
        $finish;
    end
endmodule
