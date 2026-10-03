`timescale 1ns/1ps
// Selection path of the EDGE INDEX SCORER: four per-stack streamed top-K units
// (ot_dsrom_edge_lsel) and the hub (ot_dsrom_edge_hub), driven with BF16 score
// streams (the golden's index scores) and checked against
// sorted(topk_lowest_index(s, min(K, n))) (tools/dsrom_edge_scorer_campaign.py).
//
// +S0..+S3=<file>  per stack: per query "Q <beats>", then beats
//                  "<last> <lv hex>" + LI x " <value hex> <position hex>"
// +EXP=<file>      per query "Q <count>", then <count> lines "<position hex> <value hex>"
// +RATE=<n>        keys per cycle per stack offered by the HBM service (credit
//                  model: a 16-key beat when the credit reaches 16); 0 = every cycle
// +BUBBLE=<p>      extra percent of cycles a stack withholds its beat
// +SEED=<n>
// Prints per query: EDGEQ q=.. n=.. cyc_first=.. cyc_last_in=.. cyc_out=.. errors=..
// and per stack folds/pass/stall/last-candidate cycle.
module tb_dsrom_edge_select
`ifdef VERILATOR
    (input wire clk)
`endif
    ;
`ifndef VERILATOR
    reg clk = 1'b0;
    always #0.5 clk = !clk;
