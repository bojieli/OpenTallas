`timescale 1ns/1ps
// TOKSIM-S81B/SMX (2026-10-19): golden + cycle bench of the release softmax share ot_s81_su_sms (the SM share every
// regional service slice dsdv_svc_rs instantiates as u_sms on the S81 p4l-MU die) at PRODUCTION SHAPE.
// One case = one attention softmax of the die's 16 heads (dsrom_su_softmax.py write_case files: s.mem scores, pv.mem P.V
// rows, e_exp.mem / o_exp.mem the CPU golden (hdc_golden_v41 via dsrom_su_softmax.reference), par.mem {nv, lt, scale},
// vec.mem {sink, max, es, den}, rope.mem {cos, sin}).  Golden cases = the 1M token's L0 (T 128) / L3 / L20 / L24 (T 640 =
// window 128 + 512 selected) operands from su_cases_v2_ildr.pkl, asserted against the chain's own checks by prep.
// NH shares (heads g = 0 .. NH-1, stride 16 / NH) each get their own head's rows on their serial row port, exactly the
// row protocol of tb_s81_su_sms (j_st, param rows one a cycle, operand rows one a cycle; SO: 40 cycles of cos / sin after
// its last param row).  SE scores are presented BACK TO BACK (one 16-score row a cycle, the assembler's rate).
// Checked bit-exact: every SE e row (FP32, 16 lanes) and every SO o row (BF16 inverse-RoPE output, the head's half).
// Printed (cycles at the share's pins; cycle 0 = the first score row at the pins), mapped to the DAG nodes with the
// definitions of tools/dsrom_su_softmax.py:
//   SMXT max   = first score row -> root max out (u_smh.mv)           [flat build only: internal probe]
//   SMXT exp   = root max -> last e row at the pins
//   SMXT den   = last e row at the pins -> row sum at the root (u_smh.c_ov & c_ol) [flat build only]
//   SMXT sink  = row sum at the root -> o_den at the pins (exp(sink - max) added, den at the divide engines)
//   SMXT norm  = first P.V row at the pins -> last o row at the pins
//   SMXT se_pin = last score row -> first e row (the published 106);  den_pin = last e row -> o_den (46 + 5 lt)
// Last line "SMX PASS ..." / "SMX FAIL ...".
module tb_toksim_smx;
    parameter integer NH = 16;
    localparam integer GS = 16 / NH;
    reg clk = 0, rst = 0;
    always #1 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    reg [8191:0] smem [0:39]; reg [8191:0] pvmem [0:31]; reg [8191:0] emem [0:39]; reg [4095:0] omem [0:31];
    reg [31:0] par [0:2]; reg [511:0] vec [0:3]; reg [1023:0] rope [0:1];
    reg [8*256-1:0] cdir;

    reg q_st = 0; reg [3:0] q_kind = 0; reg [7:0] q_jid = 0; reg r_v = 0, r_p = 0; reg [2:0] r_j = 0;
    reg [511:0] r_d [0:NH-1];
    wire [NH-1:0] w_v, q_fu, q_fo, q_al, q_den; wire [14*NH-1:0] w_a; wire [16*NH-1:0] w_m; wire [512*NH-1:0] w_d;
    wire [NH-1:0] p_mv, p_sum;
    genvar h;
    generate for (h = 0; h < NH; h = h + 1) begin : g_q
        ot_s81_su_sms u_sms (
            .clk(clk), .rst_in(rst), .cfg_g(4'(GS * h)), .j_st(q_st), .j_kind(q_kind), .j_jid(q_jid),
            .r_v(r_v), .r_p(r_p), .r_j(r_j), .r_d(r_d[h]),
            .w_v(w_v[h]), .w_a(w_a[14 * h +: 14]), .w_m(w_m[16 * h +: 16]), .w_d(w_d[512 * h +: 512]),
            .o_fu(q_fu[h]), .o_fo(q_fo[h]), .o_alive(q_al[h]), .o_den(q_den[h]), .o_rjid());
`ifndef SU_SMU_T
        assign p_mv[h] = u_sms.u_smh.mv;
        assign p_sum[h] = u_sms.u_smh.c_ov && u_sms.u_smh.c_ol;
