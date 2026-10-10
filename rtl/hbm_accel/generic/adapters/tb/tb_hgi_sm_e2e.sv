`timescale 1ns/1ps
// hgi-adapters (2026-10-09): END-TO-END SM.MATVEC: records -> ot_hgi_sm_record (NSM 2, LEGACY 0) -> ot_hgi_sm_xload
// (2 VM clients) -> 2 REAL ot_hbm_accel_smh (ENABLE_INT8 1, PIPE_INT8 1, RMAX 256 as the smh benches; weight lines from a line-memory model with
// in-order responses) -> ot_hgi_sm_pub (2 VM clients) -> the REAL HGI VM (ot_hgi_vm_unit NC 5: client 4 = this bench).
// Vectors tools/hgi_adapters/sm_e2e_bench.py (INT8 and BF16, P 1..8, uneven row splits, an idle SM).  Every published
// O word == the golden.  Prints HGI_SM_E2E PASS / FAIL.
module tb_hgi_sm_e2e;
`ifdef MUT_T
    localparam integer MT = 1;
`else
    localparam integer MT = 0;
`endif
`ifdef MUT_ROW
    localparam integer MW = 1;
`else
    localparam integer MW = 0;
`endif
    `include "e2e_sizes.svh"
    localparam integer NSM = 2, CW = 106;
    reg clk = 0;
    always #1 clk = ~clk;
    reg [937:0] recm [0:NREC-1]; reg [191:0] casem [0:NCASE-1];
    reg [63:0] vmim [0:NVMI-1]; reg [63:0] vmem [0:NVME-1]; reg [1119:0] linem [0:NLINE-1];
    reg [1087:0] lmem [0:LSPAN-1]; reg lhas [0:LSPAN-1];
    reg [8*256-1:0] dir; integer i;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/e2e_rec.mem"}, recm); $readmemh({dir, "/e2e_case.mem"}, casem);
        $readmemh({dir, "/e2e_vmi.mem"}, vmim); $readmemh({dir, "/e2e_vme.mem"}, vmem); $readmemh({dir, "/e2e_lines.mem"}, linem);
        for (i = 0; i < LSPAN; i = i + 1) lhas[i] = 1'b0;
        for (i = 0; i < NLINE; i = i + 1) begin lmem[linem[i][1119:1088] - LBASE] = linem[i][1087:0]; lhas[linem[i][1119:1088] - LBASE] = 1'b1; end
    end
    integer errors = 0, cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [937:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted;
    wire x_v, x_rdy, x_done, x_fault, pub_v, pub_rdy, pub_done, pub_fault;
    wire [39:0] x_base, pub_base; wire [20:0] x_n; wire [3:0] x_p, pub_p; wire [31:0] x_stride, pub_stride;
    wire [1:0] x_space, x_fmt, pub_space; wire [19:0] pub_m; wire [12:0] pub_q;
    wire [NSM*CW-1:0] sm_cmd; wire [NSM*4-1:0] sm_ret;
    ot_hgi_sm_record #(.NSM(NSM), .LEGACY(0)) u_a (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_o(cur[895:640]), .rec_n_a(cur[916:896]),
        .rec_n_b(cur[937:917]), .rec_done(done), .rec_fault(fault), .halted(halted), .x_v(x_v), .x_rdy(x_rdy),
        .x_base(x_base), .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space), .x_fmt(x_fmt), .x_done(x_done),
        .x_fault(x_fault), .pub_v(pub_v), .pub_rdy(pub_rdy), .pub_base(pub_base), .pub_stride(pub_stride),
        .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p), .pub_done(pub_done), .pub_fault(pub_fault),
        .lg_cmd({NSM*CW{1'b0}}), .lg_ret(), .sm_cmd(sm_cmd), .sm_ret(sm_ret));
    wire xw_en; wire [6:0] xw_addr, xw_grp; wire [2047:0] xw_data;
    wire [2*338-1:0] xq, pq; wire [2*274-1:0] xr, pr; wire [273:0] tr; reg [337:0] tq = 0;
    ot_hgi_sm_xload #(.NXC(2), .MUT_T(MT)) u_x (.clk(clk), .rst_n(rst_n), .x_v(x_v), .x_rdy(x_rdy), .x_base(x_base),
        .x_n(x_n), .x_p(x_p), .x_stride(x_stride), .x_space(x_space), .x_fmt(x_fmt), .x_done(x_done), .x_fault(x_fault),
        .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data), .vmq(xq), .vmr(xr));
    wire [NSM-1:0] rv; wire [NSM*12-1:0] rrow; wire [NSM*256-1:0] rdata;
    ot_hgi_sm_pub #(.NSM(NSM), .NPC(2), .MUT_ROW(MW)) u_p (.clk(clk), .rst_n(rst_n), .pub_v(pub_v), .pub_rdy(pub_rdy),
        .pub_base(pub_base), .pub_stride(pub_stride), .pub_space(pub_space), .pub_m(pub_m), .pub_q(pub_q), .pub_p(pub_p),
        .pub_done(pub_done), .pub_fault(pub_fault), .sm_rv(rv), .sm_rrow(rrow), .sm_rdata(rdata), .vmq(pq), .vmr(pr));
    ot_hgi_vm_unit #(.NC(5)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, pq, xq}), .cr({tr, pr, xr}), .status());
    genvar s;
    generate for (s = 0; s < NSM; s = s + 1) begin : g_sm
        wire [CW-1:0] c = sm_cmd[s*CW +: CW];
        wire start_ready, d_ready, req_v, fault_s, arrive, released, busy; wire [31:0] req_addr; wire [9:0] req_tag;
        reg rsp_v = 0; reg [9:0] rsp_tag; reg [1087:0] rsp_data;
        assign sm_ret[s*4 +: 4] = {fault_s, arrive, d_ready, start_ready};
        ot_hbm_accel_smh #(.ENABLE_INT8(1), .PIPE_INT8(1), .RMAX(256)) u_sm (.clk(clk), .rst_n(rst_n), .start(c[0]),
            .start_ready(start_ready), .op_rows(c[9:1]), .op_c(c[29:14]), .op_g(c[37:30]), .op_gs(c[38]),
            .op_fmt(c[40:39]), .op_xb(c[47:41]), .busy(busy), .d_valid(c[48]), .d_ready(d_ready), .d_base(c[80:49]),
            .d_lines(c[104:81]), .req_v(req_v), .req_ready(1'b1), .req_addr(req_addr), .req_tag(req_tag), .rsp_v(rsp_v),
            .rsp_tag(rsp_tag), .rsp_data(rsp_data), .xw_en(xw_en), .xw_addr(xw_addr), .xw_grp(xw_grp), .xw_data(xw_data),
            .rv(rv[s]), .rrow(rrow[s*12 +: 12]), .rdata(rdata[s*256 +: 256]), .fault(fault_s), .arrive(arrive),
            .release_in(c[105]), .released(released));
        // line memory: in-order responses, latency 6
        reg [31:0] qa [0:255]; reg [9:0] qt [0:255]; integer qh = 0, qtl = 0; integer qc [0:255];
        always @(posedge clk) begin
            rsp_v <= 1'b0;
            if (req_v) begin
                qa[qtl % 256] = req_addr; qt[qtl % 256] = req_tag; qc[qtl % 256] = cyc + 6; qtl = qtl + 1;
                if (req_addr < LBASE || req_addr >= LBASE + LSPAN || !lhas[req_addr - LBASE]) begin $display("ERR SM %0d read an unwritten line %0d", s, req_addr); errors = errors + 1; end
            end
            if (qh != qtl && qc[qh % 256] <= cyc) begin
                rsp_v <= 1'b1; rsp_tag <= qt[qh % 256]; rsp_data <= (qa[qh % 256] >= LBASE && qa[qh % 256] < LBASE + LSPAN) ? lmem[qa[qh % 256] - LBASE] : 1088'd0;
                qh = qh + 1;
            end
            if (rst_n && fault_s) begin $display("ERR SM %0d fault", s); errors = errors + 1; end
        end
    end endgenerate
    task automatic vm_req(input we, input [31:0] word, input [31:0] data, output [31:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            qd = tr[32 * word[2:0] +: 32];
        end
    endtask
    integer c, j, t, r0, nr, vi0, nvi, ve0, nve, k, nf, words = 0, t0;
    reg [31:0] qd;
    always @(posedge clk) begin if (rst_n && done) k = k + 1; if (rst_n && fault) nf = nf + 1; end
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            {r0, nr, vi0, nvi, ve0, nve} = casem[c];
            rst_n = 0; repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk);
            for (j = 0; j < nvi; j = j + 1) vm_req(1'b1, vmim[vi0 + j][63:32], vmim[vi0 + j][31:0], qd);
            $display("case %0d: %0d x words loaded at cycle %0d", c, nvi, cyc); $fflush;
            k = 0; nf = 0;
            @(negedge clk); cur = recm[r0]; rec_v = 1;
            t = 0; while (!rec_rdy && t < 1000) begin @(negedge clk); t = t + 1; end
            @(posedge clk); t0 = cyc; #0.1 rec_v = 0;
            t = 0; while (k < nr && nf == 0 && t < 400000) begin @(posedge clk); t = t + 1; end
            if (k != nr || nf != 0) begin $display("ERR case %0d: retired %0d faults %0d (x_fault %0d pub_fault %0d)", c, k, nf, x_fault, pub_fault); errors = errors + 1; end
            $display("case %0d: record -> retire %0d cycles", c, cyc - t0); $fflush;
            for (j = 0; j < nve; j = j + 1) begin
                vm_req(1'b0, vmem[ve0 + j][63:32], 0, qd);
                if (qd !== vmem[ve0 + j][31:0]) begin
                    if (errors < 30) $display("ERR case %0d O[%0d] = %h expected %h", c, vmem[ve0 + j][63:32], qd, vmem[ve0 + j][31:0]);
                    errors = errors + 1; end
            end
            words = words + nve;
        end
        $display("summary: %0d SM.MATVEC records end to end, %0d result words checked", NCASE, words);
        if (errors == 0) $display("HGI_SM_E2E PASS"); else $display("HGI_SM_E2E FAIL errors=%0d", errors);
        $finish;
    end
endmodule
