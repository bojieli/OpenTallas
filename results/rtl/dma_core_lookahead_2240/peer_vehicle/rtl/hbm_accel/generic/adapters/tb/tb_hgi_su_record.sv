`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// hgi-adapters (2026-10-09): bench of ot_hgi_su_record (+define+UNIT_SFU: ot_hgi_sfu_record, SFU.GLU).  Vectors: tools/hgi_adapters/su_bench.py (+DIR=<dir>).
//  DATA cases (hbm-sim conformance vectors with SU.VOP records): three copies of the REAL stream unit
//    ot_hdc_v41x_vec (N 16, M 8), each with its own VM:
//      H  records -> ot_hgi_su_record (hgi_en 1) -> vec_H         VM out must equal the vector's expected VM;
//      L  legacy op words -> ot_hgi_su_record (hgi_en 0) -> vec_L  must equal D cycle for cycle (DS lockstep identity);
//      D  legacy op words -> vec_D directly (the existing DS control path; issue when idle, as the DS bench w_idle).
//    Per op: the adapter's op word == the reference word, and the unit's accept -> idle span on H == on D.
//  FIELDS cases (Qwen3-8B token program SU records, random legal templates, empty ops): adapter S with a stub unit:
//    op word == reference, every record retires once, in order, never before the unit's completion.
//  NEGATIVE cases: one record each after a reset: rec_fault, no op issued, halted.
// Every retire must come after the unit went idle (the record retires on the unit's real completion).
// Prints HGI_SU PASS / HGI_SU FAIL.
// ---------------------------------------------------------------------------------------------------------------------
module tb_hgi_su_record;
`ifdef MUT_ISTRIDE
    localparam integer MI = 1;
`else
    localparam integer MI = 0;
`endif
`ifdef MUT_EARLY
    localparam integer ME = 1;
`else
    localparam integer ME = 0;
