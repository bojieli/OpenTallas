`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// qwen-tp8 bench of rtl/rom/ot_coll_tp8_die.sv: 8 dies (die r = 2 * package + die-in-package), each package's dies
// joined by two UCIe channel models (partials P, results R; LATU cycles), die d of every package joined to die d of
// the 3 other packages by SerDes link models (LATS cycles) on its 3 ports.
// +VEC/part.hex: message m, die r, word w at (m*8 + r)*WORDS + w; +VEC/sum.hex: the two-level fold of every
// all-reduce word, ((P0 + P1) + P2) + P3 with Pp = part(p, 0) + part(p, 1) (tools/hdc_golden); +VEC/mode.hex.
// Every die checks every output word: all-reduce against sum.hex; all-gather word k against TP8 rank k mod 8
// (rank = 4 * die + package) word k / 8, and out_rank.  +INJECT=m: die 2 corrupts word 0 lane 3 of message m (+IVAL)
// -> every die must fault and flag out_err.  +TAGBAD=m: die 2 tags message m wrongly -> every die must fault with
// the engine's tag code (bit 1).  +SKEW=c: die r starts c*r cycles late; +GAP: random send gaps (percent).
// ---------------------------------------------------------------------------
module tb_coll_tp8_native59 #(
    parameter integer LANES = 16,
    parameter integer LATU  = 14,
    parameter integer LATS  = 40,
    parameter integer BPC   = 3600,
    parameter integer WT    = 0,
    parameter integer ICR   = 32
) (input wire clk);
    localparam integer ND = 8, FW = 32 * LANES, TAGW = 59, PW = FW + 2 + TAGW, RW = FW + 2 + TAGW, MAXW = 1 << 16;
    reg [FW-1:0] part [0:MAXW-1];
    reg [FW-1:0] sum  [0:MAXW-1];
    reg          mode [0:4095];
    integer NMSG, WORDS, GAP, SEED, INJECT, SKEW, TAGBAD, LASTBAD, MAXCYC;
    reg [31:0] IVAL;
    string dir;
    reg [3:0] rcnt = 0;
    wire rst_n = (rcnt == 4'hF);
    always @(posedge clk) if (!rst_n) rcnt <= rcnt + 1'b1;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    wire [ND-1:0] iv, icr, ov, ol, oe, flt;
    wire [ND*FW-1:0] id, od;
    wire [ND-1:0] il, im;
    wire [ND*TAGW-1:0] it, otag;
    wire [ND*3-1:0] orank;
    wire [ND*5-1:0] fc;
    wire [ND-1:0] upv, uprdy, upcr, dpv, dpcr, urv, urrdy, urcr, drv, drcr;
    wire [ND*PW-1:0] uprec, dprec;
    wire [ND*RW-1:0] urrec, drrec;
    wire [ND*3-1:0] sxv, sxrdy, sxcr, srv, srcr;
    wire [ND*3*PW-1:0] sxrec, srrec;

    function [31:0] xs(input [31:0] v0);
        reg [31:0] v;
        begin v = v0 ^ (v0 << 13); v = v ^ (v >> 17); xs = v ^ (v << 5); end
    endfunction
    function automatic [58:0] identity(input integer msg);
        reg [15:0] ep; reg [5:0] stage, seg; reg [17:0] tok; reg [12:0] pos;
        begin
            ep=16'hc001+(msg/8); stage=msg%38; seg=msg%64;
            case(msg%4)
                0:begin tok=18'd0;pos=13'd0;end
                1:begin tok=18'd65536;pos=13'd256;end
                2:begin tok=18'd131072;pos=13'd255;end
                default:begin tok=18'd151935;pos=13'd8191;end
            endcase
            identity={ep,stage,tok,pos,seg};
        end
    endfunction
    integer identity_bad = 0;
    integer bad = 0, words_out = 0, first = -1, lastc = 0, errs = 0, done_n = 0;
    genvar g, j;
    generate
        for (g = 0; g < ND; g = g + 1) begin : g_die
            localparam integer P = g / 2, D = g % 2;
            ot_coll_tp8_die_native59 #(.PKG(P), .DIE(D), .LANES(LANES), .WT(WT), .ICR(ICR)) u_die (
                .clk(clk), .rst_n(rst_n),
                .in_valid(iv[g]), .in_cr(icr[g]), .in_data(id[g*FW +: FW]), .in_last(il[g]), .in_mode(im[g]),
                .in_tag(it[g*TAGW +: TAGW]),
                .up_valid(upv[g]), .up_rec(uprec[g*PW +: PW]), .up_ready(uprdy[g]), .up_cr_in(upcr[g]),
                .dp_valid(dpv[g]), .dp_rec(dprec[g*PW +: PW]), .dp_cr_out(dpcr[g]),
                .ur_valid(urv[g]), .ur_rec(urrec[g*RW +: RW]), .ur_ready(urrdy[g]), .ur_cr_in(urcr[g]),
                .dr_valid(drv[g]), .dr_rec(drrec[g*RW +: RW]), .dr_cr_out(drcr[g]),
                .sx_valid(sxv[g*3 +: 3]), .sx_rec(sxrec[g*3*PW +: 3*PW]), .sx_ready(sxrdy[g*3 +: 3]),
                .sx_cr_in(sxcr[g*3 +: 3]), .sr_valid(srv[g*3 +: 3]), .sr_rec(srrec[g*3*PW +: 3*PW]),
                .sr_cr_out(srcr[g*3 +: 3]),
                .out_valid(ov[g]), .out_data(od[g*FW +: FW]), .out_last(ol[g]), .out_rank(orank[g*3 +: 3]),
                .out_err(oe[g]), .out_tag(otag[g*TAGW +: TAGW]), .fault(flt[g]), .fault_code(fc[g*5 +: 5]));
            // in-package UCIe: this die -> its peer (g ^ 1)
            ot_rom_ucie_link #(.PW(PW), .LAT(LATU), .FLIT_BYTES(FW / 8), .BPC_NUM(BPC)) u_up (
                .clk(clk), .rst_n(rst_n), .in_valid(upv[g]), .in_rec(uprec[g*PW +: PW]), .in_ready(uprdy[g]),
                .out_valid(dpv[g ^ 1]), .out_rec(dprec[(g ^ 1)*PW +: PW]), .cr_in(dpcr[g ^ 1]), .cr_out(upcr[g]));
            ot_rom_ucie_link #(.PW(RW), .LAT(LATU), .FLIT_BYTES(FW / 8), .BPC_NUM(BPC)) u_ur (
                .clk(clk), .rst_n(rst_n), .in_valid(urv[g]), .in_rec(urrec[g*RW +: RW]), .in_ready(urrdy[g]),
                .out_valid(drv[g ^ 1]), .out_rec(drrec[(g ^ 1)*RW +: RW]), .cr_in(drcr[g ^ 1]), .cr_out(urcr[g]));
            // SerDes: port j -> die D of package Q = (P + 1 + j) mod 4, arriving on its port (P - Q + 3) mod 4
            for (j = 0; j < 3; j = j + 1) begin : g_sx
                localparam integer Q = (P + 1 + j) % 4, R2 = 2 * Q + D, J2 = (P - Q + 7) % 4;
                ot_rom_ucie_link #(.PW(PW), .LAT(LATS), .FLIT_BYTES(FW / 8), .BPC_NUM(BPC)) u_sx (
                    .clk(clk), .rst_n(rst_n), .in_valid(sxv[g*3 + j]), .in_rec(sxrec[(g*3 + j)*PW +: PW]),
                    .in_ready(sxrdy[g*3 + j]), .out_valid(srv[R2*3 + J2]), .out_rec(srrec[(R2*3 + J2)*PW +: PW]),
                    .cr_in(srcr[R2*3 + J2]), .cr_out(sxcr[g*3 + j]));
            end
            // sender (sequencer with ICR credits)
            integer m = 0, w = 0, cred = ICR;
            reg go = 1'b0;
            reg [31:0] rnd = 32'h9e3779b9 * (g + 1);
            always @(posedge clk) begin
                if (cyc == 1) rnd <= 32'h9e3779b9 * (g + 1) ^ SEED;
                else rnd <= xs(rnd);
                go <= rst_n && (cyc >= 20 + SKEW * g) && ((rnd % 100) >= GAP);
                cred <= cred - (iv[g] ? 1 : 0) + (icr[g] ? 1 : 0);
                if (iv[g]) begin
                    if (first < 0) first = cyc;
                    if (w == WORDS - 1) begin w <= 0; m <= m + 1; end else w <= w + 1;
                end
            end
            reg [FW-1:0] word;
            always @(*) begin
                word = part[(m*ND + g)*WORDS + w];
                if (INJECT == m && g == 2 && w == 0) word[3*32 +: 32] = IVAL;
            end
            assign iv[g] = go && m < NMSG && cred > 0;
            assign id[g*FW +: FW] = word;
            assign il[g] = (w == WORDS - 1) || (LASTBAD == m && (g == 2 || g == 3) && w == 1);
            assign im[g] = mode[m];
            assign it[g*TAGW +: TAGW] = (TAGBAD == m && g == 2) ? (identity(m) ^ (59'd1 << 58)) : identity(m);
            // checker
            integer rm = 0, rk = 0, per, rg;
            reg [FW-1:0] exp;
            always @(posedge clk) if (ov[g]) begin
                if (otag[g*TAGW +: TAGW] !== identity(rm)) begin
                    identity_bad=identity_bad+1; bad=bad+1;
                    if(bad<5) $display("IDENTITY die=%0d msg=%0d got=%h expected=%h",g,rm,otag[g*TAGW +: TAGW],identity(rm));
                end
                per = mode[rm] ? ND * WORDS : WORDS;
                if (oe[g]) errs = errs + 1;
                if (mode[rm]) begin
                    rg = rk % ND;                                    // TP8 rank = 4 * die + package
                    exp = part[(rm*ND + 2 * (rg % 4) + rg / 4)*WORDS + rk / ND];
                    if (orank[g*3 +: 3] != rg) begin
                        bad = bad + 1;
                        if (bad < 5) $display("RANK die=%0d msg=%0d word=%0d rank=%0d", g, rm, rk, orank[g*3 +: 3]);
                    end
                end else begin
                    exp = sum[rm*WORDS + rk];
                end
                if (od[g*FW +: FW] !== exp && INJECT < 0) begin
                    bad = bad + 1;
                    if (bad < 5) $display("MISMATCH die=%0d msg=%0d word=%0d mode=%0d", g, rm, rk, mode[rm]);
                end
                if (ol[g] != (rk == per - 1)) begin
                    bad = bad + 1;
                    if (bad < 5) $display("LAST die=%0d msg=%0d word=%0d last=%0d", g, rm, rk, ol[g]);
                end
                words_out = words_out + 1; lastc = cyc;
                if (rk == per - 1) begin
                    rk = 0; rm = rm + 1;
                    if (rm == NMSG) done_n = done_n + 1;
                end else rk = rk + 1;
            end
        end
    endgenerate

    initial begin
        if (!$value$plusargs("VEC=%s", dir)) dir = ".";
        if (!$value$plusargs("NMSG=%d", NMSG)) NMSG = 16;
        if (!$value$plusargs("WORDS=%d", WORDS)) WORDS = 8;
        if (!$value$plusargs("GAP=%d", GAP)) GAP = 0;
        if (!$value$plusargs("SEED=%d", SEED)) SEED = 1;
        if (!$value$plusargs("INJECT=%d", INJECT)) INJECT = -1;
        if (!$value$plusargs("IVAL=%h", IVAL)) IVAL = 32'h7fc00000;
        if (!$value$plusargs("SKEW=%d", SKEW)) SKEW = 0;
        if (!$value$plusargs("TAGBAD=%d", TAGBAD)) TAGBAD = -1;
        if (!$value$plusargs("LASTBAD=%d", LASTBAD)) LASTBAD = -1;
        if (!$value$plusargs("MAXCYC=%d", MAXCYC)) MAXCYC = 300000;
        $readmemh({dir, "/part.hex"}, part);
        $readmemh({dir, "/sum.hex"}, sum);
        $readmemh({dir, "/mode.hex"}, mode);
    end

`ifdef TP8_DEBUG
    always @(posedge clk) if (g_die[2].u_die.prot_n || g_die[2].u_die.arith_n)
        $display("DBG cyc=%0d pp=%b pbad=%b oddw=%b slv=%b tail=%b eov=%b mfhv=%b mgo=%b tl=%b mm=%b lqm=%b upbad=%b ovf=%b%b%b%b%b%b%b arith=%b sle=%b",
            cyc, g_die[2].u_die.pair_pop, g_die[2].u_die.p_bad, g_die[2].u_die.pr_red && g_die[2].u_die.p_last && !g_die[2].u_die.wpar,
            g_die[2].u_die.sl_v, g_die[2].u_die.sl_tail, g_die[2].u_die.e_ov, g_die[2].u_die.mf_hv, g_die[2].u_die.m_go,
            g_die[2].u_die.take_l, g_die[2].u_die.m_mode, g_die[2].u_die.lq_hd[FW+4], g_die[2].u_die.up_bad,
            g_die[2].u_die.lb_ovf, g_die[2].u_die.pq_ovf, g_die[2].u_die.eq_ovf, g_die[2].u_die.mf_ovf, g_die[2].u_die.lq_ovf,
            g_die[2].u_die.tq_ovf, g_die[2].u_die.rq_ovf, g_die[2].u_die.arith_n, g_die[2].u_die.sl_e);
