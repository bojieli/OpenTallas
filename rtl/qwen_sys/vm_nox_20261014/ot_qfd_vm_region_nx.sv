`timescale 1ns/1ps
`ifndef OT_QFD_VM_DELAY1_MOD
`define OT_QFD_VM_DELAY1_MOD ot_qfd_vm_delay1_t
`endif
`ifndef OT_QFD_VM_DELAY2_MOD
`define OT_QFD_VM_DELAY2_MOD ot_qfd_vm_delay2_t
`endif
// ---------------------------------------------------------------------------------------------------------------------
// TRIMMED central VM region, NO x READ (owner 08:20 PT 2026-10-14: the ME x operand comes from the distributed x slices,
// el1014-qwen-dvm-build.log; the central VM keeps banks, SU ports and row reads).  ot_qfd_vm_region_nx is
// ot_qfd_vm_region_leaf (rtl/qwen_sys/vm_plane_20261013) with the x path REMOVED, not tied:
//   removed ports   xv, pop, me_in (it gated only the x FIFO pop and the x tag), xo [4,096], ovf (x FIFO occupancy)
//   removed leaves  16 x ot_qfd_vm_xfifo8_t
//   changed leaves  ot_qfd_vm_bctl_t -> ot_qfd_vm_bctl_nx (no xv / pop / me_in inputs, no pgw / xg outputs: the pop
//                   replica, the x tag chain and the FIFO gate are gone); ot_qfd_vm_rr2_t -> ot_qfd_vm_rr2_nx (no xv /
//                   pop / me_in inputs, no ovf: the FIFO occupancy counter is gone).  Every remaining flop, chain and
//                   edge is verbatim (bank control relays, row tag chains, ro select): ro / so are cycle-identical.
//   unchanged       8 x bank_t, 6 x su_t, 3 x su1024_t, 6 x sctl_t, 2 x rr4_t, 8 x delay1_t (bq -> bx: now the row read
//                   only), 14 x delay2_t (closed views).
// Miter: tb_qfd_vm_region_nx.sv against the FLAT REFERENCE ot_qfd_vm_region_quarter (x traffic driven on the reference
// only; ro / so compared every clock).  LEAF_MUT (must FAIL): 1 rr4 slice 5 select one bank off; 2 rr4[1] row tag one
// edge short; 4 wd relay of bank 5 one stage short; 5 bx relay of bank 2 one stage short; 6 swd relay of SU (1,0) one
// stage short; 8 sctl (1,0) SU tag one edge short; 10 sctl (2,1) address relay one stage short; 11 bctl[1] address
// relay one stage short; 12 rr2 row tag one edge short; 13 rr2 half select inverted; 14 bctl[4] write strobe relay one
// stage short.  (3 / 7 / 9 of the x-path leaf were x-only and are gone with it.)
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_region_nx #(
    parameter integer NBK = 8,
    parameter integer NSB = 2,
    parameter integer NSU = 3,
    parameter integer DEPTH = 1024,
    parameter integer LAW = 10,
    parameter integer DEPTHS = 1024,
    parameter integer LAWS = 10,
    parameter integer USE_MACRO = 0,
    parameter integer NRI = 2,
    parameter integer NRX = 2,
    parameter integer NRS = 1,
    parameter integer LEAF_MUT = 0
) (
    input  wire                      clk,
    input  wire                      rst_n,
    input  wire [NBK-1:0]            re,
    input  wire [NBK*LAW-1:0]        ra,
    input  wire [NBK-1:0]            we,
    input  wire [NBK*LAW-1:0]        wl,
    input  wire [NBK*16-1:0]         wm,
    input  wire [NBK*512-1:0]        wd,
    input  wire                      rq,
    input  wire [2:0]                rqb,
    input  wire [NSU*NSB-1:0]        sre,
    input  wire [NSU*NSB*LAWS-1:0]   sra,
    input  wire [NSU-1:0]            sv,
    input  wire [NSB-1:0]            swe,
    input  wire [NSB*LAWS-1:0]       swl,
    input  wire [NSB*16-1:0]         swm,
    input  wire [NSB*512-1:0]        swd,
    output wire [511:0]              ro,
    output wire [NSU*NSB*512-1:0]    so
);
`ifndef SYNTHESIS
    initial if (NBK != 8 || NSB != 2 || NSU != 3 || NRI != 2 || NRX != 2 || NRS != 1)
        $fatal(1, "ot_qfd_vm_region_nx: unsupported leaf shape");
