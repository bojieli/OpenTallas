`timescale 1ns/1ps
`define C_CMD(m) cmdv[m][159:128]
`define C_OUT(m) cmdv[m][127:96]
`define C_PB(m) cmdv[m][95:64]
`define C_SB(m) cmdv[m][63:32]
`define C_W(m) cmdv[m][31:16]
`define C_MODE(m) cmdv[m][0]
`ifdef OT_TP8S_QFD
`define C_ISS(m) (`C_CMD(m)-1)
`else
`define C_ISS(m) `C_CMD(m)
`endif
// ---------------------------------------------------------------------------
// qwen-coll-io 2026-10-14: 8-die bench of the STATIC-SCHEDULED TP8 collective rtl/rom/ot_coll_tp8_static.sv.
// 4 packages x 2 dies (die r = 2 * package + die), every die the SAME master ranked by straps.  Links are fixed-latency
// delay models of the declared boundary (UCIe P / R: LATU (+XU) cycles; SerDes: LATS (+XS) cycles; no ready, no credit).
// The compiled program (+VEC/cmd.hex, written by tools/qwen_coll_tp8_static_bench.py's static scheduler) gives every
// message's command cycle and first output cycle; every die's producer delivers word w exactly at its compiled slot,
// and every output word must appear at exactly its compiled cycle with the exact value (tools/hdc_golden), last and
// rank.  Fault cases: +INJECT (arith), +TAGBAD (producer tag), +DROP (producer omits one word), +LATE (die 5's
// producer one cycle late), XU / XS (link one cycle longer than compiled) -- each must raise its fault class.
// ---------------------------------------------------------------------------
module tb_static_delay #(parameter integer W = 1, parameter integer L = 1) (
    input wire clk, input wire [31:0] cyc, input wire v_in, input wire [W-1:0] d_in, output wire v_out, output wire [W-1:0] d_out);
    reg          bv [0:L-1];
    reg [W-1:0]  bd [0:L-1];
    integer i;
    initial for (i = 0; i < L; i = i + 1) begin bv[i] = 1'b0; bd[i] = {W{1'b0}}; end
    always @(posedge clk) begin bv[cyc % L] <= v_in; bd[cyc % L] <= d_in; end
    assign v_out = bv[cyc % L];
    assign d_out = bd[cyc % L];
endmodule

