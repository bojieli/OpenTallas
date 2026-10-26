`timescale 1ns/1ps
// HBM-B-RTL2 2026-10-17: LOCKSTEP bench of the plan (b) split HC engine = ot_hbm_hc_root_static + 4 x
// ot_hbm_hc_qeng_static (quarter q = lanes 64q..64q+63 of every run), on the SAME golden vectors / programme form as
// tb_hbm_hc_eng_static (the single-block engine, below): tools/rtl_hbm_hc_eng_static_gate.py --split.  Quarter q's
// wave m of a schedule entry (q T count kind unit0 word0) is quarter-local wave lw = m % 20 of unit unit0 + m / 20
// (row or position) = global wave unit*80 + 8 (lw/2) + 2q + lw%2 of the full engine's layout.  Every mix and every
// result word must equal the golden (identical values to the single block), at the documented shifted times.
// Original header (tb_hbm_hc_eng_static):
// H-NETLIST/hceng 2026-10-16: bench of the die master ot_hbm_hc_eng_static (full-form HC.HC_MIX, W 256, K 20,480).
// Vectors and the static event programme come from tools/rtl_hbm_hc_eng_static_gate.py (golden hdc_golden_v41 chunk8
// mixes + the codex tail reference). The programme is installed through the engine's programme pins, the bases /
// scales table through its table pins; the four quadrant clients are modelled as wave sources that present wave n of
// a schedule entry on x_wave in cycle t == T + 4n (t = the engine programme's edge counter), exactly the hc_<q> reader
// cadence (one 32-sector wave every 4 edges). Checks: every projection mix (o_valid) and every result pin word
// against the golden; any engine fault is fatal. Prints the measured event times.
// 0600: the programme and the table are installed through the engine's folded F20 targets (strap tgt = 164: programme
// 164, table 165; F20 cfg rows, descriptor, launch); the x_wave link is XW_BEATS (default 4): beat b of wave n sits on
// the pins at t == T + 4n - 3 + b (the whole wave at T + 4n in the XW_BEATS=1 form). Sources are driven at negedge
// from the programme edge counter t (equivalent to a combinational function of t, no array sensitivity).
module tb_hbm_hc_eng4_static;
    localparam integer K = 20480;
    reg clk = 0; always #1 clk = ~clk;
    reg rst_n = 0;
    integer nwords = 0, nsched = 0, ngm = 0, npos = 1, nemit = 0, tb0 = 0, mode = 0, mutant = 0;
    reg [255:0] prog [0:1023]; reg [255:0] tbl [0:15];
    reg [31:0] wmem [0:24*K-1]; reg [31:0] xmem [0:8*K-1]; reg [31:0] expmix [0:8*24-1]; reg [31:0] exptail [0:8*24-1];
    integer sq [0:63], sT [0:63], scnt [0:63], skind [0:63], ssrc [0:63], sword [0:63];
    integer gq [0:63], gT [0:63], gpos [0:63], grow [0:63]; reg [31:0] gdat [0:63];
    integer fd, rc, i, n;
`ifdef XWB
    localparam integer XWB = `XWB;
`else
    localparam integer XWB = 4;
`endif
    localparam integer BW = 8192 / XWB;
    reg cfg_v = 0, desc_v = 0, launch_v = 0; reg [7:0] cfg_target = 0; reg [11:0] cfg_addr = 0, desc_base = 0;
    reg [255:0] cfg_data = 0; reg [12:0] desc_limit = 0; reg [15:0] desc_loops = 0; wire configured;
    reg [3:0] x_wave_v = 0; reg [39:0] x_wave_word = 0; reg [4*BW-1:0] x_wave = 0; reg [7:0] x_wave_beat = 0;
    reg [3:0] gm_v = 0; reg [19:0] gm_row = 0; reg [11:0] gm_pos = 0; reg [127:0] gm_data = 0;
    wire [3:0] result_v; wire [11:0] result_position; wire [3071:0] result; wire pa, pd, fault;
`ifdef MUT
    localparam integer MUTP = `MUT;
`else
    localparam integer MUTP = 0;
