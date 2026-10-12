`timescale 1ns/1ps
`default_nettype none
// HBM B2 VM slice CW RING STOP (el1011-hbm-b2-vm, 2026-10-12).  The slice ring is two unidirectional rings over the 4
// quadrant slices 0 (NW) -> 1 (NE) -> 2 (SE) -> 3 (SW) -> 0:
//   CW  (sid -> sid+1), WIDE (2,223 b): requests only -- packet PREQs to slice sid+1 / sid+2 and mirror-write
//        broadcasts (packet PREQ or 8-lane WBC with dmask = the other 3 slices, 3 hops, every stop writes and forwards);
//   CCW (sid -> sid-1), NARROW (ot_vms_ccwstop): PREQs to sid+3 on its request VC; every response (PRSP) and every
//        write-broadcast ack (WACK) on its response VC.
// Flow control: per-hop credits (a relay stage is a flop each way; the receiver buffer is D deep) with BUBBLE flow:
//   a forwarded flit needs 1 credit, an injected flit 2, so the ring never fills (no ring deadlock).  CW flits only
//   eject into buffers that drain without the CW ring (bank ring-write queues; the ring client, which answers on CCW),
//   and CCW responses always eject (the hub's reorder buffers are preallocated): no protocol deadlock, NO barriers.
// CW flit = {v, kind (0 PREQ, 1 WBC), dmask 4, src 2, client 4, seq 2, we, 8 x lane {v, rowm 11, data 256, wmask 8}}.
// WBC ack: a WBC ejected here is acked to its source (WACK over CCW) once every lane is in the macro (xq_done);
// mirror_busy = this slice's own broadcasts not yet acked by all 3 others (the CP's local fence, not a barrier).
module ot_vms_cwstop #(
    parameter integer D   = 3,      // CW input buffer depth (the upstream's credits)
    parameter integer HF  = 2,      // hub PREQ FIFO depth (the hub's cwi credits)
    parameter integer EJ  = 2,      // ring-client credits (its CW FIFO depth)
    parameter integer XQD = 2,      // bank ring-write credits a lane (= ot_vms_bank XQD)
    parameter integer EGC = 1,      // egress buffer depth a lane (= ot_vms_bank EGC)
    parameter integer WAK = 2,      // WACK credits (the CCW stop's WACK FIFO depth)
    parameter integer T   = 4,      // WBC ack table depth
    parameter integer MUT = 0       // 2: every 8th input credit is not returned (ring credit drop: must FAIL)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [1:0]        sid,
    input  wire [2222:0]     cw_in,
    output reg               cw_in_cr,
    output reg  [2222:0]     cw_out,
    input  wire              cw_out_cr,
    input  wire [289:0]      cwi,          // hub PREQ {v, dmask 4, client 4, seq 2, we, bank 3, rowm 11, wmask 8, data 256}
    output reg               cwi_cr,
    input  wire [8*276-1:0]  eg,           // bank egress {v, rowm 11, data 256, wmask 8} per bank
    output reg  [7:0]        eg_cr,
    output reg  [8*276-1:0]  xq,           // bank ring write {v, rowm 11, data 256, wmask 8}
    input  wire [7:0]        xq_cr,
    input  wire [7:0]        xq_done,
    output reg  [287:0]      rce,          // to the ring client {v, src 2, client 4, seq 2, we, bank 3, rowm 11, wmask 8, data 256}
    input  wire              rce_cr,
    output reg  [2:0]        wak,          // WACK request {v, dst 2} to the CCW stop
    input  wire              wak_cr,
    input  wire              ack_in,       // one WACK for this slice arrived (CCW stop)
    output reg               mirror_busy
);
    localparam integer FW = 2223;
    localparam integer DB = (D > 1) ? $clog2(D) : 1, HB = (HF > 1) ? $clog2(HF) : 1, EB = (EGC > 1) ? $clog2(EGC) : 1;
    localparam integer TB = (T > 1) ? $clog2(T) : 1;
    // ------------------------------------------------------------------ pin flops
    reg [FW-1:0] in_r; reg [289:0] cwi_r; reg [8*276-1:0] eg_r; reg [7:0] xq_cr_r, xq_done_r; reg out_cr_r, rce_cr_r, wak_cr_r, ack_r;
    reg [1:0] me;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin in_r <= '0; cwi_r <= '0; eg_r <= '0; xq_cr_r <= '0; xq_done_r <= '0; out_cr_r <= 1'b0; rce_cr_r <= 1'b0; wak_cr_r <= 1'b0; ack_r <= 1'b0; me <= 2'd0; end
        else begin in_r <= cw_in; cwi_r <= cwi; eg_r <= eg; xq_cr_r <= xq_cr; xq_done_r <= xq_done; out_cr_r <= cw_out_cr; rce_cr_r <= rce_cr; wak_cr_r <= wak_cr; ack_r <= ack_in; me <= sid; end

    // ------------------------------------------------------------------ buffers
    reg [FW-2:0] ib [0:D-1]; reg [DB-1:0] ih, it; reg [DB:0] in_n;
    reg [288:0]  hb [0:HF-1]; reg [HB-1:0] hh, ht; reg [HB:0] hn;
    reg [274:0]  gb [0:7][0:EGC-1]; reg [EB-1:0] gh [0:7], gt [0:7]; reg [EB:0] gn [0:7];
    reg [3:0] outc; reg [2:0] rcec, wakc; reg [2:0] xqc [0:7];
    reg h_ej, h_fw;                                  // the head's eject / forward already done
    // ack table
    reg t_v [0:T-1]; reg [1:0] t_src [0:T-1]; reg [7:0] t_pend [0:T-1]; reg [TB-1:0] th, tt; reg [TB:0] tn;
    reg [7:0] mc;

    wire [FW-2:0] h = ib[ih];
    wire hv = in_n != 0;
    wire h_kind = h[2221]; wire [3:0] h_dm = h[2220:2217];
    wire own = h_dm[me]; wire [3:0] rest = h_dm & ~(4'd1 << me);
    reg [7:0] h_lanes;
    always @* for (integer l = 0; l < 8; l = l + 1) h_lanes[l] = h[l*276 + 275];
    // eject possible this cycle?
    reg ej_ok;
    always @* begin
        ej_ok = 1'b0;
        if (h_kind == 1'b0) ej_ok = rcec != 3'd0;
        else begin
            ej_ok = tn != (TB+1)'(T);
            for (integer l = 0; l < 8; l = l + 1) if (h_lanes[l] && xqc[l] == 3'd0) ej_ok = 1'b0;
        end
    end
    wire need_ej = hv && own && !h_ej;
    wire need_fw = hv && rest != 4'd0 && !h_fw;
    wire do_ej = need_ej && ej_ok;
    wire do_fw = need_fw && outc != 4'd0;
    wire h_pop = hv && (!own || h_ej || do_ej) && (rest == 4'd0 || h_fw || do_fw);
    // injection (only when not forwarding): hub PREQ or the egress lanes, alternating
    reg [7:0] g_v; always @* for (integer l = 0; l < 8; l = l + 1) g_v[l] = gn[l] != 0;
    reg inj_pick;                                     // 0 hub, 1 egress (preferred alternately)
    wire can_inj = !do_fw && outc >= 4'd2;
    wire inj_hub = can_inj && hn != 0 && (!inj_pick || g_v == 8'd0);
    wire inj_eg  = can_inj && g_v != 8'd0 && !inj_hub;
    reg [7:0] d_lane;                                 // done pulses this cycle not yet consumed (applied in order)
    reg [2:0] crn; reg [2:0] crcnt;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            ih <= '0; it <= '0; in_n <= '0; hh <= '0; ht <= '0; hn <= '0; h_ej <= 1'b0; h_fw <= 1'b0; inj_pick <= 1'b0;
            outc <= 4'(D); rcec <= 3'(EJ); wakc <= 3'(WAK); th <= '0; tt <= '0; tn <= '0; mc <= 8'd0; crcnt <= 3'd0;
            cw_out <= '0; cw_in_cr <= 1'b0; cwi_cr <= 1'b0; eg_cr <= '0; xq <= '0; rce <= '0; wak <= '0; mirror_busy <= 1'b0;
            for (integer l = 0; l < 8; l = l + 1) begin gh[l] <= '0; gt[l] <= '0; gn[l] <= '0; xqc[l] <= 3'(XQD); end
            for (integer k = 0; k < T; k = k + 1) begin t_v[k] <= 1'b0; t_pend[k] <= 8'd0; end
        end else begin : seq
            reg [FW-1:0] f; reg [7:0] pend; reg [7:0] dl; reg wpop; reg [2:0] outd; reg [7:0] np [0:T-1]; reg egany;
            // ---- input buffer push (the upstream respects credits)
            if (in_r[FW-1]) begin ib[it] <= in_r[FW-2:0]; it <= (it + 1'b1 == DB'(D)) ? '0 : it + 1'b1; end
            in_n <= in_n + (in_r[FW-1] ? 1 : 0) - (h_pop ? 1 : 0);
            if (h_pop) begin ih <= (ih + 1'b1 == DB'(D)) ? '0 : ih + 1'b1; h_ej <= 1'b0; h_fw <= 1'b0; end
            else begin if (do_ej) h_ej <= 1'b1; if (do_fw) h_fw <= 1'b1; end
            // credit back upstream (MUT 2 drops every 8th)
            if (h_pop) crcnt <= crcnt + 3'd1;
            cw_in_cr <= h_pop && !(MUT == 2 && crcnt == 3'd7);
            // ---- hub FIFO / egress buffers push
            if (cwi_r[289]) begin hb[ht] <= cwi_r[288:0]; ht <= (ht + 1'b1 == HB'(HF)) ? '0 : ht + 1'b1; end
            hn <= hn + (cwi_r[289] ? 1 : 0) - (inj_hub ? 1 : 0);
            if (inj_hub) hh <= (hh + 1'b1 == HB'(HF)) ? '0 : hh + 1'b1;
            cwi_cr <= inj_hub;
            for (integer l = 0; l < 8; l = l + 1) begin
                if (eg_r[l*276 + 275]) begin gb[l][gt[l]] <= eg_r[l*276 +: 275]; gt[l] <= (gt[l] + 1'b1 == EB'(EGC)) ? '0 : gt[l] + 1'b1; end
                gn[l] <= gn[l] + (eg_r[l*276 + 275] ? 1 : 0) - ((inj_eg && g_v[l]) ? 1 : 0);
                if (inj_eg && g_v[l]) gh[l] <= (gh[l] + 1'b1 == EB'(EGC)) ? '0 : gh[l] + 1'b1;
                eg_cr[l] <= inj_eg && g_v[l];
            end
            // ---- output link
            outd = 3'd0; cw_out[FW-1] <= 1'b0;
            if (do_fw) begin
                cw_out <= {1'b1, h[2221], rest, h[2216:0]}; outd = 3'd1;
            end else if (inj_hub) begin : ih_
                reg [288:0] e; e = hb[hh]; f = '0;
                // e = {dmask 4, client 4, seq 2, we, bank 3, rowm 11, wmask 8, data 256}
                f[FW-1] = 1'b1; f[2221] = 1'b0; f[2220:2217] = e[288:285]; f[2216:2215] = me; f[2214:2211] = e[284:281];
                f[2210:2209] = e[280:279]; f[2208] = e[278];
                for (integer l = 0; l < 8; l = l + 1)
                    if (e[277:275] == 3'(l)) f[l*276 +: 276] = {1'b1, e[274:264], e[255:0], e[263:256]};
                cw_out <= f; outd = 3'd1; inj_pick <= 1'b1;
            end else if (inj_eg) begin
                f = '0; f[FW-1] = 1'b1; f[2221] = 1'b1; f[2220:2217] = 4'hf & ~(4'd1 << me); f[2216:2215] = me;
                for (integer l = 0; l < 8; l = l + 1) if (g_v[l]) f[l*276 +: 276] = {1'b1, gb[l][gh[l]]};
                cw_out <= f; outd = 3'd1; inj_pick <= 1'b0;
            end
            outc <= outc - {1'b0, outd} + (out_cr_r ? 4'd1 : 4'd0);
            // ---- eject
            rce[287] <= 1'b0; for (integer l = 0; l < 8; l = l + 1) xq[l*276 + 275] <= 1'b0;
            pend = 8'd0;
            if (do_ej && h_kind == 1'b0) begin : ep
                reg [2:0] bk; bk = 3'd0;
                for (integer l = 0; l < 8; l = l + 1) if (h_lanes[l]) bk = 3'(l);
                // lane = {v, rowm 11, data 256, wmask 8}
                rce <= {1'b1, h[2216:2215], h[2214:2211], h[2210:2209], h[2208], bk, h[bk*276 + 264 +: 11],
                        h[bk*276 +: 8], h[bk*276 + 8 +: 256]};
            end
            if (do_ej && h_kind == 1'b1) begin
                for (integer l = 0; l < 8; l = l + 1) if (h_lanes[l]) xq[l*276 +: 276] <= h[l*276 +: 276];
                pend = h_lanes;
            end
            rcec <= rcec - ((do_ej && h_kind == 1'b0) ? 3'd1 : 3'd0) + (rce_cr_r ? 3'd1 : 3'd0);
            for (integer l = 0; l < 8; l = l + 1)
                xqc[l] <= xqc[l] - ((do_ej && h_kind && h_lanes[l]) ? 3'd1 : 3'd0) + (xq_cr_r[l] ? 3'd1 : 3'd0);
            // ---- ack table: done pulses clear the oldest entry pending on that lane
            dl = xq_done_r;
            for (integer j = 0; j < T; j = j + 1) begin : tj
                integer k; reg [7:0] p; k = (th + j) % T; p = t_pend[k];
                if (t_v[k]) begin p = p & ~dl; dl = dl & ~t_pend[k]; end
                np[k] = p; t_pend[k] <= p;
            end
            wpop = t_v[th] && np[th] == 8'd0 && wakc != 3'd0;
            wak[2] <= 1'b0;
            if (wpop) begin wak <= {1'b1, t_src[th]}; t_v[th] <= 1'b0; th <= (th + 1'b1 == TB'(T)) ? '0 : th + 1'b1; end
            if (do_ej && h_kind == 1'b1) begin
                t_v[tt] <= 1'b1; t_src[tt] <= h[2216:2215]; t_pend[tt] <= pend; tt <= (tt + 1'b1 == TB'(T)) ? '0 : tt + 1'b1;
            end
            tn <= tn + ((do_ej && h_kind == 1'b1) ? 1 : 0) - (wpop ? 1 : 0);
            wakc <= wakc - (wpop ? 3'd1 : 3'd0) + (wak_cr_r ? 3'd1 : 3'd0);
            // ---- mirror broadcast accounting
            egany = 1'b0; for (integer l = 0; l < 8; l = l + 1) egany = egany | eg_r[l*276 + 275];
            mc <= mc + (inj_eg ? 8'd3 : 8'd0) - (ack_r ? 8'd1 : 8'd0);
            mirror_busy <= (mc + (inj_eg ? 8'd3 : 8'd0) - (ack_r ? 8'd1 : 8'd0)) != 8'd0 || g_v != 8'd0 || egany;
        end
endmodule
`default_nettype wire
