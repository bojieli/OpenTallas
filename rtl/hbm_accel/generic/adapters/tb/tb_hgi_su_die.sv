`timescale 1ns/1ps
// hgi-1010/c2 (2026-10-10, AUDIT N1): DIE-MASTER bench of the SU / SFU die views: the generated wrappers hfd_su / hfd_sfu
// (physical/hbm_accel_die_views/{su,sfu}_hgi/rtl: ot_hgi_su_unit WIDE, production N 512 / M 128) driven ONLY through
// their die ports:
//   * f_hgi_cmdproc = the CP's unit-2 / unit-3 record (ot_hgi_cp_die su_rec 2,198 b / sfu_rec 1,174 b), issued as the CP
//     does (one credit; a one-edge valid while the credit and ready are up; credit back on done / fault);
//   * the REAL HGI VM (ot_hgi_vm_unit RP / W2 32, LQ 32) on the VM packet client and, through ot_hgi_vm_lanearb (K 3,
//     SU slot 0 / SFU slot 1, RLY 2 = the lgW station + relays), on the lgW taps unpacked by the tap contract
//     rup {wrq, rg_req} | rdn {wrr, wrq_cr, rg_gnt} | wup {wwq, wg_req} | wdn {wwq_done, wwq_cr, wg_gnt}.
// Vectors: tools/hgi_unitrate/su_prod_vec.py (the Qwen3-8B layer-0 SU / SFU dispatches at P 8,191, production shapes):
// VM loaded with every source and sink sector, records retire without fault, every sink sector read back whole
// (written words = golden, others = pre-op).  Define SFU for the SFU master.  MUT_TAP: the bench unpacks rdn as
// {rg_gnt, wrq_cr, wrr} reversed (a station with another packing) -> must FAIL.
module tb_hgi_su_die;
`ifdef SFU
    localparam integer GL = 1, RB = 1174, SLOT = 1;
`else
    localparam integer GL = 0, RB = 2198, SLOT = 0;
`endif
    `include "su_sizes.svh"
    reg clk = 0; always #1 clk = ~clk;
    reg [2196:0] recm [0:NREC-1]; reg [223:0] casem [0:NCASE-1];
    reg [287:0] vmim [0:NVMI-1]; reg [287:0] vmem [0:NVME-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/su_rec.mem"}, recm); $readmemh({dir, "/su_case.mem"}, casem);
        $readmemh({dir, "/su_vmi.mem"}, vmim); $readmemh({dir, "/su_vme.mem"}, vmem);
    end
    integer errors = 0, cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    reg rst_n = 0; reg [RB-1:0] rec = 0; wire [2:0] ret; wire [18:0] vm_status;
    wire [337:0] uq; wire [273:0] ur, tr; reg [337:0] tq = 0;
    wire [512:0] rup; wire [8256:0] rdn; wire [8960:0] wup; wire [64:0] wdn;
    function automatic [RB-1:0] die_rec(input [2196:0] c);   // tb record {n_A, I, R, O, D, C, B, A, SUT, header} -> die
        if (GL == 0) die_rec = {c, 1'b1};
        else die_rec = RB'({c[2196:2176], c[1663:1408], c[1151:896], c[895:640], c[639:384], c[127:0], 1'b1});
    endfunction
`ifdef SFU
    hfd_sfu dut (.ck0(clk), .ck1(clk), .ck2(clk), .ck3(clk), .ck4(clk), .ck5(clk), .ck6(clk), .ck7(clk), .rst(!rst_n),
        .f_hgi_cmdproc(rec), .t_hgi_cmdproc(ret), .t_hgi_vmq(uq), .f_hgi_vmr(ur), .t_lgW_rup(rup), .f_lgW_rdn(rdn),
        .t_lgW_wup(wup), .f_lgW_wdn(wdn), .f_hc(1024'd0), .f_su(1024'd0), .t_hc(), .t_su());