module tb_coll_tp8_static #(
    parameter integer LATU = 19,
    parameter integer LATS = 344,
    parameter integer XU   = 0,      // extra UCIe link cycles vs the compiled LATU (negative control)
    parameter integer XS   = 0       // extra SerDes link cycles vs the compiled LATS (negative control)
) (input wire clk);
    localparam integer ND = 8, LANES = 16, FW = 512, TAGW = 32, PW = FW + 2 + TAGW, RW = FW + 2, MAXW = 1 << 16;
    reg [FW-1:0] part [0:MAXW-1];
    reg [FW-1:0] sum  [0:MAXW-1];
    reg [159:0]  cmdv [0:4095];      // {cmd cycle 32, first output cycle 32, part base 32, sum base 32, words 16, mode 16}
    integer NMSG, INJECT, TAGBAD, DROP, LATE, CONF, MAXCYC;
    reg [31:0] IVAL;
    string dir;
    reg [3:0] rcnt = 0;
    wire rst_n = (rcnt == 4'hF);
    always @(posedge clk) if (!rst_n) rcnt <= rcnt + 1'b1;
    reg [31:0] cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    wire [ND-1:0] iv, ov, ol, oe, flt, upv, dpv, urv, drv;
    wire [ND*FW-1:0] id, od;
    wire [ND-1:0] il, im;
    wire [ND*TAGW-1:0] it;
    wire [ND*3-1:0] orank;
    wire [ND*5-1:0] fc;
    wire [ND*PW-1:0] uprec, dprec;
    wire [ND*RW-1:0] urrec, drrec;
    wire [ND*3-1:0] sxv, srv;
    wire [ND*3*PW-1:0] sxrec, srrec;
    // the compiled program, identical on all dies
    reg cmd_v; reg cmd_mode; reg [15:0] cmd_words; reg [TAGW-1:0] cmd_tag;
    integer cm = 0;
    always @(*) begin
        cmd_v = 1'b0; cmd_mode = 1'b0; cmd_words = 16'd0; cmd_tag = 0;
        if (cm < NMSG && cyc == `C_ISS(cm)) begin cmd_v = 1'b1; cmd_mode = `C_MODE(cm); cmd_words = `C_W(cm); cmd_tag = cm; end
    end
    always @(posedge clk) if (cmd_v) cm <= cm + 1;

    integer bad = 0, words_out = 0, errs = 0, done_n = 0, extra = 0, total_out = 0, endc = 0, mi;
    genvar g, j;
    generate
        for (g = 0; g < ND; g = g + 1) begin : g_die
            localparam integer P = g / 2, D = g % 2;
`ifdef OT_TP8S_QFD
            qfd_io_collective_static u_die (       // the die-name master (LU / LS by +define, = LATU / LATS)
                .clk(clk), .clk_pfold0(clk), .clk_pfold1(clk), .clk_pfold2(clk), .clk_pfold3(clk),
                .clk_xfold0(clk), .clk_xfold1(clk), .clk_xfold2(clk), .clk_xfold3(clk),
                .clk_pring0(clk),.clk_pring1(clk),.clk_sring0(clk),.clk_sring1(clk),.clk_sring2(clk),.clk_sring3(clk),.clk_sring4(clk),.clk_rring0(clk),.clk_rring1(clk),
                .rst_n(rst_n), .pkg_s(P[1:0]), .die_ps(D[0]),
                .cmd_v(cmd_v), .cmd_mode(cmd_mode), .cmd_words(cmd_words), .cmd_tag(cmd_tag),
                .in_valid(iv[g]), .in_data(id[g*FW +: FW]), .in_last(il[g]), .in_mode(im[g]), .in_tag(it[g*TAGW +: TAGW]),
                .up_valid(upv[g]), .up_rec(uprec[g*PW +: PW]), .dp_valid(dpv[g]), .dp_rec(dprec[g*PW +: PW]),
                .ur_valid(urv[g]), .ur_rec(urrec[g*RW +: RW]), .dr_valid(drv[g]), .dr_rec(drrec[g*RW +: RW]),
                .sx0_valid(sxv[g*3]), .sx1_valid(sxv[g*3 + 1]), .sx2_valid(sxv[g*3 + 2]),
                .sx0_rec(sxrec[(g*3)*PW +: PW]), .sx1_rec(sxrec[(g*3 + 1)*PW +: PW]), .sx2_rec(sxrec[(g*3 + 2)*PW +: PW]),
                .sr0_valid(srv[g*3]), .sr1_valid(srv[g*3 + 1]), .sr2_valid(srv[g*3 + 2]),
                .sr0_rec(srrec[(g*3)*PW +: PW]), .sr1_rec(srrec[(g*3 + 1)*PW +: PW]), .sr2_rec(srrec[(g*3 + 2)*PW +: PW]),
                .out_valid(ov[g]), .out_data(od[g*FW +: FW]), .out_last(ol[g]), .out_rank(orank[g*3 +: 3]),
                .out_err(oe[g]), .fault(flt[g]), .fault_code(fc[g*5 +: 5]),
                .up_slot(), .ur_peer_slot(), .sx0_peer_slot(), .sx1_peer_slot(), .sx2_peer_slot(), .cmd_free());
`else
            ot_coll_tp8_static #(.LU(LATU), .LS(LATS)) u_die (
                .clk_mem({9{clk}}),.clk(clk), .clk_pfold({4{clk}}), .clk_xfold({4{clk}}),
                .rst_n(rst_n), .pkg_s(P[1:0]), .die_ps(D[0]),
                .cmd_v(cmd_v), .cmd_mode(cmd_mode), .cmd_words(cmd_words), .cmd_tag(cmd_tag),
                .in_valid(iv[g]), .in_data(id[g*FW +: FW]), .in_last(il[g]), .in_mode(im[g]), .in_tag(it[g*TAGW +: TAGW]),
                .up_valid(upv[g]), .up_rec(uprec[g*PW +: PW]), .dp_valid(dpv[g]), .dp_rec(dprec[g*PW +: PW]),
                .ur_valid(urv[g]), .ur_rec(urrec[g*RW +: RW]), .dr_valid(drv[g]), .dr_rec(drrec[g*RW +: RW]),
                .sx_valid(sxv[g*3 +: 3]), .sx_rec(sxrec[g*3*PW +: 3*PW]), .sr_valid(srv[g*3 +: 3]),
                .sr_rec(srrec[g*3*PW +: 3*PW]),
                .out_valid(ov[g]), .out_data(od[g*FW +: FW]), .out_last(ol[g]), .out_rank(orank[g*3 +: 3]),
                .out_err(oe[g]), .fault(flt[g]), .fault_code(fc[g*5 +: 5]),
                .up_slot(), .ur_peer_slot(), .sx_peer_slot(), .cmd_free());
`endif
            tb_static_delay #(.W(PW), .L(LATU + XU)) u_up (.clk(clk), .cyc(cyc), .v_in(upv[g]), .d_in(uprec[g*PW +: PW]),
                .v_out(dpv[g ^ 1]), .d_out(dprec[(g ^ 1)*PW +: PW]));
            tb_static_delay #(.W(RW), .L(LATU + XU)) u_ur (.clk(clk), .cyc(cyc), .v_in(urv[g]), .d_in(urrec[g*RW +: RW]),
                .v_out(drv[g ^ 1]), .d_out(drrec[(g ^ 1)*RW +: RW]));
            for (j = 0; j < 3; j = j + 1) begin : g_sx
                localparam integer Q = (P + 1 + j) % 4, R2 = 2 * Q + D, J2 = (P - Q + 7) % 4;
                tb_static_delay #(.W(PW), .L(LATS + XS)) u_sx (.clk(clk), .cyc(cyc), .v_in(sxv[g*3 + j]),
                    .d_in(sxrec[(g*3 + j)*PW +: PW]), .v_out(srv[R2*3 + J2]), .d_out(srrec[(R2*3 + J2)*PW +: PW]));
            end
            // producer: word w of message m exactly at its compiled slot (LATE: die 5 one cycle late)
            integer pm = 0, pw = 0;
            reg [31:0] slot_c;
            always @(*) begin
                slot_c = `C_CMD(pm) + 1 + (`C_MODE(pm) ? 8 * pw : pw) + ((LATE >= 0 && g == 5 && pm == LATE) ? 1 : 0);
            end
            wire fire = rst_n && pm < NMSG && cyc == slot_c;
            always @(posedge clk) if (fire) begin
                if (pw == `C_W(pm) - 1) begin pw <= 0; pm <= pm + 1; end else pw <= pw + 1;
            end
            reg [FW-1:0] word;
            always @(*) begin
                word = part[`C_PB(pm) + g*`C_W(pm) + pw];
                if (INJECT == pm && g == 2 && pw == 0) word[3*32 +: 32] = IVAL;
            end
            assign iv[g] = fire && !(DROP == pm && g == 5 && pw == 1);
            assign id[g*FW +: FW] = word;
            assign il[g] = (pw == `C_W(pm) - 1);
            assign im[g] = `C_MODE(pm);
            assign it[g*TAGW +: TAGW] = (TAGBAD == pm && g == 2) ? (pm ^ 32'h8000) : pm;
            // checker: value, last, rank and EXACT compiled cycle of every output word
            // the compiled output windows are disjoint (reserved by the scheduler): an output word belongs to the
            // message whose window holds its cycle; a word in no window is an extra (uncompiled) output
            integer rm, rk, per, rg, mm, nout = 0;
            reg [FW-1:0] exp;
            always @(posedge clk) if (ov[g]) begin
                rm = -1;
                for (mm = 0; mm < NMSG; mm = mm + 1) begin
                    per = `C_MODE(mm) ? ND * `C_W(mm) : `C_W(mm);
                    if (cyc >= `C_OUT(mm) && cyc < `C_OUT(mm) + per) rm = mm;
                end
                if (rm < 0) begin
                    extra = extra + 1;
                    if (extra < 5) $display("EXTRA die=%0d cyc=%0d", g, cyc);
                end else begin
                    per = `C_MODE(rm) ? ND * `C_W(rm) : `C_W(rm);
                    rk = cyc - `C_OUT(rm);
                    if (oe[g]) errs = errs + 1;
                    if (`C_MODE(rm)) begin
                        rg = rk % ND;                                    // TP8 rank = 4 * die + package
                        exp = part[`C_PB(rm) + (2 * (rg % 4) + rg / 4)*`C_W(rm) + rk / ND];
                        if (orank[g*3 +: 3] != rg) begin
                            bad = bad + 1;
                            if (bad < 5) $display("RANK die=%0d msg=%0d word=%0d rank=%0d", g, rm, rk, orank[g*3 +: 3]);
                        end
                    end else begin
                        exp = sum[`C_SB(rm) + rk];
                    end
                    if (od[g*FW +: FW] !== exp && INJECT < 0) begin
                        bad = bad + 1;
                        if (bad < 5) $display("MISMATCH die=%0d msg=%0d word=%0d mode=%0d", g, rm, rk, `C_MODE(rm));
                    end
                    if (ol[g] != (rk == per - 1)) begin
                        bad = bad + 1;
                        if (bad < 5) $display("LAST die=%0d msg=%0d word=%0d last=%0d", g, rm, rk, ol[g]);
                    end
                    words_out = words_out + 1;
                    nout = nout + 1;
                    if (nout == total_out) done_n = done_n + 1;
                end
            end
        end
    endgenerate

    initial begin
        if (!$value$plusargs("VEC=%s", dir)) dir = ".";
        if (!$value$plusargs("NMSG=%d", NMSG)) NMSG = 1;
        if (!$value$plusargs("INJECT=%d", INJECT)) INJECT = -1;
        if (!$value$plusargs("IVAL=%h", IVAL)) IVAL = 32'h7fc00000;
        if (!$value$plusargs("TAGBAD=%d", TAGBAD)) TAGBAD = -1;
        if (!$value$plusargs("DROP=%d", DROP)) DROP = -1;
        if (!$value$plusargs("LATE=%d", LATE)) LATE = -1;
        if (!$value$plusargs("CONF=%d", CONF)) CONF = 0;
        if (!$value$plusargs("MAXCYC=%d", MAXCYC)) MAXCYC = 400000;
        $readmemh({dir, "/part.hex"}, part);
        $readmemh({dir, "/sum.hex"}, sum);
        $readmemh({dir, "/cmd.hex"}, cmdv);
        for (mi = 0; mi < NMSG; mi = mi + 1) begin           // compiled totals: words per die, last output cycle
            total_out = total_out + (`C_MODE(mi) ? ND * `C_W(mi) : `C_W(mi));
            if (`C_OUT(mi) + (`C_MODE(mi) ? ND * `C_W(mi) : `C_W(mi)) + 64 > endc)
                endc = `C_OUT(mi) + (`C_MODE(mi) ? ND * `C_W(mi) : `C_W(mi)) + 64;
        end
    end
    // end: compiled last output + margin (the timeline is fixed: nothing can arrive later)
    integer t; reg [7:0] need;
    always @(posedge clk) begin
        if (rst_n && cyc == endc) begin
            $display("TP8S dies=%0d latu=%0d lats=%0d xu=%0d xs=%0d msgs=%0d inject=%0d tagbad=%0d drop=%0d late=%0d conf=%0d mismatches=%0d extra=%0d out_err=%0d fault=%b code=%b words_out=%0d first=%0d last=%0d",
                     ND, LATU, LATS, XU, XS, NMSG, INJECT, TAGBAD, DROP, LATE, CONF, bad, extra, errs, flt, fc, words_out,
                     `C_CMD(0) + 1, endc - 65);
            if (INJECT >= 0) begin                       // every die: arithmetic fault + flagged words
                need = 0; for (t = 0; t < ND; t = t + 1) need[t] = fc[t*5 + 0];
                if ((need == 8'hff && errs >= ND)) $display("PASS"); else $display("FAIL");
            end else if (TAGBAD >= 0) begin              // die 2 producer fault, its peer die 3 metadata fault
                if ((fc[2*5 + 2] && fc[3*5 + 1])) $display("PASS"); else $display("FAIL");
            end else if (DROP >= 0 || LATE >= 0) begin   // die 5 producer fault, its peer die 4 link fault
                if ((fc[5*5 + 2] && fc[4*5 + 3])) $display("PASS"); else $display("FAIL");
            end else if (CONF != 0) begin               // unreserved schedule: every die detects the calendar conflict
                need = 0; for (t = 0; t < ND; t = t + 1) need[t] = fc[t*5 + 4];
                if (need == 8'hff) $display("PASS"); else $display("FAIL");
            end else if (XU != 0 || XS != 0) begin       // every die sees a link-schedule fault
                need = 0; for (t = 0; t < ND; t = t + 1) need[t] = fc[t*5 + 3];
                if (need == 8'hff) $display("PASS"); else $display("FAIL");
            end else begin
                if ((bad == 0 && extra == 0 && flt == 0 && errs == 0 && done_n == ND)) $display("PASS"); else $display("FAIL");
            end
            $finish;
        end
        if (cyc > MAXCYC) begin $display("TIMEOUT"); $finish; end
    end
endmodule