`endif
    // HBM-RTL5 10-18: d4g U-ring form (+define+HC_DRLY=2 +define+HC_XRLY=1 +define+HC_QDRLY=2); defaults = ring form
`ifndef HC_DRLY
`define HC_DRLY 1
`endif
`ifndef HC_XRLY
`define HC_XRLY 0
`endif
`ifndef HC_QDRLY
`define HC_QDRLY `HC_DRLY
`endif
    // HH-9 10-19: +define+HC_CPR=1 = bank chain pin registers (qeng CPR, root QCHX 11; programme RAW0 + 11)
`ifndef HC_CPR
`define HC_CPR 0
`endif
    wire [3:0] qd_v, qd_ss, qi_v, qi_kind, qps_v, qps_f, q_fault; wire [27:0] qd_nv; wire [39:0] qd_wa, qd_xa, qi_word;
    wire [7:0] qi_slot; wire [19:0] qi_lo, qi_w; wire [47:0] qi_cnt; wire [127:0] qps;
    ot_hbm_hc_root_static #(.XRD(10),.XRU(10),.MUT(MUTP), .QDRLY(`HC_QDRLY), .QCHX(11 * `HC_CPR)) dut (.clk(clk), .rst_n(rst_n), .tgt(8'd164), .cfg_v(cfg_v),
        .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base),
        .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .configured(configured),
        .qd_v(qd_v), .qd_ss(qd_ss), .qd_nv(qd_nv), .qd_wa(qd_wa), .qd_xa(qd_xa), .qi_v(qi_v), .qi_kind(qi_kind),
        .qi_slot(qi_slot), .qi_lo(qi_lo), .qi_w(qi_w), .qi_cnt(qi_cnt), .qi_word(qi_word), .qps_v(xru_qps_v), .qps(xru_qps),
        .qps_f(xru_qps_f), .q_fault(xru_q_fault),
        .gathered_mix_v(gm_v), .gathered_mix_row(gm_row), .gathered_mix_pos(gm_pos), .gathered_mix_data(gm_data),
        .result_v(result_v), .result_position(result_position), .result(result),
        .program_active(pa), .program_done(pd), .fault(fault));
    genvar gqi;
    for (gqi = 0; gqi < 4; gqi = gqi + 1) begin : g_q
        ot_hbm_hc_qeng_static #(.MUT((MUTP == 2) ? 0 : (gqi == 0 || MUTP == 3) ? MUTP : 0), .XW_BEATS(XWB), .DRLY(`HC_DRLY), .XRLY(`HC_XRLY), .CPR(`HC_CPR)) u_q (
            .clk(clk), .rst_n(rst_n),
            .d_v(xrd_qd_v[gqi]), .d_ss(xrd_qd_ss[gqi]), .d_nv(xrd_qd_nv[gqi*7 +: 7]), .d_wa(xrd_qd_wa[gqi*10 +: 10]), .d_xa(xrd_qd_xa[gqi*10 +: 10]),
            .i_v(xrd_qi_v[gqi]), .i_kind(xrd_qi_kind[gqi]), .i_slot(xrd_qi_slot[gqi*2 +: 2]), .i_lo(xrd_qi_lo[gqi*5 +: 5]),
            .i_w(xrd_qi_w[gqi*5 +: 5]), .i_cnt(xrd_qi_cnt[gqi*12 +: 12]), .i_word(xrd_qi_word[gqi*10 +: 10]),
            .x_wave_v(x_wave_v[gqi]), .x_wave_beat(x_wave_beat[gqi*2 +: 2]), .x_wave_word(x_wave_word[gqi*10 +: 10]),
            .x_wave(x_wave[gqi*BW +: BW]), .ps_v(qps_v[gqi]), .ps(qps[gqi*32 +: 32]), .ps_f(qps_f[gqi]), .fault(q_fault[gqi]));
    end
