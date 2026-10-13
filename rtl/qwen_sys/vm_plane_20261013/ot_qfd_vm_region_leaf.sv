`timescale 1ns/1ps
`ifndef OT_QFD_VM_DELAY1_MOD
`define OT_QFD_VM_DELAY1_MOD ot_qfd_vm_delay1_t
`endif
`ifndef OT_QFD_VM_DELAY2_MOD
`define OT_QFD_VM_DELAY2_MOD ot_qfd_vm_delay2_t
`endif
// ---------------------------------------------------------------------------------------------------------------------
// claude/qwen-tp8-vm-rtl 2026-10-13 (RTL-B): the VM REGION AS HARDENABLE LEAVES ONLY.
//
// ot_qfd_vm_region_leaf is pin-compatible with ot_qfd_vm_region_quarter (rtl/qwen_sys/vm_die_split_20261012, the FLAT
// REFERENCE: same parameters, same ports, same cycle behaviour on xo / ro / so / ovf; select it with
// +define+OT_QFD_VM_TILE_MOD=ot_qfd_vm_region_leaf).  It contains ONLY leaf instances and wires: no always block, no
// register, no logic, no region clock tree (every leaf is its own clock root).  LEAF_MUT is the one extra parameter
// (default 0; the miter's mutants).  Miter: tb_qfd_vm_region_leaf.sv, runner tools/qwen_tp8/vm_region_leaf_miter.sh.
//
// Leaves of one region (NBK 8 / NSB 2 / NSU 3 / FSW 32, NRI 2 / NRX 2 / NRS 1: the only shape supported, as the flat):
//    8 x ot_qfd_vm_bank_t      closed view, bytes unchanged (copy-0 row bank: pin flop, 2 macros, capture, q register)
//    6 x ot_qfd_vm_su_t        closed view, bytes unchanged (SU row bank)
//   16 x ot_qfd_vm_xfifo8_t    closed view, bytes unchanged (x beat FIFO, 8 FSW-32 slices = a quarter bank)
//    3 x ot_qfd_vm_su1024_t    closed view, bytes unchanged (SU answer register of one copy)
//    1 x ot_qfd_vm_gctl_t      NEW: all region control (reset relays, me / pop replicas, control + address + mask pin
//                              flops and their NRI - 1 relays, tags, FIFO occupancy / ovf)
//    1 x ot_qfd_vm_rowrd_t     NEW: the row-read answer of the region (the body of the four ot_qfd_vm_row128_t)
//   14 x ot_qfd_vm_delay2_t    NEW: 512-b data relay, 2 free-running stages (= flat p_wd / p_swd pin flop + u_id):
//                              8 on wd (one per bank_t) + 6 on swd (one per su_t, so a relay sits beside its consumer
//                              and drives ONE su_t pin; the two swd words each enter three relays)
//    8 x ot_qfd_vm_delay1_t    NEW: 512-b data relay, 1 free-running stage (= flat u_bx, NRX - 1 = 1), bq -> bx
//   sx = sq is a wire (NRS - 1 = 0 stages): su_t q register -> su1024_t so register.
//   The delay leaves are behaviour-identical to ot_qwen_tree_delay1_t / ot_qwen_tree_delay2_t
//   (rtl/physical/ot_qwen_tree_delay_tiles.sv: clk, d[511:0], q[511:0]); +define+OT_QFD_VM_DELAY1_MOD=... /
//   OT_QFD_VM_DELAY2_MOD=... binds those masters instead (the miter has a run with that binding).
//
// SEAMS (launch flop -> wire -> capture flop; every one is leaf register -> wire -> leaf register except the three
// marked (*), which the flat code and the closed views already have):
//   region pins re we xv rq rqb sre sv swe ra wl wm sra swl swm pop me_in  -> gctl_t pin flops (p_*, g_rg.mg/pg, mr)
//   region pins wd[g] / swd[j]                 -> delay2_t stage 0 (pin flop); swd[j] enters 3 relays (su_t c = 0..2)
//   region pin  me_in                          -> also 16 x xfifo8_t mr_k (closed view; 8 slice flops per leaf)
//   region pin  rst_n                          -> gctl_t ONLY: async clear of rt and g_rg.r (reset relay; no D pin) (*)
//   gctl_t g_rg[g].r (rtg[g])                  -> ASYNC CLEAR pins of bank_t[g].rr, su_t.rr, su1024_t (sg, sv_k),
//                                                 2 x xfifo8_t (pp_k xv_k wpo rpo), rowrd_t (rs1 rs2 of 2 slices) (*)
//   gctl_t u_ic.line (m_re m_we m_sre m_swe)   -> bank_t p_re p_we / su_t p_sre p_swe          (m_swe[j]: 3 su_t)
//   gctl_t u_id.line (m_ra m_wl m_wm m_sra m_swl m_swm) -> bank_t p_ra p_wl p_wm / su_t p_sra p_swl p_swm
//   delay2_t stage 1 (m_wd / m_swd)            -> bank_t p_wd / su_t p_swd                       (one pin each)
//   bank_t q                                   -> delay1_t stage 0
//   delay1_t stage 0 (bx)                      -> 2 x xfifo8_t fe[e] (enable xv_k & wpo[e], no logic on D)
//                                              -> rowrd_t t1 THROUGH ONE AND-OR LEVEL (4:1 one-hot, select rs1) (*):
//                                                 row128_t has no register at bx, and adding one would add an edge
//                                                 to ro; the launch flop is the delay1_t register next door.
//   gctl_t u_rc.line last stage (rdc)          -> rowrd_t rs1 (16 slice replicas inside the leaf)
//   gctl_t u_sc.line last stage (svc[c])       -> su1024_t[c] sg
//   gctl_t g_xg[g].r (xg[g])                   -> 2 x xfifo8_t xv_k (8 slice replicas per leaf)
//   gctl_t g_rg[g].pg (pgw[g])                 -> 2 x xfifo8_t pp_k (enable me_k)
//   su_t q (sq = sx)                           -> su1024_t so (enable sv_k)
//   xfifo8_t xo / rowrd_t ro / su1024_t so / gctl_t ovf  -> region pins (all registers)
//
// INTER-LEAF FAN-OUT (leaf pins per driving register bit; limit ~32 per stage): rtg[g] <= 6 (bank_t, su_t for g < 6,
// su1024_t for g < 3, 2 x xfifo8_t, rowrd_t); xg[g] 2; pgw[g] 2; rdc[i] 1; svc[c] 1; m_re / m_we / m_ra / m_wl /
// m_wm 1; m_sre / m_sra 1; m_swe / m_swl / m_swm 3; delay2_t q 1; bx bit 2 (one xfifo8_t + rowrd_t); bq / sq bit 1.
// Region INPUT pins: me_in 17 (gctl_t + 16 xfifo8_t), swd bit 3, every other pin 1.  Nothing exceeds 6 leaf pins, so no
// per-consumer replica had to be added; the wide fan-outs (rtg -> ~193 flags, rdc -> 16 slices, me_in -> 8 slices)
// are INSIDE a leaf, on that leaf's own kept replicas.
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
    parameter integer LEAF_MUT = 0       // miter mutants: 1 rowrd select replica one bank off (slice 5); 2 gctl row tag one
                                         // edge short; 3 gctl pop replica of bank 3 stuck; 4 wd relay of bank 5 one stage
                                         // short; 5 bx relay of bank 2 one stage short; 6 swd relay of SU (1,0) one stage
                                         // short; 7 gctl central push (cnt / ovf) one edge short; 8 gctl SU tag one edge short
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
    genvar g, c, j, k;
    // ---- control leaf ----
    wire [NBK-1:0]          rtg, pgw, xg;
    wire [NBK-1:0]          m_re, m_we;
    wire [NSU*NSB-1:0]      m_sre;
    wire [NSB-1:0]          m_swe;
    wire [NBK*LAW-1:0]      m_ra, m_wl;
    wire [NBK*16-1:0]       m_wm;
    wire [NSU*NSB*LAWS-1:0] m_sra;
    wire [NSB*LAWS-1:0]     m_swl;
    wire [NSB*16-1:0]       m_swm;
    wire [5:0]              rdc;
    wire [NSU-1:0]          svc;
    localparam integer GMUT = (LEAF_MUT == 2) ? 1 : (LEAF_MUT == 3) ? 2 : (LEAF_MUT == 7) ? 3 : (LEAF_MUT == 8) ? 4 : 0;
`ifndef OT_QFD_VM_HARD
    ot_qfd_vm_gctl_t #(.NBK(NBK), .NSB(NSB), .NSU(NSU), .LAW(LAW), .LAWS(LAWS), .NPP(NPP), .MEREG(MEREG),
        .NRI(NRI), .NRX(NRX), .NRS(NRS), .MUT(GMUT)) u_gc (
`else   // hardened cluster: the leaf view is built with its defaults (the production TP8 shape); no parameters on a hard child
    ot_qfd_vm_gctl_t u_gc (
`endif
        .clk(clk), .rst_n(rst_n), .me_in(me_in), .re(re), .ra(ra), .we(we), .wl(wl), .wm(wm), .xv(xv), .rq(rq), .rqb(rqb),
        .sre(sre), .sra(sra), .sv(sv), .swe(swe), .swl(swl), .swm(swm), .pop(pop),
        .rtg(rtg), .pgw(pgw), .xg(xg), .m_re(m_re), .m_ra(m_ra), .m_we(m_we), .m_wl(m_wl), .m_wm(m_wm),
        .m_sre(m_sre), .m_sra(m_sra), .m_swe(m_swe), .m_swl(m_swl), .m_swm(m_swm), .rdc(rdc), .svc(svc), .ovf(ovf));
    // ---- copy-0 banks: write-data relay -> bank -> E-region relay ----
    wire [NBK*512-1:0] m_wd, bq, bx;
    generate for (g = 0; g < NBK; g = g + 1) begin : g_b
        if (LEAF_MUT == 4 && g == 5) begin : g_wdm
            `OT_QFD_VM_DELAY1_MOD u_wd (.clk(clk), .d(wd[g*512 +: 512]), .q(m_wd[g*512 +: 512]));
        end else begin : g_wd
            `OT_QFD_VM_DELAY2_MOD u_wd (.clk(clk), .d(wd[g*512 +: 512]), .q(m_wd[g*512 +: 512]));
        end
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_bank_t #(.DEPTH(DEPTH), .LAW(LAW), .USE_MACRO(USE_MACRO)) u_bt (.clk(clk), .rst_n(rtg[g]),
`else   // hardened cluster: the leaf view is built with the TP4 defaults (DEPTH 174 / LAW 8); no parameters on a hard child
        ot_qfd_vm_bank_t u_bt (.clk(clk), .rst_n(rtg[g]),
`endif
            .re(m_re[g]), .ra(m_ra[g*LAW +: LAW]), .q(bq[g*512 +: 512]),
            .we(m_we[g]), .wl(m_wl[g*LAW +: LAW]), .wm(m_wm[g*16 +: 16]), .wd(m_wd[g*512 +: 512]));
        if (LEAF_MUT == 5 && g == 2) begin : g_bxm
            assign bx[g*512 +: 512] = bq[g*512 +: 512];
        end else begin : g_bx
            `OT_QFD_VM_DELAY1_MOD u_bx (.clk(clk), .d(bq[g*512 +: 512]), .q(bx[g*512 +: 512]));
        end
    end endgenerate
    // ---- SU copy banks: one write-data relay beside every su_t; sx = sq (NRS - 1 = 0 stages) ----
    wire [NSU*NSB*512-1:0] sq;
    generate for (c = 0; c < NSU; c = c + 1) begin : g_c
      for (j = 0; j < NSB; j = j + 1) begin : g_j
        wire [511:0] m_swd;
        if (LEAF_MUT == 6 && c == 1 && j == 0) begin : g_sdm
            `OT_QFD_VM_DELAY1_MOD u_sd (.clk(clk), .d(swd[j*512 +: 512]), .q(m_swd));
        end else begin : g_sd
            `OT_QFD_VM_DELAY2_MOD u_sd (.clk(clk), .d(swd[j*512 +: 512]), .q(m_swd));
        end
`ifndef OT_QFD_VM_HARD
        ot_qfd_vm_su_t #(.NSB(1), .DEPTHS(DEPTHS), .LAWS(LAWS), .USE_MACRO(USE_MACRO)) u_st (.clk(clk),
