`timescale 1ns/1ps
`ifndef OT_QFD_VM_DELAY1_MOD
`define OT_QFD_VM_DELAY1_MOD ot_qfd_vm_delay1_t
`endif
`ifndef OT_QFD_VM_DELAY2_MOD
`define OT_QFD_VM_DELAY2_MOD ot_qfd_vm_delay2_t
`endif
// ---------------------------------------------------------------------------------------------------------------------
// claude/qwen-tp8-vm 2026-10-13 (RTL-B, PLAN revision): the VM REGION AS HARDENABLE LEAVES ONLY, EVERY SEAM SHORT.
//
// ot_qfd_vm_region_leaf is pin-compatible with ot_qfd_vm_region_quarter (rtl/qwen_sys/vm_die_split_20261012, the FLAT
// REFERENCE: same parameters, same ports, same cycle behaviour on xo / ro / so / ovf; select it with
// +define+OT_QFD_VM_TILE_MOD=ot_qfd_vm_region_leaf).  It contains ONLY leaf instances and wires: no always block, no
// register, no logic, no region clock tree (every leaf is its own clock root).  Miter: tb_qfd_vm_region_leaf.sv,
// runner tools/qwen_tp8/vm_region_leaf_miter.sh.
//
// PLAN revision (why the first cut was rejected by the physical plan): ONE control leaf (gctl_t) per region drove the
// pin flops of 8 banks, 16 FIFOs and 6 SU banks over up to 1,177 um, and ONE row-read leaf took all 4,096 bx bits on
// one face (393 um of pins) with no point within 500 um of the eight bx relays.  Both are dissolved into leaves that
// sit BESIDE their consumers; every chain is replicated verbatim per leaf (same flops per consumer, same edges), so
// the region gains NO edge on any path:
//    8 x ot_qfd_vm_bctl_t   one per bank: reset relay, me / pop replica, the bank's control + address + mask pin
//                           flops and their NRI - 1 relays, the x tag chain and the FIFO gate (was gctl_t's per-bank
//                           part).  Drives its bank_t and its two xfifo8_t (<= 300 um).
//    6 x ot_qfd_vm_sctl_t   one per SU row bank (c, j): reset relay, the SU bank's pin flops + relays and the SU
//                           answer tag chain (svc; the j = 0 leaf drives su1024_t[c]).  The two swe / swl / swm words
//                           each enter three leaves (one pin flop per consumer; they were one pin flop fanned to three).
//    2 x ot_qfd_vm_rr4_t    the 4:1 rung of the row read for banks 4h .. 4h + 3 (16 FSW-32 slices: select replicas +
//                           one AND-OR level into t1), with its own row tag chain.  Banks 4h .. 4h + 3 are one unit
//                           column of the region, so the leaf sits beside their four bx relays (2,048 pins, W face).
//    1 x ot_qfd_vm_rr2_t    the 2:1 rung into ro (own tag chain) + the region's FIFO occupancy / ovf counter.
//    8 x ot_qfd_vm_bank_t, 6 x ot_qfd_vm_su_t, 16 x ot_qfd_vm_xfifo8_t, 3 x ot_qfd_vm_su1024_t: closed views, unchanged.
//   14 x ot_qfd_vm_delay2_t (wd per bank, swd per SU bank) and 8 x ot_qfd_vm_delay1_t (bq -> bx): unchanged
//   (= ot_qwen_tree_delay2_t / ot_qwen_tree_delay1_t, closed; +define+OT_QFD_VM_DELAY1_MOD / _DELAY2_MOD binds them).
//
// SEAMS (launch flop -> wire -> capture flop; (*) = as the flat code and the closed views already have):
//   region pins re[g] ra wl wm we[g]            -> bctl_t[g] pin flops                      (one leaf pin each)
//   region pins xv, pop, me_in                  -> bctl_t[0..7] (p_xv, pg, mg) and rr2_t (p_xv, p_pop, mr): 9 pin flops
//   region pin  me_in                           -> also 16 x xfifo8_t mr_k (closed view)
//   region pins sre[c,j] sra                    -> sctl_t[c,j] pin flops; swe[j] swl swm -> 3 sctl_t; sv[c] -> 2 sctl_t
//   region pins rq, rqb                         -> rr4_t[0..1] and rr2_t pin flops
//   region pins wd[g] / swd[j]                  -> delay2_t stage 0; swd[j] enters 3 relays
//   region pin  rst_n                           -> the reset relay (rt, r) of every bctl / sctl / rr4 / rr2 leaf (*)
//   bctl_t r (rtg)                              -> ASYNC CLEAR of bank_t.rr and of its 2 xfifo8_t (*)
//   bctl_t m_re m_we m_ra m_wl m_wm             -> bank_t p_*;  bctl_t pg / xg -> 2 x xfifo8_t pp_k / xv_k
//   sctl_t r -> su_t.rr (and su1024_t for j = 0) (*);  sctl_t m_* -> su_t p_*;  sctl_t[c,0] svc -> su1024_t[c] sg
//   delay2_t stage 1 -> bank_t p_wd / su_t p_swd;  bank_t q -> delay1_t;  delay1_t (bx) -> 2 x xfifo8_t fe
//   delay1_t (bx)                               -> rr4_t t1 THROUGH ONE AND-OR LEVEL (4:1 one-hot) (*): as row128_t
//   rr4_t t1                                    -> rr2_t ro (2:1, enable rs2[1]);  su_t q -> su1024_t so
//   xfifo8_t xo / rr2_t ro, ovf / su1024_t so   -> region pins (all registers)
// The pins that fan to several leaves (xv, pop, me_in, rst_n, rq, rqb, swe / swl / swm, sv) are driven by the die relay
// tree with one endpoint register per <= 500 um neighbourhood (physical plan: results/arch/qwen_tp8_1012).
//
// LEAF_MUT (miter negative controls, all must FAIL): 1 rr4 slice 5 select one bank off; 2 rr4[1] row tag one edge
// short; 3 bctl[3] pop replica stuck; 4 wd relay of bank 5 one stage short; 5 bx relay of bank 2 one stage short;
// 6 swd relay of SU (1,0) one stage short; 7 rr2 central push one edge short; 8 sctl (1,0) SU tag one edge short;
// 9 bctl[6] x tag one edge short; 10 sctl (2,1) address relay one stage short; 11 bctl[1] address relay one stage
// short; 12 rr2 row tag one edge short.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_region_leaf #(
    parameter integer ROW_MUT = 0,
    parameter integer SU_MUT = 0,
    parameter integer NBK = 8,
    parameter integer NSB = 2,
    parameter integer NSU = 3,
    parameter integer DEPTH = 1024,
    parameter integer LAW = 10,
    parameter integer DEPTHS = 1024,
    parameter integer LAWS = 10,
    parameter integer USE_MACRO = 0,
    parameter integer NPP = 12,
    parameter integer MEREG = 1,
    parameter integer NRI = 2,
    parameter integer NRX = 2,
    parameter integer NRS = 1,
    parameter integer FSW = 32,
    parameter integer LEAF_MUT = 0
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
    output wire [NBK*512-1:0]        xo,
    output wire [511:0]              ro,
    output wire [NSU*NSB*512-1:0]    so,
    output wire                      ovf
);
    initial if (NBK != 8 || NSB != 2 || NSU != 3 || FSW != 32 || NRI != 2 || NRX != 2 || NRS != 1)
        $fatal(1, "ot_qfd_vm_region_leaf: unsupported leaf shape");
    genvar g, c, j, k, h;
    // ---- copy-0 banks: control leaf + write-data relay -> bank -> bx relay ----
    wire [NBK-1:0]     rtg, pgw, xg;
    wire [NBK*512-1:0] m_wd, bq, bx;
    generate for (g = 0; g < NBK; g = g + 1) begin : g_b
        wire           m_re, m_we;
        wire [LAW-1:0] m_ra, m_wl;
        wire [15:0]    m_wm;
        localparam integer BMUT = (LEAF_MUT == 3 && g == 3) ? 1 : (LEAF_MUT == 9 && g == 6) ? 2 : (LEAF_MUT == 11 && g == 1) ? 3 : 0;
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_bctl_t #(.LAW(LAW), .MEREG(MEREG), .NRI(NRI), .NRX(NRX), .MUT(BMUT)) u_bc (
`else   // hardened leaf: built with its defaults (the production TP8 shape); no parameters on a hard child
        ot_qfd_vm_bctl_t u_bc (
`endif
            .clk(clk), .rst_n(rst_n), .me_in(me_in), .re(re[g]), .ra(ra[g*LAW +: LAW]), .we(we[g]),
            .wl(wl[g*LAW +: LAW]), .wm(wm[g*16 +: 16]), .xv(xv), .pop(pop),
            .rtg(rtg[g]), .pgw(pgw[g]), .xg(xg[g]), .m_re(m_re), .m_ra(m_ra), .m_we(m_we), .m_wl(m_wl), .m_wm(m_wm));
        if (LEAF_MUT == 4 && g == 5) begin : g_wdm
            `OT_QFD_VM_DELAY1_MOD u_wd (.clk(clk), .d(wd[g*512 +: 512]), .q(m_wd[g*512 +: 512]));
        end else begin : g_wd
            `OT_QFD_VM_DELAY2_MOD u_wd (.clk(clk), .d(wd[g*512 +: 512]), .q(m_wd[g*512 +: 512]));
        end
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_bank_t #(.DEPTH(DEPTH), .LAW(LAW), .USE_MACRO(USE_MACRO)) u_bt (.clk(clk), .rst_n(rtg[g]),
`else   // hardened leaf view: built with the TP4 defaults (DEPTH 174 / LAW 8); no parameters on a hard child
        ot_qfd_vm_bank_t u_bt (.clk(clk), .rst_n(rtg[g]),
`endif
            .re(m_re), .ra(m_ra), .q(bq[g*512 +: 512]), .we(m_we), .wl(m_wl), .wm(m_wm), .wd(m_wd[g*512 +: 512]));
        if (LEAF_MUT == 5 && g == 2) begin : g_bxm
            assign bx[g*512 +: 512] = bq[g*512 +: 512];
        end else begin : g_bx
            `OT_QFD_VM_DELAY1_MOD u_bx (.clk(clk), .d(bq[g*512 +: 512]), .q(bx[g*512 +: 512]));
        end
    end endgenerate
    // ---- SU copy banks: control leaf + write-data relay beside every su_t; sx = sq (NRS - 1 = 0 stages) ----
    wire [NSU*NSB*512-1:0] sq;
    wire [NSU*NSB-1:0]     rts, svc;
    generate for (c = 0; c < NSU; c = c + 1) begin : g_c
      for (j = 0; j < NSB; j = j + 1) begin : g_j
        wire [511:0]      m_swd;
        wire              m_sre, m_swe;
        wire [LAWS-1:0]   m_sra, m_swl;
        wire [15:0]       m_swm;
        localparam integer SMUT = (LEAF_MUT == 8 && c == 1 && j == 0) ? 1 : (LEAF_MUT == 10 && c == 2 && j == 1) ? 2 : 0;
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_sctl_t #(.LAWS(LAWS), .NRI(NRI), .NRS(NRS), .MUT(SMUT)) u_sc (
`else
        ot_qfd_vm_sctl_t u_sc (
`endif
            .clk(clk), .rst_n(rst_n), .sre(sre[c*NSB + j]), .sra(sra[(c*NSB + j)*LAWS +: LAWS]), .swe(swe[j]),
            .swl(swl[j*LAWS +: LAWS]), .swm(swm[j*16 +: 16]), .sv(sv[c]),
            .rtg(rts[c*NSB + j]), .m_sre(m_sre), .m_sra(m_sra), .m_swe(m_swe), .m_swl(m_swl), .m_swm(m_swm),
            .svc(svc[c*NSB + j]));
        if (LEAF_MUT == 6 && c == 1 && j == 0) begin : g_sdm
            `OT_QFD_VM_DELAY1_MOD u_sd (.clk(clk), .d(swd[j*512 +: 512]), .q(m_swd));
        end else begin : g_sd
            `OT_QFD_VM_DELAY2_MOD u_sd (.clk(clk), .d(swd[j*512 +: 512]), .q(m_swd));
        end
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_su_t #(.NSB(1), .DEPTHS(DEPTHS), .LAWS(LAWS), .USE_MACRO(USE_MACRO)) u_st (.clk(clk),
`else   // hardened leaf view: built with the TP4 defaults (NSB 1 / DEPTHS 695 / LAWS 10)
        ot_qfd_vm_su_t u_st (.clk(clk),
`endif
            .rst_n(rts[c*NSB + j]), .sre(m_sre), .sra(m_sra), .swe(m_swe), .swl(m_swl), .swm(m_swm), .swd(m_swd),
            .q(sq[(c*NSB + j)*512 +: 512]));
      end
    end endgenerate
    generate for (c = 0; c < NSU; c = c + 1) begin : g_su_leaf
        ot_qfd_vm_su1024_t #(.MUT(SU_MUT)) u_su (.clk(clk), .rtg(rts[c*NSB]), .svc(svc[c*NSB]),
            .sx(sq[c*1024 +: 1024]), .so(so[c*1024 +: 1024]));
    end endgenerate
    // ---- row read: two 4:1 rungs (banks 0..3, 4..7), one 2:1 rung (+ the region's FIFO occupancy / ovf) ----
    wire [1023:0] t1;
    generate for (h = 0; h < 2; h = h + 1) begin : g_r4
        localparam integer R4MUT = (LEAF_MUT == 1 && h == 0) ? 1 : (LEAF_MUT == 2 && h == 1) ? 2 : 0;
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_rr4_t #(.NRI(NRI), .NRX(NRX), .MUT(R4MUT)) u_r4 (
`else
        ot_qfd_vm_rr4_t u_r4 (
`endif
            .clk(clk), .rst_n(rst_n), .rqb(rqb[1:0]),
            .bx(bx[h*2048 +: 2048]), .t1(t1[h*512 +: 512]));
    end endgenerate
    localparam integer R2MUT = (ROW_MUT != 0) ? 1 : (LEAF_MUT == 12) ? 2 : (LEAF_MUT == 7) ? 3 : 0;
