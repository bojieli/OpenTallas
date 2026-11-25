`timescale 1ns/1ps
// S81 svc SERVICE CUT (HARD-S81-SVC-1 11-13, COORD ruling 08:3x: 4 lane bands + one cut of the service logic at the
// u_att boundary): dsdv_svc_att behind a registered boundary, so the die plan can make the attention share its own
// partition S_att (asbuilt part prefix ...u_att; the engine bands sit below it at u_att.u_a.u_eng.g_tr[k].g_xb.u_band).
// Same ports and parameters as dsdv_svc_att (dsdv_svc_rs_c selects this module with -DOT_SVC_ATTCUT).
//   in : the dn stream lanes q_* / hw_* are captured by one register stage here (+1);
//   out: every output lane to the slice leaves through one more register stage (+1): scores l_*, P.V pv_o*, the SM
//        job / row lanes sm_*, go / tjob / done / tagj, the up credits hcr / hack, fault + code and the schedule taps
//        pio / pvo / jc / st / allq / hb;
//   the two HBM page-cache lanes (qrq out; qrk / qwd / qrv / qr_* in) are NOT registered: the 2 dsfd_svc_pc stages
//        belong to S_att (plan part prefix), their request / ack protocol stays as built.
// The wrapper registers carry no reset (plain relays): streams are idle while rst_n is low (boot holds it >= 64 clk).
// Effect: the attention share runs exactly 1 edge later against the dn stream and its lanes reach the slice 2 edges
// later; the HBM requests leave 1 edge later.  Bookkeeping = pin-cycle deltas of the S_att part: in +1, out +1.
// CUT_D (SVC-CUT-DEPTH, FABLE-UNC-S81-SVC 11-23; default 1 = this file as built; dsdv_svc_rs_c passes 1 + `OT_SVC_CUT_KA): uniform
// cut depth on the att side.  CUT_D - 1 plain relay stages on EVERY registered in-lane ahead of the capture register and on
// EVERY registered out-lane ahead of the output relay, so the lock-step is kept.  The HBM page-cache lanes stay unregistered.
// CUT_D = 0 (SVC-CUT0-RSV09, S81-SVC-J9 11-24): no register on any lane, u_att = dsdv_svc_att in a pass-through shell (the
// hi row then runs in step with the plain-core lo row); CUTMUT has no effect at CUT_D 0.
// CUTMUT (bench only, 0 in every kit): 1 = hw lane not captured, 2 = pv_o lane not registered, 3 = SM row lane
// (sm_rv / sm_rp / sm_rj / sm_rd) not registered.
module dsdv_svc_att_cut #(
    parameter integer MUT = 0,
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter integer PFIFO = 512,
    parameter integer PVQ = 8,
    parameter integer DQ = 8,
    parameter bit SRAM_MACRO = 0,
    parameter integer PV_IDENTITY = 0,
    parameter integer ROWX = 0,
    parameter integer XN = 128,
    parameter integer H = 16,
    parameter integer CUTMUT = 0,
    parameter integer CUT_D = 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire [3:0]           sid,
    input  wire [3:0]           tile,
    input  wire [7:0]           gd,
`ifdef OT_SVC_ALLQ
    input  wire [9:0]           pvs,
`else
    input  wire [7:0]           pvs,
`endif
    input  wire                 root,
    input  wire                 q_v,
    input  wire [511:0]         q_d,
    input  wire                 hw_v,
    input  wire [290:0]         hw_d,
    output wire [2*341-1:0]     qrq,
    input  wire [1:0]           qrk,
    input  wire [1:0]           qwd,
    input  wire [1:0]           qrv,
    input  wire [2*256-1:0]     qr_data,
    input  wire [2*17-1:0]      qr_tag,
    input  wire [2*4-1:0]       qr_beat,
    output reg                  l_v,
    output reg  [H*132+19:0]    l_d,
    output wire                 pv_ov,
    output wire [512:0]         pv_od,
    output reg                  sm_st,
    output reg  [3:0]           sm_kind,
    output reg  [7:0]           sm_jid,
    output wire                 sm_rv,
    output wire                 sm_rp,
    output wire [2:0]           sm_rj,
    output wire [511:0]         sm_rd,
    output reg                  go_o,
    output reg  [9:0]           tjob_o,
    output reg                  done,
    output reg  [7:0]           tagj,
    output reg  [1:0]           hcr,
    output reg  [1:0]           hack,
    output reg                  fault,
    output reg  [31:0]          fault_code,
    output reg  [15:0]          pio_o,
    output reg  [15:0]          pvo_o,
    output reg  [15:0]          jc_o,
    output reg  [1:0]           st_o
`ifdef OT_SVC_ALLQ
    , output reg                allq_o
