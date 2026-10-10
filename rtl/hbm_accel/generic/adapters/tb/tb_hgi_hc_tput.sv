`timescale 1ns/1ps
// HC unit THROUGHPUT bench (hgi-1010/g): ot_hgi_hc_unit (record adapter + x staging from the REAL HGI VM + the r25
// HCP on 8 HBM weight windows + post + r25 Sinkhorn + drain) running the DS-V4.1 1M G22 records BACK TO BACK
// (HC_MIX_ROWS / HC_MIX_POST interleaved, then one legacy HC_MIX).  Every record's VM operands and the HBM weight set
// are preloaded (untimed); then each record is presented the cycle the previous one was taken (the CP's unit queue
// holds it).  HBM model at the client's full rate: every request accepted, a burst's beats start FA cycles after its
// request (FA = the measured first access, default 160) and return one beat a cycle in request order.
// Prints per record: TPUT k op <op> issue <cycle> ret <cycle> cost_milli <price x1000>, then reads every O back
// through the bench's VM client and compares it with the golden (Model.hc_mixes, chunk8), with guard words.
// Vectors: tools/hgi_unit_tput/hc_vectors.py.  Mutant: +define+MUT_POST (pre without + hc_eps) must FAIL.
module tb_hgi_hc_tput;
    `include "hu_sizes.svh"
    reg clk = 0; always #1 clk = ~clk;
    reg [1163:0] casem [0:NCASE-1]; reg [63:0] vmim [0:NVMI-1]; reg [295:0] hbmm [0:NHBM-1]; reg [63:0] expm [0:NEXP-1];
    reg [31:0] costm [0:NCASE-1];
    reg [8*256-1:0] dir; integer FA;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if (!$value$plusargs("FA=%d", FA)) FA = 160;
        $readmemh({dir, "/hu_case.mem"}, casem); $readmemh({dir, "/hu_vmi.mem"}, vmim);
        $readmemh({dir, "/hu_hbm.mem"}, hbmm); $readmemh({dir, "/hu_exp.mem"}, expm); $readmemh({dir, "/hu_cost.mem"}, costm);
    end
    integer errors = 0, cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [937:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted; wire [337:0] uq; wire [273:0] ur, tr; reg [337:0] tq = 0;
    wire hq_v; wire hq_rdy = 1'b1; wire [34:0] hq_addr; wire [2:0] hq_len; wire [10:0] hq_tag;
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
    // HBM model: in-order bursts, beats from FA cycles after the request, one beat a cycle
    reg [255:0] hbm [longint];
    reg [49:0] rq [$]; integer rt [$]; reg [49:0] curq; integer bl = 0, bi = 0;
    longint hbeats = 0;
    always @(posedge clk) begin
        if (rst_n && hq_v && hq_rdy) begin rq.push_back({hq_tag, hq_len, 1'b0, hq_addr}); rt.push_back(cyc + FA); end
        hr_v <= 1'b0;
        if (bl == 0 && rq.size() > 0 && rt[0] <= cyc) begin curq = rq.pop_front(); void'(rt.pop_front()); bl = curq[38:36]; bi = 0; end
        if (bl > 0) begin
            hr_v <= 1'b1; hr_tag <= curq[49:39]; hr_beat <= bi[1:0];
            hr_data <= hbm.exists(curq[34:0] + bi) ? hbm[curq[34:0] + bi] : 256'd0;
            bi = bi + 1; bl = bl - 1; hbeats = hbeats + 1;
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
    integer nd = 0, nf = 0;
    integer c, j, t, e0, ne, t0, words = 0, bk; reg [31:0] qd;
    integer issue [0:NCASE-1]; integer retc [0:NCASE-1];
    initial for (int q = 0; q < NCASE; q++) retc[q] = -1;
    // retire stamps: the k-th done pulse belongs to the k-th record (in-order unit)
    always @(posedge clk) begin
        if (rst_n && done) begin nd = nd + 1; if (t0 >= 0 && nd <= NCASE) retc[nd - 1] = cyc - t0; end
        if (rst_n && fault) nf = nf + 1;
    end
    initial begin
        t0 = -1;
        repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
        for (j = 0; j < NHBM; j = j + 1) hbm[hbmm[j][295:256]] = hbmm[j][255:0];
        for (j = 0; j < NVMI; j = j + 1) vm_req(1'b1, vmim[j][63:32], vmim[j][31:0], qd);
        for (c = 0; c < NCASE; c = c + 1) begin            // guard words around every O
            e0 = casem[c][1003:972]; ne = casem[c][971:940];
            vm_req(1'b1, expm[e0][63:32] - 1, 32'hA5A5A5A5, qd); vm_req(1'b1, expm[e0][63:32] + ne, 32'hA5A5A5A5, qd);
        end
        repeat (4) @(negedge clk);
        nd = 0; nf = 0; t0 = cyc;
        for (c = 0; c < NCASE; c = c + 1) begin
            @(negedge clk); cur = casem[c][937:0]; rec_v = 1; issue[c] = cyc - t0;
            while (!rec_rdy) @(negedge clk);
            @(posedge clk); #0.1 rec_v = 0;
        end
        t = 0; while (nd < NCASE && nf == 0 && t < 5000000) begin @(posedge clk); t = t + 1; end
        if (nd != NCASE || nf != 0) begin $display("ERR done %0d of %0d, fault %0d (state %0d)", nd, NCASE, nf, u.st); errors = errors + 1; end
        for (c = 0; c < NCASE; c = c + 1)
            $display("TPUT %0d op %0d issue %0d ret %0d cost_milli %0d", c, u_op(c), issue[c], retc[c], costm[c]);
        $display("HBM beats %0d (%0d B) over %0d cycles", hbeats, hbeats * 32, retc[NCASE-1]);
        for (c = 0; c < NCASE; c = c + 1) begin
            e0 = casem[c][1003:972]; ne = casem[c][971:940]; bk = errors;
            for (j = 0; j < ne; j = j + 1) begin
                vm_req(1'b0, expm[e0 + j][63:32], 0, qd);
                if (qd !== expm[e0 + j][31:0]) begin
                    if (errors < 40) $display("ERR rec %0d O[%0d] = %h expected %h", c, j, qd, expm[e0 + j][31:0]);
                    errors = errors + 1; end
            end
            vm_req(1'b0, expm[e0][63:32] - 1, 0, qd); if (qd !== 32'hA5A5A5A5) begin $display("ERR guard lo %0d", c); errors = errors + 1; end
            vm_req(1'b0, expm[e0][63:32] + ne, 0, qd); if (qd !== 32'hA5A5A5A5) begin $display("ERR guard hi %0d", c); errors = errors + 1; end
            $display("EXACT %0d mismatch %0d", c, errors - bk);
            words = words + ne;
        end
        $display("summary: %0d HC records back to back, %0d O words, %0d cycles", NCASE, words, retc[NCASE-1]);
        if (errors == 0) $display("HGI_HC_TPUT PASS"); else $display("HGI_HC_TPUT FAIL errors=%0d", errors);
        $finish;
    end
    function integer u_op(input integer k); u_op = casem[k][123:118]; endfunction
endmodule
