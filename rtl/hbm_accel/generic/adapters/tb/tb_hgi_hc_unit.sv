`timescale 1ns/1ps
// hgi-adapters (2026-10-09): D1 bench of the HC unit die body ot_hgi_hc_unit: HC.HC_MIX records (adapter + x staging
// from the REAL HGI VM + the r25 HCP on 8 HBM weight windows + the post units + the r25 Sinkhorn + drain to VM) on an
// HBM model that reorders bursts and stalls.  Vectors: tools/hgi_adapters/hc_unit_bench.py (Model.hc_mixes, chunk8).
// Prints HGI_HC_UNIT PASS / FAIL.
`ifdef VIA_LANE
`define HCST u.u_hc.st
`else
`define HCST u.st
`endif
module tb_hgi_hc_unit;
    `include "hu_sizes.svh"
    reg clk = 0; always #1 clk = ~clk;
    reg [1163:0] casem [0:NCASE-1]; reg [63:0] vmim [0:NVMI-1]; reg [295:0] hbmm [0:NHBM-1]; reg [63:0] expm [0:NEXP-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/hu_case.mem"}, casem); $readmemh({dir, "/hu_vmi.mem"}, vmim);
        $readmemh({dir, "/hu_hbm.mem"}, hbmm); $readmemh({dir, "/hu_exp.mem"}, expm);
    end
    integer c0;
    integer errors = 0, cyc = 0, seed = 5; always @(posedge clk) cyc <= cyc + 1;
    initial begin if (!$value$plusargs("SEED=%d", seed)) seed = 5; $display("SEED=%0d", seed); end  // runtime seed (+SEED=<n> overrides): Verilator 5.050 drops a declaration initialiser read only by $random (tools/seed_init_lint.py)
    reg rst_n = 0; reg [937:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted; wire [337:0] uq; wire [273:0] ur, tr; reg [337:0] tq = 0;
    reg [255:0] hbm [longint];
`ifdef SPL
    localparam integer SPLN = `SPL, HLN = 8 * `SPL;   // hgi-1010/d: striped fetch, SPL sub-windows a bank, one lane each
`elsif HL8
    localparam integer SPLN = 1, HLN = 8;     // hgi-1010/d: the striped weight fetch, 8 HBM lanes (window g on lane g)
`else
    localparam integer SPLN = 1, HLN = 1;
`endif
`ifdef HCW
    localparam integer TGB = 4 + 7 + ((`HCW > 32) ? $clog2(`HCW / 32) : 0);   // the unit's HBM tag width (RMAX 128)
`else
    localparam integer TGB = 11;
`endif
    wire [HLN-1:0] hq_v; reg [HLN-1:0] hq_rdy = 0; wire [HLN*35-1:0] hq_addr; wire [HLN*3-1:0] hq_len; wire [HLN*TGB-1:0] hq_tag;
    reg [HLN-1:0] hr_v = 0; reg [HLN*TGB-1:0] hr_tag = 0; reg [HLN*2-1:0] hr_beat = 0; reg [HLN*256-1:0] hr_data = 0;
`ifdef MUT_MP
    localparam integer MM = 1;
`else
    localparam integer MM = 0;
`endif
`ifdef MUT_POST
    localparam integer MP = 1;