`endif
    parameter integer LI = 16, W = 64, VW = 16, IW = 20, K = 512, NC = 32, FA = 7, LO = 16, MACRO = 0, CONTIGUOUS = 0;

    reg               rst_n = 1'b0;
    reg               start = 1'b0;
    reg  [3:0]        iv = 0, il = 0;
    wire [3:0]        ir;
    reg  [4*LI-1:0]   ilv = 0;
    reg  [4*LI*VW-1:0] ival = 0;
    reg  [4*LI*IW-1:0] iidx = 0;
    wire [3:0]        cv, cr, cl, sb;
    wire [4*LO-1:0]   clv;
    wire [4*LO*VW-1:0] cval;
    wire [4*LO*IW-1:0] cidx;
    wire [4*32-1:0]   sf, sp, sl, ss;
    wire              ov, ol, hb;
    wire [W-1:0]      olv;
    wire [W*VW-1:0]   oval;
    wire [W*IW-1:0]   oidx;

    genvar g;
    generate
        for (g = 0; g < 4; g = g + 1) begin : g_s
            ot_dsrom_edge_lsel #(.LI(LI), .W(W), .VW(VW), .IW(IW), .K(K), .NC(NC), .FA(FA), .LO(LO), .MACRO(MACRO)) u (
                .clk(clk), .rst_n(rst_n), .start(start),
                .in_valid(iv[g]), .in_ready(ir[g]), .in_last(il[g]), .in_lv(ilv[LI*g +: LI]),
                .in_val(ival[LI*VW*g +: LI*VW]), .in_idx(iidx[LI*IW*g +: LI*IW]),
                .out_valid(cv[g]), .out_ready(cr[g]), .out_last(cl[g]), .out_lv(clv[LO*g +: LO]),
                .out_val(cval[LO*VW*g +: LO*VW]), .out_idx(cidx[LO*IW*g +: LO*IW]),
                .busy(sb[g]), .st_folds(sf[32*g +: 32]), .st_pass(sp[32*g +: 32]), .st_lines(sl[32*g +: 32]),
                .st_stall(ss[32*g +: 32]));
        end
    endgenerate
    ot_dsrom_edge_hub #(.WM(LO), .W(W), .VW(VW), .IW(IW), .K(K), .MACRO(MACRO), .CONTIGUOUS(CONTIGUOUS)) u_hub (
        .clk(clk), .rst_n(rst_n), .start(start),
        .i_valid(cv), .i_ready(cr), .i_last(cl), .i_lv(clv), .i_val(cval), .i_idx(cidx),
        .o_valid(ov), .o_last(ol), .o_lv(olv), .o_val(oval), .o_idx(oidx), .busy(hb));

    integer fin [0:3];
    integer fexp, rc, i, s;
    integer rate = 11, bubble = 0;
    reg [31:0] rng = 32'h2545F491;
    function automatic [31:0] xs(input [31:0] x);
        reg [31:0] t;
        begin t = x ^ (x << 13); t = t ^ (t >> 17); xs = t ^ (t << 5); end
    endfunction
    reg [8*512-1:0] fname, pfmt;

    // per stack: beats left in the query, the fetched beat
    integer   left [0:3];
    integer   credit [0:3];
    reg       have [0:3];
    reg [31:0] f_last [0:3];
    reg [LI-1:0] f_lv [0:3];
    reg [LI*VW-1:0] f_val [0:3];
    reg [LI*IW-1:0] f_idx [0:3];
    reg [31:0] t0, t1;
    integer   last_in [0:3], cand_last [0:3];

    task automatic fetch(input integer st);
        begin
            rc = $fscanf(fin[st], "%d %h", f_last[st], f_lv[st]);
            if (rc != 2) begin $display("EDGE vector read error stack %0d", st); $finish; end
            for (i = 0; i < LI; i = i + 1) begin
                rc = $fscanf(fin[st], " %h %h", t0, t1);
                f_val[st][VW*i +: VW] = t0[VW-1:0];
                f_idx[st][IW*i +: IW] = t1[IW-1:0];
            end
            have[st] = 1'b1;
        end
    endtask

    integer cyc = 0, q = 0, nq = 0, phase = 0, e_cnt = 0, got = 0, errors = 0, total_err = 0;
    integer cyc_start = 0, cyc_first = 0, cyc_out = 0, wait_cyc = 0, max_cyc = 2000000000;
    reg [31:0] e_idx, e_val, nb;
    reg [8*8-1:0] tag;

    initial begin
        for (s = 0; s < 4; s = s + 1) begin
            $sformat(pfmt, "S%0d=%%s", s);
            if (!$value$plusargs(pfmt, fname)) begin $display("need +S%0d", s); $finish; end
            fin[s] = $fopen(fname, "r");
            if (fin[s] == 0) begin $display("cannot open stack file"); $finish; end
        end
        if (!$value$plusargs("EXP=%s", fname)) begin $display("need +EXP"); $finish; end
        fexp = $fopen(fname, "r");
        if (!$value$plusargs("RATE=%d", rate)) rate = 11;
        if (!$value$plusargs("BUBBLE=%d", bubble)) bubble = 0;
        if (!$value$plusargs("MAXCYC=%d", max_cyc)) max_cyc = 2000000000;
        if ($value$plusargs("SEED=%d", rc)) rng = rng ^ rc;
    end

    // query sequencing: phase 0 = reset/idle, 1 = start pulse, 2 = streaming/collecting
    always @(posedge clk) begin
        cyc <= cyc + 1;
        start <= 1'b0;
        if (cyc == 4) rst_n <= 1'b1;
        if (cyc > max_cyc) begin
            $display("EDGE timeout phase=%0d iv=%b ir=%b sb=%b hb=%b cv=%b cr=%b left=%0d,%0d,%0d,%0d have=%b%b%b%b got=%0d",
                     phase, iv, ir, sb, hb, cv, cr, left[0], left[1], left[2], left[3], have[0], have[1], have[2], have[3], got);
            $display("EDGE lsel0 fs=%0d fcnt=%0d in_done=%b scan=%b emitted=%b sn=%0d tbusy=%b", g_s[0].u.fs, g_s[0].u.fcnt,
                     g_s[0].u.in_done, g_s[0].u.scan, g_s[0].u.emitted, g_s[0].u.sn, g_s[0].u.t_busy);
            $finish;
        end
        if (rst_n && phase == 0 && cyc > 16) begin
            // next query headers
            rc = $fscanf(fexp, "Q %d\n", e_cnt);
            if (rc != 1) begin
                $display("EDGEDONE queries=%0d errors=%0d", nq, total_err);
                $finish;
            end
            for (s = 0; s < 4; s = s + 1) begin
                rc = $fscanf(fin[s], " Q %d", nb);
                left[s] = nb; credit[s] = 0; have[s] = 1'b0; last_in[s] = -1; cand_last[s] = -1;
            end
            got = 0; errors = 0; cyc_out = -1; cyc_first = -1;
            start <= 1'b1; cyc_start = cyc;
            phase = 1;
        end else if (phase == 1) begin
            phase = 2;
        end else if (phase == 2) begin
            for (s = 0; s < 4; s = s + 1) begin
                if (iv[s] && ir[s]) begin
                    if (cyc_first < 0) cyc_first = cyc;
                    if (il[s]) last_in[s] = cyc;
                    left[s] = left[s] - 1;
                    have[s] = 1'b0;
                end
                if (!have[s] && left[s] > 0) fetch(s);
                if (cv[s] && cr[s] && cl[s]) cand_last[s] = cyc;
            end
            // HBM-rate credit and bubbles
            for (s = 0; s < 4; s = s + 1) begin
                if (rate > 0 && credit[s] < 2 * LI) credit[s] = credit[s] + rate;
                rng = xs(rng);
                if (have[s] && (rate == 0 || credit[s] >= LI) && (rng % 100) >= bubble && !(iv[s] && !ir[s])) begin
                    iv[s] <= 1'b1; il[s] <= f_last[s][0];
                    ilv[LI*s +: LI] <= f_lv[s]; ival[LI*VW*s +: LI*VW] <= f_val[s]; iidx[LI*IW*s +: LI*IW] <= f_idx[s];
                    if (rate > 0) credit[s] = credit[s] - LI;
                end else if (!(iv[s] && !ir[s])) iv[s] <= 1'b0;
            end
            // collect
            if (ov) begin
                for (i = 0; i < W; i = i + 1) if (olv[i]) begin
                    rc = $fscanf(fexp, "%h %h\n", e_idx, e_val);
                    if (got >= e_cnt || oidx[IW*i +: IW] != e_idx[IW-1:0] || oval[VW*i +: VW] != e_val[VW-1:0]) begin
                        if (errors < 8) $display("EDGEMISMATCH q=%0d n=%0d got %h/%h exp %h/%h", q, got,
                                                 oidx[IW*i +: IW], oval[VW*i +: VW], e_idx, e_val);
                        errors = errors + 1;
                    end
                    got = got + 1;
                end
                if (ol) begin
                    cyc_out = cyc;
                    if (got != e_cnt) begin
                        $display("EDGEMISMATCH q=%0d count got %0d exp %0d", q, got, e_cnt);
                        errors = errors + 1;
                        for (i = got; i < e_cnt; i = i + 1) rc = $fscanf(fexp, "%h %h\n", e_idx, e_val);
                    end
                    $display("EDGEQ q=%0d n=%0d start=%0d first=%0d last_in=%0d,%0d,%0d,%0d cand_last=%0d,%0d,%0d,%0d out=%0d errors=%0d",
                             q, e_cnt, cyc_start, cyc_first, last_in[0], last_in[1], last_in[2], last_in[3],
                             cand_last[0], cand_last[1], cand_last[2], cand_last[3], cyc_out, errors);
                    $fflush(); $display("EDGEST q=%0d folds=%0d,%0d,%0d,%0d pass=%0d,%0d,%0d,%0d lines=%0d,%0d,%0d,%0d stall=%0d,%0d,%0d,%0d",
                             q, sf[31:0], sf[63:32], sf[95:64], sf[127:96], sp[31:0], sp[63:32], sp[95:64], sp[127:96],
                             sl[31:0], sl[63:32], sl[95:64], sl[127:96], ss[31:0], ss[63:32], ss[95:64], ss[127:96]);
                    total_err = total_err + errors;
                    q = q + 1; nq = nq + 1;
                    phase = 3; wait_cyc = cyc;
                end
            end
        end else if (phase == 3) begin
            if (!(|sb) && !hb && cyc > wait_cyc + 4) phase = 0;
        end
    end
endmodule