`else   // hardened cluster: leaf view built with the TP4 defaults (NSB 1 / DEPTHS 695 / LAWS 10)
        ot_qfd_vm_su_t u_st (.clk(clk),
`endif
            .rst_n(rtg[(c*NSB + j) % NBK]), .sre(m_sre[c*NSB + j]), .sra(m_sra[(c*NSB + j)*LAWS +: LAWS]),
            .swe(m_swe[j]), .swl(m_swl[j*LAWS +: LAWS]), .swm(m_swm[j*16 +: 16]), .swd(m_swd),
            .q(sq[(c*NSB + j)*512 +: 512]));
      end
    end endgenerate
    // ---- answers ----
    localparam integer RMUT = (ROW_MUT != 0) ? 1 : (LEAF_MUT == 1) ? 2 : 0;
`ifndef OT_QFD_VM_HARD
    ot_qfd_vm_rowrd_t #(.MUT(RMUT)) u_row (.clk(clk), .rtg(rtg), .rdc(rdc), .bx(bx), .ro(ro));
`else
    ot_qfd_vm_rowrd_t u_row (.clk(clk), .rtg(rtg), .rdc(rdc), .bx(bx), .ro(ro));
`endif
    generate for (c = 0; c < NSU; c = c + 1) begin : g_su_leaf
        ot_qfd_vm_su1024_t #(.MUT(SU_MUT)) u_su (.clk(clk), .rtg(rtg[c % NBK]), .svc(svc[c]),
            .sx(sq[c*1024 +: 1024]), .so(so[c*1024 +: 1024]));
    end endgenerate
    generate for (k = 0; k < 16; k = k + 1) begin : g_fifo16
        ot_qfd_vm_xfifo8_t #(.NPP(NPP), .FSW(FSW), .MEREG(MEREG)) u_fifo (
            .clk(clk), .me_in(me_in), .rtg(rtg[k/2 +: 1]),
            .pgw(pgw[k/2 +: 1]), .xg(xg[k/2 +: 1]),
            .bx(bx[k*256 +: 256]), .xo(xo[k*256 +: 256]));
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_qfd_vm_gctl_t: ALL control of one VM region, the flat ot_qfd_vm_region_quarter expressions verbatim.
//   Inputs: every one lands on a pin flop with no logic before it (re we xv rq sre sv swe -> p_* (reset rt);
//   ra wl wm rqb sra swl swm -> p_* (no reset); pop -> g_rg[g].pg (enable mg) and p_pop (enable me_t);
//   me_in -> g_rg[g].mg and mr).  rst_n is the asynchronous reset: it reaches only the async-clear pins of rt and of
//   the eight g_rg.r reset relays (no D pin) -- the one input that is not a pin flop, as in the flat code.
//   With MEREG = 0 (not the production shape) me_in would gate pg / p_pop directly; production is MEREG = 1.
//   Outputs: every one is a flop.  rtg = g_rg.r; pgw = g_rg.pg; xg = g_xg.r; ovf = ovf; m_re m_we m_sre m_swe =
//   u_ic.line (NRI - 1 = 1 stage; at NRI 1 the ot_hdc_delay is a wire and the output is the p_* pin flop itself);
//   m_ra m_wl m_wm m_sra m_swl m_swm = u_id.line (same); rdc = last stage of u_rc (NRI + NRX = 4 stages; a wire
//   from the rdq flop at 0); svc = last stage of u_sc (NRI + NRS = 3).  No output is combinational at any parameter set.
//   rtg[g] also clears g_xg[g].r inside the leaf (as flat).  Defaults = the production TP8 shape (a hard child has no
//   parameters): LAW 8 (DEPTH 174), LAWS 10 (DEPTHS 695), NPP 12 (RV 1), MEREG 1, NRI 2 / NRX 2 / NRS 1.
//   MUT (miter only): 1 row tag one edge short; 2 pop replica of bank 3 stuck; 3 central push one edge short;
//   4 SU tag one edge short.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_gctl_t #(
    parameter integer NBK = 8,
    parameter integer NSB = 2,
    parameter integer NSU = 3,
    parameter integer LAW = 8,
    parameter integer LAWS = 10,
    parameter integer NPP = 12,
    parameter integer MEREG = 1,
    parameter integer NRI = 2,
    parameter integer NRX = 2,
    parameter integer NRS = 1,
    parameter integer MUT = 0
) (
    input  wire                      clk,
    input  wire                      rst_n,
    input  wire                      me_in,
    input  wire [NBK-1:0]            re,
    input  wire [NBK*LAW-1:0]        ra,
    input  wire [NBK-1:0]            we,
    input  wire [NBK*LAW-1:0]        wl,
    input  wire [NBK*16-1:0]         wm,
    input  wire                      xv,
    input  wire                      rq,
    input  wire [2:0]                rqb,
    input  wire [NSU*NSB-1:0]        sre,
    input  wire [NSU*NSB*LAWS-1:0]   sra,
    input  wire [NSU-1:0]            sv,
    input  wire [NSB-1:0]            swe,
    input  wire [NSB*LAWS-1:0]       swl,
    input  wire [NSB*16-1:0]         swm,
    input  wire                      pop,
    output wire [NBK-1:0]            rtg,
    output wire [NBK-1:0]            pgw,
    output wire [NBK-1:0]            xg,
    output wire [NBK-1:0]            m_re,
    output wire [NBK*LAW-1:0]        m_ra,
    output wire [NBK-1:0]            m_we,
    output wire [NBK*LAW-1:0]        m_wl,
    output wire [NBK*16-1:0]         m_wm,
    output wire [NSU*NSB-1:0]        m_sre,
    output wire [NSU*NSB*LAWS-1:0]   m_sra,
    output wire [NSB-1:0]            m_swe,
    output wire [NSB*LAWS-1:0]       m_swl,
    output wire [NSB*16-1:0]         m_swm,
    output wire [5:0]                rdc,
    output wire [NSU-1:0]            svc,
    output reg                       ovf
);
    localparam integer LP = (NPP > 1) ? $clog2(NPP) : 1;
    genvar g;
    // ---- reset relay, me_en replica ----
    reg rt;
    always @(posedge clk or negedge rst_n) if (!rst_n) rt <= 1'b0; else rt <= 1'b1;
    generate for (g = 0; g < NBK; g = g + 1) begin : g_rg
        (* keep = "true", dont_touch = "true" *) reg r;
        (* keep = "true", dont_touch = "true" *) reg mg;
        (* keep = "true", dont_touch = "true" *) reg pg;
        always @(posedge clk or negedge rst_n) if (!rst_n) r <= 1'b0; else r <= rt;
        always @(posedge clk) mg <= me_in;
        always @(posedge clk or negedge rt) if (!rt) pg <= 1'b0;
            else if (((MEREG != 0) ? mg : me_in) && !(MUT == 2 && g == 3)) pg <= pop;
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
    reg [2:0]         p_rqb;
    reg [NSU*NSB*LAWS-1:0] p_sra;
    reg [NSB*LAWS-1:0] p_swl;
    reg [NSB*16-1:0]   p_swm;
    always @(posedge clk) begin
        p_ra <= ra; p_wl <= wl; p_wm <= wm; p_rqb <= rqb;
        p_sra <= sra; p_swl <= swl; p_swm <= swm;
    end
    // ---- macro-side input relays (control + address + mask; the 512-b data words ride ot_qfd_vm_delay2_t) ----
    ot_hdc_delay #(.W(2*NBK + NSU*NSB + NSB), .D(NRI - 1), .RESET(1)) u_ic (.clk(clk), .rst_n(rt),
        .d({p_re, p_we, p_sre, p_swe}), .q({m_re, m_we, m_sre, m_swe}));
    ot_hdc_delay #(.W(2*NBK*LAW + NBK*16 + NSU*NSB*LAWS + NSB*LAWS + NSB*16), .D(NRI - 1)) u_id (
        .clk(clk), .rst_n(rt), .d({p_ra, p_wl, p_wm, p_sra, p_swl, p_swm}),
        .q({m_ra, m_wl, m_wm, m_sra, m_swl, m_swm}));
    // ---- tags ----
    wire          xvc;
    ot_hdc_delay #(.W(1), .D(NRI + NRX), .RESET(1)) u_xc (.clk(clk), .rst_n(rt), .d(p_xv), .q(xvc));
    wire          xpush;                // central push (FIFO occupancy / ovf), aligned with every xv_k
    ot_hdc_delay #(.W(1), .D(2 + NRI + NRX - ((MUT == 3) ? 1 : 0)), .RESET(1)) u_xp (.clk(clk), .rst_n(rt), .d(p_xv), .q(xpush));
    reg  [5:0]    rdq;                  // decoded row tag: {rq, rqb[2], onehot(rqb[1:0])}
    always @(posedge clk or negedge rt)
        if (!rt) rdq <= 6'd0;
        else rdq <= {p_rq, p_rqb[2], (p_rqb[1:0] == 2'd3), (p_rqb[1:0] == 2'd2), (p_rqb[1:0] == 2'd1), (p_rqb[1:0] == 2'd0)};
    ot_hdc_delay #(.W(6), .D(NRI + NRX - ((MUT == 1) ? 1 : 0)), .RESET(1)) u_rc (.clk(clk), .rst_n(rt), .d(rdq), .q(rdc));
    ot_hdc_delay #(.W(NSU), .D(NRI + NRS - ((MUT == 4) ? 1 : 0)), .RESET(1)) u_sc (.clk(clk), .rst_n(rt), .d(p_sv), .q(svc));
    // ---- x beat FIFO occupancy ----
    reg [LP:0]   cnt;
    wire popn = me_t && p_pop2;
    always @(posedge clk or negedge rt) begin
        if (!rt) begin cnt <= 0; ovf <= 1'b0; end
        else begin
            cnt <= cnt + (xpush ? 1'b1 : 1'b0) - (popn ? 1'b1 : 1'b0);
            if ((xpush && !popn && cnt == NPP) || (popn && cnt == 0)) ovf <= 1'b1;
        end
    end
    generate for (g = 0; g < NBK; g = g + 1) begin : g_xg
        (* keep = "true", dont_touch = "true" *) reg r;
        always @(posedge clk or negedge rtg[g]) if (!rtg[g]) r <= 1'b0; else r <= xvc;
        assign xg[g] = r;
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// ot_qfd_vm_rowrd_t: the row-read answer of one region = the body of the four ot_qfd_vm_row128_t, 16 FSW-32 slices
// (slice s = 4 * row-leaf + slice-in-leaf).  Each slice keeps its rs1 (6) / rs2 (2) select replicas, reset by
// rtg[s % 8]; two one-hot 4:1 rungs (one AND-OR level) into t1 (64), a 2:1 rung into ro (32, enable rs2[1]).
// 16 x (6 + 2 + 64 + 32) = 1,664 flops, one clock root.
//   Inputs: rdc lands on rs1 with no logic (launch: ot_qfd_vm_gctl_t u_rc last stage); rtg is the async clear of
//   rs1 / rs2 (launch: gctl_t g_rg.r); bx reaches t1 through the one AND-OR level -- NO pin register, exactly as
//   ot_qfd_vm_row128_t (launch: the ot_qfd_vm_delay1_t output register of the same bank; a pin register here would
//   add an edge to ro against the flat reference).  Output ro is a register.
//   MUT (miter only): 1 = row128_t's MUT (half select inverted); 2 = slice 5's 4:1 select replica one bank off.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_vm_rowrd_t #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire [7:0]    rtg,
    input  wire [5:0]    rdc,
    input  wire [4095:0] bx,
    output reg  [511:0]  ro
);
    genvar s;
    generate for (s = 0; s < 16; s = s + 1) begin : g_slice
        (* keep = "true", dont_touch = "true" *) reg [5:0] rs1;
        (* keep = "true", dont_touch = "true" *) reg [1:0] rs2;
        reg [63:0] t1, t1n;
        always @(posedge clk or negedge rtg[s % 8])
            if (!rtg[s % 8]) begin rs1 <= 0; rs2 <= 0; end
            else begin rs1 <= (MUT == 2 && s == 5) ? {rdc[5:4], rdc[2:0], rdc[3]} : rdc; rs2 <= rs1[5:4]; end
        integer h, i;
        always @* begin
            t1n = 0;
            for (h = 0; h < 2; h = h + 1) for (i = 0; i < 4; i = i + 1)
                t1n[h*32 +: 32] = t1n[h*32 +: 32] | (bx[(4*h + i)*512 + s*32 +: 32] & {32{rs1[i]}});
        end
        always @(posedge clk) t1 <= t1n;
        always @(posedge clk) if (rs2[1]) ro[s*32 +: 32] <= (rs2[0] ^ (MUT == 1)) ? t1[32 +: 32] : t1[0 +: 32];
    end endgenerate
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