`endif
    , output reg                hb_o
);
    // ---- input capture (dn stream lanes)
    reg         cq_v, chw_v;
    reg [511:0] cq_d;
    reg [290:0] chw_d;
    localparam integer CIW = 1 + 512 + 1 + 291;
    localparam integer CDV = (CUT_D < 1) ? 1 : CUT_D;   // vector depth (CUT_D 0 uses the stage-0 slice only)
    wire [CIW-1:0] cut_in_x = {q_v, q_d, hw_v, hw_d};
    wire [CIW-1:0] cut_in_s;
    // plain flop vectors per stage (no array: nothing a memory pass could collect); CUT_D = 1 elaborates no stage
    wire [CDV*CIW-1:0] cut_in_c;
    assign cut_in_c[CIW-1:0] = cut_in_x;
    genvar cut_gi;
    generate
        for (cut_gi = 1; cut_gi < CUT_D; cut_gi = cut_gi + 1) begin : g_cin
            reg [CIW-1:0] st;
            always @(posedge clk) st <= cut_in_c[(cut_gi-1)*CIW +: CIW];
            assign cut_in_c[cut_gi*CIW +: CIW] = st;
        end
    endgenerate
    assign cut_in_s = cut_in_c[(CDV-1)*CIW +: CIW];
    wire         s_q_v, s_hw_v;
    wire [511:0] s_q_d;
    wire [290:0] s_hw_d;
    assign {s_q_v, s_q_d, s_hw_v, s_hw_d} = cut_in_s;
    generate if (CUT_D == 0) begin : g_cap0
        always @* begin
            cq_v = s_q_v; cq_d = s_q_d; chw_v = s_hw_v; chw_d = s_hw_d;
        end
    end else begin : g_cap
        always @(posedge clk) begin
            cq_v <= s_q_v; cq_d <= s_q_d; chw_v <= s_hw_v; chw_d <= s_hw_d;
        end
    end endgenerate
    wire         a_l_v, a_pv_ov, a_sm_st, a_sm_rv, a_sm_rp, a_go, a_done, a_fault, a_hb;
    wire [H*132+19:0] a_l_d;
    wire [512:0] a_pv_od;
    wire [3:0]   a_sm_kind;
    wire [7:0]   a_sm_jid, a_tagj;
    wire [2:0]   a_sm_rj;
    wire [511:0] a_sm_rd;
    wire [9:0]   a_tjob;
    wire [1:0]   a_hcr, a_hack, a_st;
    wire [31:0]  a_fc;
    wire [15:0]  a_pio, a_pvo, a_jc;
`ifdef OT_SVC_ALLQ
    wire         a_allq;
`endif
    wire         b_l_v, b_pv_ov, b_sm_st, b_sm_rv, b_sm_rp, b_go, b_done, b_fault, b_hb;
    wire [H*132+19:0] b_l_d;
    wire [512:0] b_pv_od;
    wire [3:0]   b_sm_kind;
    wire [7:0]   b_sm_jid, b_tagj;
    wire [2:0]   b_sm_rj;
    wire [511:0] b_sm_rd;
    wire [9:0]   b_tjob;
    wire [1:0]   b_hcr, b_hack, b_st;
    wire [31:0]  b_fc;
    wire [15:0]  b_pio, b_pvo, b_jc;
`ifdef OT_SVC_ALLQ
    wire         b_allq;
`endif
    dsdv_svc_att #(.MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .PFIFO(PFIFO), .PVQ(PVQ), .DQ(DQ), .SRAM_MACRO(SRAM_MACRO),
                   .PV_IDENTITY(PV_IDENTITY), .ROWX(ROWX), .XN(XN), .H(H)) u_a (
        .clk(clk), .rst_n(rst_n), .sid(sid), .tile(tile), .gd(gd), .pvs(pvs), .root(root),
        .q_v(cq_v), .q_d(cq_d),
        .hw_v((CUTMUT == 1) ? hw_v : chw_v), .hw_d((CUTMUT == 1) ? hw_d : chw_d),
        .qrq(qrq), .qrk(qrk), .qwd(qwd), .qrv(qrv), .qr_data(qr_data), .qr_tag(qr_tag), .qr_beat(qr_beat),
        .l_v(b_l_v), .l_d(b_l_d), .pv_ov(b_pv_ov), .pv_od(b_pv_od),
        .sm_st(b_sm_st), .sm_kind(b_sm_kind), .sm_jid(b_sm_jid), .sm_rv(b_sm_rv), .sm_rp(b_sm_rp), .sm_rj(b_sm_rj),
        .sm_rd(b_sm_rd), .go_o(b_go), .tjob_o(b_tjob), .done(b_done), .tagj(b_tagj), .hcr(b_hcr), .hack(b_hack),
        .fault(b_fault), .fault_code(b_fc), .pio_o(b_pio), .pvo_o(b_pvo), .jc_o(b_jc), .st_o(b_st)
`ifdef OT_SVC_ALLQ
        , .allq_o(b_allq)
