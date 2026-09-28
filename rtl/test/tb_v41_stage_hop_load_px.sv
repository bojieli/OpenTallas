`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Gate C7 / O2 LEVER bench under BATCH LOAD: the stage hop of
// tb_v41_stage_hop_px.sv (same senders, cables, receive buffers, UCIe swap and
// T1 forwards, same parameters, same bit-for-bit check of every residual word)
// with the receiving module's T1 links SHARED with other users' collectives
// (tools/rtl_v41_hop_batch_campaign.py).
//
// At a pipeline fill of n users the module a hop lands on is running other
// users' tokens: their tensor-group all-reduces / all-gathers put words on the
// same eight die-to-die T1 links (d -> both dies of the other package) that the
// split hop forwards its one-package words over.  The campaign derives that
// traffic from the design-point DAG (the words each collective puts on one T1
// link and the cycle each is produced) and hands it over as data:
//   +VEC/bgrel.hex   per background word k (the same schedule on every link:
//                    the collectives are symmetric over the tensor group), the
//                    bench cycle it is produced; nondecreasing;
//   +VEC/bg.hex      per link l (at l*MAXB) the NB words' data;
//   +NB=             words per link.
// A link's background source queues its released words in order (open loop:
// the producer is not held back) and competes with the hop forwarder for the
// link's token bucket: ARB 0 round-robin (the side that did not send last wins
// a conflict), 1 hop first, 2 background first.  A hop word pops only when both
// of its T1 links grant it.  Records carry a flag bit: 0 residual word
// {index, data}, 1 background word {link-local index, data}.  Every background
// word is checked bit for bit against its source, exactly once (BGA lines), and
// every residual word as in the parent bench (ARR lines).
// ---------------------------------------------------------------------------
module tb_v41_stage_hop_load_px #(
    parameter integer LANES     = 128,
    parameter integer DEPTH     = 128,
    parameter integer DEPTH_F   = 64,
    parameter integer QTX       = 128,
    parameter integer LAT_C     = 228,
    parameter integer BPC_C     = 8485,
    parameter integer BPC_C_DEN = 100,
    parameter integer LAT_X     = 142,
    parameter integer BPC_X     = 15758,
    parameter integer BPC_X_DEN = 100,
    parameter integer LAT_U     = 11,
    parameter integer BPC_U     = 3864,
    parameter integer FLIT_OVH  = 0,
    parameter integer PUSHW     = 8,
    parameter integer MAXW      = 512,
    parameter integer MAXB      = 1024,
    parameter integer RELW      = 16      // background words released per cycle at most
) (input wire clk);
    localparam integer FW = 32 * LANES, IW = 16, PW = FW + IW + 1;   // record {bg, index, data}
    localparam integer COST = FW / 8 + FLIT_OVH;
    reg [FW-1:0] part [0:MAXW-1];
    reg [31:0]   rdy  [0:MAXW-1];
    reg [31:0]   lst  [0:4*MAXW-1];
    reg          uniq [0:MAXW-1];
    reg [FW-1:0] bgd  [0:8*MAXB-1];
    reg [31:0]   bgrel[0:MAXB-1];
    integer WORDS, START, TIMEOUT, LN0, LN1, LN2, LN3, NB, ARB;
    string dir;
    reg [3:0] rcnt = 0;
    wire rst_n = (rcnt == 4'hF);
    always @(posedge clk) if (!rst_n) rcnt <= rcnt + 1'b1;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    integer bad = 0, bgbad = 0;
    function integer lnum(input integer d);
        lnum = (d == 0) ? LN0 : (d == 1) ? LN1 : (d == 2) ? LN2 : LN3;
    endfunction

    wire [3:0]    c_send, c_rdy, c_ov, c_cr, c_pop;
    wire [4*PW-1:0] c_in, c_od;
    wire [3:0]    u_send, u_rdy, u_ov, u_cr;
    wire [4*PW-1:0] u_od;
    wire [7:0]    x_send, x_rdy, x_ov, x_cr;   // [2d + j]: d -> 2*(1 - d/2) + j
    wire [7:0]    h_ok, h_send, b_want, b_send;
    wire [8*PW-1:0] x_in, x_od;
    wire [4*PW-1:0] f_rec;

    genvar d, j;
    generate
        for (d = 0; d < 4; d = d + 1) begin : g_s
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
                            q[qtt] <= {1'b0, w[IW-1:0], part[w]};
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

        // -- background sources and the per-link arbiter --------------------------------------------------
        for (d = 0; d < 8; d = d + 1) begin : g_b
            integer rel = 0, sent = 0, qmax = 0, busy = 0, hsent = 0;
            reg last_bg = 1'b0;                  // round-robin: the side that sent last loses a conflict
            assign b_want[d] = rst_n && (sent < rel);
            wire bg_first = (ARB == 2) || (ARB == 0 && !last_bg);
            // the hop may use the link unless the background wants it and has priority
            assign h_ok[d] = x_rdy[d] && !(b_want[d] && bg_first);
            assign b_send[d] = x_rdy[d] && b_want[d] && !h_send[d];
            assign x_in[d*PW +: PW] = h_send[d] ? f_rec[(d/2)*PW +: PW] : {1'b1, sent[IW-1:0], bgd[d*MAXB + sent]};
            assign x_send[d] = h_send[d] || b_send[d];
            always @(posedge clk) begin : bsrc
                integer r, jj;
                r = rel;
                if (rst_n)
                    for (jj = 0; jj < RELW; jj = jj + 1)
                        if (r < NB && $signed(bgrel[r]) <= cyc) r = r + 1;
                rel <= r;
                if (b_send[d]) begin
                    sent <= sent + 1;
                    last_bg <= 1'b1;
                end
                else if (h_send[d]) last_bg <= 1'b0;
                if (h_send[d]) hsent <= hsent + 1;
                if (x_send[d]) busy <= busy + 1;
                if (r - sent > qmax) qmax <= r - sent;
            end
        end

        for (d = 0; d < 4; d = d + 1) begin : g_r
            localparam integer PEER = d ^ 1;
            localparam integer OTH = 2 * (1 - d / 2);
            reg [PW-1:0] b [0:DEPTH-1];
            integer h = 0, tl = 0, n = 0, nmax = 0, ovf = 0;
            integer ucred = DEPTH_F, xcred0 = DEPTH_F, xcred1 = DEPTH_F;
            reg [MAXW-1:0] got = {MAXW{1'b0}};
            reg [MAXB-1:0] bgot0 = {MAXB{1'b0}}, bgot1 = {MAXB{1'b0}};
            integer ngot = 0, rfirst = -1, rlast = -1, dup = 0, nbg = 0, bdup = 0;
            wire [IW-1:0] hw = b[h][FW +: IW];
            wire need_x = uniq[hw];
            assign c_pop[d] = (n > 0) && ucred > 0 && u_rdy[d]
                              && (!need_x || (xcred0 > 0 && xcred1 > 0 && h_ok[2*d] && h_ok[2*d + 1]));
            assign u_send[d] = c_pop[d];
            assign h_send[2*d] = c_pop[d] && need_x;
            assign h_send[2*d + 1] = c_pop[d] && need_x;
            assign f_rec[d*PW +: PW] = b[h];
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
            // a T1 arrival from link l (source die l/2): a residual word, or a background word of link l
            task automatic take_x(input [PW-1:0] rec, input integer l, input integer slot);
                integer w;
                begin
                    if (rec[PW-1]) begin
                        w = rec[FW +: IW];
                        if (rec[FW-1:0] !== bgd[l*MAXB + w]) bgbad = bgbad + 1;
                        if (slot == 0) begin
                            if (bgot0[w]) bdup = bdup + 1;
                            bgot0[w] = 1'b1;
                        end else begin
                            if (bgot1[w]) bdup = bdup + 1;
                            bgot1[w] = 1'b1;
                        end
                        nbg = nbg + 1;
                        $display("BGA link=%0d word=%0d cyc=%0d", l, w, cyc);
                    end
                    else take(rec);
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
                if (x_ov[2*OTH + (d % 2)]) take_x(x_od[(2*OTH + (d % 2))*PW +: PW], 2*OTH + (d % 2), 0);
                if (x_ov[2*(OTH + 1) + (d % 2)]) take_x(x_od[(2*(OTH + 1) + (d % 2))*PW +: PW], 2*(OTH + 1) + (d % 2), 1);
                nn = n + (c_ov[d] ? 1 : 0) - (c_pop[d] ? 1 : 0);
                n <= nn;
                if (nn > DEPTH) ovf <= 1;
                if (nn > nmax) nmax <= nn;
                ucred <= ucred - (u_send[d] ? 1 : 0) + (u_cr[d] ? 1 : 0);
                xcred0 <= xcred0 - (h_send[2*d] ? 1 : 0) + (x_cr[2*d] ? 1 : 0);
                xcred1 <= xcred1 - (h_send[2*d + 1] ? 1 : 0) + (x_cr[2*d + 1] ? 1 : 0);
            end
            ot_v41px_link #(.PW(PW), .CW(1), .LAT(LAT_U), .COST(COST), .BPC_NUM(BPC_U), .BPC_DEN(1)) u_fwd (
                .clk(clk), .rst_n(rst_n), .in_valid(u_send[d]), .in_rec(f_rec[d*PW +: PW]), .in_ready(u_rdy[d]),
                .out_valid(u_ov[d]), .out_rec(u_od[d*PW +: PW]), .cr_in(u_ov[d]), .cr_out(u_cr[d]));
            // T1 to both dies of the other package; a credit returns only for a residual word (the background
            // words are consumed on arrival by the other die's collective engine)
            for (j = 0; j < 2; j = j + 1) begin : g_x
                wire hop_arr = x_ov[2*d + j] && !x_od[(2*d + j)*PW + PW - 1];
                ot_v41px_link #(.PW(PW), .CW(1), .LAT(LAT_X), .COST(COST), .BPC_NUM(BPC_X), .BPC_DEN(BPC_X_DEN)) u_x (
                    .clk(clk), .rst_n(rst_n), .in_valid(x_send[2*d + j]), .in_rec(x_in[(2*d + j)*PW +: PW]),
                    .in_ready(x_rdy[2*d + j]), .out_valid(x_ov[2*d + j]), .out_rec(x_od[(2*d + j)*PW +: PW]),
                    .cr_in(hop_arr), .cr_out(x_cr[2*d + j]));
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
        if (!$value$plusargs("NB=%d", NB)) NB = 0;
        if (!$value$plusargs("ARB=%d", ARB)) ARB = 0;
        $readmemh({dir, "/part.hex"}, part);
        $readmemh({dir, "/ready.hex"}, rdy);
        $readmemh({dir, "/list.hex"}, lst);
        $readmemh({dir, "/uniq.hex"}, uniq);
        if (NB > 0) begin
            $readmemh({dir, "/bg.hex"}, bgd);
            $readmemh({dir, "/bgrel.hex"}, bgrel);
        end
    end
    reg fin = 1'b0;
    wire all_got = g_r[0].ngot == WORDS && g_r[1].ngot == WORDS && g_r[2].ngot == WORDS && g_r[3].ngot == WORDS;
    // every link's background words land at one receiver: 8 x NB in all
    wire all_bg = (g_r[0].nbg + g_r[1].nbg + g_r[2].nbg + g_r[3].nbg) == 8 * NB;
    always @(posedge clk) begin : fn
        integer faults, lastref;
        if (!fin && ((all_got && all_bg && cyc > START) || cyc > TIMEOUT)) fin <= 1'b1;
        if (fin) begin
            faults = g_r[0].ovf + g_r[1].ovf + g_r[2].ovf + g_r[3].ovf + g_r[0].dup + g_r[1].dup + g_r[2].dup
                     + g_r[3].dup + g_r[0].bdup + g_r[1].bdup + g_r[2].bdup + g_r[3].bdup;
            lastref = START + rdy[WORDS > 0 ? WORDS - 1 : 0];
            $display("SB die=10 start=%0d ref=%0d pushed_last=%0d stall=%0d hold=0 qmax=%0d first=-1 last=-1 fault=0 code=0",
                     START, lastref, g_s[0].pushed_last, g_s[0].stall, g_s[0].qmax);
            $display("SB die=11 start=%0d ref=%0d pushed_last=%0d stall=%0d hold=0 qmax=%0d first=-1 last=-1 fault=0 code=0",
                     START, lastref, g_s[1].pushed_last, g_s[1].stall, g_s[1].qmax);
            $display("SB die=12 start=%0d ref=%0d pushed_last=%0d stall=%0d hold=0 qmax=%0d first=-1 last=-1 fault=0 code=0",
                     START, lastref, g_s[2].pushed_last, g_s[2].stall, g_s[2].qmax);
            $display("SB die=13 start=%0d ref=%0d pushed_last=%0d stall=%0d hold=0 qmax=%0d first=-1 last=-1 fault=0 code=0",
                     START, lastref, g_s[3].pushed_last, g_s[3].stall, g_s[3].qmax);
            $display("SB die=0 start=%0d ref=%0d pushed_last=-1 stall=0 hold=0 qmax=%0d first=%0d last=%0d fault=%0d code=0",
                     START, lastref, g_r[0].nmax, g_r[0].rfirst, g_r[0].rlast, g_r[0].ovf + g_r[0].dup + g_r[0].bdup);
            $display("SB die=1 start=%0d ref=%0d pushed_last=-1 stall=0 hold=0 qmax=%0d first=%0d last=%0d fault=%0d code=0",
                     START, lastref, g_r[1].nmax, g_r[1].rfirst, g_r[1].rlast, g_r[1].ovf + g_r[1].dup + g_r[1].bdup);
            $display("SB die=2 start=%0d ref=%0d pushed_last=-1 stall=0 hold=0 qmax=%0d first=%0d last=%0d fault=%0d code=0",
                     START, lastref, g_r[2].nmax, g_r[2].rfirst, g_r[2].rlast, g_r[2].ovf + g_r[2].dup + g_r[2].bdup);
            $display("SB die=3 start=%0d ref=%0d pushed_last=-1 stall=0 hold=0 qmax=%0d first=%0d last=%0d fault=%0d code=0",
                     START, lastref, g_r[3].nmax, g_r[3].rfirst, g_r[3].rlast, g_r[3].ovf + g_r[3].dup + g_r[3].bdup);
            $display("BGL l0=%0d/%0d/%0d l1=%0d/%0d/%0d l2=%0d/%0d/%0d l3=%0d/%0d/%0d l4=%0d/%0d/%0d l5=%0d/%0d/%0d l6=%0d/%0d/%0d l7=%0d/%0d/%0d",
                     g_b[0].busy, g_b[0].hsent, g_b[0].qmax, g_b[1].busy, g_b[1].hsent, g_b[1].qmax,
                     g_b[2].busy, g_b[2].hsent, g_b[2].qmax, g_b[3].busy, g_b[3].hsent, g_b[3].qmax,
                     g_b[4].busy, g_b[4].hsent, g_b[4].qmax, g_b[5].busy, g_b[5].hsent, g_b[5].qmax,
                     g_b[6].busy, g_b[6].hsent, g_b[6].qmax, g_b[7].busy, g_b[7].hsent, g_b[7].qmax);
            $display("BGDONE bg=%0d/%0d bg_mismatches=%0d", g_r[0].nbg + g_r[1].nbg + g_r[2].nbg + g_r[3].nbg, 8 * NB,
                     bgbad);
            $display("SBDONE done=%0d mismatches=%0d out_err=%0d timeout=%0d %s", all_got && all_bg, bad, bgbad,
                     cyc > TIMEOUT, (all_got && all_bg && bad == 0 && bgbad == 0 && faults == 0) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
