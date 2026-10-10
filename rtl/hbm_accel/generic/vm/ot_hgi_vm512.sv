`timescale 1ns/1ps
`default_nettype none
// STATUS (2026-10-10 07:55): PAUSED by the coordinator before any bench (the >=90 % rule binds weight/KV streams, not
// DMA->VM; VM stays at 32 banks + WP 32 unless a measurement says otherwise).  Lints clean (verilator); NOT verified.
// HGI-1 vector memory, VM-512 (hgi-1010/f, 2026-10-10; spec docs/HBM_GENERIC_INTERFACE.md 2.4 "VM microarchitecture").
//
// 2^SB sectors of 8 FP32 words (SB 15: 1 MiB; SB 16: the 2 MiB the 128-row macros hold) in 512 banks:
//   sector s -> bank s[8:0], tile s[8:2] (128 ot_hgi_vm_tile), slot s[1:0], row s[SB-1:9].
// Ports (all inputs pin-flopped here):
//  * DMA lanes dl[t] (one a tile, ot_hgi_vm_tile format; credits dl_cr, written dest sectors dl_wn) -- format conversion
//    and SECDED encoding happen beside the banks, so a lane carries one RAW source sector a cycle.
//  * NGR wide READ groups x 32 lanes: rq {v, sector SB}; lane b serves sectors with s[4:0] = b (else proto fault);
//    rq_cr returns the lane's credit when the request launches (the client holds LQ); rr {v, data 256} in request
//    order at the fixed latency RLAT after launch, no back-pressure.
//  * NGW wide WRITE groups x 32 lanes: wq {v, sector SB, data 256, word mask 8}; wq_cr on launch; wq_done when the
//    write is in the macro (fixed latency WLAT after launch).
//  * NC packet clients (the ot_hgi_vm_unit ABI): cq {v, req 337 = {we, byte address 32, wdata 256, byte mask 32, tag 16}},
//    cr {v, rsp 273 = {tag 16, write echo 1, rdata 256}} in request order (reads and writes alike) at RLAT after launch;
//    a client keeps at most 4 outstanding (a 4-deep station; an overflow latches proto_fault).
// Edge schedule, per lane b and cycle: reads and writes are scheduled separately (1R1W banks); the launched requests
//   of lane b target distinct s[8:5] (= distinct banks).  Priority: an aged packet (waited AGE cycles), then the
//   groups in index order, then the packet; a loser waits in its queue.  Each launched request crosses DSP registered
//   spine stages to its tile column (tile column = b[4:2], tile row = s[8:5]); read data return through DCL registered
//   collect stages and are SECDED-decoded at the edge.  Edge writes take the bank's write port before the DMA queue.
// status = {dma_fault, proto_fault, mask_fault, ue, ce[15:0]}.
// MUT (bench): 1 no correction; 2 the edge ignores bank conflicts between groups (launches both);
//   3/4/8 tile mutants (ot_hgi_vm_tile); 5/6/9 conversion mutants (ot_hgi_vm_conv8);
//   7 packet write echoes one cycle early (overtakes an earlier read of the same client).
module ot_hgi_vm512 #(
    parameter integer SB  = 15,
    parameter integer NGR = 2,
    parameter integer NGW = 2,
    parameter integer NC  = 4,
    parameter integer LQ  = 8,
    parameter integer DSP = 2,
    parameter integer DCL = 2,
    parameter integer AGE = 8,
    parameter integer MUT = 0,
    localparam integer NT = 128,
    localparam integer RS = NGR + 1,                 // read slots a lane (groups + packet)
    localparam integer WS = NGW + 1,
    localparam integer SW = $clog2(RS + 1),
    localparam integer GRL = NGR > 0 ? NGR : 1,
    localparam integer GWL = NGW > 0 ? NGW : 1,
    localparam integer RLAT = DSP + DCL + 5,         // launch decision -> response flop (reads, packet writes)
    localparam integer WLAT = DSP + 3                // launch decision -> write in the macro (wq_done)
) (
    input  wire                        clk,
    input  wire                        rst_n,
    input  wire [NT*303-1:0]           dl,
    output wire [NT-1:0]               dl_cr,
    output wire [NT*3-1:0]             dl_wn,
    input  wire [GRL*32*(SB+1)-1:0]    rq,
    output reg  [GRL*32-1:0]           rq_cr,
    output reg  [GRL*32*257-1:0]       rr,
    input  wire [GWL*32*(SB+265)-1:0]  wq,
    output reg  [GWL*32-1:0]           wq_cr,
    output reg  [GWL*32-1:0]           wq_done,
    input  wire [NC*338-1:0]           cq,
    output reg  [NC*274-1:0]           cr,
    output reg  [19:0]                 status,
    input  wire                        inj_v,          // bench only (tie 0)
    input  wire [6:0]                  inj_tile,
    input  wire [1:0]                  inj_slot,
    input  wire [2:0]                  inj_word,
    input  wire [38:0]                 inj_mask
);
    localparam integer WQW = SB + 264;               // a write-queue entry {sector, data, mask}
    localparam integer LQB = $clog2(LQ);
    // ================================================================ pin flops
    reg [GRL*32*(SB+1)-1:0] rq_p; reg [GWL*32*(SB+265)-1:0] wq_p; reg [NC*338-1:0] cq_p;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rq_p <= '0; wq_p <= '0; cq_p <= '0; end
        else begin rq_p <= rq; wq_p <= wq; cq_p <= cq; end
    // ================================================================ lane queues (credits) and packet stations
    reg [SB-1:0]  rqq [0:GRL-1][0:31][0:LQ-1];
    reg [LQB:0]   rqn [0:GRL-1][0:31];
    reg [LQB-1:0] rqh [0:GRL-1][0:31], rqt [0:GRL-1][0:31];
    reg [WQW-1:0] wqq [0:GWL-1][0:31][0:LQ-1];
    reg [LQB:0]   wqn [0:GWL-1][0:31];
    reg [LQB-1:0] wqh [0:GWL-1][0:31], wqt [0:GWL-1][0:31];
    reg [336:0]   st  [0:NC-1][0:3];
    reg [2:0]     stn [0:NC-1];
    reg [1:0]     sth [0:NC-1], stt [0:NC-1];
    reg [7:0]     age [0:NC-1];
    // ================================================================ edge schedule (combinational)
    reg [GRL*32-1:0] r_go; reg [GWL*32-1:0] w_go; reg [NC-1:0] c_go;
    // per lane launched slots
    reg            lr_v   [0:31][0:RS-1]; reg [SB-1:0] lr_s [0:31][0:RS-1]; reg lr_nul [0:31][0:RS-1];
    reg            lw_v   [0:31][0:WS-1]; reg [SB-1:0] lw_s [0:31][0:WS-1];
    reg [255:0]    lw_d   [0:31][0:WS-1]; reg [7:0]    lw_m [0:31][0:WS-1];
    reg [4:0]      c_lane [0:NC-1];
    reg            c_we [0:NC-1]; reg [SB-1:0] c_sec [0:NC-1]; reg c_rng [0:NC-1]; reg [7:0] c_wm [0:NC-1];
    reg            c_mf [0:NC-1];
    always @* begin
        for (integer c = 0; c < NC; c = c + 1) begin : pk
            reg [336:0] h; h = st[c][sth[c]];
            c_we[c] = h[336]; c_sec[c] = h[304 + 5 +: SB]; c_lane[c] = h[309 +: 5];
            c_rng[c] = (SB + 5 < 32) ? (h[304 + 5 + SB +: (32 - SB - 5 > 0 ? 32 - SB - 5 : 1)] == '0) : 1'b1;
            for (integer w = 0; w < 8; w = w + 1) c_wm[c][w] = &h[16 + 4 * w +: 4];
            c_mf[c] = 1'b0;
            for (integer w = 0; w < 8; w = w + 1) if (|h[16 + 4 * w +: 4] && !(&h[16 + 4 * w +: 4])) c_mf[c] = 1'b1;
        end
        r_go = '0; w_go = '0; c_go = '0;
        for (integer b = 0; b < 32; b = b + 1) begin : lane
            reg [15:0] usedr, usedw; integer pr, pw; reg pr_aged, pw_aged; reg [3:0] col;
            usedr = 16'd0; usedw = 16'd0;
            for (integer s = 0; s < RS; s = s + 1) begin lr_v[b][s] = 1'b0; lr_s[b][s] = '0; lr_nul[b][s] = 1'b0; end
            for (integer s = 0; s < WS; s = s + 1) begin lw_v[b][s] = 1'b0; lw_s[b][s] = '0; lw_d[b][s] = '0; lw_m[b][s] = '0; end
            // packet candidates of this lane: aged first, then lowest index
            pr = -1; pw = -1; pr_aged = 1'b0; pw_aged = 1'b0;
            for (integer c = NC - 1; c >= 0; c = c - 1)
                if (stn[c] != 3'd0 && c_lane[c] == 5'(b)) begin
                    if (!c_we[c] && (age[c] >= 8'(AGE) || !pr_aged)) begin pr = c; pr_aged = age[c] >= 8'(AGE); end
                    if ( c_we[c] && (age[c] >= 8'(AGE) || !pw_aged)) begin pw = c; pw_aged = age[c] >= 8'(AGE); end
                end
            // ---- reads
            if (pr >= 0 && pr_aged) begin
                col = c_sec[pr][8:5]; usedr[col] = c_rng[pr];
                lr_v[b][NGR] = 1'b1; lr_s[b][NGR] = c_sec[pr]; lr_nul[b][NGR] = !c_rng[pr]; c_go[pr] = 1'b1;
            end
            for (integer g = 0; g < NGR; g = g + 1) begin
                col = rqq[g][b][rqh[g][b]][8:5];
                if (rqn[g][b] != '0 && (!usedr[col] || MUT == 2)) begin
                    usedr[col] = 1'b1; lr_v[b][g] = 1'b1; lr_s[b][g] = rqq[g][b][rqh[g][b]]; r_go[g * 32 + b] = 1'b1;
                end
            end
            if (pr >= 0 && !pr_aged) begin
                col = c_sec[pr][8:5];
                if (!usedr[col] || !c_rng[pr]) begin
                    usedr[col] = usedr[col] | c_rng[pr];
                    lr_v[b][NGR] = 1'b1; lr_s[b][NGR] = c_sec[pr]; lr_nul[b][NGR] = !c_rng[pr]; c_go[pr] = 1'b1;
                end
            end
            // ---- writes (an out-of-range packet write is launched as a null: no bank access, echo only)
            if (pw >= 0 && pw_aged) begin
                col = c_sec[pw][8:5]; usedw[col] = c_rng[pw];
                lw_v[b][NGW] = c_rng[pw]; lw_s[b][NGW] = c_sec[pw]; lw_m[b][NGW] = c_wm[pw];
                lw_d[b][NGW] = st[pw][sth[pw]][48 +: 256]; c_go[pw] = 1'b1;
            end
            for (integer g = 0; g < NGW; g = g + 1) begin : wg
                reg [WQW-1:0] e; e = wqq[g][b][wqh[g][b]];
                col = e[264 + 5 +: 4];
                if (wqn[g][b] != '0 && (!usedw[col] || MUT == 2)) begin
                    usedw[col] = 1'b1; lw_v[b][g] = 1'b1; lw_s[b][g] = e[264 +: SB]; lw_d[b][g] = e[8 +: 256];
                    lw_m[b][g] = e[7:0]; w_go[g * 32 + b] = 1'b1;
                end
            end
            if (pw >= 0 && !pw_aged) begin
                col = c_sec[pw][8:5];
                if (!usedw[col] || !c_rng[pw]) begin
                    usedw[col] = usedw[col] | c_rng[pw];
                    lw_v[b][NGW] = c_rng[pw]; lw_s[b][NGW] = c_sec[pw]; lw_m[b][NGW] = c_wm[pw];
                    lw_d[b][NGW] = st[pw][sth[pw]][48 +: 256]; c_go[pw] = 1'b1;
                end
            end
        end
    end
    // write data encoded at launch
    wire [311:0] lw_e [0:31][0:WS-1];
    genvar gb, gs, gt, gj;
    for (gb = 0; gb < 32; gb = gb + 1) begin : g_enc
        for (gs = 0; gs < WS; gs = gs + 1) begin : g_s
            ot_hgi_vm_enc8 u_e (.d(lw_d[gb][gs]), .q(lw_e[gb][gs]));
        end
    end
    // ================================================================ queues, stations, credits (sequential)
    reg proto, maskf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            proto <= 1'b0; maskf <= 1'b0; rq_cr <= '0; wq_cr <= '0;
            for (integer g = 0; g < GRL; g = g + 1) for (integer b = 0; b < 32; b = b + 1) begin rqn[g][b] <= '0; rqh[g][b] <= '0; rqt[g][b] <= '0; end
            for (integer g = 0; g < GWL; g = g + 1) for (integer b = 0; b < 32; b = b + 1) begin wqn[g][b] <= '0; wqh[g][b] <= '0; wqt[g][b] <= '0; end
            for (integer c = 0; c < NC; c = c + 1) begin stn[c] <= '0; sth[c] <= '0; stt[c] <= '0; age[c] <= '0; end
        end else begin
            rq_cr <= r_go; wq_cr <= w_go;
            for (integer g = 0; g < NGR; g = g + 1) for (integer b = 0; b < 32; b = b + 1) begin : rl
                reg push, ok; reg [SB:0] q;
                q = rq_p[(g * 32 + b) * (SB + 1) +: (SB + 1)];
                push = q[SB]; ok = q[4:0] == 5'(b) && !(rqn[g][b] == (LQB+1)'(LQ) && !r_go[g * 32 + b]);
                if (push && !ok) proto <= 1'b1;
                if (push && ok) begin rqq[g][b][rqt[g][b]] <= q[SB-1:0]; rqt[g][b] <= rqt[g][b] + 1'b1; end
                if (r_go[g * 32 + b]) rqh[g][b] <= rqh[g][b] + 1'b1;
                rqn[g][b] <= rqn[g][b] + {{LQB{1'b0}}, push && ok} - {{LQB{1'b0}}, r_go[g * 32 + b]};
            end
            for (integer g = 0; g < NGW; g = g + 1) for (integer b = 0; b < 32; b = b + 1) begin : wl
                reg push, ok; reg [SB+264:0] q;
                q = wq_p[(g * 32 + b) * (SB + 265) +: (SB + 265)];
                push = q[SB + 264]; ok = q[264 +: 5] == 5'(b) && !(wqn[g][b] == (LQB+1)'(LQ) && !w_go[g * 32 + b]);
                if (push && !ok) proto <= 1'b1;
                if (push && ok) begin wqq[g][b][wqt[g][b]] <= q[WQW-1:0]; wqt[g][b] <= wqt[g][b] + 1'b1; end
                if (w_go[g * 32 + b]) wqh[g][b] <= wqh[g][b] + 1'b1;
                wqn[g][b] <= wqn[g][b] + {{LQB{1'b0}}, push && ok} - {{LQB{1'b0}}, w_go[g * 32 + b]};
            end
            for (integer c = 0; c < NC; c = c + 1) begin : stl
                reg push, ok;
                push = cq_p[c * 338 + 337]; ok = !(stn[c] == 3'd4 && !c_go[c]);
                if (push && !ok) proto <= 1'b1;
                if (push && ok) begin st[c][stt[c]] <= cq_p[c * 338 +: 337]; stt[c] <= stt[c] + 2'd1; end
                if (c_go[c]) begin
                    sth[c] <= sth[c] + 2'd1; age[c] <= 8'd0;
                    if (!c_rng[c]) proto <= 1'b1;
                    if (c_we[c] && c_mf[c]) maskf <= 1'b1;
                end else if (stn[c] != 3'd0 && age[c] != 8'hFF) age[c] <= age[c] + 8'd1;
                stn[c] <= stn[c] + {2'd0, push && ok} - {2'd0, c_go[c]};
            end
        end
    end
    // ================================================================ spine: launch register + DSP stages
    localparam integer RBW = 1 + 1 + SB;            // {v, nul, sector}
    localparam integer WBW = 1 + SB + 312 + 8;      // {v, sector, enc, mask}
    reg [RS*RBW-1:0] sr [0:DSP][0:31];
    reg [WS*WBW-1:0] sw [0:DSP][0:31];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (integer k = 0; k <= DSP; k = k + 1) for (integer b = 0; b < 32; b = b + 1) begin sr[k][b] <= '0; sw[k][b] <= '0; end
        end else begin
            for (integer b = 0; b < 32; b = b + 1) begin
                for (integer s = 0; s < RS; s = s + 1) sr[0][b][s * RBW +: RBW] <= {lr_v[b][s] && !lr_nul[b][s], lr_nul[b][s], lr_s[b][s]};
                for (integer s = 0; s < WS; s = s + 1) sw[0][b][s * WBW +: WBW] <= {lw_v[b][s], lw_s[b][s], lw_e[b][s], lw_m[b][s]};
                for (integer k = 1; k <= DSP; k = k + 1) begin sr[k][b] <= sr[k-1][b]; sw[k][b] <= sw[k-1][b]; end
            end
        end
    end
    // ================================================================ tiles
    wire [3:0]       t_rdv  [0:NT-1];
    wire [4*SW-1:0]  t_rsid [0:NT-1];
    wire [4*312-1:0] t_rd   [0:NT-1];
    wire [NT-1:0]    t_fault;
    for (gt = 0; gt < NT; gt = gt + 1) begin : g_tile
        reg [3:0] ew_v, er_v; reg [4*7-1:0] ew_row, er_row; reg [4*312-1:0] ew_d; reg [4*8-1:0] ew_m; reg [4*SW-1:0] er_sid;
        always @* begin
            ew_v = '0; er_v = '0; ew_row = '0; er_row = '0; ew_d = '0; ew_m = '0; er_sid = '0;
            for (integer j = 0; j < 4; j = j + 1) begin : sl
                integer b; b = (gt % 8) * 4 + j;
                for (integer s = 0; s < WS; s = s + 1) begin : ws
                    reg [WBW-1:0] x; x = sw[DSP][b][s * WBW +: WBW];
                    if (x[WBW-1] && x[320 + 5 +: 4] == 4'(gt / 8)) begin
                        ew_v[j] = 1'b1; ew_row[j*7 +: 7] = 7'(x[320 + 9 +: (SB - 9)]); ew_d[j*312 +: 312] = x[8 +: 312];
                        ew_m[j*8 +: 8] = x[7:0];
                    end
                end
                for (integer s = 0; s < RS; s = s + 1) begin : rs
                    reg [RBW-1:0] x; x = sr[DSP][b][s * RBW +: RBW];
                    if (x[RBW-1] && x[5 +: 4] == 4'(gt / 8)) begin
                        er_v[j] = 1'b1; er_row[j*7 +: 7] = 7'(x[9 +: (SB - 9)]); er_sid[j*SW +: SW] = SW'(s);
                    end
                end
            end
        end
        ot_hgi_vm_tile #(.RB(SB - 9), .SW(SW), .MUT(MUT)) u_tile (.clk(clk), .rst_n(rst_n),
            .dl(dl[gt*303 +: 303]), .dl_cr(dl_cr[gt]), .dl_wn(dl_wn[gt*3 +: 3]), .dl_fault(t_fault[gt]),
            .ew_v(ew_v), .ew_row(ew_row), .ew_d(ew_d), .ew_m(ew_m), .er_v(er_v), .er_row(er_row), .er_sid(er_sid),
            .rd_v(t_rdv[gt]), .rd_sid(t_rsid[gt]), .rd_d(t_rd[gt]),
            .inj_v(inj_v && inj_tile == 7'(gt)), .inj_slot(inj_slot), .inj_word(inj_word), .inj_mask(inj_mask));
    end
    // ================================================================ collect: column OR per lane and slot, DCL stages
    reg [311:0] cl [0:DCL][0:31][0:RS-1];
    reg         cv [0:DCL][0:31][0:RS-1];
    always @* begin
        for (integer b = 0; b < 32; b = b + 1)
            for (integer s = 0; s < RS; s = s + 1) begin
                cl[0][b][s] = '0; cv[0][b][s] = 1'b0;
                for (integer r = 0; r < 16; r = r + 1) begin : rr_
                    integer t, j; t = r * 8 + b / 4; j = b % 4;
                    if (t_rdv[t][j] && t_rsid[t][j*SW +: SW] == SW'(s)) begin
                        cl[0][b][s] = cl[0][b][s] | t_rd[t][j*312 +: 312]; cv[0][b][s] = 1'b1;
                    end
                end
            end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (integer k = 1; k <= DCL; k = k + 1) for (integer b = 0; b < 32; b = b + 1) for (integer s = 0; s < RS; s = s + 1) cv[k][b][s] <= 1'b0;
        end else
            for (integer k = 1; k <= DCL; k = k + 1) for (integer b = 0; b < 32; b = b + 1) for (integer s = 0; s < RS; s = s + 1) begin
                cv[k][b][s] <= cv[k-1][b][s]; cl[k][b][s] <= cl[k-1][b][s];
            end
    // decode at the edge
    wire [255:0] dd [0:31][0:RS-1]; wire [7:0] dce [0:31][0:RS-1]; wire [7:0] due [0:31][0:RS-1];
    for (gb = 0; gb < 32; gb = gb + 1) begin : g_dec
        for (gs = 0; gs < RS; gs = gs + 1) begin : g_s
            ot_hgi_vm_dec8 #(.MUT(MUT)) u_d (.q(cl[DCL][gb][gs]), .d(dd[gb][gs]), .ce(dce[gb][gs]), .ue(due[gb][gs]));
        end
    end
    // ================================================================ responses
    // packet delay line: {v, we, nul, lane 5, tag 16} launched -> response at RLAT
    reg [23:0] pd [0:NC-1][0:RLAT-1];
    reg [15:0] ce; reg ue;
    reg [WLAT-1:0] wd_d [0:GWL*32-1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rr <= '0; cr <= '0; ce <= 16'd0; ue <= 1'b0; wq_done <= '0; status <= '0;
            for (integer c = 0; c < NC; c = c + 1) for (integer k = 0; k < RLAT; k = k + 1) pd[c][k] <= '0;
            for (integer i = 0; i < GWL * 32; i = i + 1) wd_d[i] <= '0;
        end else begin : rsp
            reg [15:0] cen; reg uen; reg [23:0] e;
            cen = 16'd0; uen = 1'b0;
            for (integer b = 0; b < 32; b = b + 1)
                for (integer s = 0; s < RS; s = s + 1)
                    if (cv[DCL][b][s]) begin
                        for (integer w = 0; w < 8; w = w + 1) begin cen = cen + {15'd0, dce[b][s][w]}; uen = uen | due[b][s][w]; end
                    end
            for (integer g = 0; g < NGR; g = g + 1) for (integer b = 0; b < 32; b = b + 1)
                rr[(g * 32 + b) * 257 +: 257] <= {cv[DCL][b][g], cv[DCL][b][g] ? dd[b][g] : 256'd0};
            // packet responses (index 0 of pd = launched this edge; RLAT-1 = the response edge)
            for (integer c = 0; c < NC; c = c + 1) begin
                pd[c][0] <= {c_go[c], c_we[c], !c_rng[c], c_lane[c], st[c][sth[c]][15:0]};
                for (integer k = 1; k < RLAT; k = k + 1) pd[c][k] <= pd[c][k-1];
                e = (MUT == 7 && pd[c][RLAT-2][23] && pd[c][RLAT-2][22]) ? pd[c][RLAT-2] : pd[c][RLAT-1];
                if (MUT == 7 && pd[c][RLAT-1][23] && pd[c][RLAT-1][22]) e = '0;
                cr[c*274 +: 274] <= {e[23], e[15:0], e[22], (e[23] && !e[22] && !e[21]) ? dd[e[20:16]][NGR] : 256'd0};
            end
            for (integer i = 0; i < NGW * 32; i = i + 1) begin
                wd_d[i] <= {wd_d[i][WLAT-2:0], w_go[i]};
                wq_done[i] <= wd_d[i][WLAT-2];
            end
            ce <= (ce + cen < ce) ? 16'hFFFF : ce + cen;
            if (uen) ue <= 1'b1;
            status <= {|t_fault_s, proto, maskf, ue, ce};
        end
    end
    reg [NT-1:0] t_fault_s;
    always @(posedge clk or negedge rst_n) if (!rst_n) t_fault_s <= '0; else t_fault_s <= t_fault_s | t_fault;
endmodule
`default_nettype wire