`endif
    genvar g, c, j, h;
    // ---- copy-0 banks: control leaf + write-data relay -> bank -> bx relay (row read) ----
    wire [NBK-1:0]     rtg;
    wire [NBK*512-1:0] m_wd, bq, bx;
    generate for (g = 0; g < NBK; g = g + 1) begin : g_b
        wire           m_re, m_we;
        wire [LAW-1:0] m_ra, m_wl;
        wire [15:0]    m_wm;
        localparam integer BMUT = (LEAF_MUT == 11 && g == 1) ? 3 : (LEAF_MUT == 14 && g == 4) ? 4 : 0;
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_bctl_nx #(.LAW(LAW), .NRI(NRI), .MUT(BMUT)) u_bc (
`else   // hardened leaf: built with its defaults (the production TP8 shape); no parameters on a hard child
        ot_qfd_vm_bctl_nx u_bc (
`endif
            .clk(clk), .rst_n(rst_n), .re(re[g]), .ra(ra[g*LAW +: LAW]), .we(we[g]),
            .wl(wl[g*LAW +: LAW]), .wm(wm[g*16 +: 16]),
            .rtg(rtg[g]), .m_re(m_re), .m_ra(m_ra), .m_we(m_we), .m_wl(m_wl), .m_wm(m_wm));
        if (LEAF_MUT == 4 && g == 5) begin : g_wdm
            `OT_QFD_VM_DELAY1_MOD u_wd (.clk(clk), .d(wd[g*512 +: 512]), .q(m_wd[g*512 +: 512]));
        end else begin : g_wd
            `OT_QFD_VM_DELAY2_MOD u_wd (.clk(clk), .d(wd[g*512 +: 512]), .q(m_wd[g*512 +: 512]));
        end
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_bank_t #(.DEPTH(DEPTH), .LAW(LAW), .USE_MACRO(USE_MACRO)) u_bt (.clk(clk), .rst_n(rtg[g]),
`else
        ot_qfd_vm_bank_t u_bt (.clk(clk), .rst_n(rtg[g]),
`endif
            .re(m_re), .ra(m_ra), .q(bq[g*512 +: 512]), .we(m_we), .wl(m_wl), .wm(m_wm), .wd(m_wd[g*512 +: 512]));
        if (LEAF_MUT == 5 && g == 2) begin : g_bxm
            assign bx[g*512 +: 512] = bq[g*512 +: 512];
        end else begin : g_bx
            `OT_QFD_VM_DELAY1_MOD u_bx (.clk(clk), .d(bq[g*512 +: 512]), .q(bx[g*512 +: 512]));
        end
    end endgenerate
    // ---- SU copy banks (unchanged from ot_qfd_vm_region_leaf) ----
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
`else
        ot_qfd_vm_su_t u_st (.clk(clk),
`endif
            .rst_n(rts[c*NSB + j]), .sre(m_sre), .sra(m_sra), .swe(m_swe), .swl(m_swl), .swm(m_swm), .swd(m_swd),
            .q(sq[(c*NSB + j)*512 +: 512]));
      end
    end endgenerate
    generate for (c = 0; c < NSU; c = c + 1) begin : g_su_leaf
        ot_qfd_vm_su1024_t u_su (.clk(clk), .rtg(rts[c*NSB]), .svc(svc[c*NSB]),
            .sx(sq[c*1024 +: 1024]), .so(so[c*1024 +: 1024]));
    end endgenerate
    // ---- row read: two 4:1 rungs (banks 0..3, 4..7), one 2:1 rung ----
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
    localparam integer R2MUT = (LEAF_MUT == 13) ? 1 : (LEAF_MUT == 12) ? 2 : 0;
`ifndef OT_QFD_VM_HARD
    ot_qfd_vm_rr2_nx #(.NRI(NRI), .NRX(NRX), .MUT(R2MUT)) u_r2 (
`else
    ot_qfd_vm_rr2_nx u_r2 (
`endif
        .clk(clk), .rst_n(rst_n), .rq(rq), .rqb(rqb), .t1a(t1[0 +: 512]), .t1b(t1[512 +: 512]), .ro(ro));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_qfd_vm_bctl_nx: the control of ONE copy-0 bank of a trimmed region = ot_qfd_vm_bctl_t without the x path (pop
// replica pg / mg, x tag chain u_xc, FIFO gate xr and their ports xv / pop / me_in / pgw / xg).
//   Inputs land on pin flops with no logic before them (re we -> p_* (reset rt); ra wl wm -> p_*); rst_n reaches only
//   rt / r.  Outputs are flops: rtg = r; m_re m_we = u_ic, m_ra = u_ia, m_wl m_wm = u_id (NRI - 1 = 1 stage).
//   MUT (miter only): 3 address relay one stage short; 4 strobe relay one stage short.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_bctl_nx #(
    parameter integer LAW = 8,
    parameter integer NRI = 2,
    parameter integer MUT = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire            re,
    input  wire [LAW-1:0]  ra,
    input  wire            we,
    input  wire [LAW-1:0]  wl,
    input  wire [15:0]     wm,
    output wire            rtg,
    output wire            m_re,
    output wire [LAW-1:0]  m_ra,
    output wire            m_we,
    output wire [LAW-1:0]  m_wl,
    output wire [15:0]     m_wm
);
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    (* keep = "true", dont_touch = "true" *) reg r;
    always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= rt;
    assign rtg = r;
    reg p_re, p_we;
    always @(posedge clk or negedge rt)
        if (!rt) begin p_re <= 1'b0; p_we <= 1'b0; end
        else begin p_re <= re; p_we <= we; end
    reg [LAW-1:0] p_ra, p_wl;
    reg [15:0]    p_wm;
    always @(posedge clk) begin p_ra <= ra; p_wl <= wl; p_wm <= wm; end
    ot_hdc_delay #(.W(2), .D(NRI - 1 - ((MUT == 4) ? 1 : 0)), .RESET(1)) u_ic (.clk(clk), .rst_n(rt), .d({p_re, p_we}), .q({m_re, m_we}));
    ot_hdc_delay #(.W(LAW), .D(NRI - 1 - ((MUT == 3) ? 1 : 0))) u_ia (.clk(clk), .rst_n(rt), .d(p_ra), .q(m_ra));
    ot_hdc_delay #(.W(LAW + 16), .D(NRI - 1)) u_id (.clk(clk), .rst_n(rt), .d({p_wl, p_wm}), .q({m_wl, m_wm}));
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_qfd_vm_rr2_nx: the 2:1 rung of the row read into ro = ot_qfd_vm_rr2_t without the x beat FIFO occupancy (p_xv,
// u_xp, p_pop, mr, cnt, ovf and the ports xv / pop / me_in / ovf).  16 slices: rs1x = {rq, rqb[2]} tag replica, rs2,
// ro 32.  Inputs: rq rqb -> pin flops; t1a / t1b land on ro through the 2:1 mux (launch: the two rr4_t t1 registers).
//   MUT (miter only): 1 half select inverted; 2 row tag one edge short.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_rr2_nx #(
    parameter integer NRI = 2,
    parameter integer NRX = 2,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          rq,
    input  wire [2:0]    rqb,
    input  wire [511:0]  t1a,
    input  wire [511:0]  t1b,
    output reg  [511:0]  ro
);
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    (* keep = "true", dont_touch = "true" *) reg [3:0] r;
    always @(posedge clk or negedge rst_n) if (!rst_n) r <= 4'd0; else r <= {4{rt}};
    reg p_rq;
    always @(posedge clk or negedge rt) if (!rt) p_rq <= 1'b0; else p_rq <= rq;
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
endmodule
