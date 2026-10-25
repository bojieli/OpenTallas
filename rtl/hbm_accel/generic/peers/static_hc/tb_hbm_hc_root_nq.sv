`timescale 1ns/1ps
// HBM-BIND B2 (2026-10-24): HC root NQ bench. DUT = the edited ot_hbm_hc_root_static #(NQ); REF = the unchanged base
// ot_hbm_hc_root_static (4 quarters, TPRE 6; run_hc_root_nq.sh renames it *_ref). Both roots run the SAME static
// programme (tools/rtl_hbm_hc_eng_static_gate.py --split, full mode, the die parameters QDRLY 2 QCHX 11) and the same
// bases / scales table, installed through their F20 programme / table pins on the same edges.
// Partial-sum engines are bench models: quarter q of task n (n = the n-th descriptor the root issued; ss tasks
// positive) produces the binary32 subtree sum s_q(n) (hash of n, q) on its output at a fixed edge after the root's
// descriptor out flop.
//   NQ 4 (default proof): REF and DUT get the same 4 quarter sums on the same edges (XRU 0 both); every root output
//        (qd_*, qi_*, result_v / result_position / result, configured, program_active / done, fault) and every mix
//        (u_core o_valid / o_data) must be equal bit for bit on every edge.
//   NQ 2 (B2 2-half form, TPRE 7): REF (4 quarters, XRU 4) gets s_0 .. s_3 through 4 relay stages; DUT half h gets
//        h_h = s_{2h} + s_{2h+1} from ot_hdc_fp32_add_lat #(LAT TLA = 7) (the half engine's 7th tree level, the qeng
//        tree adder; XRU 0). The DUT's sums are then due TLA - 3 = 4 edges later than the REF's own XRU 0 timing,
//        which REF's XRU 4 matches, so ONE programme serves both: every mix (o_valid / o_data / o_pos / o_idx),
//        program_active / done / fault, and the results (DUT slot h == REF quarter 2 + h, the NW / NE clients) must be
//        equal on every edge; DUT descriptor == REF descriptor with qd_nv[h] == REF nv[2h] + nv[2h + 1]; DUT ingest
//        event slot h == REF quarter 2h or 2h + 1 (the DUT programme is the REF programme with ingq >> 1 and qmask 0x3).
// Bench mutants MUTB (must FAIL): 1 = half pairing (s0 + s2), (s1 + s3) (NQ 2) / quarter 1 sum bit 0 flipped (NQ 4);
// 2 = DUT sums one edge late; 3 = DUT programme NOT remapped (slot 2 / 3 events: the root's slot fault). DUT MUT 2 =
// tail pre-sigmoid eps dropped.
module tb_hbm_hc_root_nq;
    parameter integer NQ = 4, MUT = 0, MUTB = 0;
    localparam integer TLA = 7, XRU_R = (NQ == 2) ? 4 : 0, NVQ = (NQ == 2) ? 8 : 7, QWW = (NQ == 2) ? 6 : 5;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    integer nwords = 0, npos = 1, nemit = 0, i, rc;
    reg [255:0] prog_r [0:1023]; reg [255:0] prog_d [0:1023]; reg [255:0] tbl [0:15];
    reg cfg_v = 0, desc_v = 0, launch_v = 0; reg [7:0] cfg_target = 0; reg [11:0] cfg_addr = 0, desc_base = 0;
    reg [255:0] cfg_r = 0, cfg_d = 0; reg [12:0] desc_limit = 0; reg [15:0] desc_loops = 0;
    // ---------------------------------------------------------------- REF (base, 4 quarters)
    wire r_conf, r_pa, r_pd, r_fault;
    wire [3:0] r_qd_v, r_qd_ss, r_qi_v, r_qi_kind, r_result_v; wire [27:0] r_qd_nv; wire [39:0] r_qd_wa, r_qd_xa, r_qi_word;
    wire [7:0] r_qi_slot; wire [19:0] r_qi_lo, r_qi_w; wire [47:0] r_qi_cnt; wire [11:0] r_result_position;
    wire [3071:0] r_result;
    reg [3:0] r_psv = 0; reg [127:0] r_ps = 0;
    ot_hbm_hc_root_static_ref #(.QDRLY(2), .QCHX(11), .XRU(XRU_R)) ref4 (.clk(clk), .rst_n(rst_n), .tgt(8'd164),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_r), .desc_v(desc_v),
        .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .configured(r_conf),
        .qd_v(r_qd_v), .qd_ss(r_qd_ss), .qd_nv(r_qd_nv), .qd_wa(r_qd_wa), .qd_xa(r_qd_xa), .qi_v(r_qi_v),
        .qi_kind(r_qi_kind), .qi_slot(r_qi_slot), .qi_lo(r_qi_lo), .qi_w(r_qi_w), .qi_cnt(r_qi_cnt), .qi_word(r_qi_word),
        .qps_v(r_psv), .qps(r_ps), .qps_f(4'd0), .q_fault(4'd0), .gathered_mix_v(4'd0), .gathered_mix_row(20'd0),
        .gathered_mix_pos(12'd0), .gathered_mix_data(128'd0), .result_v(r_result_v), .result_position(r_result_position),
        .result(r_result), .program_active(r_pa), .program_done(r_pd), .fault(r_fault));
    // ---------------------------------------------------------------- DUT (NQ slots)
    wire d_conf, d_pa, d_pd, d_fault;
    wire [NQ-1:0] d_qd_v, d_qd_ss, d_qi_v, d_qi_kind, d_result_v; wire [NQ*NVQ-1:0] d_qd_nv;
    wire [NQ*10-1:0] d_qd_wa, d_qd_xa, d_qi_word; wire [NQ*2-1:0] d_qi_slot; wire [NQ*5-1:0] d_qi_lo;
    wire [NQ*QWW-1:0] d_qi_w; wire [NQ*12-1:0] d_qi_cnt; wire [NQ*3-1:0] d_result_position; wire [NQ*768-1:0] d_result;
    wire [NQ-1:0] d_psv; wire [NQ*32-1:0] d_ps;
    ot_hbm_hc_root_static #(.QDRLY(2), .QCHX(11), .NQ(NQ), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .tgt(8'd164),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_d), .desc_v(desc_v),
        .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .configured(d_conf),
        .qd_v(d_qd_v), .qd_ss(d_qd_ss), .qd_nv(d_qd_nv), .qd_wa(d_qd_wa), .qd_xa(d_qd_xa), .qi_v(d_qi_v),
        .qi_kind(d_qi_kind), .qi_slot(d_qi_slot), .qi_lo(d_qi_lo), .qi_w(d_qi_w), .qi_cnt(d_qi_cnt), .qi_word(d_qi_word),
        .qps_v(d_psv), .qps(d_ps), .qps_f({NQ{1'b0}}), .q_fault({NQ{1'b0}}), .gathered_mix_v({NQ{1'b0}}),
        .gathered_mix_row({NQ*5{1'b0}}), .gathered_mix_pos({NQ*3{1'b0}}), .gathered_mix_data({NQ*32{1'b0}}),
        .result_v(d_result_v), .result_position(d_result_position), .result(d_result), .program_active(d_pa),
        .program_done(d_pd), .fault(d_fault));
    // ---------------------------------------------------------------- partial-sum engine models
    // quarter outputs are produced QOUT edges after the REF descriptor out flop; REF gets them through XRU_R relays,
    // DUT (NQ 4) directly, DUT (NQ 2) through the TLA-stage half adder. QOUT = REF SYS_LAT - 2 - XRU_R.
    // REF SYS_LAT = SYS_LAT0 (100 at QDRLY 2 QCHX 11) + 4 + XRD + XRU + 6 TLA = 146 + XRU_R; DUT (NQ 2) 100 + 4 + 7 TLA = 153
    localparam integer REF_SYS_LAT = 146 + XRU_R, DUT_SYS_LAT = (NQ == 2) ? 153 : 146;
    localparam integer QOUT = REF_SYS_LAT - 2 - XRU_R;
    function automatic [31:0] sval(input integer n, input integer q, input bit ss);
        reg [31:0] h;
        h = 32'(n) * 32'h9E3779B1 ^ (32'(q) * 32'h85EBCA77) ^ 32'h2545F491;
        h = h ^ (h >> 15); h = h * 32'h2C1B3C6D; h = h ^ (h >> 12); h = h * 32'h297A2D39; h = h ^ (h >> 15);
        sval = {ss ? 1'b0 : h[31], 8'(8'd121 + 8'(h[27:24])), h[22:0]};
    endfunction
    reg [QOUT:0] dv_line = 0; reg [QOUT:0] ss_line = 0; integer n_line [0:QOUT]; integer ntask = 0;
    always @(posedge clk) begin
        for (integer j = QOUT; j > 0; j = j - 1) begin dv_line[j] <= dv_line[j-1]; ss_line[j] <= ss_line[j-1]; n_line[j] <= n_line[j-1]; end
        dv_line[0] <= r_qd_v[0]; ss_line[0] <= r_qd_ss[0]; n_line[0] <= ntask;
        if (r_qd_v[0]) ntask <= ntask + 1;
    end
    wire qo_v = dv_line[QOUT-1]; wire qo_ss = ss_line[QOUT-1]; wire [31:0] qo_n = n_line[QOUT-1];
    wire [127:0] qo_s;
    for (genvar q = 0; q < 4; q = q + 1) begin : g_s
        assign qo_s[q*32 +: 32] = sval(qo_n, q, qo_ss);
    end
    // REF: XRU_R relay stages
    reg [3:0] rl_v [0:7]; reg [127:0] rl_s [0:7];
    always @(posedge clk) begin
        rl_v[0] <= {4{qo_v}}; rl_s[0] <= qo_s;
        for (integer j = 1; j < 8; j = j + 1) begin rl_v[j] <= rl_v[j-1]; rl_s[j] <= rl_s[j-1]; end
    end
    always @* begin
        if (XRU_R == 0) begin r_psv = {4{qo_v}}; r_ps = qo_s; end
        else begin r_psv = rl_v[XRU_R-1]; r_ps = rl_s[XRU_R-1]; end
    end
    // DUT
    wire [NQ-1:0] dm_v; wire [NQ*32-1:0] dm_s;
    if (NQ == 4) begin : g_d4
        assign dm_v = {4{qo_v}}; assign dm_s = qo_s ^ ((MUTB == 1) ? {96'd0, 32'd1, 32'd0} : 128'd0);
    end else begin : g_d2
        for (genvar h = 0; h < 2; h = h + 1) begin : g_h
            wire [31:0] a = qo_s[((MUTB == 1) ? h : 2 * h) * 32 +: 32];
            wire [31:0] b = qo_s[((MUTB == 1) ? h + 2 : 2 * h + 1) * 32 +: 32];
            wire vo; wire [1:0] er;
            ot_hdc_fp32_add_lat #(.LAT(TLA), .DRST(0)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(qo_v), .a(a), .b(b),
                .y(dm_s[h*32 +: 32]), .err(er), .valid_out(vo));
            assign dm_v[h] = vo;
        end
    end
    reg [NQ-1:0] late_v = 0; reg [NQ*32-1:0] late_s = 0;
    always @(posedge clk) begin late_v <= dm_v; late_s <= dm_s; end
    assign d_psv = (MUTB == 2) ? late_v : dm_v;
    assign d_ps = (MUTB == 2) ? late_s : dm_s;
    // ---------------------------------------------------------------- lockstep checks
    integer cyc = 0, err = 0, nchk = 0, nmix = 0, nres = 0, nqi = 0, nqd = 0;
    task automatic bad(input string what); err = err + 1; if (err < 12) $display("ERR cyc=%0d %s", cyc, what); endtask
    always @(negedge clk) if (rst_n) begin
        cyc = cyc + 1;
        nchk = nchk + 6;
        if (d_conf !== r_conf) bad("configured");
        if (d_pa !== r_pa) bad("program_active");
        if (d_pd !== r_pd) bad("program_done");
        if (d_fault !== r_fault) bad($sformatf("fault dut=%b ref=%b (dut ev=%b ps=%b core=%b tail=%b)", d_fault, r_fault,
            dut.ev_fault, dut.ps_fault, dut.core_fault, dut.tail_fault));
        if (dut.o_valid !== ref4.o_valid || (ref4.o_valid && (dut.o_data !== ref4.o_data || dut.o_pos !== ref4.o_pos ||
            dut.o_idx !== ref4.o_idx))) bad($sformatf("mix dut=%b/%08x ref=%b/%08x", dut.o_valid, dut.o_data, ref4.o_valid, ref4.o_data));
        if (ref4.o_valid) nmix = nmix + 1;
        if (dut.u_core.raw_wv !== ref4.u_core.raw_wv || (ref4.u_core.raw_wv && dut.u_core.raw_w !== ref4.u_core.raw_w))
            bad("raw accumulation");
        if (NQ == 4) begin
            if ({d_qd_v, d_qd_ss, d_qd_nv, d_qd_wa, d_qd_xa} !== {r_qd_v, r_qd_ss, r_qd_nv, r_qd_wa, r_qd_xa}) bad("qd");
            if ({d_qi_v, d_qi_kind, d_qi_slot, d_qi_lo, d_qi_w, d_qi_cnt, d_qi_word} !==
                {r_qi_v, r_qi_kind, r_qi_slot, r_qi_lo, r_qi_w, r_qi_cnt, r_qi_word}) bad("qi");
            if ({d_result_v, d_result_position, d_result} !== {r_result_v, r_result_position, r_result}) bad("result");
            if (|r_qi_v) nqi = nqi + 1; if (|r_qd_v) nqd = nqd + 1; if (|r_result_v) nres = nres + 1;
        end else begin
            for (integer h = 0; h < NQ; h = h + 1) begin
                nchk = nchk + 3;
                if (d_qd_v[h] !== r_qd_v[0]) bad("qd_v");
                if (r_qd_v[0] && ({d_qd_ss[h], d_qd_wa[h*10 +: 10], d_qd_xa[h*10 +: 10]} !==
                    {r_qd_ss[2*h], r_qd_wa[2*h*10 +: 10], r_qd_xa[2*h*10 +: 10]} ||
                    d_qd_nv[h*8 +: 8] !== 8'(r_qd_nv[2*h*7 +: 7]) + 8'(r_qd_nv[(2*h+1)*7 +: 7]))) bad("qd fields");
                if (d_qi_v[h] !== (r_qi_v[2*h] | r_qi_v[2*h+1])) bad("qi_v");
                if (d_qi_v[h]) begin : qi
                    integer s; s = r_qi_v[2*h] ? 2*h : 2*h+1;
                    if ({d_qi_kind[h], d_qi_slot[h*2 +: 2], d_qi_lo[h*5 +: 5], d_qi_w[h*6 +: 6], d_qi_cnt[h*12 +: 12],
                         d_qi_word[h*10 +: 10]} !== {r_qi_kind[s], r_qi_slot[s*2 +: 2], r_qi_lo[s*5 +: 5], 6'(r_qi_w[s*5 +: 5]),
                         r_qi_cnt[s*12 +: 12], r_qi_word[s*10 +: 10]}) bad("qi fields");
                end
                if (d_result_v[h] !== r_result_v[2+h]) bad("result_v");
                if (r_result_v[2+h] && ({d_result_position[h*3 +: 3], d_result[h*768 +: 768]} !==
                    {r_result_position[(2+h)*3 +: 3], r_result[(2+h)*768 +: 768]})) bad("result");
            end
            if (|r_qi_v) nqi = nqi + 1; if (r_qd_v[0]) nqd = nqd + 1; if (|r_result_v[3:2]) nres = nres + 1;
        end
        if (cyc > 40000) $fatal(1, "watchdog");
    end
    // ---------------------------------------------------------------- install + run (as tb_hbm_hc_eng4_static)
    wire busy = ref4.u_seq.busy;
    initial begin
        if (!$value$plusargs("NWORDS=%d", nwords)) $fatal(1, "NWORDS");
        rc = $value$plusargs("NPOS=%d", npos); rc = $value$plusargs("NEMIT=%d", nemit);
        $readmemh("prog.mem", prog_r); $readmemh("prog_dut.mem", prog_d); $readmemh("tbl.mem", tbl);
        repeat (5) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
        for (i = 0; i < 12; i = i + 1) begin
            @(posedge clk); #0.5 cfg_v = 1; cfg_target = 8'd165; cfg_addr = 12'(i);
            cfg_r = {16'hc7a1, 4'd0, 12'(i), tbl[i][223:0]}; cfg_d = cfg_r;
        end
        for (i = 0; i < nwords; i = i + 1) begin
            @(posedge clk); #0.5 cfg_v = 1; cfg_target = 8'd164; cfg_addr = 12'(i); cfg_r = prog_r[i]; cfg_d = prog_d[i];
        end
        @(posedge clk); #0.5 cfg_v = 0;
        repeat (4) @(posedge clk); #0.5 desc_v = 1; cfg_target = 8'd164; desc_base = 0; desc_limit = 13'(nwords);
        desc_loops = 16'd1;
        @(posedge clk); #0.5 desc_v = 0;
        for (i = 0; i < nwords + 16 && !r_conf; i = i + 1) @(posedge clk);
        if (!r_conf) $fatal(1, "HC programme target not configured");
        @(posedge clk); #0.5 launch_v = 1; @(posedge clk); #0.5 launch_v = 0;
        wait (busy);
        wait (!busy);
        repeat (40) @(posedge clk);
        if (r_fault) begin err = err + 1; $display("ERR REF root faulted (bench / programme timing)"); end
        if (nmix != 24 * npos) begin err = err + 1; $display("ERR mixes %0d != %0d", nmix, 24 * npos); end
        if (nres != npos) begin err = err + 1; $display("ERR result emits %0d != %0d", nres, npos); end
        $display("HC_ROOT_NQ%0d %s checks=%0d errors=%0d tasks=%0d mixes=%0d emits=%0d ingest_edges=%0d desc_edges=%0d QOUT=%0d REF_SYS_LAT=%0d DUT_SYS_LAT=%0d MUT=%0d MUTB=%0d",
            NQ, err == 0 ? "PASS" : "FAIL", nchk, err, ntask, nmix, nres, nqi, nqd, QOUT, REF_SYS_LAT, DUT_SYS_LAT, MUT, MUTB);
        $finish;
    end
endmodule
