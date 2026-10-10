`timescale 1ns/1ps
// hgi-adapters (2026-10-09): D1 bench of the FUSED die body: ot_hgi_fused_record UNIT = 1 (micro-ops on an internal
// ot_hgi_su_unit: stage / real ot_hdc_v41x_vec / drain) + the gain DMA on the REAL ot_hgi_dma_mover, all on the REAL
// HGI VM (ot_hgi_vm_unit NC 3: 0 the FUSED unit, 1 the mover, 2 this bench) and a kport-lane HBM model.  Vectors:
// tools/hgi_adapters/fused_bench.py DATA cases (hbm-sim CF-NORM, Qwen ROW_NORM shapes, DS HC_PRE_NORM / HC_POST):
// VM out == expected.  Prints HGI_FUSED_UNIT PASS / FAIL.
module tb_hgi_fused_unit;
    `include "fu_sizes.svh"
    reg clk = 0; always #1 clk = ~clk;
    reg [1214:0] recm [0:NREC-1]; reg [686:0] expm [0:NREC-1]; reg [287:0] casem [0:NCASE-1];
    reg [63:0] vmim [0:NVMI-1]; reg [63:0] vmem [0:NVME-1]; reg [71:0] hbmm [0:NHBM-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/fu_rec.mem"}, recm); $readmemh({dir, "/fu_exp.mem"}, expm); $readmemh({dir, "/fu_case.mem"}, casem);
        $readmemh({dir, "/fu_vmi.mem"}, vmim); $readmemh({dir, "/fu_vme.mem"}, vmem); $readmemh({dir, "/fu_hbm.mem"}, hbmm);
    end
    integer errors = 0, cyc = 0, seed = 3; always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [1214:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted, mv_v, mv_rdy, mv_done, mv_fault; wire [226:0] mv;
    wire [337:0] fq, mq; wire [273:0] fr, mr, tr; reg [337:0] tq = 0;
    ot_hgi_fused_record #(.UNIT(1)) u (.clk(clk), .rst_n(rst_n), .cfg_scratch(18'd240000), .rec_v(rec_v),
        .rec_rdy(rec_rdy), .rec_hdr(cur[127:0]), .rec_a(cur[383:128]), .rec_b(cur[639:384]), .rec_c(cur[895:640]),
        .rec_o(cur[1151:896]), .rec_n_a(cur[1172:1152]), .rec_n_b(cur[1193:1173]), .rec_n_o(cur[1214:1194]),
        .rec_done(done), .rec_fault(fault), .halted(halted), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done),
        .mv_fault(mv_fault), .op_v(), .op_rdy(1'b0), .op_w(), .su_idle(1'b1), .su_fault(1'b0), .vmq(fq), .vmr(fr),
        .ne_v(), .ne_rdy(1'b1), .ne_job(), .ne_done(1'b0), .ne_fault(1'b0), .q_rec(), .q_done(1'b0), .q_fault(1'b0));
    wire k_req_v, k_req_we, k_rsp_rdy; reg k_req_rdy = 0, k_rsp_v = 0, k_rsp_we = 0; reg [255:0] k_rsp_data = 0;
    wire [36:0] k_addr; wire [255:0] k_wd; wire [31:0] k_ws; wire [15:0] k_tag;
    ot_hgi_dma_mover u_m (.clk(clk), .rst_n(rst_n), .mv_v(mv_v), .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done),
        .mv_fault(mv_fault), .fence_v(1'b0), .fence_rdy(), .fence_done(), .k_req_v(k_req_v), .k_req_rdy(k_req_rdy),
        .k_req_we(k_req_we), .k_req_addr(k_addr), .k_req_wdata(k_wd), .k_req_wstrb(k_ws), .k_req_tag(k_tag),
        .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(k_rsp_we), .k_rsp_data(k_rsp_data), .k_fault(1'b0),
        .vmq(mq), .vmr(mr));
    ot_hgi_vm_unit #(.NC(3)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, mq, fq}), .cr({tr, mr, fr}), .status());
    reg [31:0] hbm [longint];
    integer klat = -1, q; reg pend = 0; reg [36:0] pa;
    always @(posedge clk) begin
        k_rsp_v <= 0; k_req_rdy <= !pend && ($random(seed) & 1);
        if (rst_n && k_req_v && k_req_rdy && !pend) begin pend = 1; pa = k_addr; klat = 2 + ($random(seed) & 7); end
        else if (pend && klat > 0) klat = klat - 1;
        else if (pend) begin
            for (q = 0; q < 8; q = q + 1) k_rsp_data[32*q +: 32] <= hbm.exists((pa >> 2) + q) ? hbm[(pa >> 2) + q] : 32'd0;
            k_rsp_v <= 1; k_rsp_we <= 0; pend = 0;
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
    integer k, nf;
    always @(posedge clk) begin if (rst_n && done) k = k + 1; if (rst_n && fault) nf = nf + 1; end
    integer c, j, t, kind, r0, nr, vi0, nvi, ve0, nve, h0, nh, words = 0, cases = 0, t0;
    reg [31:0] qd;
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            kind = casem[c][287:256]; r0 = casem[c][255:224]; nr = casem[c][223:192]; vi0 = casem[c][191:160];
            nvi = casem[c][159:128]; ve0 = casem[c][127:96]; nve = casem[c][95:64]; h0 = casem[c][63:32]; nh = casem[c][31:0];
            if (kind != 0) continue;
            rst_n = 0; hbm.delete(); repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
            for (j = 0; j < nvi; j = j + 1) vm_req(1'b1, vmim[vi0 + j][63:32], vmim[vi0 + j][31:0], qd);
            for (j = 0; j < nh; j = j + 1) hbm[hbmm[h0 + j][71:32]] = hbmm[h0 + j][31:0];
            k = 0; nf = 0; t0 = cyc;
            for (j = 0; j < nr; j = j + 1) begin
                @(negedge clk); cur = recm[r0 + j]; rec_v = 1;
                t = 0; while (!rec_rdy && t < 4000000) begin @(negedge clk); t = t + 1; end
                @(posedge clk); #0.1 rec_v = 0;
            end
            t = 0; while (k < nr && nf == 0 && t < 4000000) begin @(posedge clk); t = t + 1; end
            if (k != nr || nf != 0) begin $display("ERR case %0d: retired %0d of %0d, faults %0d", c, k, nr, nf); errors = errors + 1; end
            $display("case %0d: %0d records in %0d cycles", c, k, cyc - t0); $fflush;
            for (j = 0; j < nve; j = j + 1) begin
                vm_req(1'b0, vmem[ve0 + j][63:32], 0, qd);
                if (qd !== vmem[ve0 + j][31:0]) begin
                    if (errors < 20) $display("ERR case %0d VM[%0d] = %h expected %h", c, vmem[ve0 + j][63:32], qd, vmem[ve0 + j][31:0]);
                    errors = errors + 1; end
            end
            words = words + nve; cases = cases + 1;
        end
        $display("summary: %0d FUSED data cases through the D1 unit, %0d VM words exact", cases, words);
        if (errors == 0 && cases > 0) $display("HGI_FUSED_UNIT PASS"); else $display("HGI_FUSED_UNIT FAIL errors=%0d", errors);
        $finish;
    end
endmodule
