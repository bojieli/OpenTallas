`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Gate C7 / O2 LEVER bench (tools/rtl_v41_collective_levers_campaign.py): the
// same producer -> collective -> consumer stage as tb_v41_stage_collective
// (rtl/test/tb_v41_stage_collective.sv: the same producer schedules, output
// queue and backpressure, the same package-pair links at the same latencies and
// rates, the same bit-for-bit check of every output word), with the lever
// engine rtl/rom/ot_rom_oneshot_px.sv ot_rom_oneshot_die_px in place of
// ot_rom_oneshot_die:
//
//   RELAY    1: each T1 link carries half the words; the receiving die relays
//            them to its package peer over UCIe (a relay channel per source,
//            LAT_U flight; at most 3 records of 512 B per cycle leave a die on
//            UCIe, 40% of its 3,864 B/cycle, so the relay channels are not
//            rate-limited separately).
//   ADD_LAT  3 (ot_hdc_fp32_add_fast) or 5 (ot_fp32_add_rne_pipe).
//   GW       gather words emitted per cycle, no inter-index bubble.
//
// Links are ot_v41px_link: ot_v41sb_link's flight ring and token bucket (the
// bucket keeps its fractional remainder) with a CW-bit reverse credit lane,
// here one credit per index parity.
// ---------------------------------------------------------------------------
module ot_v41px_link #(
    parameter integer PW      = 64,
    parameter integer CW      = 2,
    parameter integer LAT     = 11,
    parameter integer COST    = 512,
    parameter integer BPC_NUM = 3864,
    parameter integer BPC_DEN = 1,
    parameter integer RATED   = 1       // 0: flight only (a channel whose rate cannot bind)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          in_valid,
    input  wire [PW-1:0] in_rec,
    output wire          in_ready,
    output wire          out_valid,
    output wire [PW-1:0] out_rec,
    input  wire [CW-1:0] cr_in,
    output wire [CW-1:0] cr_out
);
    localparam integer C   = COST * BPC_DEN;
    localparam integer CAP = C + BPC_NUM;
    localparam integer AB  = (LAT > 1) ? $clog2(LAT) : 1;
    reg [39:0] tokens;
    assign in_ready = (RATED == 0) || tokens >= C;
    wire send = in_valid && in_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) tokens <= CAP;
        else tokens <= ((tokens - (send ? C : 0) + BPC_NUM) > CAP) ? CAP : (tokens - (send ? C : 0) + BPC_NUM);
    end
    reg [PW-1:0] dring [0:LAT-1];
    reg [LAT-1:0] vring;
    reg [CW*LAT-1:0] cring;
    reg [AB-1:0] ptr;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ptr <= 0;
            vring <= {LAT{1'b0}};
            cring <= {CW*LAT{1'b0}};
        end else begin
            vring[ptr] <= send;
            cring[ptr*CW +: CW] <= cr_in;
            ptr <= (ptr == LAT - 1) ? {AB{1'b0}} : ptr + 1'b1;
        end
    end
    always @(posedge clk) dring[ptr] <= in_rec;
    assign out_valid = vring[ptr];
    assign out_rec   = dring[ptr];
    assign cr_out    = cring[ptr*CW +: CW];
endmodule

// ---------------------------------------------------------------------------
module tb_v41_stage_collective_px_gw4_bank #(
    parameter integer N         = 4,
    parameter integer LANES     = 128,
    parameter integer DEPTH     = 64,     // receive words per source (both parities)
    parameter integer QTX       = 16,
    parameter integer PKG_DIES  = 2,
    parameter integer RELAY     = 1,
    parameter integer ADD_LAT   = 3,
    parameter integer PAIRWISE  = 0,
    parameter integer GW        = 1,
    parameter integer LAT_U     = 11,
    parameter integer BPC_U     = 3864,
    parameter integer BPC_U_DEN = 1,
    parameter integer LAT_X     = 141,
    parameter integer BPC_X     = 15759,
    parameter integer BPC_X_DEN = 100,
    parameter integer FLIT_OVH  = 0,
    parameter integer PUSHW     = 8,
    parameter integer MAXW      = 512
) (input wire clk);
    localparam integer FW = 32 * LANES, TAGW = 32, RB = $clog2(N), PW = FW + 3 + TAGW;
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

    wire [N-1:0]    iv, ir, ov, ol, oe, flt, il;
    wire [N*FW-1:0] id;
    wire [N*GW*FW-1:0] od;
    wire [N*RB-1:0] orank;
    wire [N*3-1:0]  fc;
    wire [N*N-1:0]  txv, txrdy, rxv;
    wire [N*PW-1:0] txr;
    wire [N*N*PW-1:0] rxr;
    wire [2*N*N-1:0]  crin, crout;
    wire [N*N-1:0]    rltv, rlrv;
    wire [N*N*PW-1:0] rltr, rlrr;
    wire [N-1:0] bank_in_ready;
    genvar s, t;
    generate
        for (s = 0; s < N; s = s + 1) begin : g_die
            ot_rom_oneshot_die_px #(.N(N), .RANK(s), .LANES(LANES), .TAGW(TAGW), .DEPTH(DEPTH), .PKG_DIES(PKG_DIES),
                                    .RELAY(RELAY), .ADD_LAT(ADD_LAT), .PAIRWISE(PAIRWISE), .GW(GW), .OUT_BP(1)) u_die (
                .clk(clk), .rst_n(rst_n),
                .in_valid(iv[s]), .in_ready(ir[s]), .in_data(id[s*FW +: FW]), .in_last(il[s]),
                .in_mode(MODE[0]), .in_tag(32'd7),
                .tx_valid(txv[s*N +: N]), .tx_rec(txr[s*PW +: PW]), .tx_ready(txrdy[s*N +: N]),
                .cr_in(crin[2*s*N +: 2*N]),
                .rx_valid(rxv[s*N +: N]), .rx_rec(rxr[s*N*PW +: N*PW]), .cr_out(crout[2*s*N +: 2*N]),
                .rl_tx_valid(rltv[s*N +: N]), .rl_tx_rec(rltr[s*N*PW +: N*PW]),
                .rl_rx_valid(rlrv[s*N +: N]), .rl_rx_rec(rlrr[s*N*PW +: N*PW]),
                .out_valid(ov[s]), .out_ready(bank_in_ready[s]), .out_data(od[s*GW*FW +: GW*FW]), .out_last(ol[s]),
                .out_rank(orank[s*RB +: RB]), .out_err(oe[s]), .fault(flt[s]), .fault_code(fc[s*3 +: 3]));
            for (t = 0; t < N; t = t + 1) begin : g_to
                localparam integer SAME = (s / PKG_DIES) == (t / PKG_DIES);
                if (t == s) begin : g_self
                    assign txrdy[s*N + t] = 1'b1;
                    assign crin[2*(s*N + t) +: 2] = 2'b00;
                    assign rxv[s*N + t] = 1'b0;
                    assign rxr[(s*N + t)*PW +: PW] = {PW{1'b0}};
                end else begin : g_link
                    // link s -> t: data to die t's port s; parity credits from die t's port s back to s
                    ot_v41px_link #(.PW(PW), .CW(2), .LAT(SAME ? LAT_U : LAT_X), .COST(FW / 8 + FLIT_OVH),
                                    .BPC_NUM(SAME ? BPC_U : BPC_X), .BPC_DEN(SAME ? BPC_U_DEN : BPC_X_DEN)) u_link (
                        .clk(clk), .rst_n(rst_n),
                        .in_valid(txv[s*N + t]), .in_rec(txr[s*PW +: PW]), .in_ready(txrdy[s*N + t]),
                        .out_valid(rxv[t*N + s]), .out_rec(rxr[(t*N + s)*PW +: PW]),
                        .cr_in(crout[2*(t*N + s) +: 2]), .cr_out(crin[2*(s*N + t) +: 2]));
                end
                // relay channel die s -> its package peer, for source t's records
                if (PKG_DIES == 2) begin : g_rl
                    localparam integer PEER = s ^ 1;
                    ot_v41px_link #(.PW(PW), .CW(1), .LAT(LAT_U), .RATED(0)) u_rl (
                        .clk(clk), .rst_n(rst_n),
                        .in_valid(rltv[s*N + t]), .in_rec(rltr[(s*N + t)*PW +: PW]), .in_ready(),
                        .out_valid(rlrv[PEER*N + t]), .out_rec(rlrr[(PEER*N + t)*PW +: PW]),
                        .cr_in(1'b0), .cr_out());
                end
            end
        end
    endgenerate

    reg fin = 1'b0;
    integer bad = 0, errs = 0;
    wire [N-1:0] done;
    generate
        for (s = 0; s < N; s = s + 1) begin : g_pc
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
                    if (kk < WORDS && rdy[s*MAXW + kk] <= ptime) begin
                        if (qn + np >= QTX) stall <= stall + 1;
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
            // -- GW4 engine -> double-buffered rank-major VM transpose ------------------
            localparam integer VWA=12, DST=101;
            wire tr_out_valid, tr_out_last, tr_done, tr_fault;
            wire [3:0] tr_we;
            wire [4*VWA-1:0] tr_addr;
            wire [4*FW-1:0] tr_data;
            integer accepted=0, rk=0, first=-1, lastc=-1;
            ot_chip_v41x_coll_transpose #(.WA(VWA),.FW(FW)) u_tr (
                .clk(clk),.rst_n(rst_n),
                .start(rst_n && cyc == START + SKEW*s - 1),.dst(VWA'(DST)),.n(VWA'(WORDS)),
                .in_ready(bank_in_ready[s]),.in_valid(ov[s]),
                .in_data(od[s*GW*FW +: GW*FW]),.in_last(ol[s]),
                .out_ready(1'b1),.out_valid(tr_out_valid),.out_we(tr_we),
                .out_addr(tr_addr),.out_data(tr_data),.out_last(tr_out_last),
                .done(tr_done),.fault(tr_fault));
            assign done[s] = rk == N*WORDS;
            always @(posedge clk) if (ov[s] && bank_in_ready[s]) begin : eng_chk
                if (oe[s]) errs = errs + 1;
                if (orank[s*RB +: RB] != 0) bad = bad + 1;
                if (ol[s] != (accepted == WORDS-1)) bad = bad + 1;
                for (integer w=0;w<N;w=w+1)
                    if (od[(s*GW+w)*FW +: FW] !== part[w*MAXW+accepted]) bad = bad + 1;
                accepted <= accepted+1;
            end
            always @(posedge clk) if (tr_out_valid) begin : bank_chk
                integer addr, rank, idx, wc;
                wc=0;
                for (integer w=0;w<4;w=w+1) if (tr_we[w]) begin
                    addr=tr_addr[w*VWA +: VWA];
                    rank=(addr-DST)/WORDS;idx=(addr-DST)%WORDS;
                    if (addr<DST || addr>=DST+N*WORDS || rank<0 || rank>=N || idx<0 || idx>=WORDS)
                        bad=bad+1;
                    else if (tr_data[w*FW +: FW] !== part[rank*MAXW+idx]) bad=bad+1;
                    $display("ARR die=%0d word=%0d cyc=%0d",s,rank*WORDS+idx,cyc);
                    wc=wc+1;
                end
                if (first<0) first<=cyc;
                lastc<=cyc;
                rk<=rk+wc;
            end
            always @(posedge clk) if (tr_fault) bad=bad+1;
            always @(posedge clk) if (fin)
                $display("SB die=%0d start=%0d ref=%0d pushed_last=%0d stall=%0d hold=%0d qmax=%0d first=%0d last=%0d fault=%0d code=%0d",
                         s, START + SKEW * s, START + SKEW * s + rdy[s*MAXW + WORDS - 1], pushed_last, stall, hold,
                         qmax, first, lastc, flt[s] | tr_fault, fc[s*3 +: 3]);
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
