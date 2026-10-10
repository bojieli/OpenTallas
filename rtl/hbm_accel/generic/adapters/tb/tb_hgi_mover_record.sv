`timescale 1ns/1ps
// hgi-adapters (2026-10-09): DATA bench of the DMA path: records -> ot_hgi_dma_record -> ot_hgi_dma_mover -> the REAL
// HGI VM (ot_hgi_vm_unit, client 0 = the mover, client 1 = this bench) and a kport-lane HBM model (one transaction
// outstanding, random latency, sector memory).  Vectors tools/hgi_adapters/mover_bench.py: hbm-sim CF-IDXD n_from_vm,
// CF-KV linear append + DS KVWB x 2 (expected hbm_out / vm_out) and 60 random LOAD / STORE records (every format,
// stride, alignment; hgi_sim decode_fmt / encode_fmt).  Prints HGI_MOVER PASS / FAIL.
module tb_hgi_mover_record;
`ifdef MUT_WIDE_MASK
    localparam integer VMUT = 4;
`else
    localparam integer VMUT = 0;
`endif
`ifdef MUT_RNE
    localparam integer MR = 1;
`else
    localparam integer MR = 0;
`endif
    `include "mo_sizes.svh"
    reg clk = 0;
    always #1 clk = ~clk;
    reg [702:0] recm [0:NREC-1];
    reg [319:0] casem [0:NCASE-1];
    reg [63:0] vmim [0:VMI-1]; reg [63:0] vmem [0:VME-1];
    reg [71:0] hbim [0:HBI-1]; reg [71:0] hbem [0:HBE-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/mo_rec.mem"}, recm); $readmemh({dir, "/mo_case.mem"}, casem);
        $readmemh({dir, "/mo_vmi.mem"}, vmim); $readmemh({dir, "/mo_vme.mem"}, vmem);
        $readmemh({dir, "/mo_hbi.mem"}, hbim); $readmemh({dir, "/mo_hbe.mem"}, hbem);
    end
    integer errors = 0, seed = 5;
    reg rst_n = 0; reg [702:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted, mv_v, mv_rdy, mv_done, mv_fault, fence_v, fence_rdy, fence_done;
    wire [226:0] mv;
    ot_hgi_dma_record u_a (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_o(cur[639:384]), .rec_n_a(cur[660:640]), .rec_n_o(cur[681:661]),
        .rec_pos1(cur[702:682]), .rec_done(done), .rec_fault(fault), .halted(halted), .lg_mv_v(1'b0), .lg_mv_rdy(),
        .lg_mv(227'd0), .lg_fence_v(1'b0), .lg_fence_rdy(), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done),
        .mv_fault(mv_fault), .fence_v(fence_v), .fence_rdy(fence_rdy), .fence_done(fence_done));
    wire k_req_v, k_req_we, k_rsp_rdy; reg k_req_rdy = 0, k_rsp_v = 0, k_rsp_we = 0; reg [255:0] k_rsp_data = 0;
    wire [36:0] k_addr; wire [255:0] k_wd; wire [31:0] k_ws; wire [15:0] k_tag;
    wire [337:0] vmq; wire [273:0] vmr0, vmr1; reg [337:0] tq = 0;
    ot_hgi_dma_mover #(.MUT_RNE(MR)) u_m (.clk(clk), .rst_n(rst_n), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv),
        .mv_done(mv_done), .mv_fault(mv_fault), .fence_v(fence_v), .fence_rdy(fence_rdy), .fence_done(fence_done),
        .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we), .k_req_addr(k_addr), .k_req_wdata(k_wd),
        .k_req_wstrb(k_ws), .k_req_tag(k_tag), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(k_rsp_we),
        .k_rsp_data(k_rsp_data), .k_fault(1'b0), .vmq(vmq), .vmr(vmr0), .wl(wl), .wl_done(wl_done));
    wire [279:0] wl; wire wl_done;   // the VM wide write port (hgi-takeover 2026-10-10)
    ot_hgi_vm_unit #(.NC(2), .WP(1), .MUT(VMUT)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, vmq}), .cr({vmr1, vmr0}), .status(), .wq(wl), .wq_done(wl_done));
    // ---- kport lane HBM model
    reg [31:0] hbm [longint];
    integer klat = -1, q; reg pend = 0, pwe; reg [36:0] pa; reg [255:0] pd; reg [31:0] ps;
    always @(posedge clk) begin
        k_rsp_v <= 0;
        if (rst_n && k_req_v && k_req_rdy && !pend) begin
            pend = 1; pwe = k_req_we; pa = k_addr; pd = k_wd; ps = k_ws; klat = 2 + ($random(seed) & 7);
            if (k_addr[4:0] != 0) begin $display("ERR kport address not sector aligned"); errors = errors + 1; end
        end else if (pend && klat > 0) klat = klat - 1;
        else if (pend) begin
            for (q = 0; q < 8; q = q + 1) begin
                if (pwe) begin
                    hbm[(pa >> 2) + q] = {ps[4*q+3] ? pd[32*q+24 +: 8] : (hbm.exists((pa >> 2) + q) ? hbm[(pa >> 2) + q][31:24] : 8'd0),
                                          ps[4*q+2] ? pd[32*q+16 +: 8] : (hbm.exists((pa >> 2) + q) ? hbm[(pa >> 2) + q][23:16] : 8'd0),
                                          ps[4*q+1] ? pd[32*q+8 +: 8] : (hbm.exists((pa >> 2) + q) ? hbm[(pa >> 2) + q][15:8] : 8'd0),
                                          ps[4*q] ? pd[32*q +: 8] : (hbm.exists((pa >> 2) + q) ? hbm[(pa >> 2) + q][7:0] : 8'd0)};
                end else k_rsp_data[32*q +: 32] <= hbm.exists((pa >> 2) + q) ? hbm[(pa >> 2) + q] : 32'd0;
            end
            k_rsp_v <= 1; k_rsp_we <= pwe; pend = 0;
        end
        // ready from the state AFTER this edge's accept (hgi-takeover: a request issued the cycle after an accept was
        // shown ready but dropped -- the serial mover never issued back to back)
        k_req_rdy <= !pend && ($random(seed) & 1);
    end
    task automatic vm_req(input we, input [31:0] word, input [31:0] data, output [31:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, word[29:3], 5'd0, {8{data}}, (32'hF << (4 * word[2:0])), 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!vmr1[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            qd = vmr1[32 * word[2:0] +: 32];
        end
    endtask
    integer c, j, t, r0, nr, vi0, nvi, hi0, nhi, ve0, nve, he0, nhe, k, nf, words = 0;
    reg [31:0] qd;
    always @(posedge clk) begin if (rst_n && done) k = k + 1; if (rst_n && fault) nf = nf + 1; end
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            {r0, nr, vi0, nvi, hi0, nhi, ve0, nve, he0, nhe} = casem[c];
            rst_n = 0; hbm.delete(); repeat (3) @(posedge clk); rst_n = 1; repeat (2) @(posedge clk);
            for (j = 0; j < nvi; j = j + 1) vm_req(1'b1, vmim[vi0 + j][63:32], vmim[vi0 + j][31:0], qd);
            for (j = 0; j < nhi; j = j + 1) hbm[hbim[hi0 + j][71:32]] = hbim[hi0 + j][31:0];
            k = 0; nf = 0;
            for (j = 0; j < nr; j = j + 1) begin
                @(negedge clk); cur = recm[r0 + j]; rec_v = 1;
                t = 0; while (!rec_rdy && t < 400000) begin @(negedge clk); t = t + 1; end
                @(posedge clk); #0.1 rec_v = 0;
            end
            t = 0; while (k < nr && nf == 0 && t < 400000) begin @(posedge clk); t = t + 1; end
            if (k != nr || nf != 0) begin $display("ERR case %0d: retired %0d of %0d, faults %0d", c, k, nr, nf); errors = errors + 1; end
            for (j = 0; j < nve; j = j + 1) begin
                vm_req(1'b0, vmem[ve0 + j][63:32], 0, qd);
                if (qd !== vmem[ve0 + j][31:0]) begin
                    if (errors < 30) $display("ERR case %0d VM[%0d] = %h expected %h", c, vmem[ve0 + j][63:32], qd, vmem[ve0 + j][31:0]);
                    errors = errors + 1; end
            end
            for (j = 0; j < nhe; j = j + 1) begin
                qd = hbm.exists(hbem[he0 + j][71:32]) ? hbm[hbem[he0 + j][71:32]] : 32'd0;
                if (qd !== hbem[he0 + j][31:0]) begin
                    if (errors < 30) $display("ERR case %0d HBM word %h = %h expected %h", c, hbem[he0 + j][71:32], qd, hbem[he0 + j][31:0]);
                    errors = errors + 1; end
            end
            words = words + nve + nhe;
        end
        $display("summary: %0d cases (%0d records), %0d memory words checked", NCASE, NREC, words);
        if (errors == 0) $display("HGI_MOVER PASS"); else $display("HGI_MOVER FAIL errors=%0d", errors);
        $finish;
    end
endmodule