`else
        assign p_mv[h] = 1'b0; assign p_sum[h] = 1'b0;
`endif
    end endgenerate

    // ------------------------------------------------------------------ logs (head 0 times; all heads checked lockstep)
    integer err = 0, nchk = 0, phase = 0;               // phase 4 = SE, 5 = SO
    integer ecnt [0:NH-1]; integer ocnt [0:NH-1];
    integer t_s0 = -1, t_sl = -1, t_mv = -1, t_e0 = -1, t_el = -1, t_sum = -1, t_den = -1, t_p0 = -1, t_o0 = -1, t_ol = -1;
    reg pmv = 0, psum = 0, pden = 0;
    integer k, i, nv, lt;
    reg [511:0] want; reg [255:0] wo;
    always @(posedge clk) if (rst) begin
        if (p_mv[0] && !pmv && phase == 4 && t_mv < 0) t_mv = cyc;
        if (p_sum[0] && !psum && phase == 4 && t_sum < 0) t_sum = cyc;
        if (q_den[0] && !pden && phase == 4 && t_den < 0) t_den = cyc;
        pmv <= p_mv[0]; psum <= p_sum[0]; pden <= q_den[0];
        if (w_v != 0 && w_v != {NH{1'b1}}) begin err = err + 1; $display("SMX MISMATCH heads not lockstep w_v=%b", w_v); end
        for (k = 0; k < NH; k = k + 1) if (w_v[k]) begin
            nchk = nchk + 1;
            if (phase == 4) begin
                want = emem[ecnt[k]][512 * (GS * k) +: 512];
                if (w_m[16 * k +: 16] != 16'hFFFF || w_d[512 * k +: 512] != want) begin
                    if (err < 12) $display("SMX MISMATCH e head %0d row %0d got %h want %h", GS * k, ecnt[k], w_d[512 * k +: 512], want);
                    err = err + 1;
                end
                if (k == 0) begin if (ecnt[0] == 0) t_e0 = cyc; t_el = cyc; end
                ecnt[k] = ecnt[k] + 1;
            end else begin
                wo = omem[ocnt[k]][256 * (GS * k) +: 256];
                if (w_m[16 * k +: 16] != (((GS * k) % 2) ? 16'hFF00 : 16'h00FF) ||
                    w_d[512 * k + 256 * ((GS * k) % 2) +: 256] != wo) begin
                    if (err < 12) $display("SMX MISMATCH o head %0d row %0d got %h want %h", GS * k, ocnt[k],
                                           w_d[512 * k + 256 * ((GS * k) % 2) +: 256], wo);
                    err = err + 1;
                end
                if (k == 0) begin if (ocnt[0] == 0) t_o0 = cyc; t_ol = cyc; end
                ocnt[k] = ocnt[k] + 1;
            end
        end
    end

    task tick; begin @(posedge clk); #0.1; end endtask
    task allrd(input [511:0] x); integer m; begin for (m = 0; m < NH; m = m + 1) r_d[m] = x; end endtask
    reg [511:0] p0;
    initial begin
        if (!$value$plusargs("case=%s", cdir)) begin $display("SMX FAIL no +case"); $finish; end
        $readmemh({cdir, "/s.mem"}, smem); $readmemh({cdir, "/pv.mem"}, pvmem); $readmemh({cdir, "/e_exp.mem"}, emem);
        $readmemh({cdir, "/o_exp.mem"}, omem); $readmemh({cdir, "/par.mem"}, par); $readmemh({cdir, "/vec.mem"}, vec);
        $readmemh({cdir, "/rope.mem"}, rope);
        nv = par[0]; lt = par[1];
        for (k = 0; k < NH; k = k + 1) begin ecnt[k] = 0; ocnt[k] = 0; r_d[k] = 0; end
        repeat (4) tick; rst = 1; repeat (6) tick;
        // ---------------- SE: 2 parameter rows, nv score rows back to back
        p0 = 0; p0[64 +: 7] = nv; p0[96 +: 32] = par[2]; p0[128 +: 3] = lt;
        phase = 4;
        q_st = 1; q_kind = 4; q_jid = 1; tick; q_st = 0;
        r_v = 1; r_p = 1; r_j = 0; allrd(p0); tick;
        r_j = 1; allrd(vec[0]); tick;                                   // sinks: row1[32 g +: 32]
        r_v = 0; r_p = 0; repeat (2) tick;
        for (i = 0; i < nv; i = i + 1) begin
            r_v = 1; r_p = 0;
            for (k = 0; k < NH; k = k + 1) r_d[k] = smem[i][512 * (GS * k) +: 512];
            if (i == 0) t_s0 = cyc; t_sl = cyc;
            tick;
        end
        r_v = 0; repeat (400) tick;
        // ---------------- SO: 5 parameter rows (fields, cos lo / hi, sin lo / hi), 40 cycles, 32 P.V rows
        phase = 5;
        q_st = 1; q_kind = 5; q_jid = 2; tick; q_st = 0;
        p0 = 0;
        r_v = 1; r_p = 1; r_j = 0; allrd(p0); tick;
        r_j = 1; allrd(rope[0][511:0]); tick; r_j = 2; allrd(rope[0][1023:512]); tick;
        r_j = 3; allrd(rope[1][511:0]); tick; r_j = 4; allrd(rope[1][1023:512]); tick;
        r_v = 0; r_p = 0; repeat (40) tick;
        for (i = 0; i < 32; i = i + 1) begin
            r_v = 1; r_p = 0;
            for (k = 0; k < NH; k = k + 1) r_d[k] = pvmem[i][512 * (GS * k) +: 512];
            if (i == 0) t_p0 = cyc;
            tick;
        end
        r_v = 0; repeat (300) tick;
        for (k = 0; k < NH; k = k + 1) begin
            if (ecnt[k] != nv) begin err = err + 1; $display("SMX MISMATCH head %0d e rows %0d != %0d", GS * k, ecnt[k], nv); end
            if (ocnt[k] != 32) begin err = err + 1; $display("SMX MISMATCH head %0d o rows %0d != 32", GS * k, ocnt[k]); end
        end
        if (q_fu != 0 || q_fo != 0) begin err = err + 1; $display("SMX MISMATCH fault fu=%b fo=%b", q_fu, q_fo); end
        $display("SMX case %0s NH=%0d nv=%0d lt=%0d checks=%0d", cdir, NH, nv, lt, nchk);
        $display("SMXT raw s0=%0d sl=%0d mv=%0d e0=%0d el=%0d sum=%0d den=%0d p0=%0d o0=%0d ol=%0d",
                 t_s0, t_sl, t_mv, t_e0, t_el, t_sum, t_den, t_p0, t_o0, t_ol);
        $display("SMXT max=%0d exp=%0d den=%0d sink=%0d norm=%0d se_pin=%0d den_pin=%0d se_chain=%0d",
                 t_mv - t_s0, t_el - t_mv, t_sum - t_el, t_den - t_sum, t_ol - t_p0, t_e0 - t_sl, t_den - t_el,
                 t_den - t_s0);
        if (err == 0 && nchk == NH * (nv + 32)) $display("SMX PASS NH=%0d nv=%0d checks=%0d", NH, nv, nchk);
        else $display("SMX FAIL NH=%0d nv=%0d errors=%0d checks=%0d", NH, nv, err, nchk);
        $finish;
    end
endmodule
