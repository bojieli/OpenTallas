`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Performance + bit-exactness bench of the V4.1x weight-engine tile
// (rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv), driven by
// tools/rtl_hdc_v41x_wgt_campaign.py.  Verilator (clock from
// rtl/test/hdc_v41x_wgt_harness.cpp).
//
// The bench holds the behavioural models of what sits around a tile on the die:
//   * the banked weight ROM (rd_w) and, for a pooled tile, the operand stream
//     (rd_k: the HBM index-key stream / the KV row staging buffer): bank j of
//     the tile answers the request bus of its chain position (j mod 8) exactly
//     RL cycles later with mem[a * L + j] of the memory the request's rq_src
//     names;
//   * the activation broadcast buffer: lane j gets, for each of M positions,
//     term t of activation row (row mod xr) of the op named by the request's
//     tag (row, t: the tile's lane mapping, split or not), RL cycles later,
//     +0 past the row's last term;
//   * the output consumer: returns one credit per result event, immediately
//     or (+throttle=N) after a pseudo-random delay of up to N cycles.
// Ops are issued back to back (+gap=0, the throughput run) or one at a time
// (+gap=1: the next descriptor waits until the tile is idle and every result
// of the previous op has left; each op's latency is printed).
//
// Files (plusargs, $readmemh): +ops (16 x 32-bit words per op: plg, nb, nrows,
// wbase, ind, eid, estride, fp4, xbase, nevents, src, split, xr, -, -, -),
// +rom, +kmem, +xmem, +exp (per result event: rg, tag, mask, smask, then per
// segment s and position p: fp32, bf16, fault; then per chunk unit s and p the
// split first row: fp32, bf16, fault).
// Summary: "V41XWGT ops=.. events=.. checked=.. errors=.. faults=.. cycles=..
//           beats=.. first_beat=.. last_beat=.. last_out=.. start=.. cnt=.."
//           then per op "V41XWGT_LAT op=.. cycles=..".
// ---------------------------------------------------------------------------
module tb_hdc_v41x_wgt #(
    parameter integer KIND = 0,
    parameter integer G = 1,
    parameter integer M = 1,
    parameter integer LB = 5,
    parameter integer PMIN_LG = 0,
    parameter integer RL = 2,
    parameter integer NBW = 14,
    parameter integer POOL = 0,
    parameter integer MAXOPS = 256,
    parameter integer ROMD = 1 << 18,
    parameter integer XMD = 1 << 18,
    parameter integer EXPD = 1 << 20
) (
    input wire clk
);
    localparam integer L = 8 * G;
    localparam integer NC = G >> PMIN_LG;
    localparam integer WW = KIND ? 34 : 264;
    localparam integer XW = KIND ? 16 : 264;
    localparam integer AW = 20, RWW = 16, EIW = 9, TGW = 4, OPW = 16;
    localparam integer EVW = 4 + 3 * NC * M + 3 * G * M;

    reg rst_n = 1'b0;
    reg [31:0] opm [0:MAXOPS*OPW-1];
    reg [WW-1:0] rom [0:ROMD-1];
    reg [WW-1:0] kmem [0:ROMD-1];
    reg [XW-1:0] xmem [0:XMD-1];
    reg [31:0] expm [0:EXPD-1];

    // DUT
    reg                 d_v;
    wire                d_rdy;
    reg  [3:0]          d_plg;
    reg  [NBW-1:0]      d_nb;
    reg  [RWW-1:0]      d_nrows;
    reg  [AW-1:0]       d_wbase, d_estride;
    reg                 d_ind, d_fp4, d_src, d_split;
    reg  [EIW-1:0]      d_eid;
    reg  [TGW-1:0]      d_tag;
    wire [7:0]          rq_v, rq_src, rq_split;
    wire [8*AW-1:0]     rq_a;
    wire [8*NBW-1:0]    rq_q;
    wire [8*4-1:0]      rq_plg;
    wire [8*TGW-1:0]    rq_tag;
    wire [8*RWW-1:0]    rq_rg;
    reg  [L*WW-1:0]     rd_w, rd_k;
    reg  [L*M*XW-1:0]   rd_x;
    reg                 o_cr;
    wire                o_v;
    wire [RWW-1:0]      o_rg;
    wire [TGW-1:0]      o_tag;
    wire [NC-1:0]       o_mask;
    wire [NC*M*32-1:0]  o_y;
    wire [NC*M*16-1:0]  o_bf;
    wire [NC*M-1:0]     o_f;
    wire [G-1:0]        o_smask;
    wire [G*M*32-1:0]   o_ys;
    wire [G*M*16-1:0]   o_bfs;
    wire [G*M-1:0]      o_fs;
    wire [31:0]         cnt_rom, cnt_stream, cnt_split;
    wire                idle;

    ot_hdc_v41x_wgt_tile #(.KIND(KIND), .G(G), .M(M), .LB(LB), .PMIN_LG(PMIN_LG), .AW(AW), .NBW(NBW), .RWW(RWW),
                           .EIW(EIW), .TGW(TGW), .RL(RL), .OCRED(128), .POOL(POOL)) dut (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_fp4(d_fp4), .d_tag(d_tag),
        .d_src(d_src), .d_split(d_split),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rq_src(rq_src),
        .rq_split(rq_split), .rq_rg(rq_rg), .rd_w(rd_w), .rd_k(rd_k), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .o_smask(o_smask), .o_ys(o_ys), .o_bfs(o_bfs), .o_fs(o_fs), .o_cnt_rom(cnt_rom),
        .o_cnt_stream(cnt_stream), .o_cnt_split(cnt_split), .idle(idle));

    // -- read network model: RL register stages ----------------------------------------------------
    reg [L*WW-1:0]   pw [0:RL-1];
    reg [L*WW-1:0]   pk [0:RL-1];
    reg [L*M*XW-1:0] px [0:RL-1];
    reg [31:0] tab_xbase [0:15];
    reg [31:0] tab_nb [0:15];
    reg [31:0] tab_xr [0:15];
    integer j, c, p, st, blk, pp, tg, row, pl;
    reg [WW-1:0] wd;
    always @(posedge clk) begin
        for (j = 0; j < L; j = j + 1) begin
            c = j % 8;
            if (rq_v[c]) begin
                wd = rq_src[c] ? kmem[rq_a[c*AW +: AW] * L + j] : rom[rq_a[c*AW +: AW] * L + j];
                pw[0][j*WW +: WW] <= rq_src[c] ? {WW{1'bx}} : wd;
                pk[0][j*WW +: WW] <= rq_src[c] ? wd : {WW{1'bx}};
                tg = rq_tag[c*TGW +: TGW];
                pl = rq_plg[c*4 +: 4];
                if (rq_split[c]) begin
                    row = rq_rg[c*RWW +: RWW] * 2 * G + 2 * (j / 8) + (((j % 8) >= 4) ? 1 : 0);
                    blk = j % 4;
                end else begin
                    pp = 8 << pl;
                    row = rq_rg[c*RWW +: RWW] * (G >> pl) + j / pp;
                    blk = rq_q[c*NBW +: NBW] * pp + (j % pp);
                end
                for (p = 0; p < M; p = p + 1)
                    px[0][(j*M + p)*XW +: XW] <= (blk < tab_nb[tg]) ?
                        xmem[tab_xbase[tg] + ((row % tab_xr[tg]) * tab_nb[tg] + blk) * M + p] : {XW{1'b0}};
            end else begin
                pw[0][j*WW +: WW] <= {WW{1'bx}};
                pk[0][j*WW +: WW] <= {WW{1'bx}};
                for (p = 0; p < M; p = p + 1) px[0][(j*M + p)*XW +: XW] <= {XW{1'bx}};
            end
        end
        for (st = 1; st < RL; st = st + 1) begin
            pw[st] <= pw[st-1];
            pk[st] <= pk[st-1];
            px[st] <= px[st-1];
        end
    end
    always @(*) begin
        rd_w = pw[RL-1];
        rd_k = pk[RL-1];
        rd_x = px[RL-1];
    end

    // -- driver, checker, consumer ------------------------------------------------------------------
    integer nops, gap, throttle, cyc, nissued, nev, ep, errors, checked, faults, beats, first_beat, last_beat, last_out;
    integer op_start [0:MAXOPS-1];
    integer op_evleft [0:MAXOPS-1];
    integer op_end [0:MAXOPS-1];
    integer done_ops, s, idx, pend_cr, lfsr, cur_out_op;
    reg [31:0] ey, eb, ef;
    string fops, from, fk, fx, fexp;

    initial begin
        if (!$value$plusargs("ops=%s", fops)) $fatal(1, "+ops");
        if (!$value$plusargs("rom=%s", from)) $fatal(1, "+rom");
        if (!$value$plusargs("kmem=%s", fk)) $fatal(1, "+kmem");
        if (!$value$plusargs("xmem=%s", fx)) $fatal(1, "+xmem");
        if (!$value$plusargs("exp=%s", fexp)) $fatal(1, "+exp");
        if (!$value$plusargs("nops=%d", nops)) $fatal(1, "+nops");
        if (!$value$plusargs("gap=%d", gap)) gap = 0;
        if (!$value$plusargs("throttle=%d", throttle)) throttle = 0;
        $readmemh(fops, opm);
        $readmemh(from, rom);
        $readmemh(fk, kmem);
        $readmemh(fx, xmem);
        $readmemh(fexp, expm);
    end

    always @(posedge clk) begin
        if (cyc == 4) rst_n <= 1'b1;
    end

    initial begin
        cyc = 0; nissued = 0; nev = 0; ep = 0; errors = 0; checked = 0; faults = 0; beats = 0;
        first_beat = -1; last_beat = -1; last_out = -1; done_ops = 0; pend_cr = 0; lfsr = 32'h1234567; cur_out_op = 0;
        d_v = 1'b0; o_cr = 1'b0;
    end

    // descriptor driver
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst_n) begin
            if (d_v && d_rdy) begin
                op_start[nissued] = cyc;
                tab_xbase[nissued % 16] = opm[nissued*OPW + 8];
                tab_nb[nissued % 16] = opm[nissued*OPW + 1];
                tab_xr[nissued % 16] = opm[nissued*OPW + 12];
                op_evleft[nissued] = opm[nissued*OPW + 9];
                nissued = nissued + 1;
            end
            if (!(d_v && !d_rdy)) begin
                if (nissued < nops && (gap == 0 || (done_ops == nissued && idle && !(d_v && d_rdy)))) begin
                    d_v <= 1'b1;
                    d_plg <= opm[nissued*OPW + 0];
                    d_nb <= opm[nissued*OPW + 1];
                    d_nrows <= opm[nissued*OPW + 2];
                    d_wbase <= opm[nissued*OPW + 3];
                    d_ind <= opm[nissued*OPW + 4];
                    d_eid <= opm[nissued*OPW + 5];
                    d_estride <= opm[nissued*OPW + 6];
                    d_fp4 <= opm[nissued*OPW + 7];
                    d_src <= opm[nissued*OPW + 10];
                    d_split <= opm[nissued*OPW + 11];
                    d_tag <= nissued % 16;
                end else begin
                    d_v <= 1'b0;
                end
            end
            if (rq_v[0]) begin
                beats = beats + 1;
                if (first_beat < 0) first_beat = cyc;
                last_beat = cyc;
            end
        end
    end

    task automatic check1(input integer seg, input integer pos, input [31:0] y, input [15:0] b, input f,
                          input integer ix, input integer half);
        begin
            ey = expm[ix]; eb = expm[ix+1]; ef = expm[ix+2];
            checked = checked + 1;
            if (ef[0]) begin
                faults = faults + 1;
                if (!f) begin
                    errors = errors + 1;
                    if (errors < 10) $display("V41XWGT_ERR event %0d seg %0d.%0d pos %0d fault expected", nev, seg, half, pos);
                end
            end else if (f || y != ey || b != eb[15:0]) begin
                errors = errors + 1;
                if (errors < 10) $display("V41XWGT_ERR event %0d rg %0d seg %0d.%0d pos %0d y %h/%h bf %h/%h f %0d", nev,
                                          o_rg, seg, half, pos, y, ey, b, eb[15:0], f);
            end
        end
    endtask

    // result checker + credit return
    always @(posedge clk) begin
        o_cr <= 1'b0;
        if (rst_n && o_v) begin
            last_out = cyc;
            if (o_rg != expm[ep][RWW-1:0] || o_tag != expm[ep+1][TGW-1:0] || o_mask != expm[ep+2][NC-1:0] ||
                o_smask != expm[ep+3][G-1:0]) begin
                errors = errors + 1;
                if (errors < 10) $display("V41XWGT_ERR event %0d header rg %0d/%0d tag %0d/%0d mask %h/%h smask %h/%h",
                                          nev, o_rg, expm[ep], o_tag, expm[ep+1], o_mask, expm[ep+2], o_smask,
                                          expm[ep+3]);
            end
            for (s = 0; s < NC; s = s + 1)
                for (p = 0; p < M; p = p + 1)
                    if (o_mask[s])
                        check1(s, p, o_y[32*(s*M+p) +: 32], o_bf[16*(s*M+p) +: 16], o_f[s*M+p],
                               ep + 4 + 3 * (s * M + p), 1);
            for (s = 0; s < G; s = s + 1)
                for (p = 0; p < M; p = p + 1)
                    if (o_smask[s])
                        check1(s, p, o_ys[32*(s*M+p) +: 32], o_bfs[16*(s*M+p) +: 16], o_fs[s*M+p],
                               ep + 4 + 3 * NC * M + 3 * (s * M + p), 0);
            ep = ep + EVW;
            nev = nev + 1;
            op_evleft[cur_out_op] = op_evleft[cur_out_op] - 1;
            if (op_evleft[cur_out_op] == 0) begin
                op_end[cur_out_op] = cyc;
                cur_out_op = cur_out_op + 1;
                done_ops = done_ops + 1;
            end
            pend_cr = pend_cr + 1;
        end
        // credits: one per event, immediately or after a pseudo-random hold
        lfsr = {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
        if (pend_cr > 0 && (throttle == 0 || (lfsr % (throttle + 1)) == 0)) begin
            o_cr <= 1'b1;
            pend_cr = pend_cr - 1;
        end
        if (rst_n && done_ops == nops) begin
            $display("V41XWGT ops=%0d events=%0d checked=%0d errors=%0d faults=%0d cycles=%0d beats=%0d first_beat=%0d last_beat=%0d last_out=%0d start=%0d cnt=%0d,%0d,%0d",
                     nops, nev, checked, errors, faults, cyc - op_start[0], beats, first_beat, last_beat, last_out,
                     op_start[0], cnt_rom, cnt_stream, cnt_split);
            for (s = 0; s < nops; s = s + 1)
                $display("V41XWGT_LAT op=%0d cycles=%0d", s, op_end[s] - op_start[s]);
            $finish;
        end
        if (cyc > 4000000) begin
            $display("V41XWGT TIMEOUT events=%0d", nev);
            $finish;
        end
    end
endmodule