`else
    localparam integer MP = 0;
`endif
`ifdef VIA_LANE
    // hgi-1010/d: the die form -- ot_hgi_hc_die (unit + HBM lane client) -> 2 pin stages -> ot_hgi_hbm_rd_server (the
    // loader end) -> one kport-lane model (random ready, random latency, one transaction) -> 2 pin stages back
    wire [37:0] xq; wire [256:0] xr; reg [37:0] xq1, xq2; reg [256:0] xr1, xr2;
    wire k_v; reg k_rdy = 0; wire [36:0] k_a; reg k_rv = 0; reg [255:0] k_rd = 0; wire lane_f;
    always @(posedge clk) begin xq1 <= xq; xq2 <= xq1; end
    ot_hgi_hc_die #(.HC_EPS(NEPS), .MUT_MP(MM), .WVM(0), .SPL(1), .HL(1)) u (.clk(clk), .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_o(cur[895:640]),
        .rec_n_a(cur[916:896]), .rec_n_o(cur[937:917]), .rec_done(done), .rec_fault(fault), .halted(halted),
        .vmq(uq), .vmr(ur), .xq(xq), .xr(xr2));
    wire [256:0] xr_s;
    ot_hgi_hbm_rd_server u_srv (.clk(clk), .rst_n(rst_n), .xq(xq2), .xr(xr_s), .req_v(k_v), .req_rdy(k_rdy), .req_addr(k_a),
        .rsp_v(k_rv), .rsp_data(k_rd), .fault(lane_f));
    always @(posedge clk) begin xr1 <= xr_s; xr2 <= xr1; end
    reg [36:0] k_pa; integer k_lat = -1;
    always @(posedge clk) begin
        k_rdy <= ($random(seed) & 1); k_rv <= 1'b0;
        if (rst_n && k_v && k_rdy) begin k_pa <= k_a; k_lat = 3 + ($unsigned($random(seed)) % 20); end
        else if (k_lat > 0) k_lat = k_lat - 1;
        else if (k_lat == 0) begin
            k_rv <= 1'b1; k_lat = -1;
`ifdef MUT_LANE
            k_rd <= hbm.exists(k_pa[36:5] + 1) ? hbm[k_pa[36:5] + 1] : 256'd0;   // mutant: the next sector
`else
            k_rd <= hbm.exists(k_pa[36:5]) ? hbm[k_pa[36:5]] : 256'd0;
`endif
        end
        if (lane_f) begin $display("ERR lane fault"); errors = errors + 1; end
    end
`else
`ifdef WVM
    // hgi-1010/d: x staging over the W-group wide VM read lanes: HC = client 2 of a K = 3 ot_hgi_vm_lanearb (clients 0 / 1
    // idle) with RLY die relays each way -> ot_hgi_vm_unit RP 32 (lane b <-> bank b, LQ credits)
`ifndef WLQ
`define WLQ 16
`endif
`ifndef WRLY
`define WRLY 3
`endif
`ifdef MUT_WV
    localparam integer MWV = `MUT_WV;
`else
    localparam integer MWV = 0;
`endif
    wire rg_req, rg_gnt_h; wire [32*16-1:0] wrq_h, g_q; wire [31:0] wcr_h, g_cr; wire [32*257-1:0] wrr_h, g_rsp;
    wire [2:0] a_gnt; wire [3*32-1:0] a_cr; wire [3*32*257-1:0] a_rsp;
    ot_hgi_vm_lanearb #(.K(3), .REQW(16), .RSPW(257), .RLY(`WRLY)) u_arb (.clk(clk), .rst_n(rst_n), .c_req({rg_req, 2'b00}),
        .c_gnt(a_gnt), .c_q({wrq_h, {2*32*16{1'b0}}}), .c_cr(a_cr), .c_rsp(a_rsp), .g_q(g_q), .g_cr(g_cr), .g_rsp(g_rsp));
    assign rg_gnt_h = a_gnt[2]; assign wcr_h = a_cr[2*32 +: 32]; assign wrr_h = a_rsp[2*32*257 +: 32*257];
    ot_hgi_hc_unit #(.MUT_POST(MP), .MUT_MP(MM), .WVM(1), .WLQ(`WLQ), .MUT_WV(MWV), .HL(HLN), .SPL(SPLN)
`ifdef APW
        , .HSRC(1)
`endif
`ifdef MUT_AP
        , .MUT_AP(1)
`endif
`ifdef HCW
        , .W(`HCW)
`endif
`ifdef MUT_HL
        , .MUT_HL(1)
`endif
`ifdef XMAC
        , .XMACRO(1)
`endif
`ifdef WMAC
        , .WMACRO(1)
`endif
        ) u (.clk(clk), .rst_n(rst_n), .cfg_norm_eps(NEPS), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_o(cur[895:640]),
        .rec_n_a(cur[916:896]), .rec_n_o(cur[937:917]), .rec_done(done), .rec_fault(fault), .halted(halted),
        .vmq(uq), .vmr(ur), .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag),
        .hr_v(hr_v), .hr_tag(hr_tag), .hr_beat(hr_beat), .hr_data(hr_data),
        .rg_req(rg_req), .rg_gnt(rg_gnt_h), .wrq(wrq_h), .wrq_cr(wcr_h), .wrr(wrr_h)
`ifdef APW
        , .ap_q(apq), .ap_cr(apcr), .ap_done()
`endif
        );
    ot_hgi_vm_unit #(.NC(2), .RP(32), .LQ(`WLQ)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, uq}), .cr({tr, ur}), .status(),
        .rq(g_q), .rq_cr(g_cr), .rr(g_rsp));
    integer wv_n = 0; always @(posedge clk) if (u.xv_l != 0) wv_n = wv_n + 1;   // waves landed
    final $display("WVM waves %0d", wv_n);
