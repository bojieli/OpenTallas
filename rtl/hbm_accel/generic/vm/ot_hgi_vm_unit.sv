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
    parameter integer LQ = 8,            // per-lane request queue depth = the credits the lane's client holds (power of 2)
    parameter integer QMACRO = 0,        // the write-lane queues' SRAM (ot_fifo_sram_fwft MACRO: 0 = 64x512 macros)
    parameter integer AP = 0,            // hgi-1010 b: 1 = the HC weight APERTURE route (lead decision (b), d's HC HSRC = 1):
                                         //   the wide write lane grows an ap bit, {v, ap, sector 15, wdata 256, mask 8}
                                         //   (281 b; the DMA front sets ap for VM words >= 2^18, sector = (word - 2^18) / 8).
                                         //   An ap sector does NOT write VM: it queues (APD a DMA lane, SRAM) and leaves on
                                         //   ap_q lane k = its HC weight bank (sector [11:9]; 8 lanes {v, sector 13, wdata 256,
                                         //   mask 8} = 278 b, APC credits a lane, ap_cr returns one), ap_done = written;
                                         //   wq_done counts both kinds.  The
                                         //   front stops a lane on wq_rdy[b] = 0 (the ap queue is near full).  An ap sector
                                         //   past the two slots (sector >= 8,192) is dropped and faults (status proto).
    parameter integer APD = 16,          // ap queue depth a lane (power of two); wq_rdy is low while the queue holds >= APD - APS
    parameter integer APC = 1,           // credits an aperture lane holds (d's HC lane holds APC sectors)
    parameter integer APS = 8,           // slack: sectors the front may still send after wq_rdy falls (its X1 -> lane
                                         //   pipeline + the two pin flops)
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [NC*338-1:0] cq,         // per client {v, req 337}
    output reg  [NC*274-1:0] cr,         // per client {v, rsp 273}
    output reg  [18:0]       status,
    // wide write port, per lane {v, sector 15, wdata 256, word mask 8} (280 b; AP: {v, ap, sector 15, ...} 281 b),
    // pin-flopped here; done per lane (a written VM sector or a written aperture sector)
    input  wire [WP*(280+AP)-1:0] wq,
    output wire [WP-1:0]     wq_done,
    output wire [WP-1:0]     wq_rdy,     // AP: the lane may send (ap queue below APD - APS); 1 without AP
    output wire [8*278-1:0]  ap_q,       // AP: to the HC unit's 8 aperture lanes (lane k = weight bank k)
    input  wire [7:0]        ap_cr,
    input  wire [7:0]        ap_done,
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
    // LQ must be a power of two: the read-queue pointers are $clog2(LQ) bits and wrap at 2^n (lead / d: an LQ of 24 would
    // index past the queue), and the write queues are ot_fifo_sram_fwft (power-of-two DEPTH)
    generate if ((1 << $clog2(LQ)) != LQ) begin : g_lq_must_be_pow2
        ot_hgi_vm_unit_LQ_must_be_a_power_of_two u_trap ();
    end endgenerate
    // ---- wide read lanes: pin flop -> LQ-deep request queue -> core lane (accepted when no client reads the bank)
    reg [RPL*16-1:0] rq_r; always @(posedge clk or negedge rst_n) if (!rst_n) rq_r <= '0; else rq_r <= rq;
    // hardcore-1010 feasibility (a3e0d3e86, folded): each read lane owns its queue in its own generate block (one write
    // port a lane array), not one 2-D array written from a for-loop (a 32-96 write-port memory at elaboration)
    wire [RPL-1:0] rl_v; wire [RPL*15-1:0] rl_sec; wire [RPL-1:0] rl_acc; wire [RPL*257-1:0] rl_rsp; wire rl_conflict;
    wire [RPL-1:0] rq_ovf_l; wire rq_ovf = |rq_ovf_l;
    for (genvar lg = 0; lg < RPL; lg = lg + 1) begin : g_rq
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
    always @(posedge clk or negedge rst_n) if (!rst_n) rr <= '0; else rr <= rl_rsp;
    // ---- second wide write group: pin flop -> LQ-deep queue -> core lane (after the DMA group); done = credit
    reg [W2L*280-1:0] w2q_r; always @(posedge clk or negedge rst_n) if (!rst_n) w2q_r <= '0; else w2q_r <= w2q;
    // per-lane write queues in SRAM (feasibility review: no LQ x 279-b flop arrays behind a wide select): one
    // ot_fifo_sram_fwft a lane (registered head), DEPTH = LQ = the client's credits; the head feeds the core lane
    wire [W2L-1:0] w2_hv, w2_qovf; wire [W2L*279-1:0] w2_head;
    reg [W2L-1:0] w2_v; reg [W2L*15-1:0] w2_sec; reg [W2L*256-1:0] w2_d; reg [W2L*8-1:0] w2_m;
    wire [W2L-1:0] w2_acc, w2_done; reg w2_ovf;
    for (genvar lq_ = 0; lq_ < W2L; lq_ = lq_ + 1) begin : g_w2q
        ot_fifo_sram_fwft #(.W(279), .DEPTH(LQ), .MACRO(QMACRO)) u_q (.clk(clk), .rst_n(rst_n),
            .push((W2 > 0) && w2q_r[lq_*280 + 279]), .wdata(w2q_r[lq_*280 +: 279]), .pop(w2_acc[lq_]),
            .hv(w2_hv[lq_]), .head(w2_head[lq_*279 +: 279]), .ovf(w2_qovf[lq_]));
    end
    always @* for (integer lb = 0; lb < W2L; lb = lb + 1) begin : w2h_
        reg [278:0] e; e = w2_head[lb*279 +: 279];
        w2_v[lb] = (W2 > 0) && w2_hv[lb]; w2_m[lb*8 +: 8] = e[7:0]; w2_d[lb*256 +: 256] = e[263:8];
        w2_sec[lb*15 +: 15] = e[278:264];
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin w2q_done <= '0; w2q_cr <= '0; w2_ovf <= 1'b0; end
        else begin w2q_done <= w2_done; w2q_cr <= w2_acc; if (|w2_qovf) w2_ovf <= 1'b1; end
    localparam integer WQW = 280 + AP;
    reg [WP*WQW-1:0] wq_r;
    always @(posedge clk or negedge rst_n) if (!rst_n) wq_r <= {WP*WQW{1'b0}}; else wq_r <= wq;
    wire [WP-1:0] wl_v; wire [WP*15-1:0] wl_sec; wire [WP*256-1:0] wl_d; wire [WP*8-1:0] wl_m; wire wl_conflict;
    wire [WP-1:0] wl_done; wire [WP-1:0] ap_flt;
    // wq_done counts VM and aperture writes alike (the front only sums them): the aperture dones queue in ap_pend and
    // leave on DMA lanes whose VM done is idle this edge (total dones a cycle <= the sectors the front sent, <= WP)
    reg [WP-1:0] apx; reg [15:0] ap_pend;
    reg [WP-1:0] aq_pop; wire [WP-1:0] aq_hv; wire [WP*277-1:0] aq_head;
    reg [7:0] ap_cr_q, ap_dn_q; reg [$clog2(APC+1)-1:0] apcr [0:7]; reg [4:0] aprr [0:7]; reg [8*278-1:0] apo;
    genvar gp;
    for (gp = 0; gp < WP; gp = gp + 1) begin : g_wl
        wire v  = wq_r[gp*WQW + WQW - 1];
        wire ap = (AP != 0) && wq_r[gp*WQW + 279];
        assign wl_m[gp*8 +: 8] = wq_r[gp*WQW +: 8]; assign wl_d[gp*256 +: 256] = wq_r[gp*WQW + 8 +: 256];
        assign wl_sec[gp*15 +: 15] = wq_r[gp*WQW + 264 +: 15];
        assign wl_v[gp] = v && (!ap || MUT == 10);              // MUT 10: an aperture sector also writes VM (must FAIL)
        if (AP != 0) begin : g_ap
            // the lane's aperture queue: SRAM FWFT, APD deep; the bank-keyed arbiter below pops it
            wire push = v && ap && wq_r[gp*WQW + 264 + 13 +: 2] == 2'd0;
            wire ovf; reg rdy_q, rf; reg [$clog2(APD):0] n;
            ot_fifo_sram_fwft #(.W(277), .DEPTH(APD), .MACRO(QMACRO)) u_aq (.clk(clk), .rst_n(rst_n), .push(push),
                .wdata({wq_r[gp*WQW + 264 +: 13], wq_r[gp*WQW +: 264]}), .pop(aq_pop[gp]), .hv(aq_hv[gp]),
                .head(aq_head[gp*277 +: 277]), .ovf(ovf));
            always @(posedge clk or negedge rst_n)
                if (!rst_n) begin n <= '0; rdy_q <= 1'b1; rf <= 1'b0; end
                else begin
                    n <= n + push - aq_pop[gp];
                    rdy_q <= (MUT == 11) || ({1'b0, n} + push < (APD - APS));
                    if (ovf || (v && ap && !push)) rf <= 1'b1;           // queue overflow / sector past the slots
                end
            assign wq_rdy[gp] = rdy_q; assign wq_done[gp] = wl_done[gp] || apx[gp];
            assign ap_flt[gp] = rf;
        end else begin : g_noap
            assign wq_rdy[gp] = 1'b1; assign wq_done[gp] = wl_done[gp];
            assign ap_flt[gp] = 1'b0;
        end
    end
    // ---- the aperture's 8 bank lanes (hbm-phys / d 2026-10-11: VM -> HC 8 x 278 b, lane k = HC weight bank k = sector
    //      [11:9]): per bank a rotating-priority pick over the 32 DMA-lane queue heads of that bank, APC credits a lane
    //      (ap_cr returns one); ap_done counts into wq_done
    assign ap_q = (AP != 0) ? apo : '0;
    always @* begin : apxs
        integer left; left = (AP != 0) ? ap_pend : 0; apx = '0;
        for (integer l = 0; l < WP; l = l + 1) if (left > 0 && !wl_done[l]) begin apx[l] = 1'b1; left = left - 1; end
    end
    always @* begin
        aq_pop = '0;
        for (integer k = 0; k < 8; k = k + 1) begin : pk
            reg found; integer i, l;
            found = 1'b0;
            for (i = 0; i < WP; i = i + 1) begin
                l = (aprr[k] + 1 + i) % WP;
                if (AP != 0 && !found && apcr[k] != '0 && aq_hv[l] && aq_head[l*277 + (MUT == 13 ? 272 : 273) +: 3] == 3'(k)) begin
                    found = 1'b1; aq_pop[l] = 1'b1;
                end
            end
        end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            ap_cr_q <= '0; ap_dn_q <= '0; apo <= '0; ap_pend <= '0;
            for (integer k = 0; k < 8; k = k + 1) begin apcr[k] <= APC; aprr[k] <= 5'd31; end
        end else begin
            ap_cr_q <= ap_cr; ap_dn_q <= ap_done;                      // pin flops
            ap_pend <= ap_pend + 16'($countones(ap_dn_q)) - 16'($countones(apx));
            for (integer k = 0; k < 8; k = k + 1) begin : snd
                reg sent; reg [276:0] h; sent = 1'b0; h = '0;
                for (integer l = 0; l < WP; l = l + 1)
                    if (aq_pop[l] && aq_head[l*277 + (MUT == 13 ? 272 : 273) +: 3] == 3'(k)) begin sent = 1'b1; h = aq_head[l*277 +: 277]; aprr[k] <= 5'(l); end
                apo[k*278 +: 278] <= {sent, h};
                apcr[k] <= apcr[k] - sent + ap_cr_q[k];
            end
        end
    // per-client station: a 4-entry FIFO with one explicit write enable per entry (hgi-1010/c: the for-loop over clients
    // writing a 2-D array elaborated as a 24-deep procmux chain from cq to sq; rtl_boundary refused in->reg 25 levels)
    wire [NC-1:0]     h_v;
    wire [NC*337-1:0] h_q;
    wire [NC-1:0]     ovf;                 // a push into a full station that does not pop this cycle
    wire [NC-1:0]     pk_rng;              // a packet address past the VM
    wire [NC-1:0]     req_r, rsp_v;
    wire [NC*273-1:0] rsp;
    wire [15:0] ce; wire ue, mask_fault;
    reg proto;
    ot_hgi_vm_core #(.NC(NC), .OUT(4), .WP(WP), .WDIRECT(WDIRECT), .RP(RP), .W2(W2), .MUT(MUT)) u_core (.clk(clk), .rst_n(rst_n), .req_v(h_v), .req_r(req_r), .req(h_q),
        .rsp_v(rsp_v), .rsp_r({NC{1'b1}}), .rsp(rsp), .ce(ce), .ue(ue), .mask_fault(mask_fault),
        .inj_v(1'b0), .inj_bank(5'd0), .inj_word(3'd0), .inj_mask(39'd0),
        .wl_v(wl_v), .wl_sec(wl_sec), .wl_d(wl_d), .wl_m(wl_m), .wl_done(wl_done), .wl_conflict(wl_conflict),
        .rl_v(rl_v), .rl_sec(rl_sec), .rl_acc(rl_acc), .rl_rsp(rl_rsp), .rl_conflict(rl_conflict),
        .w2_v(w2_v), .w2_sec(w2_sec), .w2_d(w2_d), .w2_m(w2_m), .w2_acc(w2_acc), .w2_done(w2_done));
    genvar gc;
    for (gc = 0; gc < NC; gc = gc + 1) begin : g_st
        reg [336:0] e0, e1, e2, e3; reg rflt;
        reg [1:0] sh, stl; reg [2:0] sn;
        wire push = cq[gc*338 + 337];
        // hgi-1010 b: a packet address past the VM (byte address [31:20] != 0, e.g. the aperture's words >= 2^18) faults
        // (status proto) and its write mask is cleared (nothing written; a read returns an aliased sector, the CP halts)
        wire rng = (MUT != 12) && (cq[gc*338 + 324 +: 12] != 12'd0);
        wire [336:0] cqe = rng ? {cq[gc*338 + 48 +: 289], 32'd0, cq[gc*338 +: 16]} : cq[gc*338 +: 337];
        wire pop  = h_v[gc] && req_r[gc];
        assign ovf[gc] = push && sn == 3'd4 && !pop;
        wire wr = push && !ovf[gc];
        assign h_v[gc] = sn != 3'd0;
        assign h_q[gc*337 +: 337] = (sh == 2'd0) ? e0 : (sh == 2'd1) ? e1 : (sh == 2'd2) ? e2 : e3;
        assign pk_rng[gc] = rflt;
        always @(posedge clk) begin
            if (wr && stl == 2'd0) e0 <= cqe;
            if (wr && stl == 2'd1) e1 <= cqe;
            if (wr && stl == 2'd2) e2 <= cqe;
            if (wr && stl == 2'd3) e3 <= cqe;
        end
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin sh <= 2'd0; stl <= 2'd0; sn <= 3'd0; cr[gc*274 +: 274] <= 274'd0; rflt <= 1'b0; end
            else begin
                if (push && rng) rflt <= 1'b1;
                if (wr) stl <= stl + 2'd1;
                if (pop) sh <= sh + 2'd1;
                sn <= sn + {2'd0, wr} - {2'd0, pop};
                cr[gc*274 +: 274] <= {rsp_v[gc], rsp[gc*273 +: 273]};
            end
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin proto <= 1'b0; status <= 19'd0; end
        else begin
            if (|ovf) proto <= 1'b1;
            status <= {proto | wl_conflict | rl_conflict | rq_ovf | w2_ovf | (|ap_flt) | (|pk_rng), mask_fault, ue, ce};
        end
endmodule
`default_nettype wire