`else
    hfd_su dut (.ck0(clk), .ck1(clk), .ck2(clk), .ck3(clk), .ck4(clk), .ck5(clk), .ck6(clk), .ck7(clk), .rst(!rst_n),
        .f_hgi_cmdproc(rec), .t_hgi_cmdproc(ret), .t_hgi_vmq(uq), .f_hgi_vmr(ur), .t_lgW_rup(rup), .f_lgW_rdn(rdn),
        .t_lgW_wup(wup), .f_lgW_wdn(wdn), .a(1058'd0), .f_coll(620'd0), .f_hgi_vmaddr(80'd0),
        .f_sfu(1024'd0), .f_su_ew(1024'd0), .f_su_ns(1024'd0), .f_vm(2048'd0), .r(2165'd0), .t_coll(),
        .t_sfu(), .t_su_ew(), .t_su_ns(), .t_vm());
`endif
    wire [2:0] rgnt, wgnt; wire [3*32-1:0] rcr, wcr, wdone; wire [3*32*257-1:0] rrs;
    wire [32*16-1:0] g_rq; wire [31:0] g_rcr, g_wcr, g_wdone; wire [32*257-1:0] g_rr; wire [32*280-1:0] g_wq;
    ot_hgi_vm_lanearb #(.K(3), .REQW(16), .RSPW(257), .RLY(2)) u_ar (.clk(clk), .rst_n(rst_n), .c_req(3'(rup[0]) << SLOT),
        .c_gnt(rgnt), .c_q((3*32*16)'(rup[512:1]) << (SLOT*32*16)), .c_cr(rcr), .c_rsp(rrs), .g_q(g_rq), .g_cr(g_rcr), .g_rsp(g_rr));
    ot_hgi_vm_lanearb #(.K(3), .REQW(280), .RSPW(1), .RLY(2)) u_aw (.clk(clk), .rst_n(rst_n), .c_req(3'(wup[0]) << SLOT),
        .c_gnt(wgnt), .c_q((3*32*280)'(wup[8960:1]) << (SLOT*32*280)), .c_cr(wcr), .c_rsp(wdone), .g_q(g_wq), .g_cr(g_wcr),
        .g_rsp(g_wdone));
`ifdef MUT_TAP
    assign rdn = {rgnt[SLOT], rcr[SLOT*32 +: 32], rrs[SLOT*32*257 +: 32*257]};
`else
    assign rdn = {rrs[SLOT*32*257 +: 32*257], rcr[SLOT*32 +: 32], rgnt[SLOT]};
`endif
    assign wdn = {wdone[SLOT*32 +: 32], wcr[SLOT*32 +: 32], wgnt[SLOT]};
    ot_hgi_vm_unit #(.NC(2), .RP(32), .W2(32), .LQ(32)) u_vm (.clk(clk), .rst_n(rst_n), .cq({tq, uq}), .cr({tr, ur}),
        .status(vm_status), .wq(280'd0), .wq_done(), .rq(g_rq), .rq_cr(g_rcr), .rr(g_rr), .w2q(g_wq), .w2q_cr(g_wcr),
        .w2q_done(g_wdone));
    task automatic vm_sec(input we, input [31:0] sec, input [255:0] data, output [255:0] qd);
        integer tw;
        begin
            @(negedge clk); tq = {1'b1, we, sec[26:0], 5'd0, data, 32'hFFFFFFFF, 16'h0BE0};
            @(negedge clk); tq[337] = 1'b0;
            tw = 0; while (!tr[273] && tw < 1000) begin @(negedge clk); tw = tw + 1; end
            if (tw >= 1000) begin $display("ERR bench VM request timed out"); errors = errors + 1; end
            qd = tr[255:0];
        end
    endtask
    integer k, nf; reg credit = 1;
    always @(posedge clk) begin
        if (rst_n && ret[1]) k = k + 1;
        if (rst_n && ret[2]) nf = nf + 1;
        if (!rst_n) credit <= 1; else if (ret[1] || ret[2]) credit <= 1; else if (rec[0]) credit <= 0;
    end
    integer c, j, t, cid, sfu, r0, nr, vi0, nvi, ve0, nve, cases = 0, words = 0, t0, w;
    integer wd = 4000000;          // +WD=<cycles>: per-wait watchdog (mutant runs: a hang fails in WD cycles, not days)
    reg [255:0] qd;
    initial begin
        if (!$value$plusargs("WD=%d", wd)) wd = 4000000;
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            r0 = casem[c][223:192]; nr = casem[c][191:160]; vi0 = casem[c][159:128];
            nvi = casem[c][127:96]; ve0 = casem[c][95:64]; nve = casem[c][63:32]; cid = casem[c][30:0]; sfu = casem[c][31];
            if (sfu != GL) continue;
            rst_n = 0; repeat (4) @(posedge clk); rst_n = 1; repeat (12) @(posedge clk);
            for (j = 0; j < nvi; j = j + 1) vm_sec(1'b1, vmim[vi0 + j][287:256], vmim[vi0 + j][255:0], qd);
            k = 0; nf = 0; t0 = cyc;
            for (j = 0; j < nr; j = j + 1) begin
                t = 0; while (!(credit && ret[0]) && t < wd) begin @(negedge clk); t = t + 1; end
                @(negedge clk); rec = die_rec(recm[r0 + j]);
                @(negedge clk); rec[0] = 1'b0;
                t = 0; while (credit && t < 100) begin @(negedge clk); t = t + 1; end
            end
            t = 0; while (k < nr && nf == 0 && t < wd) begin @(posedge clk); t = t + 1; end
            if (k != nr || nf != 0) begin $display("ERR case %0d: retired %0d of %0d, faults %0d", cid, k, nr, nf); errors = errors + 1; $fflush; end
            $display("CASE %0d: %0d records retired in %0d cycles (die ports, real VM, lgW taps)", cid, k, cyc - t0); $fflush;
            for (j = 0; j < nve; j = j + 1) begin
                vm_sec(1'b0, vmem[ve0 + j][287:256], 256'd0, qd);
                for (w = 0; w < 8; w = w + 1)
                    if (qd[32*w +: 32] !== vmem[ve0 + j][32*w +: 32]) begin
                        if (errors < 20) $display("ERR case %0d VM[%0d] = %h expected %h", cid, vmem[ve0 + j][287:256] * 8 + w,
                                                  qd[32*w +: 32], vmem[ve0 + j][32*w +: 32]);
                        errors = errors + 1;
                    end
                words = words + 8;
            end
            cases = cases + 1;
        end
        if (vm_status[18]) begin errors = errors + 1; $display("ERR VM status fault %b", vm_status[18:16]); end
        $display("summary: %0d production-shape cases through the %s die master, %0d sink-sector words checked", cases,
                 GL ? "hfd_sfu" : "hfd_su", words);
        if (errors == 0 && cases > 0) $display("HGI_SU_DIE PASS"); else $display("HGI_SU_DIE FAIL errors=%0d", errors);
        $finish;
    end
endmodule
