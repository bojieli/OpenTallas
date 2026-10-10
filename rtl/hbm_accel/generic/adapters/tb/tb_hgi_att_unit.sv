`timescale 1ns/1ps
// hgi-adapters (2026-10-09): D4 bench of the ATT unit die body ot_hgi_att_unit: hbm-sim CF-ATT conformance vectors
// (Ref's dispatch of every ATT.QK / ATT.PV, die 0's VM / HBM images, the expected VM out) + synthetic Qwen-shape
// records past one engine job, on the REAL HGI VM (ot_hgi_vm_unit NC 2) and an HBM model answering sector reads in
// random order with stalls.  Prints HGI_ATT_UNIT PASS / FAIL.
module tb_hgi_att_unit;
    `include "au_sizes.svh"
    reg clk = 0; always #1 clk = ~clk;
    reg [255:0] casem [0:NCASE-1]; reg [1215:0] recm [0:NREC-1]; reg [63:0] vmim [0:NVMI-1];
    reg [295:0] hbmm [0:NHBM-1]; reg [63:0] expm [0:NEXP-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/au_case.mem"}, casem); $readmemh({dir, "/au_rec.mem"}, recm);
        $readmemh({dir, "/au_vmi.mem"}, vmim); $readmemh({dir, "/au_hbm.mem"}, hbmm); $readmemh({dir, "/au_exp.mem"}, expm);
    end
    integer errors = 0, cyc = 0, seed = 7; always @(posedge clk) cyc <= cyc + 1;
`ifdef MUT_RING
    localparam integer MR = 1;
`else
    localparam integer MR = 0;
`endif
    reg rst_n = 0; reg [1215:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted; wire [337:0] uq; wire [273:0] ur, tr; reg [337:0] tq = 0;
    wire hq_v; reg hq_rdy = 0; wire [34:0] hq_addr; wire [7:0] hq_tag;
    reg hr_v = 0; reg [7:0] hr_tag = 0; reg [255:0] hr_data = 0;
    ot_hgi_att_unit #(.H(4), .MUT_RING(MR)) u (.clk(clk), .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_c(cur[895:640]), .rec_o(cur[1151:896]),
        .rec_n_b(cur[1172:1152]), .rec_n_c(cur[1193:1173]), .rec_pos1(cur[1214:1194]), .rec_done(done),
        .rec_fault(fault), .halted(halted), .vmq(uq), .vmr(ur), .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr),
        .hq_tag(hq_tag), .hr_v(hr_v), .hr_tag(hr_tag), .hr_data(hr_data));
    ot_hgi_vm_unit #(.NC(2)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, uq}), .cr({tr, ur}), .status());
    reg [255:0] hbm [longint];
    reg [42:0] rq [$]; reg [42:0] cq; integer pk, lat = 0;
    always @(posedge clk) begin
        hq_rdy <= ($random(seed) & 3) != 0;
        if (rst_n && hq_v && hq_rdy) rq.push_back({hq_tag, hq_addr});
        hr_v <= 1'b0;
        if (lat > 0) lat = lat - 1;
        else if (rq.size() > 0 && ($random(seed) & 3) != 0) begin
            pk = $unsigned($random(seed)) % rq.size(); cq = rq[pk]; rq.delete(pk);
            hr_v <= 1'b1; hr_tag <= cq[42:35]; hr_data <= hbm.exists(cq[34:0]) ? hbm[cq[34:0]] : 256'd0;
            lat = $unsigned($random(seed)) % 3;
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
    integer c, j, t, r0, nr, v0, nv, h0, nh, e0, ne, t0, words = 0, cerr, c_lo = 0, c_hi = NCASE, c_st = 1; reg [31:0] qd;
    initial begin
        if ($value$plusargs("FIRST=%d", c_lo)) ; if ($value$plusargs("LAST=%d", c_hi)) ; if ($value$plusargs("STEP=%d", c_st)) ;
        repeat (3) @(posedge clk);
        for (c = c_lo; c < c_hi && c < NCASE; c = c + c_st) begin
            r0 = casem[c][255:224]; nr = casem[c][223:192]; v0 = casem[c][191:160]; nv = casem[c][159:128];
            h0 = casem[c][127:96]; nh = casem[c][95:64]; e0 = casem[c][63:32]; ne = casem[c][31:0];
            rst_n = 0; hbm.delete(); rq.delete(); repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
            for (j = 0; j < nh; j = j + 1) hbm[hbmm[h0 + j][295:256]] = hbmm[h0 + j][255:0];
            for (j = 0; j < nv; j = j + 1) vm_req(1'b1, vmim[v0 + j][63:32], vmim[v0 + j][31:0], qd);
            nd = 0; nf = 0; t0 = cyc;
            for (j = 0; j < nr; j = j + 1) begin
                @(negedge clk); cur = recm[r0 + j]; rec_v = 1;
                t = 0; while (!rec_rdy && t < 4000000) begin @(negedge clk); t = t + 1; end
                @(posedge clk); #0.1 rec_v = 0;
                t = 0; while (nd <= j && nf == 0 && t < 4000000) begin @(posedge clk); t = t + 1; end
            end
            if (nd != nr || nf != 0) begin $display("ERR case %0d: done %0d of %0d, faults %0d (state %0d)", c, nd, nr, nf, u.st); errors = errors + 1; end
            cerr = 0;
            for (j = 0; j < ne; j = j + 1) begin
                vm_req(1'b0, expm[e0 + j][63:32], 0, qd);
                if (qd !== expm[e0 + j][31:0]) begin
                    if (cerr < 6) $display("ERR case %0d VM[%0d] = %h expected %h", c, expm[e0 + j][63:32], qd, expm[e0 + j][31:0]);
                    cerr = cerr + 1; end
            end
            errors = errors + cerr; words = words + ne;
            $display("case %0d: %0d records in %0d cycles, %0d words, %0d wrong", c, nr, cyc - t0, ne, cerr); $fflush;
        end
        $display("summary: ATT cases %0d..%0d step %0d, %0d VM words checked", c_lo, c_hi, c_st, words);
        if (errors == 0) $display("HGI_ATT_UNIT PASS"); else $display("HGI_ATT_UNIT FAIL errors=%0d", errors);
        $finish;
    end
endmodule