`ifndef OT_QFD_VM_HARD
    ot_qfd_vm_rr2_t #(.NPP(NPP), .MEREG(MEREG), .NRI(NRI), .NRX(NRX), .MUT(R2MUT)) u_r2 (
`else
    ot_qfd_vm_rr2_t u_r2 (
`endif
        .clk(clk), .rst_n(rst_n), .me_in(me_in), .rq(rq), .rqb(rqb), .xv(xv), .pop(pop),
        .t1a(t1[0 +: 512]), .t1b(t1[512 +: 512]), .ro(ro), .ovf(ovf));
    generate for (k = 0; k < 16; k = k + 1) begin : g_fifo16
        ot_qfd_vm_xfifo8_t #(.NPP(NPP), .FSW(FSW), .MEREG(MEREG)) u_fifo (
            .clk(clk), .me_in(me_in), .rtg(rtg[k/2 +: 1]),
            .pgw(pgw[k/2 +: 1]), .xg(xg[k/2 +: 1]),
            .bx(bx[k*256 +: 256]), .xo(xo[k*256 +: 256]));
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_qfd_vm_bctl_t: the control of ONE bank of a VM region = the per-bank part of the flat ot_qfd_vm_region_quarter
// expressions, every shared chain replicated verbatim (reset relay rt -> r, x tag chain u_xc).
//   Inputs: every one lands on a pin flop with no logic before it (re we xv -> p_* (reset rt); ra wl wm -> p_*;
//   pop -> pg (enable mg); me_in -> mg).  rst_n is the asynchronous reset: it reaches only the async-clear pins of
//   rt and r (no D pin) -- the one input that is not a pin flop, as in the flat code.
//   Outputs: every one is a flop.  rtg = r; pgw = pg; xg = the FIFO gate (async clear r); m_re m_we = u_ic (NRI - 1
//   = 1 stage); m_ra m_wl m_wm = u_id.  Defaults = the production TP8 shape (a hard child has no parameters).
//   MUT (miter only): 1 pop replica stuck; 2 x tag one edge short; 3 address relay one stage short.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_bctl_t #(
    parameter integer LAW = 8,
    parameter integer MEREG = 1,
    parameter integer NRI = 2,
    parameter integer NRX = 2,
    parameter integer MUT = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            me_in,
    input  wire            re,
    input  wire [LAW-1:0]  ra,
    input  wire            we,
    input  wire [LAW-1:0]  wl,
    input  wire [15:0]     wm,
    input  wire            xv,
    input  wire            pop,
    output wire            rtg,
    output wire            pgw,
    output wire            xg,
    output wire            m_re,
    output wire [LAW-1:0]  m_ra,
    output wire            m_we,
    output wire [LAW-1:0]  m_wl,
    output wire [15:0]     m_wm
);
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    (* keep = "true", dont_touch = "true" *) reg r;
    (* keep = "true", dont_touch = "true" *) reg mg;
    (* keep = "true", dont_touch = "true" *) reg pg;
    always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= rt;
    always @(posedge clk) mg <= me_in;
    always @(posedge clk or negedge rt) if (!rt) pg <= 1'b0;
        else if (((MEREG != 0) ? mg : me_in) && MUT != 1) pg <= pop;
    assign rtg = r;
    assign pgw = pg;
    reg p_re, p_we, p_xv;
    always @(posedge clk or negedge rt)
        if (!rt) begin p_re <= 1'b0; p_we <= 1'b0; p_xv <= 1'b0; end
        else begin p_re <= re; p_we <= we; p_xv <= xv; end
    reg [LAW-1:0] p_ra, p_wl;
    reg [15:0]    p_wm;
    always @(posedge clk) begin p_ra <= ra; p_wl <= wl; p_wm <= wm; end
    ot_hdc_delay #(.W(2), .D(NRI - 1), .RESET(1)) u_ic (.clk(clk), .rst_n(rt), .d({p_re, p_we}), .q({m_re, m_we}));
    ot_hdc_delay #(.W(LAW), .D(NRI - 1 - ((MUT == 3) ? 1 : 0))) u_ia (.clk(clk), .rst_n(rt), .d(p_ra), .q(m_ra));
    ot_hdc_delay #(.W(LAW + 16), .D(NRI - 1)) u_id (.clk(clk), .rst_n(rt), .d({p_wl, p_wm}), .q({m_wl, m_wm}));
    wire xvc;
    ot_hdc_delay #(.W(1), .D(NRI + NRX - ((MUT == 2) ? 1 : 0)), .RESET(1)) u_xc (.clk(clk), .rst_n(rt), .d(p_xv), .q(xvc));
    (* keep = "true", dont_touch = "true" *) reg xr;
    always @(posedge clk or negedge r) if (!r) xr <= 1'b0; else xr <= xvc;
    assign xg = xr;
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_qfd_vm_sctl_t: the control of ONE SU row bank (copy c, bank j) of a VM region, flat expressions verbatim.
//   Inputs land on pin flops (sre swe sv -> p_* (reset rt); sra swl swm -> p_*); rst_n reaches only rt / r.
//   Outputs are flops: rtg = r; m_sre m_swe = u_ic; m_sra m_swl m_swm = u_id (NRI - 1 = 1 stage); svc = the SU answer
//   tag (NRI + NRS = 3 stages; used from the j = 0 leaf of a copy).
//   MUT (miter only): 1 SU tag one edge short; 2 address relay one stage short.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_sctl_t #(
    parameter integer LAWS = 10,
    parameter integer NRI = 2,
    parameter integer NRS = 1,
    parameter integer MUT = 0
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             sre,
    input  wire [LAWS-1:0]  sra,
    input  wire             swe,
    input  wire [LAWS-1:0]  swl,
    input  wire [15:0]      swm,
    input  wire             sv,
    output wire             rtg,
    output wire             m_sre,
    output wire [LAWS-1:0]  m_sra,
    output wire             m_swe,
    output wire [LAWS-1:0]  m_swl,
    output wire [15:0]      m_swm,
    output wire             svc
);
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    (* keep = "true", dont_touch = "true" *) reg r;
    always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= rt;
    assign rtg = r;
    reg p_sre, p_swe, p_sv;
    always @(posedge clk or negedge rt)
        if (!rt) begin p_sre <= 1'b0; p_swe <= 1'b0; p_sv <= 1'b0; end
        else begin p_sre <= sre; p_swe <= swe; p_sv <= sv; end
    reg [LAWS-1:0] p_sra, p_swl;
    reg [15:0]     p_swm;
    always @(posedge clk) begin p_sra <= sra; p_swl <= swl; p_swm <= swm; end
    ot_hdc_delay #(.W(2), .D(NRI - 1), .RESET(1)) u_ic (.clk(clk), .rst_n(rt), .d({p_sre, p_swe}), .q({m_sre, m_swe}));
    ot_hdc_delay #(.W(LAWS), .D(NRI - 1 - ((MUT == 2) ? 1 : 0))) u_ia (.clk(clk), .rst_n(rt), .d(p_sra), .q(m_sra));
    ot_hdc_delay #(.W(LAWS + 16), .D(NRI - 1)) u_id (.clk(clk), .rst_n(rt), .d({p_swl, p_swm}), .q({m_swl, m_swm}));
    ot_hdc_delay #(.W(1), .D(NRI + NRS - ((MUT == 1) ? 1 : 0)), .RESET(1)) u_sc (.clk(clk), .rst_n(rt), .d(p_sv), .q(svc));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_qfd_vm_rr4_t: the 4:1 rung of the row read for FOUR banks (16 FSW-32 slices): per slice a one-hot select
// replica rs1 (4) and t1 (32) = one AND-OR level over the four banks' bx (as ot_qfd_vm_row128_t: NO pin register on
// bx -- the launch flop is the bank's ot_qfd_vm_delay1_t next door; a pin register would add an edge to ro).
//   Only rqb[1:0] enters (the one-hot select free-runs, as flat; rr2_t gates ro with the {rq, rqb[2]} tag).
//   Own row tag chain (rqb pin flop -> decode -> NRI + NRX = 4 stages) and own reset relay (rt -> 4 r replicas).
//   16 x (4 + 32) + 2 + 4 + 4 * 4 + 1 + 4 = 603 flops, one root.  bx: 2,048 pins (two faces), t1: 512.
//   MUT (miter only): 1 slice 5's select replica one bank off; 2 row tag one edge short.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_rr4_t #(
    parameter integer NRI = 2,
    parameter integer NRX = 2,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [1:0]    rqb,
    input  wire [2047:0] bx,            // bx of banks 4h .. 4h + 3 (one unit column, bank-major = bottom to top): W face
    output wire [511:0]  t1
);
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    (* keep = "true", dont_touch = "true" *) reg [3:0] r;
    always @(posedge clk or negedge rst_n) if (!rst_n) r <= 4'd0; else r <= {4{rt}};
    reg [1:0] p_rqb;
    always @(posedge clk) p_rqb <= rqb;
    reg [3:0] rdq;
    always @(posedge clk or negedge rt)
        if (!rt) rdq <= 4'd0;
        else rdq <= {(p_rqb == 2'd3), (p_rqb == 2'd2), (p_rqb == 2'd1), (p_rqb == 2'd0)};
    wire [3:0] rdc;
    ot_hdc_delay #(.W(4), .D(NRI + NRX - ((MUT == 2) ? 1 : 0)), .RESET(1)) u_rc (.clk(clk), .rst_n(rt), .d(rdq), .q(rdc));
    genvar s;
    generate for (s = 0; s < 16; s = s + 1) begin : g_slice
        (* keep = "true", dont_touch = "true" *) reg [3:0] rs1;
        always @(posedge clk or negedge r[s % 4])
            if (!r[s % 4]) rs1 <= 4'd0;
            else rs1 <= (MUT == 1 && s == 5) ? {rdc[2:0], rdc[3]} : rdc;
        // VM3 2026-10-13: the one-hot AND-OR as a KEPT TREE (banks 0 | 1, banks 2 | 3, then the OR; same function, same
        // single level between the bx relays and t).  Mapped as one star gate per bit, up to two of the four bank nets
        // crossed mid height for every bit (1,024 crossings in a 17.28-um leaf: GRT-0116); with the two pair nets kept
        // every horizontal cut of the leaf is crossed by ONE net a bit (512).
        reg [31:0] t;
        (* keep = "true" *) wire [31:0] p01 = (bx[0*512 + s*32 +: 32] & {32{rs1[0]}}) | (bx[1*512 + s*32 +: 32] & {32{rs1[1]}});
        (* keep = "true" *) wire [31:0] p23 = (bx[2*512 + s*32 +: 32] & {32{rs1[2]}}) | (bx[3*512 + s*32 +: 32] & {32{rs1[3]}});
        always @(posedge clk) t <= p01 | p23;
        assign t1[s*32 +: 32] = t;
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_qfd_vm_rr2_t: the 2:1 rung of the row read into ro (16 slices: rs1x = {rq, rqb[2]} tag replica, rs2, ro 32) and
// the region's x beat FIFO occupancy / ovf (the flat cnt / ovf with its own p_xv / u_xp / p_pop / mr).
//   Inputs: rq rqb xv -> pin flops; pop -> p_pop (enable me_t); me_in -> mr; t1a / t1b land on ro through the 2:1
//   mux (launch: the two rr4_t t1 registers, as flat t1 -> ro); rst_n reaches only rt / r.  Outputs ro, ovf: flops.
//   MUT (miter only): 1 half select inverted (= row128_t's MUT); 2 row tag one edge short; 3 central push one edge short.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_rr2_t #(
    parameter integer NPP = 12,
    parameter integer MEREG = 1,
    parameter integer NRI = 2,
    parameter integer NRX = 2,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          me_in,
    input  wire          rq,
    input  wire [2:0]    rqb,
    input  wire          xv,
    input  wire          pop,
    input  wire [511:0]  t1a,
    input  wire [511:0]  t1b,
    output reg  [511:0]  ro,
    output reg           ovf
);
    localparam integer LP = (NPP > 1) ? $clog2(NPP) : 1;
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    (* keep = "true", dont_touch = "true" *) reg [3:0] r;
    always @(posedge clk or negedge rst_n) if (!rst_n) r <= 4'd0; else r <= {4{rt}};
    // ---- row tag ----
    reg p_rq, p_xv;
    always @(posedge clk or negedge rt) if (!rt) begin p_rq <= 1'b0; p_xv <= 1'b0; end else begin p_rq <= rq; p_xv <= xv; end
    reg p_rqb2;
    always @(posedge clk) p_rqb2 <= rqb[2];
    reg [1:0] rdq;
    always @(posedge clk or negedge rt) if (!rt) rdq <= 2'd0; else rdq <= {p_rq, p_rqb2};
    wire [1:0] rdc;
    ot_hdc_delay #(.W(2), .D(NRI + NRX - ((MUT == 2) ? 1 : 0)), .RESET(1)) u_rc (.clk(clk), .rst_n(rt), .d(rdq), .q(rdc));
    genvar s;
    generate for (s = 0; s < 16; s = s + 1) begin : g_slice
        (* keep = "true", dont_touch = "true" *) reg [1:0] rs1x;
        (* keep = "true", dont_touch = "true" *) reg [1:0] rs2;
        always @(posedge clk or negedge r[s % 4])
            if (!r[s % 4]) begin rs1x <= 2'd0; rs2 <= 2'd0; end
            else begin rs1x <= rdc; rs2 <= rs1x; end
        always @(posedge clk) if (rs2[1]) ro[s*32 +: 32] <= (rs2[0] ^ (MUT == 1)) ? t1b[s*32 +: 32] : t1a[s*32 +: 32];
    end endgenerate
    // ---- x beat FIFO occupancy ----
    wire me_t;
    generate if (MEREG != 0) begin : g_mer
        reg mr;
        always @(posedge clk) mr <= me_in;
        assign me_t = mr;
    end else begin : g_mew
        assign me_t = me_in;
    end endgenerate
    reg p_pop, p_pop2;
    always @(posedge clk or negedge rt) if (!rt) begin p_pop <= 1'b0; p_pop2 <= 1'b0; end
        else if (me_t) begin p_pop <= pop; p_pop2 <= p_pop; end
    wire xpush;
    ot_hdc_delay #(.W(1), .D(2 + NRI + NRX - ((MUT == 3) ? 1 : 0)), .RESET(1)) u_xp (.clk(clk), .rst_n(rt), .d(p_xv), .q(xpush));
    reg [LP:0] cnt;
    wire popn = me_t && p_pop2;
    always @(posedge clk or negedge rt) begin
        if (!rt) begin cnt <= 0; ovf <= 1'b0; end
        else begin
            cnt <= cnt + (xpush ? 1'b1 : 1'b0) - (popn ? 1'b1 : 1'b0);
            if ((xpush && !popn && cnt == NPP) || (popn && cnt == 0)) ovf <= 1'b1;
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// 512-b data relay leaves: free-running registers, no reset, no enable, no logic (pin flop in, register out).
//   ot_qfd_vm_delay1_t  1 stage  (512 flops):  bq -> bx            (flat u_bx, NRX - 1 = 1)
//   ot_qfd_vm_delay2_t  2 stages (1,024 flops): wd / swd -> macro leaf (flat p_wd / p_swd pin flop + u_id, NRI = 2)
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_delay1_t (input wire clk, input wire [511:0] d, output wire [511:0] q);
    (* keep = "true" *) reg [511:0] s0;
    always @(posedge clk) s0 <= d;
    assign q = s0;
endmodule

module ot_qfd_vm_delay2_t (input wire clk, input wire [511:0] d, output wire [511:0] q);
    (* keep = "true" *) reg [511:0] s0, s1;
    always @(posedge clk) begin s0 <= d; s1 <= s0; end
    assign q = s1;
endmodule
