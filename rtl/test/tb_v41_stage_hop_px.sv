`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Gate C7 / O2 LEVER bench: the stage hop on the physical stage lanes
// (tools/rtl_v41_collective_levers_campaign.py).
//
// docs/ARCH_V41_RACK.md 2: a package's 14 stage lanes go forward on two 7-lane
// cables to the SAME-POSITION package of the next module, and each die owns its
// SerDes (a die's 45 lanes: 26 TP, 7 + 7 stage, 2 switch, 3 spare).  So a hop
// is four die-to-die cable streams: sender die (P, i) -> receiver die (P, i),
// P in {A, B} the package, i in {0, 1} the die -- each at LANES_PER_DIE lanes.
// Every receiver needs the whole residual (hc_pre of the next group is
// elementwise over the full vector on every die).
//
// Which words each sender puts on its cable is data (+VEC/list.hex, per sender
// the word indices in send order; +VEC/uniq.hex, per word, 1 when the word is
// carried by ONE package only):
//   full        every package carries every word, each die half of them (the
//               receiving package's dies swap halves over UCIe);
//   split u     the first u words ride package A's cables only and the next u
//               package B's only; each receiving die forwards such a word
//               over its T1 links to both dies of the other package;
//   one-die     (the O2 bench's abstraction) one die drives all 14 lanes.
// A receiving die buffers its cable stream (DEPTH words, credits back over the
// cable's reverse lanes) and pops a word only when every forward target has a
// credit: the UCIe peer (DEPTH_F) and, for a one-package word, both T1 targets
// (DEPTH_F).  Words arriving over UCIe or T1 are consumed on arrival.  Every
// receiver checks every word bit for bit, exactly once, in any order.
// ARR lines: die = 2P + i of the RECEIVING side (0..3).
// ---------------------------------------------------------------------------
module tb_v41_stage_hop_px #(
    parameter integer LANES     = 128,
    parameter integer DEPTH     = 128,
    parameter integer DEPTH_F   = 64,
    parameter integer QTX       = 128,
    parameter integer LAT_C     = 228,
    parameter integer BPC_C     = 8485,   // per die: 7 lanes x 13.18 GB/s = 84.85 B/cycle
    parameter integer BPC_C_DEN = 100,
    parameter integer LAT_X     = 142,
    parameter integer BPC_X     = 15758,
    parameter integer BPC_X_DEN = 100,
    parameter integer LAT_U     = 11,
    parameter integer BPC_U     = 3864,
    parameter integer FLIT_OVH  = 0,
    parameter integer PUSHW     = 8,
    parameter integer MAXW      = 512
) (input wire clk);
    localparam integer FW = 32 * LANES, IW = 16, PW = FW + IW;   // record {word index, data}
    localparam integer COST = FW / 8 + FLIT_OVH;
    reg [FW-1:0] part [0:MAXW-1];
    reg [31:0]   rdy  [0:MAXW-1];
    reg [31:0]   lst  [0:4*MAXW-1];          // sender d's list at d*MAXW; lst_n[d] entries
    reg          uniq [0:MAXW-1];
    integer WORDS, START, TIMEOUT, LN0, LN1, LN2, LN3;
    string dir;
    reg [3:0] rcnt = 0;
    wire rst_n = (rcnt == 4'hF);
    always @(posedge clk) if (!rst_n) rcnt <= rcnt + 1'b1;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    integer bad = 0;
    function integer lnum(input integer d);
        lnum = (d == 0) ? LN0 : (d == 1) ? LN1 : (d == 2) ? LN2 : LN3;
    endfunction

    // -- cables: sender d -> receiver d ------------------------------------------------------------
    wire [3:0]    c_send, c_rdy, c_ov, c_cr, c_pop;
    wire [4*PW-1:0] c_in, c_od;
    // -- UCIe forward: receiver d -> receiver d^1; T1 forward: receiver d -> receivers of the other package
    wire [3:0]    u_send, u_rdy, u_ov, u_cr;
    wire [4*PW-1:0] u_od;
    wire [7:0]    x_send, x_rdy, x_ov, x_cr;   // [2d + j]: d -> 2*(1 - d/2) + j
    wire [8*PW-1:0] x_od;
    wire [4*PW-1:0] f_rec;                    // the record a receiver pops (forwarded as is)

    genvar d, j;
    generate
        for (d = 0; d < 4; d = d + 1) begin : g_s
            // -- sender d: producer over its list, output queue, cable credits --------------------------
            reg [PW-1:0] q [0:QTX-1];
            integer ptime = 0, k = 0, qh = 0, qt = 0, qn = 0;
            integer pushed_last = -1, stall = 0, qmax = 0;
            integer cred = DEPTH;
            wire go = rst_n && (cyc >= START);
            assign c_send[d] = (qn > 0) && (cred > 0) && c_rdy[d];
            assign c_in[d*PW +: PW] = q[qh];
            always @(posedge clk) begin : step
                integer kk, qtt, np, jj, nq, w;
                kk = k; qtt = qt; np = 0;
                if (go) begin
                    for (jj = 0; jj < PUSHW; jj = jj + 1)
                        if (kk < lnum(d) && rdy[lst[d*MAXW + kk]] <= ptime && qn + np < QTX) begin
                            w = lst[d*MAXW + kk];
                            q[qtt] <= {w[IW-1:0], part[w]};
                            qtt = (qtt == QTX - 1) ? 0 : qtt + 1;
                            np = np + 1;
                            if (kk == lnum(d) - 1) pushed_last <= cyc;
                            kk = kk + 1;
                        end
                    if (kk < lnum(d) && rdy[lst[d*MAXW + kk]] <= ptime) begin
                        if (qn + np >= QTX) stall <= stall + 1;
                    end
                    else ptime <= ptime + 1;
                end
                k <= kk;
                qt <= qtt;
                if (c_send[d]) qh <= (qh == QTX - 1) ? 0 : qh + 1;
                nq = qn + np - (c_send[d] ? 1 : 0);
                qn <= nq;
                if (nq > qmax) qmax <= nq;
                cred <= cred - (c_send[d] ? 1 : 0) + (c_cr[d] ? 1 : 0);
            end
            ot_v41px_link #(.PW(PW), .CW(1), .LAT(LAT_C), .COST(COST), .BPC_NUM(BPC_C), .BPC_DEN(BPC_C_DEN)) u_cable (
                .clk(clk), .rst_n(rst_n), .in_valid(c_send[d]), .in_rec(c_in[d*PW +: PW]), .in_ready(c_rdy[d]),
                .out_valid(c_ov[d]), .out_rec(c_od[d*PW +: PW]), .cr_in(c_pop[d]), .cr_out(c_cr[d]));
        end

        for (d = 0; d < 4; d = d + 1) begin : g_r
            // -- receiver d: cable buffer, forwards, consumer --------------------------------------------
            localparam integer PEER = d ^ 1;
            localparam integer OTH = 2 * (1 - d / 2);          // first die of the other package
            reg [PW-1:0] b [0:DEPTH-1];
            integer h = 0, tl = 0, n = 0, nmax = 0, ovf = 0;
            integer ucred = DEPTH_F, xcred0 = DEPTH_F, xcred1 = DEPTH_F;
            reg [MAXW-1:0] got = {MAXW{1'b0}};
            integer ngot = 0, rfirst = -1, rlast = -1, dup = 0;
            wire [IW-1:0] hw = b[h][FW +: IW];
            wire need_x = uniq[hw];
            assign c_pop[d] = (n > 0) && ucred > 0 && u_rdy[d]
                              && (!need_x || (xcred0 > 0 && xcred1 > 0 && x_rdy[2*d] && x_rdy[2*d + 1]));
            assign u_send[d] = c_pop[d];
            assign x_send[2*d] = c_pop[d] && need_x;
            assign x_send[2*d + 1] = c_pop[d] && need_x;
            assign f_rec[d*PW +: PW] = b[h];
            // words consumed this cycle: the popped cable word, a UCIe word, two T1 words
            task automatic take(input [PW-1:0] rec);
                integer w;
                begin
                    w = rec[FW +: IW];
                    if (rec[FW-1:0] !== part[w]) bad = bad + 1;
                    if (got[w]) dup = dup + 1;
                    got[w] = 1'b1;
                    ngot = ngot + 1;
                    $display("ARR die=%0d word=%0d cyc=%0d", d, w, cyc);
                    if (rfirst < 0) rfirst = cyc;
                    rlast = cyc;
                end
            endtask
            always @(posedge clk) begin : rx
                integer nn;
                if (c_ov[d]) begin
                    b[tl] <= c_od[d*PW +: PW];
                    tl <= (tl == DEPTH - 1) ? 0 : tl + 1;
                end
                if (c_pop[d]) begin
                    take(b[h]);
                    h <= (h == DEPTH - 1) ? 0 : h + 1;
                end
                if (u_ov[PEER]) take(u_od[PEER*PW +: PW]);
                if (x_ov[2*OTH + (d % 2)]) take(x_od[(2*OTH + (d % 2))*PW +: PW]);
                if (x_ov[2*(OTH + 1) + (d % 2)]) take(x_od[(2*(OTH + 1) + (d % 2))*PW +: PW]);
                nn = n + (c_ov[d] ? 1 : 0) - (c_pop[d] ? 1 : 0);
                n <= nn;
                if (nn > DEPTH) ovf <= 1;
                if (nn > nmax) nmax <= nn;
                ucred <= ucred - (u_send[d] ? 1 : 0) + (u_cr[d] ? 1 : 0);
                xcred0 <= xcred0 - (x_send[2*d] ? 1 : 0) + (x_cr[2*d] ? 1 : 0);
                xcred1 <= xcred1 - (x_send[2*d + 1] ? 1 : 0) + (x_cr[2*d + 1] ? 1 : 0);
            end
            // UCIe to the package peer; the peer consumes on arrival and returns the credit then
            ot_v41px_link #(.PW(PW), .CW(1), .LAT(LAT_U), .COST(COST), .BPC_NUM(BPC_U), .BPC_DEN(1)) u_fwd (
                .clk(clk), .rst_n(rst_n), .in_valid(u_send[d]), .in_rec(f_rec[d*PW +: PW]), .in_ready(u_rdy[d]),
                .out_valid(u_ov[d]), .out_rec(u_od[d*PW +: PW]), .cr_in(u_ov[d]), .cr_out(u_cr[d]));
            // T1 to both dies of the other package (consumed on arrival)
            for (j = 0; j < 2; j = j + 1) begin : g_x
                ot_v41px_link #(.PW(PW), .CW(1), .LAT(LAT_X), .COST(COST), .BPC_NUM(BPC_X), .BPC_DEN(BPC_X_DEN)) u_x (
                    .clk(clk), .rst_n(rst_n), .in_valid(x_send[2*d + j]), .in_rec(f_rec[d*PW +: PW]),
                    .in_ready(x_rdy[2*d + j]), .out_valid(x_ov[2*d + j]), .out_rec(x_od[(2*d + j)*PW +: PW]),
                    .cr_in(x_ov[2*d + j]), .cr_out(x_cr[2*d + j]));
            end
        end
    endgenerate

    initial begin
        if (!$value$plusargs("VEC=%s", dir)) dir = ".";
        if (!$value$plusargs("WORDS=%d", WORDS)) WORDS = 81;
        if (!$value$plusargs("START=%d", START)) START = 20;
        if (!$value$plusargs("TIMEOUT=%d", TIMEOUT)) TIMEOUT = 200000;
        if (!$value$plusargs("LN0=%d", LN0)) LN0 = 0;
        if (!$value$plusargs("LN1=%d", LN1)) LN1 = 0;
        if (!$value$plusargs("LN2=%d", LN2)) LN2 = 0;
        if (!$value$plusargs("LN3=%d", LN3)) LN3 = 0;
        $readmemh({dir, "/part.hex"}, part);
        $readmemh({dir, "/ready.hex"}, rdy);
        $readmemh({dir, "/list.hex"}, lst);
        $readmemh({dir, "/uniq.hex"}, uniq);
    end
    reg fin = 1'b0;
    wire all_got = g_r[0].ngot == WORDS && g_r[1].ngot == WORDS && g_r[2].ngot == WORDS && g_r[3].ngot == WORDS;
    always @(posedge clk) begin : fn
        integer dd, faults, lastref;
        if (!fin && (all_got || cyc > TIMEOUT)) fin <= 1'b1;
        if (fin) begin
            faults = g_r[0].ovf + g_r[1].ovf + g_r[2].ovf + g_r[3].ovf + g_r[0].dup + g_r[1].dup + g_r[2].dup
                     + g_r[3].dup;
            // the producer's model finish: its LAST word complete (every die produces the whole residual)
            lastref = START + rdy[WORDS - 1];
            $display("SB die=10 start=%0d ref=%0d pushed_last=%0d stall=%0d hold=0 qmax=%0d first=-1 last=-1 fault=0 code=0",
                     START, lastref, g_s[0].pushed_last, g_s[0].stall, g_s[0].qmax);
            $display("SB die=11 start=%0d ref=%0d pushed_last=%0d stall=%0d hold=0 qmax=%0d first=-1 last=-1 fault=0 code=0",
                     START, lastref, g_s[1].pushed_last, g_s[1].stall, g_s[1].qmax);
            $display("SB die=12 start=%0d ref=%0d pushed_last=%0d stall=%0d hold=0 qmax=%0d first=-1 last=-1 fault=0 code=0",
                     START, lastref, g_s[2].pushed_last, g_s[2].stall, g_s[2].qmax);
            $display("SB die=13 start=%0d ref=%0d pushed_last=%0d stall=%0d hold=0 qmax=%0d first=-1 last=-1 fault=0 code=0",
                     START, lastref, g_s[3].pushed_last, g_s[3].stall, g_s[3].qmax);
            $display("SB die=0 start=%0d ref=%0d pushed_last=-1 stall=0 hold=0 qmax=%0d first=%0d last=%0d fault=%0d code=0",
                     START, lastref, g_r[0].nmax, g_r[0].rfirst, g_r[0].rlast, g_r[0].ovf + g_r[0].dup);
            $display("SB die=1 start=%0d ref=%0d pushed_last=-1 stall=0 hold=0 qmax=%0d first=%0d last=%0d fault=%0d code=0",
                     START, lastref, g_r[1].nmax, g_r[1].rfirst, g_r[1].rlast, g_r[1].ovf + g_r[1].dup);
            $display("SB die=2 start=%0d ref=%0d pushed_last=-1 stall=0 hold=0 qmax=%0d first=%0d last=%0d fault=%0d code=0",
                     START, lastref, g_r[2].nmax, g_r[2].rfirst, g_r[2].rlast, g_r[2].ovf + g_r[2].dup);
            $display("SB die=3 start=%0d ref=%0d pushed_last=-1 stall=0 hold=0 qmax=%0d first=%0d last=%0d fault=%0d code=0",
                     START, lastref, g_r[3].nmax, g_r[3].rfirst, g_r[3].rlast, g_r[3].ovf + g_r[3].dup);
            $display("SBDONE done=%0d mismatches=%0d out_err=0 timeout=%0d %s", all_got, bad, cyc > TIMEOUT,
                     (all_got && bad == 0 && faults == 0) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
