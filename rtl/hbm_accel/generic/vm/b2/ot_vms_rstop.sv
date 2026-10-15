`timescale 1ns/1ps
`default_nettype none
// HBM B2 VM slice RING STOP (el1011-hbm-b2-vm, SPEC v0.4, 2026-10-12).  The slice ring is two unidirectional WIDE rings
// over the 4 quadrant slices: CW (sid -> sid+1) and CCW (sid -> sid-1).  Both directions are this one netlist (a slice
// has 2 instances: dir strap 0 = CW, 1 = CCW), each on one wide physical channel (2,224 b + a 2-b per-VC credit
// return) carrying 2 virtual channels:
//   VC0 (requests)   PREQ  packet request to the slices in dmask (1 hop, or along the ring for a packet mirror write)
//                    WBC   8-lane mirror (REPL) write broadcast from the bank egress: CW copy -> {sid+1, sid+2},
//                          CCW copy -> {sid+3}, so every remote mirror is <= 2 hops (SPEC 2a "Ring link" v0.4)
//   VC1 (responses)  PRSP  packet response (the ring client answers on the direction opposite to the request's)
//                    WACK  WBC ack (sent by the ejecting stop's ack table through the OPPOSITE stop)
// Flow control: per-hop, per-VC credits (a relay stage is a flop each way; the receiver holds D flits a VC) with BUBBLE
//   flow per VC: forwarding takes 1 credit of the VC, injecting 2, so neither VC's ring ever fills.  VC1 always ejects
//   (hub reorder buffers are preallocated; a WACK is a pulse), VC0 ejects only into buffers that drain without VC0 (bank
//   ring-write queues, the ring client): no protocol deadlock, NO barriers.
// Flit = {v, kind 2 (0 PREQ, 1 WBC, 2 PRSP, 3 WACK; vc = kind[1]), dmask 4, src 2, client 4, seq 2, we/echo,
//         8 x lane {v, rowm 11, data 256, wmask 8}}   (PRSP data rides in lane 0's data field).
// WBC ack: a WBC ejected here is acked to its source (WACK, via the opposite stop) once every lane is in the macro
//   (xq_done); mirror_busy = this stop's own broadcasts not yet acked (acks arrive at the OPPOSITE stop: ack_i).
// Reset only on control (valids, pointers, counters, credits); payload flops and buffers have no reset.
// Physical structure: the VC0 input buffer is lane-sliced (8 x 276-b lane chunks + the 15-b header chunk), each chunk
// with its OWN kept copies of the write enable and the read / write pointers, so no pointer or enable net drives more
// than one chunk (~800 loads) -- no 2,223-b-wide select net.  VC1 (PRSP / WACK) flits carry only the header and lane 0's
// data, so the VC1 buffer stores 271 b an entry and the forwarded flit is rebuilt (the other lanes are zero).
module ot_vms_rstop #(
    parameter integer PHYSICAL_RING = 0, // 1: global SID order SW0,SE1,NE3,NW2 on physical perimeter
    parameter integer FW  = 2224,   // flit width (fixed)
    parameter integer D   = 3,      // per-VC input buffer depth (= the upstream's credits a VC)
    parameter integer HF  = 2,      // hub PREQ FIFO depth (the hub's pi credits)
    parameter integer RF  = 2,      // ring-client PRSP FIFO depth (the ring client's ri credits)
    parameter integer EJ  = 2,      // ring-client credits (its FIFO depth for this stop)
    parameter integer XQD = 2,      // bank ring-write credits a lane (= ot_vms_bank XQD)
    parameter integer EGC = 1,      // egress buffer depth a lane (= ot_vms_bank EGC)
    parameter integer WAK = 2,      // WACK FIFO depth (the opposite stop's wko credits)
    parameter integer T   = 4,      // WBC ack table depth
    parameter integer MUT = 0       // 2: every 8th VC0 credit dropped; 3 (CCW stop only): VC1 credits returned on VC0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [1:0]        sid,
    input  wire              dir,          // strap: 0 CW, 1 CCW
    input  wire [FW-1:0]     l_in,
    output reg  [1:0]        l_in_cr,      // per-VC credit back upstream
    output wire [FW-1:0]     l_out,
    input  wire [1:0]        l_out_cr,
    input  wire [289:0]      pi,           // hub PREQ {v, dmask 4, client 4, seq 2, we, bank 3, rowm 11, wmask 8, data 256}
    output reg               pi_cr,
    input  wire [8*276-1:0]  eg,           // bank egress {v, rowm 11, data 256, wmask 8} per bank
    output reg  [7:0]        eg_cr,
    output wire [8*276-1:0]  xq,           // bank ring write {v, rowm 11, data 256, wmask 8}
    input  wire [7:0]        xq_cr,
    input  wire [7:0]        xq_done,
    output wire [287:0]      rce,          // to the ring client {v, src 2, client 4, seq 2, we, bank 3, rowm 11, wmask 8, data 256}
    input  wire              rce_cr,
    input  wire [265:0]      ri,           // ring-client PRSP {v, dst 2, client 4, seq 2, echo, data 256}
    output reg               ri_cr,
    output reg  [2:0]        wko,          // WACK request {v, dst 2} to the opposite stop
    input  wire              wko_cr,
    input  wire [2:0]        wki,          // WACK request from the opposite stop
    output reg               wki_cr,
    output wire [263:0]      cco,          // PRSP to the hub {v, client 4, seq 2, echo, data 256}
    output reg               ack_o,        // a WACK for this slice arrived here (-> the opposite stop's ack_i)
    input  wire              ack_i,
    output reg               mirror_busy
);
    localparam integer DB = (D > 1) ? $clog2(D) : 1, HB = (HF > 1) ? $clog2(HF) : 1, EB = (EGC > 1) ? $clog2(EGC) : 1;
    localparam integer TB = (T > 1) ? $clog2(T) : 1, RB = (RF > 1) ? $clog2(RF) : 1, WB = (WAK > 1) ? $clog2(WAK) : 1;
    // ------------------------------------------------------------------ pin flops (payload: no reset)
    reg [FW-2:0] in_d; reg in_v; reg [288:0] pi_d; reg pi_v; reg [8*276-1:0] eg_d; reg [7:0] eg_v; reg [264:0] ri_d; reg ri_v;
    reg [2:0] wki_r; reg [7:0] xq_cr_r, xq_done_r; reg [1:0] out_cr_r; reg rce_cr_r, wko_cr_r, ack_r; reg [1:0] me; reg dr;
    wire [FW-1:0] in_r = {in_v, in_d}; wire [289:0] pi_r = {pi_v, pi_d}; wire [265:0] ri_r = {ri_v, ri_d};
    reg [8*276-1:0] eg_r;
    always @* begin eg_r = eg_d; for (integer l = 0; l < 8; l = l + 1) eg_r[l*276 + 275] = eg_v[l]; end
    // output registers: control valid + payload
    reg lo_v; reg [FW-2:0] lo_d; reg [7:0] xq_v; reg [8*276-1:0] xq_d; reg rce_v; reg [286:0] rce_d; reg cco_v; reg [262:0] cco_d;
    assign l_out = {lo_v, lo_d}; assign rce = {rce_v, rce_d}; assign cco = {cco_v, cco_d};
    genvar gl;
    for (gl = 0; gl < 8; gl = gl + 1) begin : g_xq
        assign xq[gl*276 +: 276] = {xq_v[gl], xq_d[gl*276 +: 275]};
    end

    // ------------------------------------------------------------------ buffers
    reg [270:0]  ib1 [0:D-1]; reg [DB-1:0] ih [0:1], it [0:1]; reg [DB:0] inn [0:1];   // VC1: {header 15, lane-0 data 256}
    reg [288:0]  hb [0:HF-1]; reg [HB-1:0] hh, ht; reg [HB:0] hn;
    reg [264:0]  rb [0:RF-1]; reg [RB-1:0] rh, rt; reg [RB:0] rn;
    reg [1:0]    wb [0:WAK-1]; reg [WB-1:0] wh, wt; reg [WB:0] wn;
    reg [274:0]  gb [0:7][0:EGC-1]; reg [EB-1:0] gh [0:7], gt [0:7]; reg [EB:0] gn [0:7];
    reg [3:0] outc [0:1]; reg [2:0] rcec, wkoc; reg [2:0] xqc [0:7];
    reg h_ej, h_fw;                                  // the VC0 head's eject / forward already done
    reg t_v [0:T-1]; reg [1:0] t_src [0:T-1]; reg [7:0] t_pend [0:T-1]; reg [TB-1:0] th, tt; reg [TB:0] tn;
    reg [7:0] mc; reg [2:0] crcnt; reg inj_pick, v1pick;

    // ------------------------------------------------------------------ decisions
    wire [FW-2:0] h0;                                 // VC0 head, assembled from the lane chunks (g_ck below)
    wire [270:0] h1n = ib1[ih[1]];
    wire [FW-2:0] h1 = {h1n[270:256], 1944'd0, h1n[255:0], 8'd0};
    wire hv0 = inn[0] != 0, hv1 = inn[1] != 0;
    wire k0 = h0[2221];                               // VC0 kind: 0 PREQ, 1 WBC
    wire [3:0] dm0 = h0[2220:2217], dm1 = h1[2220:2217];
    wire own0 = dm0[me]; wire [3:0] rest0 = dm0 & ~(4'd1 << me);
    wire own1 = dm1[me];
    reg [7:0] h_lanes;
    always @* for (integer l = 0; l < 8; l = l + 1) h_lanes[l] = h0[l*276 + 275];
    reg ej_ok;
    always @* begin
        ej_ok = 1'b0;
        if (k0 == 1'b0) ej_ok = rcec != 3'd0;
        else begin
            ej_ok = tn != (TB+1)'(T);
            for (integer l = 0; l < 8; l = l + 1) if (h_lanes[l] && xqc[l] == 3'd0) ej_ok = 1'b0;
        end
    end
    wire ej1 = hv1 && own1;                           // VC1 always ejects
    wire fw1 = hv1 && !own1 && outc[1] != 4'd0;
    wire need_ej = hv0 && own0 && !h_ej;
    wire need_fw = hv0 && rest0 != 4'd0 && !h_fw;
    wire do_ej = need_ej && ej_ok;
    wire fw0 = need_fw && outc[0] != 4'd0 && !fw1;
    wire pop0 = hv0 && (!own0 || h_ej || do_ej) && (rest0 == 4'd0 || h_fw || fw0);
    wire busy_o = fw1 || fw0;
    // injection: VC1 (PRSP / WACK, alternating) before VC0 (hub PREQ / egress WBC, alternating); 2 credits of the VC
    wire inj_r = !busy_o && outc[1] >= 4'd2 && rn != 0 && (!v1pick || wn == 0);
    wire inj_w = !busy_o && outc[1] >= 4'd2 && wn != 0 && !inj_r;
    reg [7:0] g_v; always @* for (integer l = 0; l < 8; l = l + 1) g_v[l] = gn[l] != 0;
    wire can0 = !busy_o && !inj_r && !inj_w && outc[0] >= 4'd2;
    wire inj_hub = can0 && hn != 0 && (!inj_pick || g_v == 8'd0);
    wire inj_eg  = can0 && g_v != 8'd0 && !inj_hub;
    // WBC destinations of this direction: CW {sid+1, sid+2}, CCW {sid+3}
    wire [1:0] me_rank={me[1],me[1]^me[0]};
    wire [1:0] rank1=me_rank+2'd1,rank2=me_rank+2'd2,rank3=me_rank+2'd3;
    wire [1:0] me1=PHYSICAL_RING?{rank1[1],rank1[1]^rank1[0]}:me+2'd1;
    wire [1:0] me2=PHYSICAL_RING?{rank2[1],rank2[1]^rank2[0]}:me+2'd2;
    wire [1:0] me3=PHYSICAL_RING?{rank3[1],rank3[1]^rank3[0]}:me+2'd3;
    wire [3:0] wdm = dr ? (4'd1 << me3) : ((4'd1 << me1) | (4'd1 << me2));
    wire [7:0] wdn = dr ? 8'd1 : 8'd2;

    // ------------------------------------------------------------------ VC0 input buffer: lane chunks
    genvar gc;
    for (gc = 0; gc < 9; gc = gc + 1) begin : g_ck
        localparam integer LO = (gc < 8) ? gc * 276 : 2208, CW = (gc < 8) ? 276 : 15;
        (* keep = "true", dont_touch = "true" *) reg [DB-1:0] rp, wp;
        (* keep = "true", dont_touch = "true" *) reg we;
        reg [CW-1:0] m [0:D-1];
        always @(posedge clk or negedge rst_n)
            if (!rst_n) begin rp <= '0; wp <= '0; we <= 1'b0; end
            else begin
                we <= l_in[FW-1] && !l_in[2222];          // this chunk's copy of "a VC0 flit lands next cycle"
                if (we) wp <= (wp + 1'b1 == DB'(D)) ? '0 : wp + 1'b1;
                if (pop0) rp <= (rp + 1'b1 == DB'(D)) ? '0 : rp + 1'b1;
            end
        always @(posedge clk) if (we) m[wp] <= in_d[LO +: CW];
        assign h0[LO +: CW] = m[rp];
    end

    // ------------------------------------------------------------------ control (reset)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (integer v = 0; v < 2; v = v + 1) begin ih[v] <= '0; it[v] <= '0; inn[v] <= '0; outc[v] <= 4'(D); end
            hh <= '0; ht <= '0; hn <= '0; rh <= '0; rt <= '0; rn <= '0; wh <= '0; wt <= '0; wn <= '0;
            h_ej <= 1'b0; h_fw <= 1'b0; inj_pick <= 1'b0; v1pick <= 1'b0;
            rcec <= 3'(EJ); wkoc <= 3'(WAK); th <= '0; tt <= '0; tn <= '0; mc <= 8'd0; crcnt <= 3'd0;
            l_in_cr <= 2'b00; pi_cr <= 1'b0; ri_cr <= 1'b0; wki_cr <= 1'b0; eg_cr <= '0; wko <= '0; ack_o <= 1'b0; mirror_busy <= 1'b0;
            lo_v <= 1'b0; xq_v <= '0; rce_v <= 1'b0; cco_v <= 1'b0;
            in_v <= 1'b0; pi_v <= 1'b0; eg_v <= '0; ri_v <= 1'b0; wki_r <= '0; xq_cr_r <= '0; xq_done_r <= '0; out_cr_r <= '0;
            rce_cr_r <= 1'b0; wko_cr_r <= 1'b0; ack_r <= 1'b0;
            for (integer l = 0; l < 8; l = l + 1) begin gh[l] <= '0; gt[l] <= '0; gn[l] <= '0; xqc[l] <= 3'(XQD); end
            for (integer k = 0; k < T; k = k + 1) begin t_v[k] <= 1'b0; t_pend[k] <= 8'd0; end
        end else begin : seq
            reg [7:0] dl; reg wpop; reg [7:0] np [0:T-1]; reg egany; reg c0, c1;
            in_v <= l_in[FW-1]; pi_v <= pi[289]; ri_v <= ri[265]; wki_r <= wki; xq_cr_r <= xq_cr; xq_done_r <= xq_done;
            out_cr_r <= l_out_cr; rce_cr_r <= rce_cr; wko_cr_r <= wko_cr; ack_r <= ack_i;
            for (integer l = 0; l < 8; l = l + 1) eg_v[l] <= eg[l*276 + 275];
            // ---- input VC buffers (the upstream respects the per-VC credits)
            for (integer v = 0; v < 2; v = v + 1) begin
                if (in_r[FW-1] && in_r[2222] == v[0]) it[v] <= (it[v] + 1'b1 == DB'(D)) ? '0 : it[v] + 1'b1;
                inn[v] <= inn[v] + ((in_r[FW-1] && in_r[2222] == v[0]) ? 1 : 0) - (((v == 0) ? pop0 : (ej1 || fw1)) ? 1 : 0);
            end
            if (pop0) begin ih[0] <= (ih[0] + 1'b1 == DB'(D)) ? '0 : ih[0] + 1'b1; h_ej <= 1'b0; h_fw <= 1'b0; end
            else begin if (do_ej) h_ej <= 1'b1; if (fw0) h_fw <= 1'b1; end
            if (ej1 || fw1) ih[1] <= (ih[1] + 1'b1 == DB'(D)) ? '0 : ih[1] + 1'b1;
            // credits back upstream (MUT 2 drops every 8th VC0 credit; MUT 3 on the CCW stop returns VC1 credits as VC0)
            if (pop0) crcnt <= crcnt + 3'd1;
            c0 = pop0 && !(MUT == 2 && crcnt == 3'd7);
            c1 = ej1 || fw1;
            if (MUT == 3 && dr) begin c0 = c0 || c1; c1 = 1'b0; end
            l_in_cr <= {c1, c0};
            // ---- VC1 eject
            cco_v <= ej1 && h1[2221] == 1'b0;     // PRSP (kind 2)
            ack_o <= ej1 && h1[2221] == 1'b1;     // WACK (kind 3)
            // ---- hub / ring-client / WACK FIFOs and egress buffers
            if (pi_r[289]) ht <= (ht + 1'b1 == HB'(HF)) ? '0 : ht + 1'b1;
            hn <= hn + (pi_r[289] ? 1 : 0) - (inj_hub ? 1 : 0);
            if (inj_hub) hh <= (hh + 1'b1 == HB'(HF)) ? '0 : hh + 1'b1;
            pi_cr <= inj_hub;
            if (ri_r[265]) rt <= (rt + 1'b1 == RB'(RF)) ? '0 : rt + 1'b1;
            rn <= rn + (ri_r[265] ? 1 : 0) - (inj_r ? 1 : 0);
            if (inj_r) rh <= (rh + 1'b1 == RB'(RF)) ? '0 : rh + 1'b1;
            ri_cr <= inj_r;
            if (wki_r[2]) wt <= (wt + 1'b1 == WB'(WAK)) ? '0 : wt + 1'b1;
            wn <= wn + (wki_r[2] ? 1 : 0) - (inj_w ? 1 : 0);
            if (inj_w) wh <= (wh + 1'b1 == WB'(WAK)) ? '0 : wh + 1'b1;
            wki_cr <= inj_w;
            if (inj_r || inj_w) v1pick <= inj_r;
            for (integer l = 0; l < 8; l = l + 1) begin
                if (eg_r[l*276 + 275]) gt[l] <= (gt[l] + 1'b1 == EB'(EGC)) ? '0 : gt[l] + 1'b1;
                gn[l] <= gn[l] + (eg_r[l*276 + 275] ? 1 : 0) - ((inj_eg && g_v[l]) ? 1 : 0);
                if (inj_eg && g_v[l]) gh[l] <= (gh[l] + 1'b1 == EB'(EGC)) ? '0 : gh[l] + 1'b1;
                eg_cr[l] <= inj_eg && g_v[l];
            end
            // ---- output link
            lo_v <= fw1 || fw0 || inj_r || inj_w || inj_hub || inj_eg;
            if (inj_hub) inj_pick <= 1'b1; else if (inj_eg) inj_pick <= 1'b0;
            outc[1] <= outc[1] - ((fw1 || inj_r || inj_w) ? 4'd1 : 4'd0) + (out_cr_r[1] ? 4'd1 : 4'd0);
            outc[0] <= outc[0] - ((fw0 || inj_hub || inj_eg) ? 4'd1 : 4'd0) + (out_cr_r[0] ? 4'd1 : 4'd0);
            // ---- VC0 eject
            rce_v <= do_ej && k0 == 1'b0;
            for (integer l = 0; l < 8; l = l + 1) xq_v[l] <= do_ej && k0 && h_lanes[l];
            rcec <= rcec - ((do_ej && k0 == 1'b0) ? 3'd1 : 3'd0) + (rce_cr_r ? 3'd1 : 3'd0);
            for (integer l = 0; l < 8; l = l + 1)
                xqc[l] <= xqc[l] - ((do_ej && k0 && h_lanes[l]) ? 3'd1 : 3'd0) + (xq_cr_r[l] ? 3'd1 : 3'd0);
            // ---- ack table: done pulses clear the oldest entry pending on that lane
            dl = xq_done_r;
            for (integer j = 0; j < T; j = j + 1) begin : tj
                integer k; reg [7:0] p; k = (th + j) % T; p = t_pend[k];
                if (t_v[k]) begin p = p & ~dl; dl = dl & ~t_pend[k]; end
                np[k] = p; t_pend[k] <= p;
            end
            wpop = t_v[th] && np[th] == 8'd0 && wkoc != 3'd0;
            wko[2] <= wpop;
            if (wpop) begin wko[1:0] <= t_src[th]; t_v[th] <= 1'b0; th <= (th + 1'b1 == TB'(T)) ? '0 : th + 1'b1; end
            if (do_ej && k0) begin t_v[tt] <= 1'b1; t_pend[tt] <= h_lanes; tt <= (tt + 1'b1 == TB'(T)) ? '0 : tt + 1'b1; end
            tn <= tn + ((do_ej && k0) ? 1 : 0) - (wpop ? 1 : 0);
            wkoc <= wkoc - (wpop ? 3'd1 : 3'd0) + (wko_cr_r ? 3'd1 : 3'd0);
            // ---- mirror broadcast accounting (this stop's WBCs; their acks arrive at the opposite stop)
            egany = 1'b0; for (integer l = 0; l < 8; l = l + 1) egany = egany | eg_r[l*276 + 275];
            mc <= mc + (inj_eg ? wdn : 8'd0) - (ack_r ? 8'd1 : 8'd0);
            mirror_busy <= (mc + (inj_eg ? wdn : 8'd0) - (ack_r ? 8'd1 : 8'd0)) != 8'd0 || g_v != 8'd0 || egany;
        end

    // ------------------------------------------------------------------ payload (no reset)
    always @(posedge clk) begin : dat
        reg [FW-1:0] f; reg [288:0] e; reg [264:0] r; reg [2:0] bk; reg [274:0] sl;
        in_d <= l_in[FW-2:0]; pi_d <= pi[288:0]; eg_d <= eg; ri_d <= ri[264:0]; me <= sid; dr <= dir;
        if (in_r[FW-1] && in_r[2222]) ib1[it[1]] <= {in_r[2222:2208], in_r[263:8]};
        if (pi_r[289]) hb[ht] <= pi_r[288:0];
        if (ri_r[265]) rb[rt] <= ri_r[264:0];
        if (wki_r[2]) wb[wt] <= wki_r[1:0];
        for (integer l = 0; l < 8; l = l + 1)
            if (eg_r[l*276 + 275]) gb[l][gt[l]] <= eg_r[l*276 +: 275];
        // ---- output flit
        f = '0;
        if (fw1) f[FW-2:0] = h1;
        else if (fw0) f[FW-2:0] = {h0[2222:2221], rest0, h0[2216:0]};
        else if (inj_r) begin
            r = rb[rh];   // {dst 2, client 4, seq 2, echo, data 256}
            f[2222:2221] = 2'd2; f[2220:2217] = 4'd1 << r[264:263]; f[2216:2215] = me; f[2214:2211] = r[262:259];
            f[2210:2209] = r[258:257]; f[2208] = r[256]; f[263:8] = r[255:0];
        end else if (inj_w) begin
            f[2222:2221] = 2'd3; f[2220:2217] = 4'd1 << wb[wh]; f[2216:2215] = me;
        end else if (inj_hub) begin
            e = hb[hh];   // {dmask 4, client 4, seq 2, we, bank 3, rowm 11, wmask 8, data 256}
            f[2222:2221] = 2'd0; f[2220:2217] = e[288:285]; f[2216:2215] = me; f[2214:2211] = e[284:281];
            f[2210:2209] = e[280:279]; f[2208] = e[278];
            for (integer l = 0; l < 8; l = l + 1)
                if (e[277:275] == 3'(l)) f[l*276 +: 276] = {1'b1, e[274:264], e[255:0], e[263:256]};
        end else begin
            f[2222:2221] = 2'd1; f[2220:2217] = wdm; f[2216:2215] = me;
            for (integer l = 0; l < 8; l = l + 1) if (g_v[l]) f[l*276 +: 276] = {1'b1, gb[l][gh[l]]};
        end
        lo_d <= f[FW-2:0];
        // ---- eject payloads
        // a PREQ has exactly one lane: AND-OR select (no runtime part-select)
        bk = 3'd0; sl = '0;
        for (integer l = 0; l < 8; l = l + 1) if (h_lanes[l]) begin bk = 3'(l); sl = sl | h0[l*276 +: 275]; end
        rce_d <= {h0[2216:2215], h0[2214:2211], h0[2210:2209], h0[2208], bk, sl[274:264], sl[7:0], sl[263:8]};
        for (integer l = 0; l < 8; l = l + 1) xq_d[l*276 +: 275] <= h0[l*276 +: 275];
        if (do_ej && k0) t_src[tt] <= h0[2216:2215];
        cco_d <= {h1[2214:2211], h1[2210:2209], h1[2208], h1[263:8]};
    end
endmodule
`default_nettype wire