`endif
        , .hb_o(b_hb));
`ifdef OT_SVC_ALLQ
    localparam integer COW = (H*132+20) + 513 + 4 + 8 + 8 + 3 + 512 + 10 + 2 + 2 + 2 + 32 + 16 + 16 + 16 + 9 + 1;
    wire [COW-1:0] cut_out_x = {b_allq, b_l_v, b_l_d, b_pv_ov, b_pv_od, b_sm_st, b_sm_kind, b_sm_jid, b_sm_rv, b_sm_rp, b_sm_rj, b_sm_rd, b_go, b_tjob, b_done, b_tagj, b_hcr, b_hack, b_fault, b_fc, b_pio, b_pvo, b_jc, b_st, b_hb};
    wire [COW-1:0] cut_out_s;
    assign {a_allq, a_l_v, a_l_d, a_pv_ov, a_pv_od, a_sm_st, a_sm_kind, a_sm_jid, a_sm_rv, a_sm_rp, a_sm_rj, a_sm_rd, a_go, a_tjob, a_done, a_tagj, a_hcr, a_hack, a_fault, a_fc, a_pio, a_pvo, a_jc, a_st, a_hb} = cut_out_s;
`else
    localparam integer COW = (H*132+20) + 513 + 4 + 8 + 8 + 3 + 512 + 10 + 2 + 2 + 2 + 32 + 16 + 16 + 16 + 9;
    wire [COW-1:0] cut_out_x = {b_l_v, b_l_d, b_pv_ov, b_pv_od, b_sm_st, b_sm_kind, b_sm_jid, b_sm_rv, b_sm_rp, b_sm_rj, b_sm_rd, b_go, b_tjob, b_done, b_tagj, b_hcr, b_hack, b_fault, b_fc, b_pio, b_pvo, b_jc, b_st, b_hb};
    wire [COW-1:0] cut_out_s;
    assign {a_l_v, a_l_d, a_pv_ov, a_pv_od, a_sm_st, a_sm_kind, a_sm_jid, a_sm_rv, a_sm_rp, a_sm_rj, a_sm_rd, a_go, a_tjob, a_done, a_tagj, a_hcr, a_hack, a_fault, a_fc, a_pio, a_pvo, a_jc, a_st, a_hb} = cut_out_s;
`endif
    wire [CDV*COW-1:0] cut_out_c;
    assign cut_out_c[COW-1:0] = cut_out_x;
    generate
        for (cut_gi = 1; cut_gi < CUT_D; cut_gi = cut_gi + 1) begin : g_cout
            reg [COW-1:0] st;
            always @(posedge clk) st <= cut_out_c[(cut_gi-1)*COW +: COW];
            assign cut_out_c[cut_gi*COW +: COW] = st;
        end
    endgenerate
    assign cut_out_s = cut_out_c[(CDV-1)*COW +: COW];
    // ---- output relays
    reg         r_pv_ov;
    reg [512:0] r_pv_od;
    assign pv_ov = (CUTMUT == 2) ? a_pv_ov : r_pv_ov;
    assign pv_od = (CUTMUT == 2) ? a_pv_od : r_pv_od;
    reg         r_sm_rv, r_sm_rp;
    reg [2:0]   r_sm_rj;
    reg [511:0] r_sm_rd;
    assign sm_rv = (CUTMUT == 3) ? a_sm_rv : r_sm_rv;
    assign sm_rp = (CUTMUT == 3) ? a_sm_rp : r_sm_rp;
    assign sm_rj = (CUTMUT == 3) ? a_sm_rj : r_sm_rj;
    assign sm_rd = (CUTMUT == 3) ? a_sm_rd : r_sm_rd;
    generate if (CUT_D == 0) begin : g_out0
        always @* begin
            l_v = a_l_v; l_d = a_l_d; r_pv_ov = a_pv_ov; r_pv_od = a_pv_od;
            sm_st = a_sm_st; sm_kind = a_sm_kind; sm_jid = a_sm_jid;
            r_sm_rv = a_sm_rv; r_sm_rp = a_sm_rp; r_sm_rj = a_sm_rj; r_sm_rd = a_sm_rd;
            go_o = a_go; tjob_o = a_tjob; done = a_done; tagj = a_tagj; hcr = a_hcr; hack = a_hack;
            fault = a_fault; fault_code = a_fc; pio_o = a_pio; pvo_o = a_pvo; jc_o = a_jc; st_o = a_st;
`ifdef OT_SVC_ALLQ
            allq_o = a_allq;
`endif
            hb_o = a_hb;
        end
    end else begin : g_out
        always @(posedge clk) begin
            l_v <= a_l_v; l_d <= a_l_d; r_pv_ov <= a_pv_ov; r_pv_od <= a_pv_od;
            sm_st <= a_sm_st; sm_kind <= a_sm_kind; sm_jid <= a_sm_jid;
            r_sm_rv <= a_sm_rv; r_sm_rp <= a_sm_rp; r_sm_rj <= a_sm_rj; r_sm_rd <= a_sm_rd;
            go_o <= a_go; tjob_o <= a_tjob; done <= a_done; tagj <= a_tagj; hcr <= a_hcr; hack <= a_hack;
            fault <= a_fault; fault_code <= a_fc; pio_o <= a_pio; pvo_o <= a_pvo; jc_o <= a_jc; st_o <= a_st;
`ifdef OT_SVC_ALLQ
            allq_o <= a_allq;
`endif
            hb_o <= a_hb;
        end
    end endgenerate
endmodule
