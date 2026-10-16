`timescale 1ns/1ps
// hgi-adapters (2026-10-09): D1 bench of the HC unit die body ot_hgi_hc_unit: HC.HC_MIX records (adapter + x staging
// from the REAL HGI VM + the r25 HCP on 8 HBM weight windows + the post units + the r25 Sinkhorn + drain to VM) on an
// HBM model that reorders bursts and stalls.  Vectors: tools/hgi_adapters/hc_unit_bench.py (Model.hc_mixes, chunk8).
// Prints HGI_HC_UNIT PASS / FAIL.
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
    integer errors = 0, cyc = 0, seed = 5; always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [937:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted; wire [337:0] uq; wire [273:0] ur, tr; reg [337:0] tq = 0;
    wire hq_v; reg hq_rdy = 0; wire [34:0] hq_addr; wire [2:0] hq_len; wire [10:0] hq_tag;
    reg hr_v = 0; reg [10:0] hr_tag = 0; reg [1:0] hr_beat = 0; reg [255:0] hr_data = 0;
`ifdef MUT_POST
    localparam integer MP = 1;
`else
    localparam integer MP = 0;
`endif
    ot_hgi_hc_unit #(.MUT_POST(MP)) u (.clk(clk), .rst_n(rst_n), .cfg_norm_eps(NEPS), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_o(cur[895:640]),
        .rec_n_a(cur[916:896]), .rec_n_o(cur[937:917]), .rec_done(done), .rec_fault(fault), .halted(halted),
        .vmq(uq), .vmr(ur), .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag),
        .hr_v(hr_v), .hr_tag(hr_tag), .hr_beat(hr_beat), .hr_data(hr_data));
    ot_hgi_vm_unit #(.NC(2)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, uq}), .cr({tr, ur}), .status());
    // HBM model: bursts served in random order, one beat a cycle, random gaps
    reg [255:0] hbm [longint];
    reg [49:0] rq [$]; reg [49:0] curq; integer bl = 0, bi = 0, pk;
    always @(posedge clk) begin
        hq_rdy <= ($random(seed) & 3) != 0;
        if (rst_n && hq_v && hq_rdy) rq.push_back({hq_tag, hq_len, 1'b0, hq_addr});
        hr_v <= 1'b0;
        if (bl == 0 && rq.size() > 0 && ($random(seed) & 1)) begin
            pk = $unsigned($random(seed)) % rq.size(); curq = rq[pk]; rq.delete(pk); bl = curq[38:36]; bi = 0;
        end
        if (bl > 0 && ($random(seed) & 7) != 0) begin
            hr_v <= 1'b1; hr_tag <= curq[49:39]; hr_beat <= bi[1:0];
            hr_data <= hbm.exists(curq[34:0] + bi) ? hbm[curq[34:0] + bi] : 256'd0;
            bi = bi + 1; bl = bl - 1;
        end
    end
    task automatic vm_req(input we, input [31:0] word, input [31:0] data, output [31:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            qd = tr[32 * word[2:0] +: 32];
        end
    endtask
    integer nd, nf;
    always @(posedge clk) begin if (rst_n && done) nd = nd + 1; if (rst_n && fault) nf = nf + 1; end
    integer c, j, t, v0, nv, h0, nh, e0, ne, t0, words = 0; reg [31:0] qd;
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            v0 = casem[c][1131:1100]; nv = casem[c][1099:1068]; h0 = casem[c][1067:1036]; nh = casem[c][1035:1004];
            e0 = casem[c][1003:972]; ne = casem[c][971:940];
            rst_n = 0; hbm.delete(); rq.delete(); repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
            for (j = 0; j < nh; j = j + 1) hbm[hbmm[h0 + j][295:256]] = hbmm[h0 + j][255:0];
            for (j = 0; j < nv; j = j + 1) vm_req(1'b1, vmim[v0 + j][63:32], vmim[v0 + j][31:0], qd);
            // guard words around O
            vm_req(1'b1, expm[e0][63:32] - 1, 32'hA5A5A5A5, qd); vm_req(1'b1, expm[e0][63:32] + ne, 32'hA5A5A5A5, qd);
            nd = 0; nf = 0; t0 = cyc;
            @(negedge clk); cur = casem[c][937:0]; rec_v = 1;
            while (!rec_rdy) @(negedge clk);
            @(posedge clk); #0.1 rec_v = 0;
            t = 0; while (nd == 0 && nf == 0 && t < 3000000) begin @(posedge clk); t = t + 1; end
            if (nd != 1 || nf != 0) begin $display("ERR case %0d: done %0d fault %0d (state %0d)", c, nd, nf, u.st); errors = errors + 1; end
            $display("case %0d: op %0d, K %0d, %0d O words, record -> retire %0d cycles", c, cur[123:118], casem[c][1163:1132], ne, cyc - t0); $fflush;
            for (j = 0; j < ne; j = j + 1) begin
                vm_req(1'b0, expm[e0 + j][63:32], 0, qd);
                if (qd !== expm[e0 + j][31:0]) begin
                    if (errors < 40) $display("ERR case %0d O[%0d] = %h expected %h", c, j, qd, expm[e0 + j][31:0]);
                    errors = errors + 1; end
            end
            vm_req(1'b0, expm[e0][63:32] - 1, 0, qd); if (qd !== 32'hA5A5A5A5) begin $display("ERR guard lo"); errors = errors + 1; end
            vm_req(1'b0, expm[e0][63:32] + ne, 0, qd); if (qd !== 32'hA5A5A5A5) begin $display("ERR guard hi"); errors = errors + 1; end
            words = words + ne;
        end
        $display("summary: %0d HC records (G22 ops 0 / 1 / 2), %0d O words exact", NCASE, words);
        if (errors == 0) $display("HGI_HC_UNIT PASS"); else $display("HGI_HC_UNIT FAIL errors=%0d", errors);
        $finish;
    end
endmodule
