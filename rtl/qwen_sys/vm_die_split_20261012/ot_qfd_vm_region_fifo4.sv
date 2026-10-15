`timescale 1ns/1ps
// Candidate region wiring vehicle: four M5 FIFO leaves and original hard bank/SU children.
// Remaining distributed reset/pop/tag/row/SU glue needs its own M5 leaf boundaries.
// The original FIFO slice loops are replaced with four equivalent FIFO leaves.
// All other functional code remains pinned; this is not a hardened parent view. Existing ot_qfd_vm_bank_t/ot_qfd_vm_su_t hard children remain
// byte-identical and place directly in the die at vm_distributed_plan positions.
// Import its child definitions from the pinned q-sp source before elaboration.
// This preserves the existing FIFO/old-word/tags operation while the die's
// physical generator assigns independent local glue roots and registered seams.
// Do not claim its current NRI/NRX/NRS settings implement the new die corridors.
// Source: 87256eef919f75f48fa9d713940d0eefab803dbd
// rtl/qwen_sys/vm_me_20261008/ot_qfd_sp_vector_memory_bv.sv
module ot_qfd_vm_region_fifo4 #(
    parameter integer NBK = 8,
    parameter integer NSB = 2,
    parameter integer NSU = 3,
    parameter integer DEPTH = 1024,
    parameter integer LAW = 10,
    parameter integer DEPTHS = 1024,
    parameter integer LAWS = 10,
    parameter integer USE_MACRO = 0,
    parameter integer NPP = 12,          // production RV 1: RV + 6 + TLX (TLX = 1 + NRI + NRX = 5)
    parameter integer MEREG = 1,         // 1: me_in is me_en one edge early (registered here: the tile's replica)
    parameter integer NRI = 2,           // clock relays pin flop -> macro inputs (every read / write port, uniform)
    parameter integer NRX = 2,           // clock relays copy-0 capture -> E region (x FIFO + row-read rungs)
    parameter integer NRS = 1,           // clock relays SU capture -> E region (so)
    parameter integer FSW = 32           // x FIFO slice width: each FSW-bit slice owns kept one-hot wp/rp + push/pop replicas
                                         // (128 -> 32 after e39fac4f9: pp_k -> 128 xo enables across the pin face was -1,068.9 ps)
) (
    input  wire                      clk,
    input  wire                      rst_n,
    input  wire                      me_in,
    input  wire [NBK-1:0]            re,
    input  wire [NBK*LAW-1:0]        ra,
    input  wire [NBK-1:0]            we,
    input  wire [NBK*LAW-1:0]        wl,
    input  wire [NBK*16-1:0]         wm,
    input  wire [NBK*512-1:0]        wd,
    input  wire                      xv,
    input  wire                      rq,
    input  wire [2:0]                rqb,
    input  wire [NSU*NSB-1:0]        sre,
    input  wire [NSU*NSB*LAWS-1:0]   sra,
    input  wire [NSU-1:0]            sv,
    input  wire [NSB-1:0]            swe,
    input  wire [NSB*LAWS-1:0]       swl,
    input  wire [NSB*16-1:0]         swm,
    input  wire [NSB*512-1:0]        swd,
    input  wire                      pop,
    output reg  [NBK*512-1:0]        xo,
    output reg  [511:0]              ro,
    output reg  [NSU*NSB*512-1:0]    so,
    output reg                       ovf
);
    localparam integer LP = (NPP > 1) ? $clog2(NPP) : 1;
    genvar g, c, j;
    // ---- reset relay, me_en replica ----
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    // r6: per-bank reset relays (one flop drove 3,690 async flops: recovery -254 ps) and per-bank pop pin flops
    //     (pop -> 128 slice replicas across the face was -745 ps): pop gains one engine edge (parent TPP).
    wire [NBK-1:0] rtg, pgw;
    generate for (g = 0; g < NBK; g = g + 1) begin : g_rg
        (* keep = "true", dont_touch = "true" *) reg r;
        (* keep = "true", dont_touch = "true" *) reg mg;
        (* keep = "true", dont_touch = "true" *) reg pg;
        always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= rt;
        always @(posedge clk) mg <= me_in;
        always @(posedge clk or negedge rt) if (!rt) pg <= 1'b0; else if ((MEREG != 0) ? mg : me_in) pg <= pop;
        assign rtg[g] = r;
        assign pgw[g] = pg;
    end endgenerate
    wire me_t;
    generate if (MEREG != 0) begin : g_mer
        reg mr;
        always @(posedge clk) mr <= me_in;
        assign me_t = mr;
    end else begin : g_mew
        assign me_t = me_in;
    end endgenerate
    // ---- pin flops ----
    reg [NBK-1:0] p_re, p_we;
    reg           p_xv, p_rq, p_pop;
    reg [NSU*NSB-1:0] p_sre;
    reg [NSU-1:0] p_sv;
    reg [NSB-1:0] p_swe;
    always @(posedge clk or negedge rt)
        if (!rt) begin p_re <= 0; p_we <= 0; p_xv <= 1'b0; p_rq <= 1'b0; p_sre <= 0; p_sv <= 0; p_swe <= 0; end
        else begin p_re <= re; p_we <= we; p_xv <= xv; p_rq <= rq; p_sre <= sre; p_sv <= sv; p_swe <= swe; end
    reg p_pop2;                           // central copy of the per-bank pop stage (occupancy / ovf)
    always @(posedge clk or negedge rt) if (!rt) begin p_pop <= 1'b0; p_pop2 <= 1'b0; end
        else if (me_t) begin p_pop <= pop; p_pop2 <= p_pop; end
    reg [NBK*LAW-1:0] p_ra, p_wl;
    reg [NBK*16-1:0]  p_wm;
    reg [NBK*512-1:0] p_wd;
    reg [2:0]         p_rqb;
    reg [NSU*NSB*LAWS-1:0] p_sra;
    reg [NSB*LAWS-1:0] p_swl;
    reg [NSB*16-1:0]   p_swm;
    reg [NSB*512-1:0]  p_swd;
    always @(posedge clk) begin
        p_ra <= ra; p_wl <= wl; p_wm <= wm; p_wd <= wd; p_rqb <= rqb;
        p_sra <= sra; p_swl <= swl; p_swm <= swm; p_swd <= swd;
    end
    // ---- macro-side input relays: every macro input crosses the tile from the E-face pin flops in NRI clock stages
    //      (the far copy-0 column sits ~750 um from the pins; <= ~500 um of wire per stage).  Uniform delay on every
    //      read / write port keeps the base ordering argument (a read sees exactly the writes presented before it). ----
    wire [NBK-1:0]          m_re, m_we;
    wire [NSU*NSB-1:0]      m_sre;
    wire [NSB-1:0]          m_swe;
    wire [NBK*LAW-1:0]      m_ra, m_wl;
    wire [NBK*16-1:0]       m_wm;
    wire [NBK*512-1:0]      m_wd;
    wire [NSU*NSB*LAWS-1:0] m_sra;
    wire [NSB*LAWS-1:0]     m_swl;
    wire [NSB*16-1:0]       m_swm;
    wire [NSB*512-1:0]      m_swd;
    ot_hdc_delay #(.W(2*NBK + NSU*NSB + NSB), .D(NRI - 1), .RESET(1)) u_ic (.clk(clk), .rst_n(rt),
        .d({p_re, p_we, p_sre, p_swe}), .q({m_re, m_we, m_sre, m_swe}));
    ot_hdc_delay #(.W(2*NBK*LAW + NBK*16 + NBK*512 + NSU*NSB*LAWS + NSB*LAWS + NSB*16 + NSB*512), .D(NRI - 1)) u_id (
        .clk(clk), .rst_n(rt), .d({p_ra, p_wl, p_wm, p_wd, p_sra, p_swl, p_swm, p_swd}),
        .q({m_ra, m_wl, m_wm, m_wd, m_sra, m_swl, m_swm, m_swd}));
    // ---- copy-0 banks ----
    //      r6: hard leaf children (pin flop + macros + capture + registered q = 1 input + 1 + 1 + 1 output relay of r5)
    wire [NBK*512-1:0] bq;
    generate for (g = 0; g < NBK; g = g + 1) begin : g_b
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_bank_t #(.DEPTH(DEPTH), .LAW(LAW), .USE_MACRO(USE_MACRO)) u_bt (.clk(clk), .rst_n(rtg[g]),
`else   // hardened cluster: the leaf view is built with the TP4 defaults (DEPTH 174 / LAW 8); no parameters on a hard child
        ot_qfd_vm_bank_t u_bt (.clk(clk), .rst_n(rtg[g]),
`endif
            .re(m_re[g]), .ra(m_ra[g*LAW +: LAW]), .q(bq[g*512 +: 512]),
            .we(m_we[g]), .wl(m_wl[g*LAW +: LAW]), .wm(m_wm[g*16 +: 16]), .wd(m_wd[g*512 +: 512]));
    end endgenerate
    // ---- SU copy banks ----
    wire [NSU*NSB*512-1:0] sq;
    //      r6b: one hard child per SU row bank (NSB = 1: pin flops -> 2 x 1024x256 -> capture -> registered q), NSU x NSB
    //      per grp -- the NSB = 2 child (4 macros, 3,149 flops) gated at TT clock insertion 312-451 ps vs 188-268 for the
    //      2-macro bank_t.  Same per-row-bank pipeline, so latency and behaviour are unchanged.
    generate for (c = 0; c < NSU; c = c + 1) begin : g_c
      for (j = 0; j < NSB; j = j + 1) begin : g_j
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_su_t #(.NSB(1), .DEPTHS(DEPTHS), .LAWS(LAWS), .USE_MACRO(USE_MACRO)) u_st (.clk(clk),
`else   // hardened cluster: leaf view built with the TP4 defaults (NSB 1 / DEPTHS 695 / LAWS 10)
        ot_qfd_vm_su_t u_st (.clk(clk),
`endif
            .rst_n(rtg[(c*NSB + j) % NBK]), .sre(m_sre[c*NSB + j]), .sra(m_sra[(c*NSB + j)*LAWS +: LAWS]),
            .swe(m_swe[j]), .swl(m_swl[j*LAWS +: LAWS]), .swm(m_swm[j*16 +: 16]), .swd(m_swd[j*512 +: 512]),
            .q(sq[(c*NSB + j)*512 +: 512]));
      end
    end endgenerate
    // ---- output data path: capture register beside every macro (no logic before it), then NRX (copy-0) / NRS (SU)
    //      clock relays toward the E face.  Datapath registers carry no reset and no enable. ----
    wire [NBK*512-1:0]     bx;          // copy-0 words at the E region: bq + 1 + NRX edges
    wire [NSU*NSB*512-1:0] sx;          // SU words at the E region:     sq + 1 + NRS edges
    ot_hdc_delay #(.W(NBK*512), .D(NRX - 1)) u_bx (.clk(clk), .rst_n(rt), .d(bq), .q(bx));
    ot_hdc_delay #(.W(NSU*NSB*512), .D(NRS - 1)) u_sx (.clk(clk), .rst_n(rt), .d(sq), .q(sx));
    // ---- tags (pin flop -> central control chain -> per-region kept replicas -> per-slice kept replicas) ----
    //   x push:  p_xv + 2 + NRI + NRX edges (aligned with bx)   = central (NRI + NRX) + xg (bank) + xv_k (slice)
    //   row:     one-hot select of p_rqb, p_rqb[2], p_rq   + 2 + NRI + NRX = decode + central (NRI + NRX) + slice
    //   SU:      p_sv + 2 + NRI + NRS edges (aligned with sx) = central (NRI + NRS) + sg (copy) + sv_k (slice)
    wire          xvc;
    ot_hdc_delay #(.W(1), .D(NRI + NRX), .RESET(1)) u_xc (.clk(clk), .rst_n(rt), .d(p_xv), .q(xvc));
    wire          xpush;                // central push (FIFO occupancy / ovf), aligned with every xv_k
    ot_hdc_delay #(.W(1), .D(2 + NRI + NRX), .RESET(1)) u_xp (.clk(clk), .rst_n(rt), .d(p_xv), .q(xpush));
    reg  [5:0]    rdq;                  // decoded row tag: {rq, rqb[2], onehot(rqb[1:0])}
    always @(posedge clk or negedge rt)
        if (!rt) rdq <= 6'd0;
        else rdq <= {p_rq, p_rqb[2], (p_rqb[1:0] == 2'd3), (p_rqb[1:0] == 2'd2), (p_rqb[1:0] == 2'd1), (p_rqb[1:0] == 2'd0)};
    wire [5:0]    rdc;
    ot_hdc_delay #(.W(6), .D(NRI + NRX), .RESET(1)) u_rc (.clk(clk), .rst_n(rt), .d(rdq), .q(rdc));
    wire [NSU-1:0] svc;
    ot_hdc_delay #(.W(NSU), .D(NRI + NRS), .RESET(1)) u_sc (.clk(clk), .rst_n(rt), .d(p_sv), .q(svc));
    // ---- row read: registered 8:1 as two 4:1 rungs (one-hot select, one AND-OR level) + a 2:1 rung into ro ----
    localparam integer RSL = 512 / FSW;
    genvar k, e;
    generate for (k = 0; k < RSL; k = k + 1) begin : g_rs
        (* keep = "true", dont_touch = "true" *) reg [5:0] rs1;   // select replica, rung 1
        (* keep = "true", dont_touch = "true" *) reg [1:0] rs2;   // {en, half} replica, rung 2
        reg [2*FSW-1:0] t1, t1n;
        always @(posedge clk or negedge rtg[k % NBK]) if (!rtg[k % NBK]) begin rs1 <= 6'd0; rs2 <= 2'd0; end
            else begin rs1 <= rdc; rs2 <= rs1[5:4]; end
        integer h, i;
        always @* begin
            t1n = {(2*FSW){1'b0}};
            for (h = 0; h < 2; h = h + 1)
                for (i = 0; i < 4; i = i + 1)
                    t1n[h*FSW +: FSW] = t1n[h*FSW +: FSW] | (bx[(4*h + i)*512 + k*FSW +: FSW] & {FSW{rs1[i]}});
        end
        always @(posedge clk) t1 <= t1n;
        always @(posedge clk) if (rs2[1]) ro[k*FSW +: FSW] <= rs2[0] ? t1[FSW +: FSW] : t1[0 +: FSW];
    end endgenerate
    // ---- SU answers: per-copy region replica, per-slice enable replica ----
    localparam integer SSL = (NSB * 512) / FSW;
    generate for (c = 0; c < NSU; c = c + 1) begin : g_sc
        (* keep = "true", dont_touch = "true" *) reg sg;
        always @(posedge clk or negedge rtg[c % NBK]) if (!rtg[c % NBK]) sg <= 1'b0; else sg <= svc[c];
        for (k = 0; k < SSL; k = k + 1) begin : g_k
            (* keep = "true", dont_touch = "true" *) reg sv_k;
            always @(posedge clk or negedge rtg[c % NBK]) if (!rtg[c % NBK]) sv_k <= 1'b0; else sv_k <= sg;
            always @(posedge clk) if (sv_k) so[c*NSB*512 + k*FSW +: FSW] <= sx[c*NSB*512 + k*FSW +: FSW];
        end
    end endgenerate
    // ---- x beat FIFO in the E region: push on the clock (aligned with bx), pop on engine edges ----
    // Every FSW-bit slice owns kept one-hot wp / rp and its own push / pop / me replicas (a select drives FSW x NPP
    // flops, the read is one AND-OR level, no pointer net crosses the tile); push comes from a per-bank region replica.
    localparam integer NSL = (NBK * 512) / FSW;
    localparam integer SPB = 512 / FSW;
    reg [LP:0]   cnt;
    wire popn = me_t && p_pop2;
    always @(posedge clk or negedge rt) begin
        if (!rt) begin cnt <= 0; ovf <= 1'b0; end
        else begin
            cnt <= cnt + (xpush ? 1'b1 : 1'b0) - (popn ? 1'b1 : 1'b0);
            if ((xpush && !popn && cnt == NPP) || (popn && cnt == 0)) ovf <= 1'b1;
        end
    end
    wire [NBK-1:0] xg;
    generate for (g = 0; g < NBK; g = g + 1) begin : g_xg
        (* keep = "true", dont_touch = "true" *) reg r;
        always @(posedge clk or negedge rtg[g]) if (!rtg[g]) r <= 1'b0; else r <= xvc;
        assign xg[g] = r;
    end endgenerate
    generate for (k = 0; k < 4; k = k + 1) begin : g_fifo4
        ot_qfd_vm_xfifo32_t #(.NPP(NPP), .FSW(FSW), .MEREG(MEREG)) u_fifo (
            .clk(clk), .me_in(me_in), .rtg(rtg[k*2 +: 2]),
            .pgw(pgw[k*2 +: 2]), .xg(xg[k*2 +: 2]),
            .bx(bx[k*1024 +: 1024]), .xo(xo[k*1024 +: 1024]));
    end endgenerate
endmodule
