`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_link_tx: transmit half of one direction of a die-to-die link (W15).
//
// One physical link direction (UCIe-A in a package, or a 112G PAM4 SerDes
// board link between packages) carrying NVC virtual channels of engine
// records and a credit-return field.  Everything a flit meets between the
// collective engine (in the die's hub) and the PHY is here and is real,
// clocked logic:
//
//   HUB (core clock)   A BUNDLE per core cycle in which anything is sent:
//                      {ts, dv[NVC], cm[CW], rec[NVC]} -- ts is the sender's
//                      global time (its synchronised cycle counter) at the
//                      cycle the engine fired; dv marks the VCs carrying a
//                      record; cm is the credit pulses returned to the far
//                      engine this cycle.  Hub-side flow control: a credit
//                      counter of the edge FIFO space, refilled over the
//                      return wire (HUBFC = 1).  VCs in GATED obey vc_ready;
//                      the others (relays, credits) cannot be refused -- the
//                      edge FIFO drains faster than they arrive (overflow is
//                      latched).  HUBFC = 0 drops the loop where the link side
//                      drains NL bundles a link cycle, more than the one a core
//                      cycle the hub can offer, so a small FIFO never fills.
//   WIRE               WIRE register stages hub -> die edge (the floorplan's
//                      registered crossing, core clock), and WIRE stages of
//                      the credit return edge -> hub.
//   EDGE CDC           NL asynchronous FIFOs (ot_link_afifo) written in
//                      rotation, core clock -> link clock.  NL lanes let the
//                      link side take NL bundles a link cycle with Gray
//                      pointers that still step by one.
//   FRAMER (link clk)  Each link cycle takes up to NL bundles in order into
//                      the next NL slots of a FRAME of FRAME_CYCLES x NL
//                      slots; the frame leaves with a CRC-32 over its slots
//                      when the last cycle of the frame is filled.  An empty
//                      slot is an idle (valid = 0).  A frame leaves every
//                      FRAME_CYCLES link cycles whether or not it carries data
//                      (a serial PHY sends continuously).
//                        UCIe-A: a frame is one FDI cycle (FRAME_CYCLES 1).
//                        Board:  a frame is one RS(272,257) codeword payload
//                                (FRAME_CYCLES 2 at twice the codeword rate).
//   ENC                ENC_STAGES link-clock register stages: the PCS / FEC
//                      encoder pipeline of the PHY (a stand-in for hard IP;
//                      the depth is the cited or ASSUMED encoder latency).
//
// Slot format: {valid, ts[TSW], dv[NVC], cm[CW], rec[NVC][PW]}.
// Frame format: {crc32, slot[FRAME_CYCLES*NL-1], ..., slot[0]}.
// ---------------------------------------------------------------------------
module ot_link_tx #(
    parameter integer NVC          = 1,
    parameter integer PW           = 547,
    parameter integer CW           = 2,
    parameter integer TSW          = 16,
    parameter integer WIRE         = 0,
    parameter integer AW           = 4,
    parameter integer NL           = 2,
    parameter integer FRAME_CYCLES = 1,
    parameter integer ENC_STAGES   = 0,
    parameter integer SYNC         = 2,
    parameter [NVC-1:0] GATED      = {NVC{1'b1}},
    parameter integer RESERVE      = 2,
    parameter integer HUBFC        = 1,        // 0: no hub credit loop (the edge FIFO drains faster than
                                               //    one bundle a core cycle; overflow is still latched)
    parameter integer PACE_NUM     = 0,        // >0: DETERMINISTIC PACING -- bundles only on slots of a token bucket
    parameter integer PACE_DEN     = 1,        //     (PACE_NUM / PACE_DEN bundles a core cycle, set below the link's
                                               //     drain rate), so no backpressure ever reaches the engine
                                               //     through the phase-dependent CDC credit return; credit pulses
                                               //     are accumulated and sent as counts (CNTW bits per credit)
    parameter integer CNTW         = (PACE_NUM > 0) ? 3 : 1,
    parameter integer CFW          = CW * CNTW,
    parameter integer BW           = TSW + NVC + CFW + NVC * PW,  // bundle
    parameter integer SW           = BW + 1,                       // slot
    parameter integer NS           = FRAME_CYCLES * NL,            // slots per frame
    parameter integer FRW          = NS * SW + 32                  // frame
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [TSW-1:0]       now,
    input  wire [NVC-1:0]       vc_valid,
    output wire [NVC-1:0]       vc_ready,
    input  wire [NVC*PW-1:0]    vc_rec,
    input  wire [CW-1:0]        cr_pulse,
    input  wire                 lclk,
    input  wire                 lrst_n,
    output wire                 f_valid,
    output wire [FRW-1:0]       f_data,
    output reg                  fault,          // latched: a bundle met a full edge FIFO
    output reg  [31:0]          stat_bundles,
    output reg  [31:0]          stat_gated_stall
);
    localparam integer CAP = NL << AW;
    localparam integer CRW = $clog2(CAP + 1);
    localparam integer LB  = (NL > 1) ? $clog2(NL) : 1;

    // ---- hub ------------------------------------------------------------------------------------------
    wire [NL-1:0]  lovf;
    reg  [CRW-1:0] hub_cr;
    wire [CRW-1:0] ret;                                   // entries freed at the edge, after the return wire
    // pacing bucket (PACE_NUM > 0): capacity DEN + NUM - 1, so an idle link banks at most one extra bundle
    localparam integer PB = $clog2(PACE_DEN + PACE_NUM + 1) + 1;
    reg  [PB-1:0]  pace;
    wire           slot = (PACE_NUM == 0) || (pace >= PACE_DEN);
    assign vc_ready = ((HUBFC == 0 || hub_cr > RESERVE) && slot) ? {NVC{1'b1}} : ~GATED;
    wire [NVC-1:0] dv = vc_valid;
    // credit field: the pulses themselves (CNTW 1, unpaced), or counts accumulated to the next slot
    reg  [CNTW-1:0] ccnt [0:CW-1];
    reg  [CFW-1:0]  cfield;
    reg             cpend, covf;
    integer c;
    always @(*) begin
        cpend = 1'b0; covf = 1'b0;
        for (c = 0; c < CW; c = c + 1) begin
            if (PACE_NUM == 0) cfield[c*CNTW +: CNTW] = cr_pulse[c];
            else begin
                cfield[c*CNTW +: CNTW] = ccnt[c] + cr_pulse[c];
                if (ccnt[c] == {CNTW{1'b1}} && cr_pulse[c]) covf = 1'b1;
            end
            if (cfield[c*CNTW +: CNTW] != 0) cpend = 1'b1;
        end
    end
    // paced: a credit-only bundle would take a data slot, so pending credits ride the next data bundle and go
    // alone only when they have waited CAGE cycles or a count is near its limit (deterministic: a function of
    // the local cycle stream only)
    localparam integer CAGE = 8;
    reg  [3:0]     cwait;
    reg            cfull;
    always @(*) begin
        cfull = 1'b0;
        for (c = 0; c < CW; c = c + 1) if (cfield[c*CNTW +: CNTW] >= {1'b1, {(CNTW-1){1'b0}}}) cfull = 1'b1;
    end
    wire           cgo = (PACE_NUM == 0) ? cpend : (cpend && (cwait >= CAGE - 1 || cfull));
    wire           bv = slot && ((|dv) || cgo);
    wire [BW-1:0]  bundle = {now, dv, cfield, vc_rec};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            hub_cr <= CAP; fault <= 1'b0; stat_bundles <= 0; stat_gated_stall <= 0; pace <= PACE_DEN; cwait <= 0;
            for (c = 0; c < CW; c = c + 1) ccnt[c] <= 0;
        end else begin
            cwait <= (bv || !cpend) ? 4'd0 : (cwait == 4'hF ? cwait : cwait + 1'b1);
            if (PACE_NUM != 0) begin
                // capacity DEN + NUM - 1: a smaller cap drops the fractional refill (capped at DEN, 7/8 pacing
                // gave one slot every 2 cycles) -- the same bucket rule as ot_rom_ucie_link
                pace <= ((bv ? pace - PACE_DEN : pace) + PACE_NUM > PACE_DEN + PACE_NUM - 1) ? PACE_DEN + PACE_NUM - 1
                        : (bv ? pace - PACE_DEN : pace) + PACE_NUM;
                for (c = 0; c < CW; c = c + 1) ccnt[c] <= bv ? 0 : cfield[c*CNTW +: CNTW];
                if (covf || ((|(dv & ~GATED)) && !slot)) fault <= 1'b1;   // count overflow / ungated off-slot
            end
            hub_cr <= hub_cr - (bv ? 1'b1 : 1'b0) + ret;
            if ((HUBFC != 0 && bv && hub_cr == 0) || (|lovf)) fault <= 1'b1;
            if (bv) stat_bundles <= stat_bundles + 1;
            if (HUBFC != 0 && hub_cr <= RESERVE) stat_gated_stall <= stat_gated_stall + 1;
        end
    end

    // ---- hub -> edge wire, and the credit return wire ----------------------------------------------------
    wire          ev;
    wire [BW-1:0] eb;
    wire [CRW-1:0] freed;
    generate if (WIRE == 0) begin : g_nowire
        assign ev = bv; assign eb = bundle; assign ret = freed;
    end else begin : g_wire
        reg [WIRE-1:0]  wv;
        reg [BW-1:0]    wd [0:WIRE-1];
        reg [CRW-1:0]   wr_ [0:WIRE-1];
        integer i;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                wv <= 0;
                for (i = 0; i < WIRE; i = i + 1) wr_[i] <= 0;
            end else begin
                wv[0] <= bv;
                for (i = 1; i < WIRE; i = i + 1) wv[i] <= wv[i-1];
                wr_[0] <= freed;
                for (i = 1; i < WIRE; i = i + 1) wr_[i] <= wr_[i-1];
            end
        end
        always @(posedge clk) begin
            wd[0] <= bundle;
            for (i = 1; i < WIRE; i = i + 1) wd[i] <= wd[i-1];
        end
        assign ev = wv[WIRE-1]; assign eb = wd[WIRE-1]; assign ret = wr_[WIRE-1];
    end endgenerate

    // ---- edge CDC: NL async FIFOs written in rotation --------------------------------------------------
    reg  [LB-1:0]  wl;                                     // next write lane
    wire [NL-1:0]  lfull, lempty;
    wire [NL*BW-1:0] lhead;
    wire [NL*(AW+1)-1:0] lfreed;
    reg  [NL-1:0]  lrd;
    genvar g;
    generate for (g = 0; g < NL; g = g + 1) begin : g_lane
        ot_link_afifo #(.W(BW), .AW(AW), .SYNC(SYNC)) u_f (
            .wclk(clk), .wrst_n(rst_n), .wr(ev && wl == g), .wdata(eb), .wfull(lfull[g]),
            .wfreed(lfreed[g*(AW+1) +: AW+1]), .ovf(lovf[g]),
            .rclk(lclk), .rrst_n(lrst_n), .rd(lrd[g]), .rempty(lempty[g]), .rdata(lhead[g*BW +: BW]), .rcount());
    end endgenerate
    reg [CRW-1:0] fsum;
    integer j;
    always @(*) begin
        fsum = 0;
        for (j = 0; j < NL; j = j + 1) fsum = fsum + lfreed[j*(AW+1) +: AW+1];
    end
    assign freed = fsum;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) wl <= 0;
        else if (ev) wl <= (wl == NL - 1) ? 0 : wl + 1'b1;
    end

    // ---- framer (link clock) -------------------------------------------------------------------------------
    reg  [LB-1:0]  rl;                                     // next lane in order
    reg  [NL*SW-1:0] cyc_slots;
    reg  [LB:0]    npop;
    integer k, ln;
    reg ok;
    always @(*) begin
        cyc_slots = 0; lrd = 0; npop = 0; ok = 1'b1;
        for (k = 0; k < NL; k = k + 1) begin
            ln = (rl + k) % NL;
            if (ok && !lempty[ln]) begin
                cyc_slots[k*SW +: SW] = {1'b1, lhead[ln*BW +: BW]};
                lrd[ln] = 1'b1;
                npop = npop + 1'b1;
            end else ok = 1'b0;
        end
    end
    localparam integer FCB = (FRAME_CYCLES > 1) ? $clog2(FRAME_CYCLES) : 1;
    reg [FCB-1:0]  fk;
    reg [NS*SW-1:0] acc;
    wire [NS*SW-1:0] full_slots;
    generate if (FRAME_CYCLES == 1) begin : g_f1
        assign full_slots = cyc_slots;
    end else begin : g_fn
        assign full_slots = acc | ({{(NS-NL)*SW{1'b0}}, cyc_slots} << (fk * NL * SW));
    end endgenerate
    reg          fv0;
    reg [FRW-1:0] fd0;
    always @(posedge lclk or negedge lrst_n) begin
        if (!lrst_n) begin
            rl <= 0; fk <= 0; acc <= 0; fv0 <= 1'b0;
        end else begin
            rl <= (rl + npop) % NL;
            if (fk == FRAME_CYCLES - 1) begin
                fk <= 0; acc <= 0; fv0 <= 1'b1;
            end else begin
                fk <= fk + 1'b1; acc <= full_slots; fv0 <= 1'b0;
            end
        end
    end
    wire [31:0] fcrc;
    ot_link_crc32 #(.W(NS * SW)) u_crc (.d(full_slots), .crc(fcrc));
    always @(posedge lclk) if (fk == FRAME_CYCLES - 1) fd0 <= {fcrc, full_slots};

    // ---- PCS / FEC encoder pipeline --------------------------------------------------------------------
    generate if (ENC_STAGES == 0) begin : g_noenc
        assign f_valid = fv0; assign f_data = fd0;
    end else begin : g_enc
        reg [ENC_STAGES-1:0] pv;
        reg [FRW-1:0] pd [0:ENC_STAGES-1];
        integer i;
        always @(posedge lclk or negedge lrst_n)
            if (!lrst_n) pv <= 0;
            else begin
                pv[0] <= fv0;
                for (i = 1; i < ENC_STAGES; i = i + 1) pv[i] <= pv[i-1];
            end
        always @(posedge lclk) begin
            pd[0] <= fd0;
            for (i = 1; i < ENC_STAGES; i = i + 1) pd[i] <= pd[i-1];
        end
        assign f_valid = pv[ENC_STAGES-1]; assign f_data = pd[ENC_STAGES-1];
    end endgenerate

endmodule