wire [3:0] xrd_qd_v;
wire [3:0] xrd_qd_ss;
wire [27:0] xrd_qd_nv;
wire [39:0] xrd_qd_wa;
wire [39:0] xrd_qd_xa;
wire [3:0] xrd_qi_v;
wire [3:0] xrd_qi_kind;
wire [7:0] xrd_qi_slot;
wire [19:0] xrd_qi_lo;
wire [19:0] xrd_qi_w;
wire [47:0] xrd_qi_cnt;
wire [39:0] xrd_qi_word;
wire [3:0] xru_qps_v;
wire [127:0] xru_qps;
wire [3:0] xru_qps_f;
wire [3:0] xru_q_fault;
ot_codex_hc_r8_pad #(.W(260),.D(10)) xrd(clk,rst_n,{qd_v,qd_ss,qd_nv,qd_wa,qd_xa,qi_v,qi_kind,qi_slot,qi_lo,qi_w,qi_cnt,qi_word},{xrd_qd_v,xrd_qd_ss,xrd_qd_nv,xrd_qd_wa,xrd_qd_xa,xrd_qi_v,xrd_qi_kind,xrd_qi_slot,xrd_qi_lo,xrd_qi_w,xrd_qi_cnt,xrd_qi_word});
ot_codex_hc_r8_pad #(.W(140),.D(10)) xru(clk,rst_n,{qps_v,qps,qps_f,q_fault},{xru_qps_v,xru_qps,xru_qps_f,xru_q_fault});
    wire busy = dut.u_seq.busy;
    wire [19:0] t = dut.u_seq.t;
    // ---- quadrant wave sources and gathered-mix words (functions of the programme edge counter t)
    always @(negedge clk) begin
        x_wave_v <= 0; x_wave_beat <= 0; gm_v <= 0;
        if (busy) begin
            for (integer s = 0; s < nsched; s = s + 1)
                if (t + 3 >= sT[s] && (t + 3 - sT[s]) / 4 < scnt[s] && (XWB == 4 || (t - sT[s]) % 4 == 0)) begin : src
                    integer m, q, b, w0;
                    q = sq[s]; m = (t + 3 - sT[s]) / 4; b = (XWB == 4) ? (t + 3 - sT[s]) % 4 : 0;
                    x_wave_v[q] <= 1'b1;
                    x_wave_beat[q*2 +: 2] <= 2'(b);
                    x_wave_word[q*10 +: 10] <= 10'(sword[s] + m);
                    begin : gw
                        integer lw, un;
                        lw = m % 20; un = ssrc[s] + m / 20;
                        w0 = (un * 80 + 8 * (lw / 2) + 2 * q + lw % 2) * 256 + b * (BW / 32);
                    end
                    for (integer l = 0; l < BW / 32; l = l + 1)
                        x_wave[q*BW + l*32 +: 32] <= skind[s] ? wmem[w0 + l] : xmem[w0 + l];
                end
            for (integer g = 0; g < ngm; g = g + 1)
                if (t == gT[g]) begin
                    gm_v[gq[g]] <= 1'b1; gm_row[gq[g]*5 +: 5] <= 5'(grow[g]); gm_pos[gq[g]*3 +: 3] <= 3'(gpos[g]);
                    gm_data[gq[g]*32 +: 32] <= gdat[g];
                end
        end
    end
    // ---- checks
    integer mixseen = 0, mixbad = 0, outseen = 0, outbad = 0, cyc = 0, last_out_t = 0, first_out_t = -1;
    integer last_mix_t = 0;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n && fault) begin
            $display("HC_ENG_FAULT t=%0d seq=%0d ev=%0d ps=%0d qf=%b core=%0d mix=%0d tbl=%0d tail=%0d tfl=%0d", t,
                dut.seq_fault, dut.ev_fault, dut.ps_fault, dut.qf_q, dut.core_fault, dut.mix_fault, dut.tbl_fault,
                dut.tail_fault, dut.tfl);
            $fatal(1, "engine fault");
        end
        if (mode == 1 && dut.u_core.raw_wv) $display("PROBE raw t=%0d ss=%0d pos=%0d idx=%0d", t,
            dut.u_core.raw_w[40], dut.u_core.raw_w[32 + 5 +: 3], dut.u_core.raw_w[32 +: 5]);
        if (dut.o_valid) begin
            mixseen = mixseen + 1; last_mix_t = t;
            if (dut.o_data !== expmix[dut.o_pos*24 + dut.o_idx]) begin
                mixbad = mixbad + 1;
                if (mixbad < 6) $display("MIX_MISMATCH pos%0d row%0d got=%08x exp=%08x", dut.o_pos, dut.o_idx,
                    dut.o_data, expmix[dut.o_pos*24 + dut.o_idx]);
            end
        end
        for (integer q = 0; q < 4; q = q + 1) if (result_v[q]) begin : chk
            integer p; p = result_position[q*3 +: 3];
            outseen = outseen + 1; last_out_t = t; if (first_out_t < 0) first_out_t = t;
            for (integer j = 0; j < 24; j = j + 1) if (result[q*768 + j*32 +: 32] !== exptail[p*24 + j]) begin
                outbad = outbad + 1;
                if (outbad < 6) $display("TAIL_MISMATCH q%0d pos%0d word%0d got=%08x exp=%08x", q, p, j,
                    result[q*768 + j*32 +: 32], exptail[p*24 + j]);
            end
        end
        if (cyc > 40000) $fatal(1, "watchdog");
    end
    initial begin
        if (!$value$plusargs("NWORDS=%d", nwords)) $fatal(1, "NWORDS");
        rc = $value$plusargs("NSCHED=%d", nsched); rc = $value$plusargs("NGM=%d", ngm);
        rc = $value$plusargs("NPOS=%d", npos); rc = $value$plusargs("NEMIT=%d", nemit);
        rc = $value$plusargs("TB=%d", tb0); rc = $value$plusargs("MODE=%d", mode);
        $readmemh("prog.mem", prog); $readmemh("tbl.mem", tbl);
        $readmemh("wmem.mem", wmem); $readmemh("xmem.mem", xmem);
        $readmemh("expmix.mem", expmix); $readmemh("exptail.mem", exptail);
        fd = $fopen("sched.txt", "r");
        for (i = 0; i < nsched; i = i + 1) rc = $fscanf(fd, "%d %d %d %d %d %d\n", sq[i], sT[i], scnt[i], skind[i], ssrc[i], sword[i]);
        $fclose(fd);
        fd = $fopen("gm.txt", "r");
        for (i = 0; i < ngm; i = i + 1) rc = $fscanf(fd, "%d %d %d %d %d\n", gq[i], gT[i], gpos[i], grow[i], gdat[i]);
        $fclose(fd);
        repeat (5) @(posedge clk); rst_n = 1; repeat (3) @(posedge clk);
        // table rows -> target 165 (F20 header {c7a1, row}), programme rows -> target 164 (header written by the tool)
        for (i = 0; i < 12; i = i + 1) begin
            @(posedge clk); #0.5 cfg_v = 1; cfg_target = 8'd165; cfg_addr = 12'(i);
            cfg_data = {16'hc7a1, 4'd0, 12'(i), tbl[i][223:0]};
        end
        for (i = 0; i < nwords; i = i + 1) begin
            @(posedge clk); #0.5 cfg_v = 1; cfg_target = 8'd164; cfg_addr = 12'(i); cfg_data = prog[i];
        end
        @(posedge clk); #0.5 cfg_v = 0;
        repeat (4) @(posedge clk); #0.5 desc_v = 1; cfg_target = 8'd164; desc_base = 0; desc_limit = 13'(nwords);
        desc_loops = 16'd1;
        @(posedge clk); #0.5 desc_v = 0;
        for (i = 0; i < nwords + 16 && !configured; i = i + 1) @(posedge clk);
        if (!configured) $fatal(1, "HC programme target not configured");
        @(posedge clk); #0.5 launch_v = 1; @(posedge clk); #0.5 launch_v = 0;
        wait (busy);
        wait (!busy);
        repeat (40) @(posedge clk);
        $display("HC_ENG_DONE mode=%0d npos=%0d mixes=%0d mixbad=%0d outs=%0d outbad=%0d TB=%0d last_mix_t=%0d first_out_t=%0d last_out_t=%0d HC_MIX_CYCLES=%0d",
            mode, npos, mixseen, mixbad, outseen, outbad, tb0, last_mix_t, first_out_t, last_out_t, last_out_t - tb0);
        if (mode == 1) $finish;
        if (mixbad || outbad || outseen != nemit || (mode == 0 && mixseen != 24 * npos)) $fatal(1, "HC_ENG FAIL");
        $display("HC_ENG PASS");
        $finish;
    end
endmodule

module ot_codex_hc_r8_pad #(parameter W=1,D=10)(input clk,rst_n,input [W-1:0]a,output [W-1:0]b);reg[W-1:0]q[0:D-1];integer i;always@(posedge clk)if(!rst_n)begin for(i=0;i<D;i=i+1)q[i]<=0;end else begin q[0]<=a;for(i=1;i<D;i=i+1)q[i]<=q[i-1];end assign b=q[D-1];endmodule
