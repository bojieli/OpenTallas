`timescale 1ns/1ps
`default_nettype none
// HBM-NSFIX/KQS 10-18 lockstep bench: registered ot_hgi_coll_kq_share2 (4 bank-pair leaves, 2,248-bit kq face) against
// the combinational version it replaces (kqs_comb_ref_leaf = the pre-10-18 leaf, verbatim) shifted by the recorded delta:
//   vm_kq(DUT) after edge t == vm_kq(comb) as sampled at edge t-1   (KQ_SHARE_EDGES = 2 at the bank sample edge)
//   fault(DUT) after edge t == fault(comb) after edge t-1           (+1 on the sticky fault)
// checked after every edge, every bit, through reset episodes: 0/3 clean static bookings (each bank edge booked for
// at most one of A / B, random data also on unbooked words), 1/4 one double booking (random edge, bank), 2/5 dense
// random bookings with ~10% double bookings. MUT 1..5 (see the leaf) must FAIL.
module kqs_comb_ref_leaf(
    input  wire clk, rst_n,
    input  wire [561:0] a_kq, b_kq,
    output reg  [561:0] vm_kq,
    output reg  fault
);
    always @* for (integer k = 0; k < 2; k = k + 1) begin : nb_14
        reg [1:0] v; v = {b_kq[281*k+280], a_kq[281*k+280]};
        vm_kq[281*k +: 281] = (v == 2'b01) ? a_kq[281*k +: 281] : (v == 2'b10) ? b_kq[281*k +: 281] : 281'd0;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) fault <= 1'b0;
        else for (integer k = 0; k < 2; k = k + 1) if (a_kq[281*k+280] && b_kq[281*k+280]) fault <= 1'b1;
endmodule

module tb_hgi_coll_kq_share2;
    parameter integer MUT = 0;
    localparam integer NEP = 6, NCY = 500;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    reg [2247:0] a = 0, b = 0;
    wire [2247:0] y, yr; wire f; wire [3:0] fr;
    ot_hgi_coll_kq_share2 #(.MUT(MUT)) dut(.clk_pair({4{clk}}), .rst_n(rst_n), .a_kq(a), .b_kq(b), .vm_kq(y), .fault(f));
    for (genvar p = 0; p < 4; p = p + 1) begin : g_ref
        kqs_comb_ref_leaf r(.clk(clk), .rst_n(rst_n), .a_kq(a[562*p +: 562]), .b_kq(b[562*p +: 562]), .vm_kq(yr[562*p +: 562]), .fault(fr[p]));
    end
    // the delta: the comb output as the bank sampled it at edge t-1, the comb fault after edge t-1
    reg [2247:0] e1 = 0, e2 = 0; reg fe1 = 0;
    always @(posedge clk) begin e1 <= yr; e2 <= e1; fe1 <= |fr; end
    integer checks = 0, errors = 0, wa = 0, wb = 0, dbl = 0, faulted = 0;
    reg chk = 0;
    always @(negedge clk) if (chk) begin
        checks++;
        if (y !== e2 || f !== fe1) begin
            errors++;
            if (errors <= 8) for (integer k = 0; k < 8; k = k + 1)
                if (y[281*k +: 281] !== e2[281*k +: 281] || k == 0)
                    $display("KQS mismatch t=%0t bank%0d y.v=%b exp.v=%b data_eq=%0d fault=%b exp=%b", $time, k, y[281*k+280], e2[281*k+280],
                             y[281*k +: 280] === e2[281*k +: 280], f, fe1);
        end
    end
    function automatic [279:0] rword();
        reg [287:0] w; for (integer j = 0; j < 9; j = j + 1) w[32*j +: 32] = $urandom; return w[279:0];
    endfunction
    initial begin
        void'($urandom(32'h4b51_5332));
        for (integer ep = 0; ep < NEP; ep = ep + 1) begin
            integer kind, hit_c, hit_b;
            kind = ep % 3; hit_c = 20 + ($urandom % (NCY - 40)); hit_b = $urandom % 8;
            @(negedge clk); chk = 0; rst_n = 0; a = 0; b = 0;
            repeat (4) @(negedge clk); rst_n = 1;
            repeat (8) @(negedge clk); chk = 1;
            for (integer c = 0; c < NCY; c = c + 1) begin
                for (integer k = 0; k < 8; k = k + 1) begin
                    integer r; reg va, vb; r = $urandom % 100;
                    if (kind == 2) begin va = r < 45; vb = (r >= 35 && r < 80); end      // 10% both
                    else begin va = r < 40; vb = r >= 55; end                           // never both
                    if (kind == 1 && c == hit_c && k == hit_b) begin va = 1; vb = 1; end
                    a[281*k +: 281] = {va, rword()}; b[281*k +: 281] = {vb, rword()};
                    wa += (va && !vb); wb += (vb && !va); dbl += (va && vb);
                end
                @(negedge clk);
            end
            a = 0; b = 0; repeat (4) @(negedge clk);
            faulted += f;
        end
        chk = 0;
        $display("KQS_SHARE2 MUT%0d episodes%0d checks%0d writesA%0d writesB%0d double%0d faulted_episodes%0d errors%0d %s",
                 MUT, NEP, checks, wa, wb, dbl, faulted, errors, (errors == 0 && faulted == 4 && checks > 0) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
`default_nettype wire