`endif
    `include "su_sizes.svh"
    localparam integer N = 16, M = 8, AW = 24, NR = N / 8, VMA = 18, WB = 670;
    reg clk = 0;
    always #1 clk = ~clk;
    reg [2196:0] recm [0:NREC-1];
    reg [671:0]  refm [0:NREC-1];
    reg [223:0]  casem [0:NCASE-1];
    reg [63:0]   vmim [0:NVMI-1];
    reg [63:0]   vmem [0:NVME-1];
    reg [8*256-1:0] dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        $readmemh({dir, "/su_rec.mem"}, recm); $readmemh({dir, "/su_ref.mem"}, refm);
        $readmemh({dir, "/su_case.mem"}, casem); $readmemh({dir, "/su_vmi.mem"}, vmim);
        $readmemh({dir, "/su_vme.mem"}, vmem);
    end
    integer errors = 0, cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // ================================================================ three vec units with their VMs
    reg rst_n = 0;
    reg [2196:0] cur;                     // record driven into H / S
    reg          h_rec_v = 0;
    wire         h_rec_rdy, h_done, h_fault, h_halted;
    wire         h_op_v, h_op_rdy; wire [WB-1:0] h_op_w;
    reg          lg_v = 0; reg [WB-1:0] lg_w = 0; wire lg_rdy;
    wire         l_op_v, l_op_rdy; wire [WB-1:0] l_op_w;
    wire         d_go;
    wire [2:0]   v_idle, v_fault, v_ready;
    wire [N*AW-1:0] vm_waddr [0:2]; wire [N*32-1:0] vm_wdata [0:2]; wire [N-1:0] vm_we [0:2];
    wire [NR-1:0] res_we [0:2]; wire [NR*AW-1:0] res_addr [0:2]; wire [NR*32-1:0] res_data [0:2];
    reg  [31:0] vm [0:2][0:(1<<VMA)-1];
    wire [WB-1:0] vw [0:2];
    wire [2:0] vgo;
    assign vw[0] = h_op_w; assign vgo[0] = h_op_v;
    assign vw[1] = l_op_w; assign vgo[1] = l_op_v;
    assign vw[2] = lg_w;   assign vgo[2] = d_go;
    assign h_op_rdy = v_ready[0]; assign l_op_rdy = v_ready[1];
    assign d_go = lg_v;    // the legacy issuer drives vec_D directly and vec_L through the adapter, same cycle

    tb_hgi_vec_adapter #(.MI(MI), .ME(ME)) u_h (.clk(clk), .rst_n(rst_n), .hgi_en(1'b1),
        .rec_v(h_rec_v), .rec_rdy(h_rec_rdy), .rec_hdr(cur[127:0]), .rec_sut(cur[383:128]),
        .rec_a(cur[639:384]), .rec_b(cur[895:640]), .rec_c(cur[1151:896]), .rec_d(cur[1407:1152]),
        .rec_o(cur[1663:1408]), .rec_r(cur[1919:1664]), .rec_i(cur[2175:1920]), .rec_n_a(cur[2196:2176]),
        .rec_done(h_done), .rec_fault(h_fault), .halted(h_halted), .lg_v(1'b0), .lg_rdy(), .lg_w({WB{1'b0}}),
        .op_v(h_op_v), .op_rdy(h_op_rdy), .op_w(h_op_w), .su_idle(v_idle[0]), .su_fault(v_fault[0]));
    wire l_rec_rdy, l_done, l_fault, l_halted;
    tb_hgi_vec_adapter #(.MI(MI), .ME(ME)) u_l (.clk(clk), .rst_n(rst_n), .hgi_en(1'b0),
        .rec_v(1'b0), .rec_rdy(l_rec_rdy), .rec_hdr(128'd0), .rec_sut(256'd0), .rec_a(256'd0), .rec_b(256'd0),
        .rec_c(256'd0), .rec_d(256'd0), .rec_o(256'd0), .rec_r(256'd0), .rec_i(256'd0), .rec_n_a(21'd0),
        .rec_done(l_done), .rec_fault(l_fault), .halted(l_halted), .lg_v(lg_v), .lg_rdy(lg_rdy), .lg_w(lg_w),
        .op_v(l_op_v), .op_rdy(l_op_rdy), .op_w(l_op_w), .su_idle(v_idle[1]), .su_fault(v_fault[1]));

    genvar g;
    generate for (g = 0; g < 3; g = g + 1) begin : gv
        wire [N-1:0] vi_re; wire [N*AW-1:0] vi_addr; reg [N*32-1:0] vi_q;
        wire [4*N*AW-1:0] rd_addr; wire [4*N-1:0] rd_re; wire [8*N-1:0] rd_src; reg [4*N*32-1:0] rd_q;
        wire [N-1:0] kv_we; wire [N*AW-1:0] kv_waddr; wire [N*32-1:0] kv_wdata;
        wire [7:0] cr_seq, cr_dseq, cr_rseq; wire [15:0] cr_cnt, emitted; wire order_fault, retire_o;
        wire dbg_emit, dbg_ret, dbg_res; wire [7:0] dbg_eseq, dbg_rseq, dbg_sseq;
        wire [WB-1:0] w = vw[g];
        ot_hdc_v41x_vec #(.N(N), .M(M), .LV(6)) dut (
            .clk(clk), .rst_n(rst_n), .go(vgo[g]), .ready(v_ready[g]), .idle(v_idle[g]),
            .i_nout(w[0 +: 16]), .i_nin(w[16 +: 16]), .i_asrc(w[32 +: 2]), .i_bsrc(w[34 +: 2]), .i_csrc(w[36 +: 2]),
            .i_dsrc(w[38 +: 2]), .i_abase(w[40 +: 24]), .i_aso(w[64 +: 24]), .i_asi(w[88 +: 24]),
            .i_aibase(w[112 +: 24]), .i_aind(w[136 +: 2]), .i_bbase(w[138 +: 24]), .i_bso(w[162 +: 24]),
            .i_bsi(w[186 +: 24]), .i_bhalf(w[210]), .i_cbase(w[211 +: 24]), .i_cso(w[235 +: 24]),
            .i_csi(w[259 +: 24]), .i_cpair(w[283]), .i_dbase(w[284 +: 24]), .i_dso(w[308 +: 24]),
            .i_dsi(w[332 +: 24]), .i_arnd(w[356]), .i_arelu(w[357]), .i_amin(w[358]), .i_cclip(w[359]),
            .i_m1(w[360 +: 3]), .i_m2(w[363 +: 2]), .i_qm(w[365 +: 3]), .i_ad(w[368 +: 3]), .i_sfu(w[371 +: 3]),
            .i_e1(w[374 +: 3]), .i_e2(w[377 +: 2]), .i_rnd(w[379]), .i_dst(w[380 +: 2]), .i_obase(w[382 +: 24]),
            .i_oso(w[406 +: 24]), .i_osi(w[430 +: 24]), .i_orow(w[454 +: 24]), .i_red(w[478 +: 2]),
            .i_redsq(w[480]), .i_redwhole(w[481]), .i_redtree(w[482]), .i_redrnd(w[483]), .i_rbase(w[484 +: 24]),
            .i_rso(w[508 +: 24]), .i_imm1(w[532 +: 32]), .i_imm2(w[564 +: 32]), .i_imm3(w[596 +: 32]),
            .i_ch_src(w[628 +: 2]), .i_ch_seq(w[630 +: 8]), .i_ch_lead(w[638 +: 16]), .i_ch_mul(w[654 +: 16]),
            .x_seq(8'd0), .x_dseq(8'hFF), .x_cnt(16'd0),
            .cr_seq(cr_seq), .cr_dseq(cr_dseq), .cr_rseq(cr_rseq), .cr_cnt(cr_cnt),
            .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .rd_addr(rd_addr), .rd_re(rd_re), .rd_src(rd_src),
            .rd_q(rd_q), .vm_we(vm_we[g]), .vm_waddr(vm_waddr[g]), .vm_wdata(vm_wdata[g]), .kv_we(kv_we),
            .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .res_we(res_we[g]), .res_addr(res_addr[g]),
            .res_data(res_data[g]), .fault(v_fault[g]), .order_fault(order_fault), .emitted(emitted),
            .retire_o(retire_o), .dbg_emit(dbg_emit), .dbg_eseq(dbg_eseq), .dbg_ret(dbg_ret), .dbg_rseq(dbg_rseq),
            .dbg_res(dbg_res), .dbg_sseq(dbg_sseq));
        integer l, s;
        always @(posedge clk) begin
            for (l = 0; l < N; l = l + 1) begin
                if (vi_re[l]) vi_q[32*l +: 32] <= vm[g][vi_addr[l*AW +: AW] & ((1<<VMA)-1)];
                for (s = 0; s < 4; s = s + 1)
                    if (rd_re[4*l + s]) rd_q[(4*l + s)*32 +: 32] <= vm[g][rd_addr[(4*l + s)*AW +: AW] & ((1<<VMA)-1)];
            end
            for (l = 0; l < N; l = l + 1)
                if (vm_we[g][l]) vm[g][vm_waddr[g][l*AW +: AW] & ((1<<VMA)-1)] <= vm_wdata[g][32*l +: 32];
            for (l = 0; l < NR; l = l + 1)
                if (res_we[g][l]) vm[g][res_addr[g][l*AW +: AW] & ((1<<VMA)-1)] <= res_data[g][32*l +: 32];
            if (rst_n && kv_we != 0) begin $display("ERR unit %0d wrote the KV port", g); errors = errors + 1; end
        end
    end endgenerate

    // ---- DS lockstep identity: vec_L == vec_D on every output, every cycle
    integer lock_cmp = 0;
    always @(posedge clk) if (rst_n) begin
        lock_cmp = lock_cmp + 1;
        if (v_idle[1] !== v_idle[2] || v_ready[1] !== v_ready[2] || v_fault[1] !== v_fault[2] ||
            vm_we[1] !== vm_we[2] || vm_waddr[1] !== vm_waddr[2] || vm_wdata[1] !== vm_wdata[2] ||
            res_we[1] !== res_we[2] || res_addr[1] !== res_addr[2] || res_data[1] !== res_data[2] ||
            l_op_w !== lg_w || l_op_v !== d_go) begin
            if (errors < 20) $display("ERR lockstep L != D at cycle %0d", cyc);
            errors = errors + 1;
        end
        if (l_done || l_fault || l_rec_rdy) begin $display("ERR legacy-mode adapter emitted a record event"); errors = errors + 1; end
    end

    // ---- H: op word check at accept, accept -> idle span, retire after the unit's completion
    integer h_k = 0, h_base = 0, h_acc_cyc = 0, h_span [0:NREC-1], d_span [0:NREC-1], h_retired = 0, h_issued = 0;
    reg     h_running = 0;
    reg [1:0] idle_hist = 2'b11;
    always @(posedge clk) begin
        idle_hist <= {idle_hist[0], v_idle[0]};
        if (rst_n && h_op_v && h_op_rdy) begin   // a retire in the same cycle belongs to the op ahead
            if (h_op_w !== refm[h_base + h_k + h_done][WB-1:0] || refm[h_base + h_k + h_done][671:670] != 2'd0) begin
                $display("ERR H op word mismatch at dispatch %0d", h_base + h_k + h_done);
                errors = errors + 1;
            end
            h_acc_cyc = cyc; h_running = 1; h_issued = h_issued + 1;
        end
        if (rst_n && h_running && cyc > h_acc_cyc + 1 && v_idle[0]) begin
            h_span[h_base + h_k] = cyc - h_acc_cyc; h_running = 0;
        end
        if (rst_n && h_done) begin
            if (!(idle_hist[0] && idle_hist[1]) && refm[h_base + h_k][671:670] == 2'd0) begin
                $display("ERR H retired dispatch %0d before the unit completed", h_base + h_k); errors = errors + 1;
            end
            h_k = h_k + 1; h_retired = h_retired + 1;
        end
    end

    // ---- stub unit for FIELDS / NEGATIVE cases (adapter S)
    reg s_rst_n = 0; reg s_rec_v = 0;
    wire s_rec_rdy, s_done, s_fault, s_halted, s_op_v; wire [WB-1:0] s_op_w;
    reg [3:0] s_busy = 0;
    wire s_idle = (s_busy == 0);
    tb_hgi_vec_adapter #(.MI(MI), .ME(ME)) u_s (.clk(clk), .rst_n(s_rst_n), .hgi_en(1'b1),
        .rec_v(s_rec_v), .rec_rdy(s_rec_rdy), .rec_hdr(cur[127:0]), .rec_sut(cur[383:128]),
        .rec_a(cur[639:384]), .rec_b(cur[895:640]), .rec_c(cur[1151:896]), .rec_d(cur[1407:1152]),
        .rec_o(cur[1663:1408]), .rec_r(cur[1919:1664]), .rec_i(cur[2175:1920]), .rec_n_a(cur[2196:2176]),
        .rec_done(s_done), .rec_fault(s_fault), .halted(s_halted), .lg_v(1'b0), .lg_rdy(), .lg_w({WB{1'b0}}),
        .op_v(s_op_v), .op_rdy(1'b1), .op_w(s_op_w), .su_idle(s_idle), .su_fault(1'b0));
    integer s_k = 0, s_base = 0, s_done_n = 0, s_fault_n = 0, s_iss = 0;
    always @(posedge clk) begin
        if (s_busy != 0) s_busy <= s_busy - 1;
        if (s_rst_n && s_op_v) begin
            s_busy <= 4'd9; s_iss = s_iss + 1;
            if (s_op_w !== refm[s_base + s_k + s_done][WB-1:0] || refm[s_base + s_k + s_done][671:670] != 2'd0) begin
                $display("ERR S op word mismatch at dispatch %0d", s_base + s_k + s_done); errors = errors + 1;
            end
        end
        if (s_rst_n && s_done) begin
            if (refm[s_base + s_k][671:670] == 2'd2) begin $display("ERR S retired a refused record %0d", s_base + s_k); errors = errors + 1; end
            if (refm[s_base + s_k][671:670] == 2'd0 && s_busy > 4'd6) begin
                $display("ERR S retired dispatch %0d before the stub completed", s_base + s_k); errors = errors + 1;
            end
            s_k = s_k + 1; s_done_n = s_done_n + 1;
        end
        if (s_rst_n && s_fault) begin s_k = s_k + 1; s_fault_n = s_fault_n + 1; end
    end

    // ================================================================ sequencing
    integer c, i, j, kind, r0, nr, vi0, nvi, ve0, nve, t, run_ops, lg_k, data_cases = 0, field_recs = 0, neg_ok = 0;
    integer lg_acc;
    task automatic clear_vms;
        integer a;
        for (a = 0; a < (1 << VMA); a = a + 1) begin vm[0][a] = 0; vm[1][a] = 0; vm[2][a] = 0; end
    endtask
    initial begin
        repeat (3) @(posedge clk);
        for (c = 0; c < NCASE; c = c + 1) begin
            kind = casem[c][223:192]; r0 = casem[c][191:160]; nr = casem[c][159:128]; vi0 = casem[c][127:96];
            nvi = casem[c][95:64]; ve0 = casem[c][63:32]; nve = casem[c][31:0];
            if (kind == 0) begin
                // ---------------- DATA: H (records) and L / D (legacy words), same VM image
                rst_n = 0; clear_vms();
                for (i = 0; i < nvi; i = i + 1) begin
                    vm[0][vmim[vi0 + i][63:32]] = vmim[vi0 + i][31:0]; vm[1][vmim[vi0 + i][63:32]] = vmim[vi0 + i][31:0];
                    vm[2][vmim[vi0 + i][63:32]] = vmim[vi0 + i][31:0];
                end
                h_base = r0; h_k = 0;
                repeat (4) @(posedge clk); rst_n = 1; repeat (4) @(posedge clk);
                fork
                    begin : feed_h
                        for (j = 0; j < nr; j = j + 1) begin
                            @(negedge clk); cur = recm[r0 + j]; h_rec_v = 1;
                            while (!h_rec_rdy) @(negedge clk);
                            @(posedge clk); #0.1 h_rec_v = 0;
                        end
                    end
                    begin : feed_legacy
                        for (lg_k = 0; lg_k < nr; lg_k = lg_k + 1) if (refm[r0 + lg_k][671:670] == 2'd0) begin
                            while (!v_idle[2]) @(posedge clk);
                            @(negedge clk); lg_w = refm[r0 + lg_k][WB-1:0]; lg_v = 1;
                            while (!v_ready[2]) @(negedge clk);
                            @(posedge clk); lg_acc = cyc; #0.1 lg_v = 0;
                            @(posedge clk); @(posedge clk);
                            while (!v_idle[2]) @(posedge clk);
                            d_span[r0 + lg_k] = cyc - lg_acc;
                        end
                    end
                join
                t = 0;
                while ((h_k < nr || !v_idle[0] || !v_idle[2]) && t < 2000000) begin @(posedge clk); t = t + 1; end
                repeat (8) @(posedge clk);
                if (t >= 2000000) begin $display("ERR data case %0d timeout", c); errors = errors + 1; end
                for (i = 0; i < nr; i = i + 1) if (refm[r0 + i][671:670] == 2'd0 && h_span[r0 + i] != d_span[r0 + i]) begin
                    $display("ERR dispatch %0d: unit span via record %0d != legacy %0d", r0 + i, h_span[r0 + i], d_span[r0 + i]);
                    errors = errors + 1;
                end
                for (i = 0; i < nve; i = i + 1) begin
                    if (vm[0][vmem[ve0 + i][63:32]] !== vmem[ve0 + i][31:0]) begin
                        if (errors < 40) $display("ERR case %0d VM[%0d] = %h, expected %h (record path)", c, vmem[ve0 + i][63:32],
                                                  vm[0][vmem[ve0 + i][63:32]], vmem[ve0 + i][31:0]);
                        errors = errors + 1;
                    end
                    if (vm[2][vmem[ve0 + i][63:32]] !== vmem[ve0 + i][31:0]) begin
                        if (errors < 40) $display("ERR case %0d VM[%0d] legacy path mismatch", c, vmem[ve0 + i][63:32]);
                        errors = errors + 1;
                    end
                end
                if (h_halted) begin $display("ERR data case %0d halted", c); errors = errors + 1; end
                $display("DATA case %0d: %0d dispatches, %0d VM words checked, issued %0d", c, nr, nve, h_issued);
                data_cases = data_cases + 1;
            end else begin
                // ---------------- FIELDS (stub unit) / NEGATIVE (one record, fresh reset)
                s_rst_n = 0; repeat (3) @(posedge clk); s_rst_n = 1; @(posedge clk);
                s_base = r0; s_k = 0; s_done_n = 0; s_fault_n = 0; s_iss = 0;
                for (j = 0; j < nr; j = j + 1) begin
                    @(negedge clk); cur = recm[r0 + j]; s_rec_v = 1;
                    t = 0; while (!s_rec_rdy && t < 1000) begin @(negedge clk); t = t + 1; end
                    @(posedge clk); #0.1 s_rec_v = 0;
                    if (kind == 2) begin repeat (12) @(posedge clk); end
                end
                t = 0; while (s_k < nr && t < 4000) begin @(posedge clk); t = t + 1; end
                repeat (12) @(posedge clk);
                if (kind == 1) begin
                    run_ops = 0; for (i = 0; i < nr; i = i + 1) if (refm[r0 + i][671:670] == 2'd0) run_ops = run_ops + 1;
                    if (s_done_n != nr || s_fault_n != 0 || s_iss != run_ops) begin
                        $display("ERR fields case %0d: done %0d fault %0d issued %0d of %0d / %0d", c, s_done_n, s_fault_n, s_iss, nr, run_ops);
                        errors = errors + 1;
                    end
                    field_recs = field_recs + nr;
                end else begin
                    if (s_fault_n != 1 || s_done_n != 0 || s_iss != 0 || !s_halted) begin
                        $display("ERR negative case %0d: fault %0d done %0d issued %0d halted %0d", c, s_fault_n, s_done_n, s_iss, s_halted);
                        errors = errors + 1;
                    end else neg_ok = neg_ok + 1;
                end
            end
        end
        $display("summary: data cases %0d (records + lockstep, %0d compared cycles), field records %0d, negatives %0d refused",
                 data_cases, lock_cmp, field_recs, neg_ok);
        `ifdef UNIT_SFU
        if (errors == 0 && data_cases > 0) $display("HGI_SFU PASS"); else $display("HGI_SFU FAIL errors=%0d", errors);
`else
        if (errors == 0 && data_cases > 0) $display("HGI_SU PASS"); else $display("HGI_SU FAIL errors=%0d", errors);
`endif
        $finish;
    end
endmodule

// the adapter under test behind one port set: SU (default) or SFU (+define+UNIT_SFU; MUT_ISTRIDE -> the SFU's MUT_SWAP)
module tb_hgi_vec_adapter #(parameter integer MI = 0, parameter integer ME = 0) (
    input wire clk, rst_n, hgi_en, rec_v, output wire rec_rdy, input wire [127:0] rec_hdr, input wire [255:0] rec_sut,
    input wire [255:0] rec_a, rec_b, rec_c, rec_d, rec_o, rec_r, rec_i, input wire [20:0] rec_n_a,
    output wire rec_done, rec_fault, halted, input wire lg_v, output wire lg_rdy, input wire [669:0] lg_w,
    output wire op_v, input wire op_rdy, output wire [669:0] op_w, input wire su_idle, su_fault);
`ifdef UNIT_SFU
    ot_hgi_sfu_record #(.MUT_SWAP(MI)) u (.clk(clk), .rst_n(rst_n), .hgi_en(hgi_en), .rec_v(rec_v), .rec_rdy(rec_rdy),
        .rec_hdr(rec_hdr), .rec_a(rec_a), .rec_b(rec_b), .rec_c(rec_c), .rec_o(rec_o), .rec_n_a(rec_n_a),
        .rec_done(rec_done), .rec_fault(rec_fault), .halted(halted), .lg_v(lg_v), .lg_rdy(lg_rdy), .lg_w(lg_w),
        .op_v(op_v), .op_rdy(op_rdy), .op_w(op_w), .su_idle(su_idle), .su_fault(su_fault));
`else
    ot_hgi_su_record #(.MUT_ISTRIDE(MI), .MUT_EARLY(ME)) u (.clk(clk), .rst_n(rst_n), .hgi_en(hgi_en), .rec_v(rec_v),
        .rec_rdy(rec_rdy), .rec_hdr(rec_hdr), .rec_sut(rec_sut), .rec_a(rec_a), .rec_b(rec_b), .rec_c(rec_c),
        .rec_d(rec_d), .rec_o(rec_o), .rec_r(rec_r), .rec_i(rec_i), .rec_n_a(rec_n_a), .rec_done(rec_done),
        .rec_fault(rec_fault), .halted(halted), .drained(), .lg_v(lg_v), .lg_rdy(lg_rdy), .lg_w(lg_w), .op_v(op_v),
        .op_rdy(op_rdy), .op_w(op_w), .su_idle(su_idle), .su_fault(su_fault));
`endif
endmodule
