`timescale 1ns/1ps
// S81-RF1 (DIE-S81-51/RF-C/gu 11-03): dsdv_gunit_l4 RE-FORM bench.  gold = RF 0 / OLAT 0, gate = RF 1 / OLAT 1 (one-hot
// store / read selects registered one edge ahead, face lockup latches): 0 cycles.  Random inputs every edge (group
// stream with random index / accumulator, jobs, cw rows incl. the eps row, L4r r returns, rung / CTL feedthroughs);
// every output port compared every edge, bit for bit (mx_y on mx_v edges: its valid-qualified payload).  Prints L4_RF PASS / FAIL <n> (+ coverage counts).
module tb_l4_rf (input wire clk);
    reg rst_n = 0;
    reg [275:0] rs_i = 0, rn_i = 0; reg g_v = 0; reg [3:0] g_i = 0; reg [4:0] g_acc = 0; reg [319:0] g_d = 0;
    reg j_v = 0, j_set = 0, j_w = 0; reg [9:0] j_row = 0; reg [4:0] j_lm = 0; reg [15:0] j_sm = 0;
    reg cw_v = 0; reg [7:0] cw_a = 0; reg [255:0] cw_d = 0; reg [3:0] sid_i = 0;
    reg hct5_v = 0; reg [169:0] hct5_b = 0; reg f5 = 0; reg r_v = 0; reg [31:0] r_y = 0; reg r_f = 0;
    localparam integer OW = 1132;
    wire [OW-1:0] o0, o1;
    wire [OW-1:0] msk = ~({{(OW-765){1'b0}}, {32{1'b1}}, {733{1'b0}}});
    dsdv_gunit_l4 #(.RF(0), .OLAT(0)) u_old (.clk(clk), .rst_n(rst_n), .rs_i(rs_i), .rs_o(o0[275:0]), .g_v(g_v), .g_i(g_i),
        .g_acc(g_acc), .g_d(g_d), .j_v(j_v), .j_set(j_set), .j_w(j_w), .j_row(j_row), .j_lm(j_lm), .j_sm(j_sm), .cw_v(cw_v),
        .cw_a(cw_a), .cw_d(cw_d), .sid_i(sid_i), .hct_v(o0[276]), .hct_b(o0[446:277]), .mix_go_s(o0[447]), .launch_s(o0[448]),
        .fault(o0[449]), .rn_o(o0[725:450]), .rn_i(rn_i), .launch(o0[726]), .mx_v(o0[727]), .mx_i(o0[732:728]), .mx_y(o0[764:733]),
        .t_set(o0[765]), .t_w(o0[766]), .t_row(o0[776:767]), .t_lm(o0[781:777]), .t_sm(o0[797:782]), .cwo_v(o0[798]),
        .cwo_a(o0[806:799]), .cwo_d(o0[1062:807]), .sid_o(o0[1066:1063]), .hct5_v(hct5_v), .hct5_b(hct5_b), .f5(f5),
        .ss_v(o0[1067]), .ss(o0[1099:1068]), .eps_c(o0[1131:1100]), .r_v(r_v), .r_y(r_y), .r_f(r_f));
    dsdv_gunit_l4 #(.RF(1), .OLAT(1)) u_new (.clk(clk), .rst_n(rst_n), .rs_i(rs_i), .rs_o(o1[275:0]), .g_v(g_v), .g_i(g_i),
        .g_acc(g_acc), .g_d(g_d), .j_v(j_v), .j_set(j_set), .j_w(j_w), .j_row(j_row), .j_lm(j_lm), .j_sm(j_sm), .cw_v(cw_v),
        .cw_a(cw_a), .cw_d(cw_d), .sid_i(sid_i), .hct_v(o1[276]), .hct_b(o1[446:277]), .mix_go_s(o1[447]), .launch_s(o1[448]),
        .fault(o1[449]), .rn_o(o1[725:450]), .rn_i(rn_i), .launch(o1[726]), .mx_v(o1[727]), .mx_i(o1[732:728]), .mx_y(o1[764:733]),
        .t_set(o1[765]), .t_w(o1[766]), .t_row(o1[776:767]), .t_lm(o1[781:777]), .t_sm(o1[797:782]), .cwo_v(o1[798]),
        .cwo_a(o1[806:799]), .cwo_d(o1[1062:807]), .sid_o(o1[1066:1063]), .hct5_v(hct5_v), .hct5_b(hct5_b), .f5(f5),
        .ss_v(o1[1067]), .ss(o1[1099:1068]), .eps_c(o1[1131:1100]), .r_v(r_v), .r_y(r_y), .r_f(r_f));
    integer cyc = 0, errs = 0, ncyc, nmx = 0, nss = 0, nl = 0, gi = 0, x, ph = 0;
    function [31:0] fp(input integer z); fp = {1'b0, 8'd120 + 8'($urandom % 16), 23'($urandom)}; endfunction
    initial begin if (!$value$plusargs("CYC=%d", ncyc)) ncyc = 200000; end
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc > 8) begin
            // mx_y (bits 764:733) is the valid-qualified mix payload: compared on mx_v edges only (RF 0 reads proj[m_i]
            // with m_i un-reset / 24 = past the store while idle, RF 1 reads 0 there)
            if ((o1 & msk) !== (o0 & msk) || (o0[727] && o1[764:733] !== o0[764:733])) begin errs = errs + 1;
                if (errs < 6) for (x = 0; x < OW; x = x + 1) if (o1[x] !== o0[x]) begin $display("ERR cyc %0d bit %0d", cyc, x); x = OW; end end
            if (o0[727]) nmx = nmx + 1; if (o0[1067]) nss = nss + 1; if (o0[726]) nl = nl + 1;
        end
        rst_n <= (cyc >= 4) && !(cyc % 50000 == 25000);       // one mid-run reset
        rs_i <= {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
        rn_i <= {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
        hct5_v <= $urandom; hct5_b <= {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
        sid_i <= $urandom; f5 <= ($urandom % 20000 == 0);
        // group stream: bursts of 16 groups (index 0..15) one a cycle, accumulator 0..24 per burst, plus random noise
        ph = (ph + 1) % 40;
        if (ph < 16) begin g_v <= 1; g_i <= ph; if (ph == 0) gi = $urandom % 25; g_acc <= gi; end
        else begin g_v <= ($urandom % 8 == 0); g_i <= $urandom; g_acc <= $urandom; end
        for (x = 0; x < 10; x = x + 1) g_d[32 * x +: 32] <= fp(x);
        j_v <= $urandom % 4 != 0; j_set <= $urandom; j_w <= $urandom; j_row <= $urandom; j_lm <= $urandom; j_sm <= $urandom;
        cw_v <= $urandom % 3 == 0; cw_a <= ($urandom % 4 == 0) ? {2'($urandom), 6'd62} : 8'($urandom); cw_d <= {8{$urandom}};
        r_v <= $urandom % 30 == 0; r_y <= fp(0); r_f <= ($urandom % 50000 == 0);
        if (cyc == ncyc) begin
            if (errs == 0 && nmx > 100) $display("L4_RF PASS cycles=%0d mx_v=%0d ss_v=%0d launch=%0d (all 1132 output bits, 0 edges)", ncyc, nmx, nss, nl);
            else $display("L4_RF FAIL %0d (mx_v %0d ss_v %0d launch %0d)", errs, nmx, nss, nl);
            $finish;
        end
    end
endmodule