`endif
    integer t;
    reg tagok;
    always @(posedge clk) begin
        if(LASTBAD>=0 && cyc>6000) begin
            tagok=1'b1;
            for(t=0;t<ND;t=t+1) if(!fc[t*5+1])tagok=1'b0;
            $display("PARTICIPANT_LAST fault=%b complete_metadata_rejected=%0d outputs=%0d",flt,tagok,words_out);
            if(tagok && flt=={ND{1'b1}} && words_out==0) $display("PASS"); else $display("FAIL");
            $finish;
        end
`ifdef OT_NATIVE59_MUT_PEERID
        if(cyc > 6000) begin
            tagok=1'b1;
            for(t=0;t<ND;t=t+1) if(!fc[t*5+4]) tagok=1'b0;
            $display("STALE_PEER_IDENTITY fault=%b protocol_detected=%0d identity_escapes=%0d outputs=%0d",flt,tagok,identity_bad,words_out);
            if(tagok && flt=={ND{1'b1}} && identity_bad==0) $display("PASS"); else $display("FAIL");
            $finish;
        end
`endif
        if ((done_n == ND && INJECT < 0 && TAGBAD < 0) ||
            ((INJECT >= 0 || TAGBAD >= 0) && cyc > 4000 + 4 * LATS + NMSG * WORDS * 16)) begin
            $display("TP8COLL dies=%0d latu=%0d lats=%0d msgs=%0d words=%0d gap=%0d skew=%0d inject=%0d mismatches=%0d out_err=%0d fault=%b code=%b words_out=%0d first=%0d last=%0d",
                     ND, LATU, LATS, NMSG, WORDS, GAP, SKEW, INJECT, bad, errs, flt, fc, words_out, first, lastc);
            if (TAGBAD >= 0) begin
                tagok = 1'b1;
                for (t = 0; t < ND; t = t + 1) if (!fc[t*5 + 1]) tagok = 1'b0;
                if (flt == {ND{1'b1}} && tagok) $display("PASS"); else $display("FAIL");
            end else if (INJECT < 0) begin
                if (bad == 0 && flt == 0 && errs == 0 && done_n == ND) $display("PASS"); else $display("FAIL");
            end else begin
                if (flt == {ND{1'b1}} && errs >= ND) $display("PASS"); else $display("FAIL");
            end
            $finish;
        end
        if (cyc > MAXCYC) begin
            $display("TIMEOUT cyc=%0d done_n=%0d words_out=%0d mismatches=%0d fault=%b code=%b", cyc, done_n, words_out, bad, flt, fc);
            `define TP8_DUMP(i) $display("die %0d sent_msgs=%0d lb_hv=%b pq_hv=%b eq_res=%0d infl=%0d eq_hv=%b ecred=%0d lq_res=%0d tq_res=%0d mf_n=%0d lq_hv=%b rq_hv=%b mc=%0d cr_a=%0d cr_b=%0d wpar=%b", i, g_die[i].m, g_die[i].u_die.lb_hv, g_die[i].u_die.pq_hv, g_die[i].u_die.eq_res, g_die[i].u_die.infl, g_die[i].u_die.eq_hv, g_die[i].u_die.ecred, g_die[i].u_die.lq_res, g_die[i].u_die.tq_res, g_die[i].u_die.mf_n, g_die[i].u_die.lq_hv, g_die[i].u_die.rq_hv, g_die[i].u_die.mc, g_die[i].u_die.cr_a, g_die[i].u_die.cr_b, g_die[i].u_die.wpar);
            `TP8_DUMP(0) `TP8_DUMP(1) `TP8_DUMP(2) `TP8_DUMP(3) `TP8_DUMP(4) `TP8_DUMP(5) `TP8_DUMP(6) `TP8_DUMP(7)
            $display("TIMEOUT"); $finish;
        end
    end
endmodule