`else
    ot_hgi_hc_unit #(.MUT_POST(MP), .MUT_MP(MM), .HL(HLN), .SPL(SPLN)
`ifdef HCW
        , .W(`HCW)
`endif
`ifdef MUT_HL
        , .MUT_HL(1)
`endif
        ) u (.clk(clk), .rst_n(rst_n), .cfg_norm_eps(NEPS), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_o(cur[895:640]),
        .rec_n_a(cur[916:896]), .rec_n_o(cur[937:917]), .rec_done(done), .rec_fault(fault), .halted(halted),
        .vmq(uq), .vmr(ur), .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag),
        .hr_v(hr_v), .hr_tag(hr_tag), .hr_beat(hr_beat), .hr_data(hr_data));
`endif
`endif
`ifndef WVM
    ot_hgi_vm_unit #(.NC(2)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, uq}), .cr({tr, ur}), .status());
`endif
`ifndef VIA_LANE
    // HBM model a lane: bursts served in random order, one beat a cycle, random gaps
    for (genvar hl = 0; hl < HLN; hl = hl + 1) begin : g_hbm
        reg [39+TGB-1:0] rq [$]; reg [39+TGB-1:0] curq; integer bl = 0, bi = 0, pk, sd = 5 + 17 * hl;
        always @(posedge clk) begin
            if (!rst_n) begin rq.delete(); bl = 0; end      // a new case: drop the previous case's queue
            hq_rdy[hl] <= ($random(sd) & 3) != 0;
            if (rst_n && hq_v[hl] && hq_rdy[hl]) rq.push_back({hq_tag[hl*TGB +: TGB], hq_len[hl*3 +: 3], 1'b0, hq_addr[hl*35 +: 35]});
            hr_v[hl] <= 1'b0;
            if (bl == 0 && rq.size() > 0 && ($random(sd) & 1)) begin
                pk = $unsigned($random(sd)) % rq.size(); curq = rq[pk]; rq.delete(pk); bl = curq[38:36]; bi = 0;
            end
            if (bl > 0 && ($random(sd) & 7) != 0) begin
                hr_v[hl] <= 1'b1; hr_tag[hl*TGB +: TGB] <= curq[39 +: TGB]; hr_beat[hl*2 +: 2] <= bi[1:0];
                hr_data[hl*256 +: 256] <= hbm.exists(curq[34:0] + bi) ? hbm[curq[34:0] + bi] : 256'd0;
                bi = bi + 1; bl = bl - 1;
            end
        end
    end
`endif
    task automatic vm_req(input we, input [31:0] word, input [31:0] data, output [31:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            qd = tr[32 * word[2:0] +: 32];
        end
    endtask
    // ---- hgi-1010/d weight APERTURE driver (APW): an op-1 one-row record reads its row from slot (case % 2), which this
    // bench fills first through the 32 aperture lanes (one sector a lane in flight, credit = ap_cr), from the weight
    // set in hbm[]: slot s sector s 4096 + k 512 + r SPW + q = weight-set sector S0 + 4 + o 8 R SPW + k R SPW + r SPW + q
`ifdef HCW
    localparam integer HCWT = `HCW;
`else
    localparam integer HCWT = 32;
`endif
    integer naps = 0;
    reg [32*278-1:0] apq = '0; wire [31:0] apcr; reg [31:0] ap_busy = 0, ap_set = 0;
    always @(posedge clk) ap_busy <= (ap_busy | ap_set) & ~apcr;    // a lane is busy from its request to its credit
    task automatic ap_fill(input integer slot, input [34:0] s0, input integer o, input integer K);
        integer R, SPWt, nsec, k2, r2, q2, i2, l2; reg [34:0] hs; reg [12:0] as;
        begin
            SPWt = HCWT / 8; R = ((K / 8) + HCWT - 1) / HCWT; i2 = 0;
            for (k2 = 0; k2 < 8; k2 = k2 + 1) for (r2 = 0; r2 < R; r2 = r2 + 1) for (q2 = 0; q2 < SPWt; q2 = q2 + 1) begin
                hs = s0 + 4 + o * 8 * R * SPWt + k2 * R * SPWt + r2 * SPWt + q2;
                as = 13'(slot * 4096 + k2 * 512 + r2 * SPWt + q2);
                l2 = i2 % 32;
                while (ap_busy[l2]) @(negedge clk);
                apq[l2*278 +: 278] = {1'b1, as, hbm.exists(hs) ? hbm[hs] : 256'd0, 8'hFF}; ap_set[l2] = 1'b1;
                @(negedge clk); apq[l2*278 + 277] = 1'b0; ap_set[l2] = 1'b0;
                i2 = i2 + 1;
            end
        end
    endtask
    integer nd, nf;
    always @(posedge clk) begin if (rst_n && done) nd = nd + 1; if (rst_n && fault) nf = nf + 1; end
    integer c, j, t, v0, nv, h0, nh, e0, ne, t0, words = 0; reg [31:0] qd;
    initial begin
        repeat (3) @(posedge clk);
        if (!$value$plusargs("C0=%d", c0)) c0 = 0;
        for (c = c0; c < NCASE; c = c + 1) begin
            v0 = casem[c][1131:1100]; nv = casem[c][1099:1068]; h0 = casem[c][1067:1036]; nh = casem[c][1035:1004];
            e0 = casem[c][1003:972]; ne = casem[c][971:940];
            rst_n = 0; hbm.delete();
            repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
            for (j = 0; j < nh; j = j + 1) hbm[hbmm[h0 + j][295:256]] = hbmm[h0 + j][255:0];
            for (j = 0; j < nv; j = j + 1) vm_req(1'b1, vmim[v0 + j][63:32], vmim[v0 + j][31:0], qd);
            // guard words around O
            vm_req(1'b1, expm[e0][63:32] - 1, 32'hA5A5A5A5, qd); vm_req(1'b1, expm[e0 + ne - 1][63:32] + 1, 32'hA5A5A5A5, qd);
            nd = 0; nf = 0; t0 = cyc;
            cur = casem[c][937:0];
`ifdef APW
            if (cur[123:118] == 6'd1 && cur[937:917] == 21'd1) begin   // op 1, one row: through aperture slot c % 2
                ap_fill(c % 2, cur[431:397], cur[63:32], cur[916:896]);
                cur[385:384] = 2'd1; cur[431:392] = 40'h40000 + 40'(32768 * (c % 2));
                naps = naps + 1;
            end
`endif
            @(negedge clk); rec_v = 1;
            while (!rec_rdy) @(negedge clk);
            @(posedge clk); #0.1 rec_v = 0;
            t = 0; while (nd == 0 && nf == 0 && t < 3000000) begin @(posedge clk); t = t + 1; end
            if (nd != 1 || nf != 0) begin $display("ERR case %0d: done %0d fault %0d (state %0d)", c, nd, nf, `HCST); errors = errors + 1; end
            $display("case %0d: op %0d, K %0d, %0d O words, record -> retire %0d cycles", c, cur[123:118], casem[c][1163:1132], ne, cyc - t0); $fflush;
            for (j = 0; j < ne; j = j + 1) begin
                vm_req(1'b0, expm[e0 + j][63:32], 0, qd);
                if (qd !== expm[e0 + j][31:0]) begin
                    if (errors < 40) $display("ERR case %0d O[%0d] = %h expected %h", c, j, qd, expm[e0 + j][31:0]);
                    errors = errors + 1; end
            end
            vm_req(1'b0, expm[e0][63:32] - 1, 0, qd); if (qd !== 32'hA5A5A5A5) begin $display("ERR guard lo"); errors = errors + 1; end
            vm_req(1'b0, expm[e0 + ne - 1][63:32] + 1, 0, qd); if (qd !== 32'hA5A5A5A5) begin $display("ERR guard hi"); errors = errors + 1; end
            words = words + ne;
        end
        $display("summary: %0d HC records (G22 ops 0 / 1 / 2), %0d O words exact, %0d through the weight aperture", NCASE, words, naps);
        if (errors == 0) $display("HGI_HC_UNIT PASS"); else $display("HGI_HC_UNIT FAIL errors=%0d", errors);
        $finish;
    end
endmodule
