`timescale 1ns/1ps
`default_nettype none
// HGI-1 VM block body (hgi-takeover 2026-10-09): ot_hgi_vm_core + one die station per packet client.  Die protocol (VM
// fast path, review ~16:40): a client keeps at most OUT = 4 requests outstanding (request sent, response not yet
// received) and receives the responses IN REQUEST ORDER (tags echoed).  A request carries only a valid bit: the station
// queues up to 4 until the core grants them; a response needs no back-pressure.  A request arriving to a full station is
// a protocol violation (the client exceeded 4 outstanding): it latches proto_fault.  A v1 client (one outstanding) is a
// legal fast-path client.
// status = {proto_fault, mask_fault, ue, ce[15:0]} (19 b) to the command processor (UE / faults halt the CP).
module ot_hgi_vm_unit #(
    parameter integer NC = 1,
    parameter integer WP = 1,            // wide write lanes (the DMA streaming port, 32 B a lane a cycle)
    parameter integer WDIRECT = 0,       // lane b -> bank b only (WP 32 with the DMA front)
    parameter integer RP = 0,            // hgi-unitrate: wide READ lanes (lane b <-> bank b): the SU / SFU wide stage
    parameter integer W2 = 0,            // hgi-unitrate: second wide WRITE group (lane b <-> bank b): the SU / SFU drain
    parameter integer LQ = 8,            // per-lane request queue depth = the credits the lane's client holds
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NC*338-1:0] cq,         // per client {v, req 337}
    output reg  [NC*274-1:0] cr,         // per client {v, rsp 273}
    output reg  [18:0]       status,
    // wide write port, per lane {v, sector 15, wdata 256, word mask 8} (280 b), pin-flopped here; done per lane
    input  wire [WP*280-1:0] wq,
    output wire [WP-1:0]     wq_done,
    // hgi-unitrate wide lanes (credit links; every port pin-flopped here):
    //   rq lane b {v, sector 15} (sector bank must be b); the client holds LQ credits a lane, rq_cr[b] returns one when
    //   the queued request reaches its bank; rr lane b {v, data 256}: the sector, in request order, 5 edges after it
    //   reached the bank (core 4 + this response flop); no back-pressure (the client always accepts).
    //   w2q lane b {v, sector 15, wdata 256, word mask 8} (wq layout); w2q_cr[b] = the write reached its bank (a
    //   credit back), w2q_done[b] = the write is in the macro (the client retires after its last).
    input  wire [(RP>0?RP:1)*16-1:0]  rq,
    output wire [(RP>0?RP:1)-1:0]     rq_cr,
    output reg  [(RP>0?RP:1)*257-1:0] rr,
    input  wire [(W2>0?W2:1)*280-1:0] w2q,
    output reg  [(W2>0?W2:1)-1:0]     w2q_cr,
    output reg  [(W2>0?W2:1)-1:0]     w2q_done
);
    localparam integer RPL = RP > 0 ? RP : 1, W2L = W2 > 0 ? W2 : 1;
    // ---- wide read lanes: pin flop -> LQ-deep request queue -> core lane (accepted when no client reads the bank)
    reg [RPL*16-1:0] rq_r; always @(posedge clk or negedge rst_n) if (!rst_n) rq_r <= '0; else rq_r <= rq;
    // [fe E] hardcore-1010 feasibility: each wide lane owns its queue in its own generate block (1 write port per lane
    // array).  The previous single 2-D array written from a for-loop over lanes elaborated as ONE memory with RPL / W2L
    // write ports (a priority mux per word); behaviour is identical (lockstep tb_hgi_vm_lanes, MUT 9 = head read at
    // tail, must FAIL).
    wire [RPL-1:0] rl_v; wire [RPL*15-1:0] rl_sec; wire [RPL-1:0] rl_acc; wire [RPL*257-1:0] rl_rsp; wire rl_conflict;
    wire [RPL-1:0] rq_ovf_l;
    wire rq_ovf = |rq_ovf_l;                                               // sticky per lane, as before
    genvar lg;
    for (lg = 0; lg < RPL; lg = lg + 1) begin : g_rq
        reg [14:0] q [0:LQ-1]; reg [$clog2(LQ):0] n; reg [$clog2(LQ)-1:0] h, t; reg ovf, cr_q;
        wire push = (RP > 0) && rq_r[lg*16 + 15], pop = rl_acc[lg], full = n == LQ;
        assign rl_v[lg] = (RP > 0) && n != 0; assign rl_sec[lg*15 +: 15] = q[(MUT == 9) ? t : h]; assign rq_cr[lg] = cr_q;
        always @(posedge clk) if (push && !(full && !pop)) q[t] <= rq_r[lg*16 +: 15];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin n <= 0; h <= 0; t <= 0; ovf <= 1'b0; cr_q <= 1'b0; end
            else begin
                if (push && full && !pop) ovf <= 1'b1;                        // the client exceeded its credits
                else if (push) t <= t + 1'b1;
                if (pop) h <= h + 1'b1;
                n <= n + (push && !(full && !pop)) - pop;
                cr_q <= pop;
            end
        assign rq_ovf_l[lg] = ovf;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) rr <= '0; else rr <= rl_rsp;
    // ---- second wide write group: pin flop -> LQ-deep queue -> core lane (after the DMA group); done = credit
    reg [W2L*280-1:0] w2q_r; always @(posedge clk or negedge rst_n) if (!rst_n) w2q_r <= '0; else w2q_r <= w2q;
    wire [W2L-1:0] w2_v; wire [W2L*15-1:0] w2_sec; wire [W2L*256-1:0] w2_d; wire [W2L*8-1:0] w2_m;
    wire [W2L-1:0] w2_acc, w2_done; wire [W2L-1:0] w2_ovf_l; wire w2_ovf = |w2_ovf_l;
    for (lg = 0; lg < W2L; lg = lg + 1) begin : g_w2
        reg [278:0] q [0:LQ-1]; reg [$clog2(LQ):0] n; reg [$clog2(LQ)-1:0] h, t; reg ovf;
        wire push = (W2 > 0) && w2q_r[lg*280 + 279], pop = w2_acc[lg], full = n == LQ;
        wire [278:0] e = q[h];
        assign w2_v[lg] = (W2 > 0) && n != 0; assign w2_m[lg*8 +: 8] = e[7:0]; assign w2_d[lg*256 +: 256] = e[263:8];
        assign w2_sec[lg*15 +: 15] = e[278:264];
        always @(posedge clk) if (push && !(full && !pop)) q[t] <= w2q_r[lg*280 +: 279];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin n <= 0; h <= 0; t <= 0; ovf <= 1'b0; end
            else begin
                if (push && full && !pop) ovf <= 1'b1;
                else if (push) t <= t + 1'b1;
                if (pop) h <= h + 1'b1;
                n <= n + (push && !(full && !pop)) - pop;
            end
        assign w2_ovf_l[lg] = ovf;
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin w2q_done <= '0; w2q_cr <= '0; end
        else begin w2q_done <= w2_done; w2q_cr <= w2_acc; end
    reg [WP*280-1:0] wq_r;
    always @(posedge clk or negedge rst_n) if (!rst_n) wq_r <= {WP*280{1'b0}}; else wq_r <= wq;
    wire [WP-1:0] wl_v; wire [WP*15-1:0] wl_sec; wire [WP*256-1:0] wl_d; wire [WP*8-1:0] wl_m; wire wl_conflict;
    genvar gp;
    for (gp = 0; gp < WP; gp = gp + 1) begin : g_wl
        assign wl_m[gp*8 +: 8] = wq_r[gp*280 +: 8]; assign wl_d[gp*256 +: 256] = wq_r[gp*280 + 8 +: 256];
        assign wl_sec[gp*15 +: 15] = wq_r[gp*280 + 264 +: 15]; assign wl_v[gp] = wq_r[gp*280 + 279];
    end
    reg  [336:0] sq [0:NC-1][0:3];
    reg  [1:0]   sh [0:NC-1];
    reg  [1:0]   stl [0:NC-1];
    reg  [2:0]   sn [0:NC-1];
    reg  [NC-1:0]     h_v;
    reg  [NC*337-1:0] h_q;
    always @* for (integer cc = 0; cc < NC; cc = cc + 1) begin h_v[cc] = sn[cc] != 3'd0; h_q[cc*337 +: 337] = sq[cc][sh[cc]]; end
    wire [NC-1:0]     req_r, rsp_v;
    wire [NC*273-1:0] rsp;
    wire [15:0] ce; wire ue, mask_fault;
    reg proto;
    ot_hgi_vm_core #(.NC(NC), .OUT(4), .WP(WP), .WDIRECT(WDIRECT), .RP(RP), .W2(W2), .MUT(MUT)) u_core (.clk(clk), .rst_n(rst_n), .req_v(h_v), .req_r(req_r), .req(h_q),
        .rsp_v(rsp_v), .rsp_r({NC{1'b1}}), .rsp(rsp), .ce(ce), .ue(ue), .mask_fault(mask_fault),
        .inj_v(1'b0), .inj_bank(5'd0), .inj_word(3'd0), .inj_mask(39'd0),
        .wl_v(wl_v), .wl_sec(wl_sec), .wl_d(wl_d), .wl_m(wl_m), .wl_done(wq_done), .wl_conflict(wl_conflict),
        .rl_v(rl_v), .rl_sec(rl_sec), .rl_acc(rl_acc), .rl_rsp(rl_rsp), .rl_conflict(rl_conflict),
        .w2_v(w2_v), .w2_sec(w2_sec), .w2_d(w2_d), .w2_m(w2_m), .w2_acc(w2_acc), .w2_done(w2_done));
    integer c;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            proto <= 1'b0; cr <= {NC*274{1'b0}}; status <= 19'd0;
            for (c = 0; c < NC; c = c + 1) begin sh[c] <= 2'd0; stl[c] <= 2'd0; sn[c] <= 3'd0; end
        end else begin
            for (c = 0; c < NC; c = c + 1) begin : st
                reg push, pop;
                push = cq[c*338 + 337]; pop = h_v[c] && req_r[c];
                if (push) begin
                    if (sn[c] == 3'd4 && !pop) proto <= 1'b1;
                    else begin sq[c][stl[c]] <= cq[c*338 +: 337]; stl[c] <= stl[c] + 2'd1; end
                end
                if (pop) sh[c] <= sh[c] + 2'd1;
                sn[c] <= sn[c] + {2'd0, push && !(sn[c] == 3'd4 && !pop)} - {2'd0, pop};
                cr[c*274 +: 274] <= {rsp_v[c], rsp[c*273 +: 273]};
            end
            status <= {proto | wl_conflict | rl_conflict | rq_ovf | w2_ovf, mask_fault, ue, ce};
        end
endmodule
`default_nettype wire
