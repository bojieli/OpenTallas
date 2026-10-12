`timescale 1ns/1ps
`default_nettype none
// HBM B2 VM slice CCW RING STOP + RING CLIENT (el1011-hbm-b2-vm, 2026-10-12).  See ot_vms_cwstop for the ring.
// CCW link (sid -> sid-1), narrow flit (292 b), two VCs with per-hop credits and bubble flow:
//   VC0 request: PREQ to sid-1 (= sid+3, one hop);  VC1 response: PRSP (packet response) and WACK (broadcast ack).
// Flit = {v, vc, ack, dst 2, src 2, client 4, seq 2, we/echo, bank 3, rowm 11, wmask 8, data 256}.
// Output priority: forward VC1, forward VC0, inject VC1 (PRSP / WACK), inject VC0 (hub PREQ); forward needs 1 credit
// of its VC, inject 2.  VC1 always ejects here (hub reorder buffers are preallocated; a WACK is a pulse to the CW stop).
// RING CLIENT: PREQs that reach this slice (CW eject via the CW stop, CCW VC0 eject) are replayed as packet requests on
// the hub's ring-client port (<= 4 outstanding, in order) and answered with a PRSP to their source; a PREQ is taken
// only while its PRSP has a reserved slot, so VC0 ejection never waits on VC1 injection beyond that bound.
module ot_vms_ccwstop #(
    parameter integer D   = 4,      // per-VC input buffer depth (the upstream's credits per VC)
    parameter integer HF  = 2,      // hub PREQ FIFO (the hub's cci credits)
    parameter integer EJ  = 2,      // ring-client FIFO depth per source (CW stop's rce credits; VC0 eject space)
    parameter integer WAK = 2,      // WACK FIFO depth (the CW stop's wak credits)
    parameter integer MUT = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire [1:0]        sid,
    input  wire [291:0]      ccw_in,
    output reg  [1:0]        ccw_in_cr,
    output reg  [291:0]      ccw_out,
    input  wire [1:0]        ccw_out_cr,
    input  wire [287:0]      cci,          // hub PREQ {v, dst 2, client 4, seq 2, we, bank 3, rowm 11, wmask 8, data 256}
    output reg               cci_cr,
    output reg  [263:0]      cco,          // to the hub {v, client 4, seq 2, echo, data 256}
    input  wire [2:0]        wak,          // {v, dst 2} from the CW stop
    output reg               wak_cr,
    output reg               ack_out,      // a WACK for this slice arrived
    input  wire [287:0]      rce,          // CW-ejected PREQ {v, src 2, client 4, seq 2, we, bank 3, rowm 11, wmask 8, data 256}
    output reg               rce_cr,
    output reg  [337:0]      hq,           // ring client -> hub {v, req 337}
    input  wire [273:0]      hr            // hub -> ring client {v, rsp 273}
);
    localparam integer DB = (D > 1) ? $clog2(D) : 1, HB = (HF > 1) ? $clog2(HF) : 1, JB = (EJ > 1) ? $clog2(EJ) : 1;
    localparam integer WB = (WAK > 1) ? $clog2(WAK) : 1;
    reg [291:0] in_r; reg [287:0] cci_r, rce_r; reg [2:0] wak_r; reg [273:0] hr_r; reg [1:0] ocr_r; reg [1:0] me;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin in_r <= '0; cci_r <= '0; rce_r <= '0; wak_r <= '0; hr_r <= '0; ocr_r <= '0; me <= 2'd0; end
        else begin in_r <= ccw_in; cci_r <= cci; rce_r <= rce; wak_r <= wak; hr_r <= hr; ocr_r <= ccw_out_cr; me <= sid; end

    // ------------------------------------------------------------------ per-VC input buffers
    reg [290:0] ib [0:1][0:D-1]; reg [DB-1:0] ih [0:1], it [0:1]; reg [DB:0] inn [0:1];
    reg [290:0] h [0:1]; reg [1:0] hv, h_me;
    always @* for (integer v = 0; v < 2; v = v + 1) begin
        h[v] = ib[v][ih[v]]; hv[v] = inn[v] != 0; h_me[v] = h[v][288:287] == me;
    end
    // ring client FIFOs: 0 = CW eject, 1 = CCW VC0 eject; entry {src 2, client 4, seq 2, we, bank 3, rowm 11, wmask 8, data 256}
    reg [286:0] rf [0:1][0:EJ-1]; reg [JB-1:0] rh [0:1], rt [0:1]; reg [JB:0] rn [0:1];
    reg [286:0] hb [0:HF-1]; reg [HB-1:0] hh, ht; reg [HB:0] hn;     // hub PREQ FIFO (cci minus v)
    reg [1:0]   wb [0:WAK-1]; reg [WB-1:0] wh, wt; reg [WB:0] wn;    // WACK FIFO
    // ring client: outstanding headers (in order) and PRSP slots
    reg [8:0]   oh [0:3]; reg [1:0] ohh, oht; reg [2:0] ohn;           // {src 2, client 4, seq 2, we}
    reg [265:0] pb [0:3]; reg [1:0] pbh, pbt; reg [2:0] pbn;           // PRSP {dst 2, client 4, seq 2, echo, data 256} (+pad)
    reg [3:0] outc [0:1];
    reg rpick;
    // ---- decisions
    wire ej1 = hv[1] && h_me[1];                                       // VC1 always ejects
    wire ej0 = hv[0] && h_me[0] && rn[1] != (JB+1)'(EJ);
    wire fw1 = hv[1] && !h_me[1] && outc[1] != 4'd0;
    wire fw0 = hv[0] && !h_me[0] && outc[0] != 4'd0 && !fw1;
    wire busy_o = fw1 || fw0;
    wire inj_p = !busy_o && pbn != 3'd0 && outc[1] >= 4'd2;           // PRSP
    wire inj_w = !busy_o && !inj_p && wn != 0 && outc[1] >= 4'd2;     // WACK
    wire inj_h = !busy_o && !inj_p && !inj_w && hn != 0 && outc[0] >= 4'd2;
    // ring client issue: a slot is reserved for the response (outstanding + waiting PRSPs <= 4)
    wire can_iss = (ohn + pbn) < 3'd4;
    wire iss0 = can_iss && rn[0] != 0 && (!rpick || rn[1] == 0);
    wire iss1 = can_iss && rn[1] != 0 && !iss0;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            for (integer v = 0; v < 2; v = v + 1) begin ih[v] <= '0; it[v] <= '0; inn[v] <= '0; rh[v] <= '0; rt[v] <= '0; rn[v] <= '0; outc[v] <= 4'(D); end
            hh <= '0; ht <= '0; hn <= '0; wh <= '0; wt <= '0; wn <= '0; ohh <= '0; oht <= '0; ohn <= '0; pbh <= '0; pbt <= '0; pbn <= '0;
            rpick <= 1'b0; ccw_in_cr <= '0; ccw_out <= '0; cci_cr <= 1'b0; cco <= '0; wak_cr <= 1'b0; ack_out <= 1'b0; rce_cr <= 1'b0; hq <= '0;
        end else begin : seq
            reg [1:0] pop; reg [1:0] od;
            // ---- input buffers
            pop = {ej1 || fw1, ej0 || fw0};
            for (integer v = 0; v < 2; v = v + 1) begin
                if (in_r[291] && in_r[290] == v[0]) begin ib[v][it[v]] <= in_r[290:0]; it[v] <= (it[v] + 1'b1 == DB'(D)) ? '0 : it[v] + 1'b1; end
                inn[v] <= inn[v] + ((in_r[291] && in_r[290] == v[0]) ? 1 : 0) - (pop[v] ? 1 : 0);
                if (pop[v]) ih[v] <= (ih[v] + 1'b1 == DB'(D)) ? '0 : ih[v] + 1'b1;
            end
            ccw_in_cr <= pop;
            // ---- VC1 eject: PRSP -> hub, WACK -> CW stop
            cco[263] <= 1'b0; ack_out <= 1'b0;
            if (ej1) begin
                if (h[1][289]) ack_out <= 1'b1;
                else cco <= {1'b1, h[1][284:281], h[1][280:279], h[1][278], h[1][255:0]};
            end
            // ---- output link
            od = 2'd0; ccw_out[291] <= 1'b0;
            if (fw1) begin ccw_out <= {1'b1, h[1]}; od[1] = 1'b1; end
            else if (fw0) begin ccw_out <= {1'b1, h[0]}; od[0] = 1'b1; end
            else if (inj_p) begin : ip
                reg [265:0] e; e = pb[pbh];
                // {v, vc 1, ack 0, dst, src me, client, seq, echo, bank 0, rowm 0, wmask 0, data}
                ccw_out <= {1'b1, 1'b1, 1'b0, e[264:263], me, e[262:259], e[258:257], e[256], 3'd0, 11'd0, 8'd0, e[255:0]};
                pbh <= pbh + 2'd1; od[1] = 1'b1;
            end else if (inj_w) begin
                ccw_out <= {1'b1, 1'b1, 1'b1, wb[wh], me, 4'd0, 2'd0, 1'b0, 3'd0, 11'd0, 8'd0, 256'd0};
                wh <= (wh + 1'b1 == WB'(WAK)) ? '0 : wh + 1'b1; od[1] = 1'b1;
            end else if (inj_h) begin : ihb
                reg [286:0] e; e = hb[hh];
                // e = {dst 2, client 4, seq 2, we, bank 3, rowm 11, wmask 8, data 256}
                ccw_out <= {1'b1, 1'b0, 1'b0, e[286:285], me, e[284:281], e[280:279], e[278], e[277:275], e[274:264], e[263:256], e[255:0]};
                hh <= (hh + 1'b1 == HB'(HF)) ? '0 : hh + 1'b1; od[0] = 1'b1;
            end
            outc[1] <= outc[1] - (od[1] ? 4'd1 : 4'd0) + (ocr_r[1] ? 4'd1 : 4'd0);
            outc[0] <= outc[0] - (od[0] ? 4'd1 : 4'd0) + (ocr_r[0] ? 4'd1 : 4'd0);
            // ---- hub PREQ FIFO / WACK FIFO
            if (cci_r[287]) begin hb[ht] <= cci_r[286:0]; ht <= (ht + 1'b1 == HB'(HF)) ? '0 : ht + 1'b1; end
            hn <= hn + (cci_r[287] ? 1 : 0) - (inj_h ? 1 : 0); cci_cr <= inj_h;
            if (wak_r[2]) begin wb[wt] <= wak_r[1:0]; wt <= (wt + 1'b1 == WB'(WAK)) ? '0 : wt + 1'b1; end
            wn <= wn + (wak_r[2] ? 1 : 0) - (inj_w ? 1 : 0); wak_cr <= inj_w;
            // ---- ring client FIFOs: CW eject (rce) and VC0 eject
            if (rce_r[287]) begin rf[0][rt[0]] <= rce_r[286:0]; rt[0] <= (rt[0] + 1'b1 == JB'(EJ)) ? '0 : rt[0] + 1'b1; end
            if (ej0) begin
                // flit {vc, ack, dst, src, client, seq, we, bank, rowm, wmask, data} -> entry {src, client, seq, we, bank, rowm, wmask, data}
                rf[1][rt[1]] <= h[0][286:0];
                rt[1] <= (rt[1] + 1'b1 == JB'(EJ)) ? '0 : rt[1] + 1'b1;
            end
            rn[0] <= rn[0] + (rce_r[287] ? 1 : 0) - (iss0 ? 1 : 0);
            rn[1] <= rn[1] + (ej0 ? 1 : 0) - (iss1 ? 1 : 0);
            rce_cr <= iss0;
            if (iss0) rh[0] <= (rh[0] + 1'b1 == JB'(EJ)) ? '0 : rh[0] + 1'b1;
            if (iss1) rh[1] <= (rh[1] + 1'b1 == JB'(EJ)) ? '0 : rh[1] + 1'b1;
            if (iss0 || iss1) rpick <= iss0;
            // ---- issue to the hub (rebuild the packet request; the sector is local by construction)
            hq[337] <= 1'b0;
            if (iss0 || iss1) begin : is_
                reg [286:0] e; reg [14:0] s; reg [31:0] bm; reg [31:0] ad;
                e = iss0 ? rf[0][rh[0]] : rf[1][rh[1]];
                // e = {src 286:285, client 284:281, seq 280:279, we 278, bank 277:275, rowm 274:264, wmask 263:256, data 255:0}
                s = {e[274] ? 2'd0 : me, e[273:264], e[277:275]};
                ad = {11'd0, e[274], s, 5'd0};
                for (integer k = 0; k < 8; k = k + 1) bm[4*k +: 4] = {4{e[256 + k]}};
                hq <= {1'b1, e[278], ad, e[255:0], bm, 16'd0};
                oh[oht] <= {e[286:285], e[284:281], e[280:279], e[278]}; oht <= oht + 2'd1;
            end
            // ---- hub responses (in order) -> PRSP slots
            if (hr_r[273]) begin
                pb[pbt] <= {1'b0, oh[ohh][8:7], oh[ohh][6:3], oh[ohh][2:1], oh[ohh][0], hr_r[255:0]};
                pbt <= pbt + 2'd1; ohh <= ohh + 2'd1;
            end
            ohn <= ohn + ((iss0 || iss1) ? 3'd1 : 3'd0) - (hr_r[273] ? 3'd1 : 3'd0);
            pbn <= pbn + (hr_r[273] ? 3'd1 : 3'd0) - (inj_p ? 3'd1 : 3'd0);
        end
endmodule
`default_nettype wire
