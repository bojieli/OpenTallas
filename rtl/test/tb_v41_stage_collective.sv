`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Gate C7 / O2: one V4.1 layer stage's producer -> collective -> consumer, in RTL
// (Verilator; tools/rtl_v41_stage_collective_campaign.py drives it).
//
// The V4.1 ROM array's tensor group is 4 dies on a PACKAGE PAIR of 2-die packages
// (docs/ARCH_V41_RACK.md, R-L9 lanes): of each die's three one-shot peers one is in
// its own package (UCIe) and two are in the partner package (the rack's T1 board
// link, 13 lanes of 112G per die pair).  Stage hops leave the group on the rack
// cable (T2, full KP4).  This file benches the physical pieces a collective on the
// token's critical path is made of:
//
//   ot_v41sb_link            a point-to-point link: LAT cycles of flight (a ring
//                            buffer), a token-bucket byte rate of BPC_NUM / BPC_DEN
//                            bytes per cycle charged COST bytes per record (payload +
//                            framing), and a reverse credit lane with the same flight.
//   tb_v41_stage_collective  4 dies.  Per die: a PRODUCER that emits the op's output
//                            words on the schedule the campaign derives from the
//                            producing engine (+VEC/ready.hex: the cycle, in the
//                            producer's own unstalled time, at which word k is
//                            complete); a bounded output queue of QTX words between
//                            producer and collective -- when a completed word finds
//                            it full the producer STALLS (the weight tile starts a
//                            row group only while it holds an output credit); the
//                            real one-shot engine ot_rom_oneshot_die (rtl/rom/
//                            ot_rom_oneshot_allreduce.sv: a DEPTH-word receive FIFO
//                            per source, a credit per (source, destination) returned
//                            over the link, rank-order fold on ot_fp32_add_rne_pipe);
//                            and a CONSUMER taking the engine's output in its emission
//                            order.  Every output word is checked bit for bit against
//                            +VEC/exp.hex (tools/hdc_golden.fold for an all-reduce;
//                            the senders' words, index-major rank order, for an
//                            all-gather).
//   tb_v41_stage_hop         the stage hop: the sending die streams the residual from
//                            its producer through a QTX-word queue onto the cable
//                            (LAT_C, BPC_C) into the receiving die's DEPTH-word credit
//                            buffer; the receiving die consumes each word and forwards
//                            it cut-through over UCIe to its package peer (the fan-out,
//                            DEPTH_U credits), which consumes it too.
//
// Every run prints one ARR line per consumed word (die, word, cycle) and one SB line
// per die; the campaign computes the exposed times from them.  A producer's time 0
// is cycle START (+ SKEW x die); `ref` = START + ready[last] is the cycle its last
// word completes with no backpressure (the model's producer finish).
// ---------------------------------------------------------------------------
module ot_v41sb_link #(
    parameter integer PW      = 64,
    parameter integer LAT     = 11,
    parameter integer COST    = 512,      // bytes a record costs on the link (payload + framing)
    parameter integer BPC_NUM = 3864,     // bytes per cycle = BPC_NUM / BPC_DEN
    parameter integer BPC_DEN = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          in_valid,
    input  wire [PW-1:0] in_rec,
    output wire          in_ready,
    output wire          out_valid,
    output wire [PW-1:0] out_rec,
    input  wire          cr_in,           // credit issued at the receiver
    output wire          cr_out           // ... arriving at the sender LAT cycles later
);
    localparam integer C   = COST * BPC_DEN;
    // the bucket holds one record plus a cycle's accrual, so a fractional rate keeps its remainder (a cap at one
    // record would round every record up to whole cycles: 3.25 -> 4 cycles per 512 B on the T1 link)
    localparam integer CAP = C + BPC_NUM;
    localparam integer AB  = (LAT > 1) ? $clog2(LAT) : 1;
    reg [39:0] tokens;
    assign in_ready = tokens >= C;
    wire send = in_valid && in_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tokens <= CAP;
        else tokens <= ((tokens - (send ? C : 0) + BPC_NUM) > CAP) ? CAP : (tokens - (send ? C : 0) + BPC_NUM);
    end
    reg [PW-1:0] dring [0:LAT-1];
    reg [LAT-1:0] vring;
    reg [LAT-1:0] cring;
    reg [AB-1:0] ptr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ptr <= 0;
            vring <= {LAT{1'b0}};
            cring <= {LAT{1'b0}};
        end else begin
            vring[ptr] <= send;
            cring[ptr] <= cr_in;
            ptr <= (ptr == LAT - 1) ? {AB{1'b0}} : ptr + 1'b1;
        end
    end
    always @(posedge clk) dring[ptr] <= in_rec;
    // the slot about to be overwritten was written LAT cycles ago
    assign out_valid = vring[ptr];
    assign out_rec   = dring[ptr];
    assign cr_out    = cring[ptr];
endmodule

// ---------------------------------------------------------------------------
module tb_v41_stage_collective #(
    parameter integer N         = 4,
    parameter integer LANES     = 128,
    parameter integer DEPTH     = 64,     // one-shot receive FIFO words per source (credits per link)
    parameter integer QTX       = 16,     // producer output queue words
    parameter integer PKG_DIES  = 2,
    parameter integer LAT_U     = 11,     // UCIe 10 ns at 1.087 GHz
    parameter integer BPC_U     = 3864,   // 4.2 TB/s
    parameter integer BPC_U_DEN = 1,
    parameter integer LAT_X     = 141,    // T1 board link 130 ns (light FEC, incl. CDC + endpoint)
    parameter integer BPC_X     = 15759,  // 13 lanes x 13.18 GB/s = 157.59 B/cycle
    parameter integer BPC_X_DEN = 100,
    parameter integer FLIT_OVH  = 0,      // framing bytes per record beyond the lane's net rate
    parameter integer PUSHW     = 8,      // words per cycle the producer's collector can write
    parameter integer MAXW      = 512
) (input wire clk);
    localparam integer FW = 32 * LANES, TAGW = 32, RB = $clog2(N), PW = FW + 2 + TAGW;
    reg [FW-1:0] part [0:N*MAXW-1];
    reg [FW-1:0] expw [0:N*MAXW-1];
    reg [31:0]   rdy  [0:N*MAXW-1];
    integer WORDS, MODE, START, SKEW, TIMEOUT;
    string dir;
    reg [3:0] rcnt = 0;
    wire rst_n = (rcnt == 4'hF);
    always @(posedge clk) if (!rst_n) rcnt <= rcnt + 1'b1;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // -- the one-shot dies and their links ---------------------------------------------
    wire [N-1:0]    iv, ir, ov, ol, oe, flt, il;
    wire [N*FW-1:0] id, od;
    wire [N*RB-1:0] orank;
    wire [N*3-1:0]  fc;
    wire [N-1:0]    txv;
    wire [N*PW-1:0] txr;
    wire [N*N-1:0]  txrdy, crin, rxv, crout;
    wire [N*N*PW-1:0] rxr;
    genvar s, t;
    generate
        for (s = 0; s < N; s = s + 1) begin : g_die
            ot_rom_oneshot_die #(.N(N), .RANK(s), .LANES(LANES), .TAGW(TAGW), .DEPTH(DEPTH)) u_die (
                .clk(clk), .rst_n(rst_n),
                .in_valid(iv[s]), .in_ready(ir[s]), .in_data(id[s*FW +: FW]), .in_last(il[s]),
                .in_mode(MODE[0]), .in_tag(32'd7),
                .tx_valid(txv[s]), .tx_rec(txr[s*PW +: PW]), .tx_ready(txrdy[s*N +: N]), .cr_in(crin[s*N +: N]),
                .rx_valid(rxv[s*N +: N]), .rx_rec(rxr[s*N*PW +: N*PW]), .cr_out(crout[s*N +: N]),
                .out_valid(ov[s]), .out_data(od[s*FW +: FW]), .out_last(ol[s]),
                .out_rank(orank[s*RB +: RB]), .out_err(oe[s]), .fault(flt[s]), .fault_code(fc[s*3 +: 3]));
            for (t = 0; t < N; t = t + 1) begin : g_to
                if (t == s) begin : g_self
                    assign txrdy[s*N + t] = 1'b1;
                    assign crin[s*N + t] = 1'b0;
                    assign rxv[s*N + t] = 1'b0;
                    assign rxr[(s*N + t)*PW +: PW] = {PW{1'b0}};
                end else begin : g_link
                    localparam integer SAME = (s / PKG_DIES) == (t / PKG_DIES);
                    ot_v41sb_link #(.PW(PW), .LAT(SAME ? LAT_U : LAT_X), .COST(FW / 8 + FLIT_OVH),
                                    .BPC_NUM(SAME ? BPC_U : BPC_X), .BPC_DEN(SAME ? BPC_U_DEN : BPC_X_DEN)) u_link (
                        .clk(clk), .rst_n(rst_n),
                        .in_valid(txv[s]), .in_rec(txr[s*PW +: PW]), .in_ready(txrdy[s*N + t]),
                        .out_valid(rxv[t*N + s]), .out_rec(rxr[(t*N + s)*PW +: PW]),
                        .cr_in(crout[t*N + s]), .cr_out(crin[s*N + t]));
                end
            end
        end
    endgenerate

    reg fin = 1'b0;
    integer bad = 0, errs = 0;
    wire [N-1:0] done;
    generate
        for (s = 0; s < N; s = s + 1) begin : g_pc
            // -- producer and its output queue ------------------------------------------------
            reg [FW-1:0] q [0:QTX-1];
            integer ptime = 0, k = 0, qh = 0, qt = 0, qn = 0, sent = 0;
            integer pushed_last = -1, stall = 0, hold = 0, qmax = 0;
            wire go = rst_n && (cyc >= START + SKEW * s);
            wire take = iv[s] && ir[s];
            always @(posedge clk) begin : step
                integer kk, qtt, np, jj, nq;
                kk = k; qtt = qt; np = 0;
                if (go) begin
                    for (jj = 0; jj < PUSHW; jj = jj + 1)
                        if (kk < WORDS && rdy[s*MAXW + kk] <= ptime && qn + np < QTX) begin
                            q[qtt] <= part[s*MAXW + kk];
                            qtt = (qtt == QTX - 1) ? 0 : qtt + 1;
                            np = np + 1;
                            if (kk == WORDS - 1) pushed_last <= cyc;
                            kk = kk + 1;
                        end
                    if (kk < WORDS && rdy[s*MAXW + kk] <= ptime) begin   // completed, not written: time waits
                        if (qn + np >= QTX) stall <= stall + 1;         // ... because the queue is full
                    end
                    else ptime <= ptime + 1;
                end
                k <= kk;
                qt <= qtt;
                if (take) begin
                    qh <= (qh == QTX - 1) ? 0 : qh + 1;
                    sent <= sent + 1;
                end
                if (qn > 0 && !take) hold <= hold + 1;
                nq = qn + np - (take ? 1 : 0);
                qn <= nq;
                if (nq > qmax) qmax <= nq;
            end
            assign iv[s] = qn > 0;
            assign id[s*FW +: FW] = q[qh];
            assign il[s] = (sent == WORDS - 1);
            // -- consumer: every output word, in the engine's emission order ------------------
            integer rk = 0, first = -1, lastc = -1;
            assign done[s] = rk == (MODE[0] ? N * WORDS : WORDS);
            always @(posedge clk) if (ov[s]) begin : chk
                integer per;
                reg [FW-1:0] e;
                per = MODE[0] ? N * WORDS : WORDS;
                e = MODE[0] ? part[(rk % N)*MAXW + rk / N] : expw[rk];
                if (oe[s]) errs = errs + 1;
                if (od[s*FW +: FW] !== e) begin
                    bad = bad + 1;
                    if (bad < 5) $display("MISMATCH die=%0d word=%0d", s, rk);
                end
                if (MODE[0] && orank[s*RB +: RB] != rk % N) bad = bad + 1;
                if (ol[s] != (rk == per - 1)) bad = bad + 1;
                $display("ARR die=%0d word=%0d cyc=%0d", s, rk, cyc);
                if (first < 0) first <= cyc;
                lastc <= cyc;
                rk <= rk + 1;
            end
            always @(posedge clk) if (fin)
                $display("SB die=%0d start=%0d ref=%0d pushed_last=%0d stall=%0d hold=%0d qmax=%0d first=%0d last=%0d fault=%0d code=%0d",
                         s, START + SKEW * s, START + SKEW * s + rdy[s*MAXW + WORDS - 1], pushed_last, stall, hold,
                         qmax, first, lastc, flt[s], fc[s*3 +: 3]);
        end
    endgenerate

    initial begin
        if (!$value$plusargs("VEC=%s", dir)) dir = ".";
        if (!$value$plusargs("WORDS=%d", WORDS)) WORDS = 40;
        if (!$value$plusargs("MODE=%d", MODE)) MODE = 0;
        if (!$value$plusargs("START=%d", START)) START = 20;
        if (!$value$plusargs("SKEW=%d", SKEW)) SKEW = 0;
        if (!$value$plusargs("TIMEOUT=%d", TIMEOUT)) TIMEOUT = 200000;
        $readmemh({dir, "/part.hex"}, part);
        $readmemh({dir, "/exp.hex"}, expw);
        $readmemh({dir, "/ready.hex"}, rdy);
    end
    always @(posedge clk) begin
        if (!fin && (&done || cyc > TIMEOUT)) fin <= 1'b1;
        if (fin) begin
            $display("SBDONE done=%0d mismatches=%0d out_err=%0d timeout=%0d %s", &done, bad, errs, cyc > TIMEOUT,
                     (&done && bad == 0 && errs == 0 && flt == 0) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule

// ---------------------------------------------------------------------------
// The stage hop: sending die S -> rack cable -> receiving die R0 (credit buffer of
// DEPTH words, credits back over the cable's reverse lane) -> cut-through over UCIe
// -> R0's package peer R1 (credit buffer of DEPTH_U words).  Both receivers consume
// every word; ARR lines give R0 as die 1 and R1 as die 2.
// ---------------------------------------------------------------------------
module tb_v41_stage_hop #(
    parameter integer LANES     = 128,
    parameter integer DEPTH     = 64,
    parameter integer DEPTH_U   = 16,
    parameter integer QTX       = 16,
    parameter integer LAT_C     = 227,    // T2 rack cable 209 ns (full KP4, incl. CDC + endpoint)
    parameter integer BPC_C     = 16972,  // 14 lanes x 13.18 GB/s = 169.72 B/cycle
    parameter integer BPC_C_DEN = 100,
    parameter integer LAT_U     = 11,
    parameter integer BPC_U     = 3864,
    parameter integer FLIT_OVH  = 0,
    parameter integer PUSHW     = 8,
    parameter integer MAXW      = 512
) (input wire clk);
    localparam integer FW = 32 * LANES;
    reg [FW-1:0] part [0:MAXW-1];
    reg [31:0]   rdy  [0:MAXW-1];
    integer WORDS, START, TIMEOUT;
    string dir;
    reg [3:0] rcnt = 0;
    wire rst_n = (rcnt == 4'hF);
    always @(posedge clk) if (!rst_n) rcnt <= rcnt + 1'b1;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    integer bad = 0;

    // -- S: producer, queue, cable credits ------------------------------------------------------
    reg [FW-1:0] q [0:QTX-1];
    integer ptime = 0, k = 0, qh = 0, qt = 0, qn = 0;
    integer pushed_last = -1, stall = 0, hold = 0, qmax = 0;
    integer cred = DEPTH;
    wire go = rst_n && (cyc >= START);
    wire c_rdy, c_ov, c_cr;
    wire [FW-1:0] c_od;
    wire s_send = (qn > 0) && (cred > 0) && c_rdy;
    reg  r0_pop = 1'b0;
    always @(posedge clk) begin : step
        integer kk, qtt, np, jj, nq;
        kk = k; qtt = qt; np = 0;
        if (go) begin
            for (jj = 0; jj < PUSHW; jj = jj + 1)
                if (kk < WORDS && rdy[kk] <= ptime && qn + np < QTX) begin
                    q[qtt] <= part[kk];
                    qtt = (qtt == QTX - 1) ? 0 : qtt + 1;
                    np = np + 1;
                    if (kk == WORDS - 1) pushed_last <= cyc;
                    kk = kk + 1;
                end
            if (kk < WORDS && rdy[kk] <= ptime) begin
                if (qn + np >= QTX) stall <= stall + 1;
            end
            else ptime <= ptime + 1;
        end
        k <= kk;
        qt <= qtt;
        if (s_send) qh <= (qh == QTX - 1) ? 0 : qh + 1;
        if (qn > 0 && !s_send) hold <= hold + 1;
        nq = qn + np - (s_send ? 1 : 0);
        qn <= nq;
        if (nq > qmax) qmax <= nq;
        cred <= cred - (s_send ? 1 : 0) + (c_cr ? 1 : 0);
    end
    ot_v41sb_link #(.PW(FW), .LAT(LAT_C), .COST(FW / 8 + FLIT_OVH), .BPC_NUM(BPC_C), .BPC_DEN(BPC_C_DEN)) u_cable (
        .clk(clk), .rst_n(rst_n), .in_valid(s_send), .in_rec(q[qh]), .in_ready(c_rdy),
        .out_valid(c_ov), .out_rec(c_od), .cr_in(r0_pop), .cr_out(c_cr));

    // -- R0: DEPTH-word buffer; a word is consumed and forwarded in the same cycle ----------------
    reg [FW-1:0] b0 [0:DEPTH-1];
    integer h0 = 0, t0 = 0, n0 = 0, n0max = 0, r0k = 0, r0first = -1, r0last = -1, ovf = 0;
    integer ucred = DEPTH_U;
    wire u_rdy, u_ov, u_cr;
    wire [FW-1:0] u_od;
    wire fwd = (n0 > 0) && (ucred > 0) && u_rdy;
    always @(posedge clk) begin : r0
        integer nn;
        r0_pop <= fwd;
        if (c_ov) begin
            b0[t0] <= c_od;
            t0 <= (t0 == DEPTH - 1) ? 0 : t0 + 1;
        end
        if (fwd) begin
            if (b0[h0] !== part[r0k]) bad = bad + 1;
            $display("ARR die=1 word=%0d cyc=%0d", r0k, cyc);
            if (r0first < 0) r0first <= cyc;
            r0last <= cyc;
            r0k <= r0k + 1;
            h0 <= (h0 == DEPTH - 1) ? 0 : h0 + 1;
        end
        nn = n0 + (c_ov ? 1 : 0) - (fwd ? 1 : 0);
        n0 <= nn;
        if (nn > DEPTH) ovf <= 1;
        if (nn > n0max) n0max <= nn;
        ucred <= ucred - (fwd ? 1 : 0) + (u_cr ? 1 : 0);
    end
    ot_v41sb_link #(.PW(FW), .LAT(LAT_U), .COST(FW / 8 + FLIT_OVH), .BPC_NUM(BPC_U), .BPC_DEN(1)) u_fan (
        .clk(clk), .rst_n(rst_n), .in_valid(fwd), .in_rec(b0[h0]), .in_ready(u_rdy),
        .out_valid(u_ov), .out_rec(u_od), .cr_in(u_ov), .cr_out(u_cr));
    // -- R1 consumes on arrival (its buffer slot frees the same cycle) ---------------------------
    integer r1k = 0, r1first = -1, r1last = -1;
    always @(posedge clk) if (u_ov) begin
        if (u_od !== part[r1k]) bad = bad + 1;
        $display("ARR die=2 word=%0d cyc=%0d", r1k, cyc);
        if (r1first < 0) r1first <= cyc;
        r1last <= cyc;
        r1k <= r1k + 1;
    end

    initial begin
        if (!$value$plusargs("VEC=%s", dir)) dir = ".";
        if (!$value$plusargs("WORDS=%d", WORDS)) WORDS = 80;
        if (!$value$plusargs("START=%d", START)) START = 20;
        if (!$value$plusargs("TIMEOUT=%d", TIMEOUT)) TIMEOUT = 200000;
        $readmemh({dir, "/part.hex"}, part);
        $readmemh({dir, "/ready.hex"}, rdy);
    end
    reg fin = 1'b0;
    always @(posedge clk) begin
        if (!fin && (r1k == WORDS || cyc > TIMEOUT)) fin <= 1'b1;
        if (fin) begin
            $display("SB die=0 start=%0d ref=%0d pushed_last=%0d stall=%0d hold=%0d qmax=%0d first=-1 last=-1 fault=0 code=0",
                     START, START + rdy[WORDS - 1], pushed_last, stall, hold, qmax);
            $display("SB die=1 start=%0d ref=%0d pushed_last=-1 stall=0 hold=0 qmax=%0d first=%0d last=%0d fault=%0d code=0",
                     START, START + rdy[WORDS - 1], n0max, r0first, r0last, ovf);
            $display("SB die=2 start=%0d ref=%0d pushed_last=-1 stall=0 hold=0 qmax=0 first=%0d last=%0d fault=0 code=0",
                     START, START + rdy[WORDS - 1], r1first, r1last);
            $display("SBDONE done=%0d mismatches=%0d out_err=0 timeout=%0d %s", r1k == WORDS, bad, cyc > TIMEOUT,
                     (r1k == WORDS && bad == 0 && ovf == 0) ? "PASS" : "FAIL");
            $finish;
        end
    end
endmodule
