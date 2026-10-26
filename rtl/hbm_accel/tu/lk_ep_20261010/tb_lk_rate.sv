`timescale 1ns/1ps
// tb_lk_rate ([link] 2026-10-10): the FULL link credit loop at rate, both directions.
//   die A: ot_hcoll_port P0 (SWCRED = lk_ep TXQ) -> ph_tx -> hfd_lk_ep core L0 (t_cr -> P0.sw_cr_ret) -> 487-b lane ->
//   L1 -> r_v / r_flit -> ot_hcoll_port P1 ph_rx -> 256-flit SRAM receive buffer -> consumer (pop every edge) ->
//   rx_credit -> L1.r_cr -> carried to L0 (far credits, FCR 256).  B -> A symmetric through the same pair.
// The partial queues are kept fed (push while the local count < 96); every received flit is checked in order and
// bit-exact; any port / link fault fails.  PASS line reports flits / cycle per direction over the steady window.
//   +N=<flits each way>  defines: OT_LKEP_MUT_CREDIT (link credit mutant: must FAIL)
module tb_lk_rate;
    parameter integer TXQ = 32;
    parameter integer FS = 0;       // die-wrapper face stages on the coll side, each way (hfd_coll R25GQ: 5 in + 5 out)
    localparam integer W = 545, LW = 487;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0;
    integer N, cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    function [W-1:0] pay(input integer dir, input integer n);
        integer j; begin for (j = 0; j < W; j = j + 1) pay[j] = ((j * 11 + n * 5 + dir * 3) ^ (n >> (j % 7))) & 1;
            pay[31:0] = n; pay[33:32] = dir; end
    endfunction
    // ---- ports
    reg  [1:0]    qp_push; reg [W-1:0] qp_din [0:1];
    wire [1:0]    ptx_v, prb_v, pstall, pfault, lcr, lrv, lflt, llk;
    wire [W-1:0]  ptx_f [0:1], prb_d [0:1], lrf [0:1];
    reg  [1:0]    prb_cr, lrcr;
    wire [LW-1:0] lx [0:1];
    reg  [LW-1:0] lane [0:1];
    genvar g;
    generate for (g = 0; g < 2; g = g + 1) begin : g_d
        // face stages: coll -> link {tx_v, tx_flit, rx_credit}, link -> coll {rx_v, rx_flit, sw_cr} each delayed FS edges
        reg [W+1:0] dn [0:FS]; reg [W+1:0] up [0:FS];
        wire [W+1:0] dn_in = {ptx_v[g], ptx_f[g], lrcr[g]};
        wire [W+1:0] up_in = {lrv[g], lrf[g], lcr[g]};
        always @* begin dn[0] = dn_in; up[0] = up_in; end
        for (genvar z = 1; z <= FS; z = z + 1) begin : g_fs
            always @(posedge clk or negedge rst_n) if (!rst_n) begin dn[z] <= '0; up[z] <= '0; end else begin dn[z] <= dn[z-1]; up[z] <= up[z-1]; end
        end
        wire [W+1:0] dn_o = dn[FS], up_o = up[FS];
        ot_hcoll_port #(.SWCRED(TXQ)) P (.clk(clk), .rst_n(rst_n), .qp_push(qp_push[g]), .qp_din(qp_din[g]), .qr_push(1'b0),
            .qr_din({W{1'b0}}), .sw_cr_ret(up_o[0]), .ph_tx_v(ptx_v[g]), .ph_tx_flit(ptx_f[g]), .ph_rx_v(up_o[W+1]), .ph_rx_flit(up_o[W:1]),
            .rb_v(prb_v[g]), .rb_d(prb_d[g]), .rb_cr(prb_cr[g]), .stall(pstall[g]), .fault(pfault[g]));
        ot_hbm_lk_ep #(.NS(3), .TXQ(TXQ), .FCR(256), .LW(LW)) L (.clk(clk), .rst_n(rst_n), .session(24'hC0FFEE),
            .t_v(dn_o[W+1]), .t_flit(dn_o[W:1]), .t_cr(lcr[g]), .r_v(lrv[g]), .r_flit(lrf[g]), .r_cr(dn_o[0]),
            .x_tx(lx[g]), .x_rx(lane[1-g]), .fault(lflt[g]), .locked(llk[g]));
    end endgenerate
    always @(posedge clk) begin lane[0] <= lx[0]; lane[1] <= lx[1]; end
    // ---- feeders (partial queue kept fed)
    integer sent [0:1], txd [0:1];
    integer d;
    always @(posedge clk) if (rst_n) for (d = 0; d < 2; d = d + 1) begin
        if (qp_push[d]) sent[d] <= sent[d] + 1;
        if (ptx_v[d]) txd[d] <= txd[d] + 1;
    end
    always @(negedge clk) for (integer e = 0; e < 2; e = e + 1) begin
        qp_push[e] = rst_n && cyc > 10 && sent[e] < N && (sent[e] - txd[e]) < 96;
        qp_din[e] = pay(e, sent[e]);
    end
    // ---- consumers (die B receives A's flits on P1, die A receives B's on P0)
    integer seen [0:1], t0 [0:1], t1 [0:1];
    always @(posedge clk) if (rst_n) begin
        for (integer e = 0; e < 2; e = e + 1) begin
            prb_cr[e] <= prb_v[e]; lrcr[e] <= prb_v[e];
            if (prb_v[e]) begin
                if (prb_d[e] !== pay(1 - e, seen[e])) $fatal(1, "dir %0d flit %0d mismatch (got %0d)", 1 - e, seen[e], prb_d[e][31:0]);
                if (seen[e] == N / 4) t0[e] <= cyc;
                if (seen[e] == N - 1) t1[e] <= cyc;
                seen[e] <= seen[e] + 1;
            end
        end
        if (|pfault || |lflt) $fatal(1, "fault: port %b link %b", pfault, lflt);
    end
    integer k;
    real r0, r1;
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 6000;
        sent[0] = 0; sent[1] = 0; txd[0] = 0; txd[1] = 0; seen[0] = 0; seen[1] = 0; qp_push = 0; prb_cr = 0; lrcr = 0;
        lane[0] = 0; lane[1] = 0;
        repeat (5) @(posedge clk); rst_n = 1;
        for (k = 0; k < 20 * N + 20000 && !(seen[0] == N && seen[1] == N); k = k + 1) @(posedge clk);
        if (seen[0] != N || seen[1] != N) $fatal(1, "TIMEOUT seen %0d / %0d of %0d", seen[1], seen[0], N);
        @(posedge clk);
        r0 = (N - 1 - N / 4) * 1.0 / (t1[1] - t0[1]); r1 = (N - 1 - N / 4) * 1.0 / (t1[0] - t0[0]);
        $display("LKRATE PASS FS %0d TXQ %0d N %0d A->B %.3f B->A %.3f flits/cycle (steady window)", FS, TXQ, N, r0, r1);
        if (r0 < 0.70 || r1 < 0.70) $display("LKRATE BELOW 0.70");
        $finish;
    end
endmodule
