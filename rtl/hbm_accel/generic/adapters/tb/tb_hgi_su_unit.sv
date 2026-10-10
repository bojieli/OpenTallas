`timescale 1ns/1ps
// hgi-adapters (2026-10-09): D1 bench of the stream-unit die body ot_hgi_su_unit: records -> adapter -> STAGE from the
// REAL HGI VM (ot_hgi_vm_unit NC 2: client 0 the unit, 4 outstanding; client 1 this bench) -> the REAL ot_hdc_v41x_vec on
// its local memory -> DRAIN back to VM.  Vectors: tools/hgi_adapters/su_bench.py DATA cases (hbm-sim CF-BCAST, CF-LOOP2,
// CF-ROPE x 2): VM out == the vector's expect; a guard word after every expected region must keep its value (the drain
// writes only words the op wrote).  Prints HGI_SU_UNIT PASS / FAIL.
module tb_hgi_su_unit;
`ifdef MUT_DIRTY
    localparam integer MD = 1;
`else
    localparam integer MD = 0;
`endif
    `include "su_sizes.svh"
    reg clk = 0; always #1 clk = ~clk;
    reg [2196:0] recm [0:NREC-1]; reg [671:0] refm [0:NREC-1]; reg [223:0] casem [0:NCASE-1];
    reg [63:0] vmim [0:NVMI-1]; reg [63:0] vmem [0:NVME-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/su_rec.mem"}, recm); $readmemh({dir, "/su_ref.mem"}, refm); $readmemh({dir, "/su_case.mem"}, casem);
        $readmemh({dir, "/su_vmi.mem"}, vmim); $readmemh({dir, "/su_vme.mem"}, vmem);
    end
    integer errors = 0, cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [2196:0] cur; reg rec_v = 0;
    wire rec_rdy, done, fault, halted; wire [337:0] uq; wire [273:0] ur, tr; reg [337:0] tq = 0;
    ot_hgi_su_unit #(.N(32), .M(8), .LV(7), .MUT_DIRTY(MD)) u (.clk(clk), .rst_n(rst_n), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(cur[127:0]), .rec_sut(cur[383:128]), .rec_a(cur[639:384]), .rec_b(cur[895:640]), .rec_c(cur[1151:896]),
        .rec_d(cur[1407:1152]), .rec_o(cur[1663:1408]), .rec_r(cur[1919:1664]), .rec_i(cur[2175:1920]),
        .rec_n_a(cur[2196:2176]), .rec_done(done), .rec_fault(fault), .halted(halted), .vmq(uq), .vmr(ur));
    ot_hgi_vm_unit #(.NC(2)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, uq}), .cr({tr, ur}), .status());
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
    integer c, j, t, kind, r0, nr, vi0, nvi, ve0, nve, words = 0, cases = 0, t0;
    reg [31:0] qd, gaddr;
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            kind = casem[c][223:192]; r0 = casem[c][191:160]; nr = casem[c][159:128]; vi0 = casem[c][127:96];
            nvi = casem[c][95:64]; ve0 = casem[c][63:32]; nve = casem[c][31:0];
            if (kind != 0) continue;
            rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
            for (j = 0; j < nvi; j = j + 1) vm_req(1'b1, vmim[vi0 + j][63:32], vmim[vi0 + j][31:0], qd);
            // guard words: one past each expected word that is not itself expected or an input -> 0xA5A5A5A5
            for (j = 0; j < nve; j = j + 1) begin
                gaddr = vmem[ve0 + j][63:32] + 1;
                if (j + 1 == nve || vmem[ve0 + j + 1][63:32] != gaddr) vm_req(1'b1, gaddr, 32'hA5A5A5A5, qd);
            end
            k = 0; nf = 0; t0 = cyc;
            for (j = 0; j < nr; j = j + 1) begin
                @(negedge clk); cur = recm[r0 + j]; rec_v = 1;
                t = 0; while (!rec_rdy && t < 2000000) begin @(negedge clk); t = t + 1; end
                @(posedge clk); #0.1 rec_v = 0;
            end
            t = 0; while (k < nr && nf == 0 && t < 2000000) begin @(posedge clk); t = t + 1; end
            if (k != nr || nf != 0) begin $display("ERR case %0d: retired %0d of %0d, faults %0d", c, k, nr, nf); errors = errors + 1; end
            $display("case %0d: %0d records retired in %0d cycles (stage + compute + drain)", c, k, cyc - t0); $fflush;
            for (j = 0; j < nve; j = j + 1) begin
                vm_req(1'b0, vmem[ve0 + j][63:32], 0, qd);
                if (qd !== vmem[ve0 + j][31:0]) begin
                    if (errors < 20) $display("ERR case %0d VM[%0d] = %h expected %h", c, vmem[ve0 + j][63:32], qd, vmem[ve0 + j][31:0]);
                    errors = errors + 1; end
                gaddr = vmem[ve0 + j][63:32] + 1;
                if (j + 1 == nve || vmem[ve0 + j + 1][63:32] != gaddr) begin
                    vm_req(1'b0, gaddr, 0, qd);
                    if (qd !== 32'hA5A5A5A5) begin
                        if (errors < 20) $display("ERR case %0d guard VM[%0d] overwritten (%h)", c, gaddr, qd); errors = errors + 1; end
                end
            end
            words = words + nve; cases = cases + 1;
        end
        $display("summary: %0d SU data cases through stage / compute / drain, %0d VM words exact", cases, words);
        if (errors == 0 && cases > 0) $display("HGI_SU_UNIT PASS"); else $display("HGI_SU_UNIT FAIL errors=%0d", errors);
        $finish;
    end
endmodule
