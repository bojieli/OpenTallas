`timescale 1ns/1ps
// DIE-KV-93 11-08: miter ot_fdi_join2 RP_COPIES=16 vs RP_COPIES=1 (the original).  Random a/b valid streams with lane
// skew (bursts, gaps, resets): o_v / o_d identical EVERY edge.  -DKV93_RPC_MUT (copy 3 of arp advances on !pop) must FAIL.
module tb_fdi_join2_rpc;
    localparam integer WA = 522, WB = 521, DEPTH = 16;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0, a_v = 0, b_v = 0; reg [WA-1:0] a_d = 0; reg [WB-1:0] b_d = 0;
    wire ov0, ov1; wire [WA+WB-1:0] od0, od1;
    ot_fdi_join2 #(.WA(WA), .WB(WB), .DEPTH(DEPTH), .RP_COPIES(1)) u_a (.clk(clk), .rst_n(rst_n), .a_v(a_v), .a_d(a_d),
        .b_v(b_v), .b_d(b_d), .o_v(ov0), .o_d(od0));
    ot_fdi_join2 #(.WA(WA), .WB(WB), .DEPTH(DEPTH), .RP_COPIES(16)) u_b (.clk(clk), .rst_n(rst_n), .a_v(a_v), .a_d(a_d),
        .b_v(b_v), .b_d(b_d), .o_v(ov1), .o_d(od1));
`ifdef KV93_RPC_MUT
    always @(posedge clk) if (rst_n && !u_b.pop && ($urandom % 7) == 0) u_b.g_rpc.arp_c[3] <= u_b.g_rpc.arp_c[3] + 1'b1;
`endif
    integer i, k, mism = 0, edges = 0, pops = 0, an = 0, bn = 0;
    initial begin
        repeat (4) @(posedge clk);
        #0.1 rst_n = 1;
        for (i = 0; i < 20000; i = i + 1) begin
            #0.1;
            if (i % 5000 == 4999) rst_n = 0; else rst_n = 1;
            // keep both queues within DEPTH: send a half only while its queue has room
            a_v = ($urandom % 3 != 0) && (u_a.an < DEPTH - 1);
            b_v = ($urandom % 3 != 0) && (u_a.bn < DEPTH - 1);
            for (k = 0; k < 17; k = k + 1) begin a_d[32*k +: 32] = $urandom; b_d[32*k +: 32] = $urandom; end
            @(posedge clk); #0.05;
            edges = edges + 1; if (ov0) pops = pops + 1;
            if (ov0 !== ov1 || (ov0 && od0 !== od1) || od0 !== od1) begin
                mism = mism + 1;
                if (mism < 4) $display("MISMATCH edge %0d ov %b/%b", edges, ov0, ov1);
            end
        end
        if (mism == 0 && pops > 1000) $display("PASS fdi_join2_rpc edges=%0d pops=%0d mismatches=0", edges, pops);
        else $display("FAIL fdi_join2_rpc edges=%0d pops=%0d mismatches=%0d", edges, pops, mism);
        $finish;
    end
endmodule
