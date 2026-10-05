`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_w15_link_rx: receive half of one direction of a die-to-die link (W15).
//
//   DEC (recovered clk)  DEC_STAGES register stages: the PHY's PCS alignment /
//                        deskew and FEC decoder pipeline (hard IP stand-in; a
//                        fixed-latency decoder, as FEC decoders built for
//                        deterministic latency are).
//   CRC                  CRC-32 over the frame's slots, one register stage.  A
//                        mismatch latches fault_crc (an uncorrectable error;
//                        the link layer would replay -- see the W15 record's
//                        determinism note) and the frame is dropped.
//   DEFRAME              The frame's valid slots are written, in order, into
//                        NL async FIFOs in rotation (NL per recovered-clock
//                        cycle; a frame of FRAME_CYCLES x NL slots is drained
//                        over FRAME_CYCLES cycles, before the next arrives).
//   CDC + RELEASE (core) The core side reads the lanes in order, one bundle a
//                        cycle.  det = 1: a bundle stamped ts leaves the edge
//                        at global time ts + drel - WIRE exactly, so it
//                        reaches the hub at ts + drel whatever the PHY phase,
//                        channel delay, clock phases and synchroniser outcome
//                        were -- provided it arrived in time.  A bundle first
//                        visible later than its release time latches
//                        fault_late (a deadline miss, never silent).  drel is
//                        a register set at link training (DREL_* in
//                        tools/w15_collectives.py derive it from the link's
//                        worst-case arrival), not a synthesis constant.
//                        det = 0: a bundle leaves as soon as it is visible
//                        (the free-running link, for comparison).
//   WIRE                 WIRE register stages edge -> hub (core clock).
//
// Statistics (core clock): the minimum and maximum age (now - ts) at which a
// bundle first became visible at the edge -- the link's measured arrival
// latency distribution -- and the maximum number of bundles waiting.
// ---------------------------------------------------------------------------
module ot_w15_link_rx #(
    parameter integer NVC          = 1,
    parameter integer PW           = 547,
    parameter integer CW           = 2,
    parameter integer TSW          = 16,
    parameter integer WIRE         = 1,        // >= 1
    parameter integer AW           = 5,
    parameter integer NL           = 2,
    parameter integer FRAME_CYCLES = 1,
    parameter integer DEC_STAGES   = 0,
    parameter integer SYNC         = 2,
    parameter integer CRC_PIPE     = 1,        // 1: CRC check over two recovered-clock stages (partials registered)
    parameter integer HEAD_PIPE    = 1,        // 1: FIFO head -> prefetch register -> release register, due by an
                                               //    equality against a precomputed time; age statistics and the
                                               //    late check pipelined (the one-cycle age compare was the SS
                                               //    critical path of the hardened port, e9ec0311: 1.52 ns)
    parameter integer CNTW         = 1,        // credit counts per bundle (ot_link_tx PACE_NUM > 0: 3)
    parameter integer CFW          = CW * CNTW,
    parameter integer BW           = TSW + NVC + CFW + NVC * PW,
    parameter integer SW           = BW + 1,
    parameter integer NS           = FRAME_CYCLES * NL,
    parameter integer FRW          = NS * SW + 32
) (
    input  wire                 rclk,
    input  wire                 rrst_n,
    input  wire                 f_valid,
    input  wire [FRW-1:0]       f_data,
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [TSW-1:0]       now,
    input  wire                 det,            // 1: deterministic release at ts + drel
    input  wire [TSW-1:0]       drel,           // hub-to-hub cycles from the sender's ts (a link-training CSR)
    output wire [NVC-1:0]       vc_valid,
    output wire [NVC*PW-1:0]    vc_rec,
    output wire [CW-1:0]        cr_pulse,
    output reg                  fault_crc,
    output reg                  fault_late,
    output reg                  fault_ovf,
    output reg  [TSW-1:0]       stat_min_age,
    output reg  [TSW-1:0]       stat_max_age,
    output reg  [15:0]          stat_max_wait,
    output reg  [31:0]          stat_bundles
);
    localparam integer LB = (NL > 1) ? $clog2(NL) : 1;

    // ---- decoder pipeline -----------------------------------------------------------------------------
    wire          dv;
    wire [FRW-1:0] dd;
    generate if (DEC_STAGES == 0) begin : g_nodec
        assign dv = f_valid; assign dd = f_data;
    end else begin : g_dec
        reg [DEC_STAGES-1:0] pv;
        reg [FRW-1:0] pd [0:DEC_STAGES-1];
        integer i;
        always @(posedge rclk or negedge rrst_n)
            if (!rrst_n) pv <= 0;
            else begin
                pv[0] <= f_valid;
                for (i = 1; i < DEC_STAGES; i = i + 1) pv[i] <= pv[i-1];
            end
        always @(posedge rclk) begin
            pd[0] <= f_data;
            for (i = 1; i < DEC_STAGES; i = i + 1) pd[i] <= pd[i-1];
        end
        assign dv = pv[DEC_STAGES-1]; assign dd = pd[DEC_STAGES-1];
    end endgenerate


    // ---- CRC stage ------------------------------------------------------------------------------------
    reg          cv;
    reg [NS*SW-1:0] cs;
    wire [31:0]  dcrc;
    wire         kv;                                      // the frame whose CRC dcrc is
    wire [FRW-1:0] kd;
    generate if (CRC_PIPE == 0) begin : g_crc1
        ot_link_crc32 #(.W(NS * SW)) u_crc (.d(dd[NS*SW-1:0]), .crc(dcrc));
        assign kv = dv; assign kd = dd;
    end else begin : g_crc2
        reg          kv_r;
        reg [FRW-1:0] kd_r;
        ot_link_crc32_pipe #(.W(NS * SW)) u_crc (.clk(rclk), .en(dv), .d(dd[NS*SW-1:0]), .crc(dcrc));
        always @(posedge rclk or negedge rrst_n) if (!rrst_n) kv_r <= 1'b0; else kv_r <= dv;
        always @(posedge rclk) if (dv) kd_r <= dd;
        assign kv = kv_r; assign kd = kd_r;
    end endgenerate
    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            cv <= 1'b0; fault_crc <= 1'b0;
        end else begin
            cv <= kv && (dcrc == kd[FRW-1 -: 32]);
            if (kv && dcrc != kd[FRW-1 -: 32]) fault_crc <= 1'b1;
        end
    end
    always @(posedge rclk) if (kv) cs <= kd[NS*SW-1:0];

    // ---- deframe: NL slots a cycle into the lanes, in order -------------------------------------------
    localparam integer FCB = (FRAME_CYCLES > 1) ? $clog2(FRAME_CYCLES) : 1;
    reg  [NS*SW-1:0] hold;
    reg  [FCB-1:0]   hk;                                  // group of the held frame emitted next
    reg              hbusy;
    wire [NS*SW-1:0] src = cv ? cs : hold;
    wire [FCB-1:0]   grp = cv ? {FCB{1'b0}} : hk;
    wire             emit = cv || hbusy;
    reg  [NL*SW-1:0] gs;
    always @(*) gs = src >> (grp * NL * SW);
    reg  [LB-1:0]    wl;
    reg  [NL-1:0]    lwr;
    reg  [NL*BW-1:0] lwd;
    reg  [LB:0]      nw;
    integer k, ln;
    always @(*) begin
        lwr = 0; lwd = 0; nw = 0;
        if (emit)
            for (k = 0; k < NL; k = k + 1)
                if (gs[k*SW + SW - 1]) begin
                    ln = (wl + nw) % NL;
                    lwr[ln] = 1'b1;
                    lwd[ln*BW +: BW] = gs[k*SW +: BW];
                    nw = nw + 1'b1;
                end
    end
    always @(posedge rclk or negedge rrst_n) begin
        if (!rrst_n) begin
            hbusy <= 1'b0; hk <= 0; wl <= 0;
        end else begin
            wl <= (wl + nw) % NL;
            if (cv) begin
                hbusy <= (FRAME_CYCLES > 1); hk <= 1;
            end else if (hbusy) begin
                if (hk == FRAME_CYCLES - 1) hbusy <= 1'b0;
                hk <= hk + 1'b1;
            end
        end
    end
    always @(posedge rclk) if (cv) hold <= cs;

    wire [NL-1:0]    lempty, lovf;
    wire [NL*BW-1:0] lhead;
    reg  [NL-1:0]    lrd;
    wire [NL*(AW+1)-1:0] lcnt;
    genvar g;
    generate for (g = 0; g < NL; g = g + 1) begin : g_lane
        ot_link_afifo #(.W(BW), .AW(AW), .SYNC(SYNC)) u_f (
            .wclk(rclk), .wrst_n(rrst_n), .wr(lwr[g]), .wdata(lwd[g*BW +: BW]), .wfull(), .wfreed(), .ovf(lovf[g]),
            .rclk(clk), .rrst_n(rst_n), .rd(lrd[g]), .rempty(lempty[g]), .rdata(lhead[g*BW +: BW]),
            .rcount(lcnt[g*(AW+1) +: AW+1]));
    end endgenerate
    always @(posedge rclk or negedge rrst_n)
        if (!rrst_n) fault_ovf <= 1'b0;
        else if (|lovf) fault_ovf <= 1'b1;

    // ---- core side ------------------------------------------------------------------------------------------
    reg  [LB-1:0]  rn;
    wire           hv = !lempty[rn];
    wire [BW-1:0]  hb = lhead[rn*BW +: BW];
    wire [TSW-1:0] hts = hb[BW-1 -: TSW];
    wire [TSW-1:0] RELAGE = drel - WIRE;
    reg            hr_v, hr_due;
    reg  [BW-1:0]  hr;
    wire [TSW-1:0] hr_ts = hr[BW-1 -: TSW];
    wire           go = hr_v && (!det || hr_due);
    reg  [15:0]    waiting;
    integer q;
    always @(*) begin
        waiting = 0;
        for (q = 0; q < NL; q = q + 1) waiting = waiting + lcnt[q*(AW+1) +: AW+1];
    end
    generate if (HEAD_PIPE == 0) begin : g_head1
    // In-order read into a head register; whether that register is due NEXT cycle is computed and registered
    // with it, so the release decision is a flop (the hardened 0.92 ns port's critical path was lane mux -> age
    // -> compare -> pop pointer).  A bundle visible at the FIFO at age a is in the register at a + 1, so
    // deterministic release needs every arrival at a <= RELAGE - 1: the late check is one cycle stricter than
    // the release point (the calibrated drel carries one guard cycle).
    wire [TSW-1:0] age = now - hts;
    wire           ld = hv && (!hr_v || go);
    reg            seen;                                  // the current FIFO head was already visible
    always @(*) begin
        lrd = 0;
        if (ld) lrd[rn] = 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rn <= 0; seen <= 1'b0; fault_late <= 1'b0; hr_v <= 1'b0; hr_due <= 1'b0;
            stat_min_age <= {TSW{1'b1}}; stat_max_age <= 0; stat_max_wait <= 0; stat_bundles <= 0;
        end else begin
            if (ld) rn <= (rn == NL - 1) ? 0 : rn + 1'b1;
            hr_v <= ld || (hr_v && !go);
            hr_due <= ld ? (TSW'(age + 1'b1) >= RELAGE) : (TSW'(now + 1'b1 - hr_ts) >= RELAGE);
            seen <= hv && !ld;
            if (hv && !seen) begin
                if (age < stat_min_age) stat_min_age <= age;
                if (age > stat_max_age) stat_max_age <= age;
                if (det && age >= RELAGE) fault_late <= 1'b1;
            end
            if (waiting > stat_max_wait) stat_max_wait <= waiting;
            if (go) stat_bundles <= stat_bundles + 1;
        end
    end
    always @(posedge clk) if (ld) hr <= hb;
    end else begin : g_head3
    // FIFO head -> prefetch register (pb) -> release register (hr).  hr is due next cycle when its stamp equals
    // m1 = now + 1 - RELAGE (a register, advanced with the free-running global counter now): a 16-bit equality
    // from a register instead of lane mux -> subtract -> magnitude compare.  A bundle visible at the FIFO at age a
    // is in pb at a + 1 and in hr at a + 2 at the earliest, so deterministic release needs every arrival at
    // a <= RELAGE - 2 (the late check; the calibrated drel carries the extra guard cycle).  A late bundle is
    // released at once after fault_late latches (fail closed, never stuck).  The first-visibility age and its
    // statistics are pipelined: stamp and time registered, subtracted, then compared (2 cycles later, same values).
    reg            pv;
    reg  [BW-1:0]  pb;
    wire [TSW-1:0] pts = pb[BW-1 -: TSW];
    wire           ld = pv && (!hr_v || go);             // pb -> hr
    wire           pf = hv && (!pv || ld);               // FIFO head -> pb
    reg  [TSW-1:0] m1;
    reg            seen, v1, v2;
    reg  [TSW-1:0] ts1, now1, age2;
    always @(*) begin
        lrd = 0;
        if (pf) lrd[rn] = 1'b1;
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rn <= 0; seen <= 1'b0; fault_late <= 1'b0; hr_v <= 1'b0; hr_due <= 1'b0; pv <= 1'b0; m1 <= 0;
            v1 <= 1'b0; v2 <= 1'b0;
            stat_min_age <= {TSW{1'b1}}; stat_max_age <= 0; stat_max_wait <= 0; stat_bundles <= 0;
        end else begin
            m1 <= TSW'(now + 2'd2 - RELAGE);
            if (pf) rn <= (rn == NL - 1) ? 0 : rn + 1'b1;
            pv <= pf || (pv && !ld);
            hr_v <= ld || (hr_v && !go);
            hr_due <= (ld ? (pts == m1) : (hr_ts == m1)) || fault_late;
            seen <= hv && !pf;
            v1 <= hv && !seen;
            v2 <= v1;
            if (v2) begin
                if (age2 < stat_min_age) stat_min_age <= age2;
                if (age2 > stat_max_age) stat_max_age <= age2;
                if (det && age2 >= TSW'(RELAGE - 1'b1)) fault_late <= 1'b1;
            end
            if (waiting > stat_max_wait) stat_max_wait <= waiting;
            if (go) stat_bundles <= stat_bundles + 1;
        end
    end
    always @(posedge clk) begin
        if (pf) pb <= hb;
        if (ld) hr <= pb;
        ts1 <= hts; now1 <= now;
        age2 <= now1 - ts1;
    end
    end endgenerate

    // ---- edge -> hub wire --------------------------------------------------------------------------------
    reg  [WIRE-1:0] wv;
    reg  [BW-1:0]   wd [0:WIRE-1];
    integer i;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) wv <= 0;
        else begin
            wv[0] <= go;
            for (i = 1; i < WIRE; i = i + 1) wv[i] <= wv[i-1];
        end
    always @(posedge clk) begin
        wd[0] <= hr;
        for (i = 1; i < WIRE; i = i + 1) wd[i] <= wd[i-1];
    end
    wire [BW-1:0] ob = wd[WIRE-1];
    wire [NVC-1:0] odv = ob[BW-TSW-1 -: NVC];
    wire [CFW-1:0] ocm = ob[NVC*PW +: CFW];
    assign vc_valid = wv[WIRE-1] ? odv : {NVC{1'b0}};
    generate if (CNTW == 1) begin : g_pulse
        assign cr_pulse = wv[WIRE-1] ? ocm : {CW{1'b0}};
    end else begin : g_count
        // counts -> one pulse per cycle per credit (the engine takes one a cycle); deterministic, as the bundles are
        reg [CNTW+3:0] pend [0:CW-1];
        genvar cc;
        for (cc = 0; cc < CW; cc = cc + 1) begin : g_c
            wire [CNTW+3:0] tot = pend[cc] + (wv[WIRE-1] ? ocm[cc*CNTW +: CNTW] : 0);
            assign cr_pulse[cc] = tot != 0;
            always @(posedge clk or negedge rst_n)
                if (!rst_n) pend[cc] <= 0;
                else pend[cc] <= tot - (tot != 0 ? 1'b1 : 1'b0);
        end
    end endgenerate
    assign vc_rec   = ob[NVC*PW-1:0];
endmodule
