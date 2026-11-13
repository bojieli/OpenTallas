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
    parameter integer CUTMUT = 0
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
    always @(posedge clk) begin
        cq_v <= q_v; cq_d <= q_d; chw_v <= hw_v; chw_d <= hw_d;
    end
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
    dsdv_svc_att #(.MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .PFIFO(PFIFO), .PVQ(PVQ), .DQ(DQ), .SRAM_MACRO(SRAM_MACRO),
                   .PV_IDENTITY(PV_IDENTITY), .ROWX(ROWX), .XN(XN), .H(H)) u_a (
        .clk(clk), .rst_n(rst_n), .sid(sid), .tile(tile), .gd(gd), .pvs(pvs), .root(root),
        .q_v(cq_v), .q_d(cq_d),
        .hw_v((CUTMUT == 1) ? hw_v : chw_v), .hw_d((CUTMUT == 1) ? hw_d : chw_d),
        .qrq(qrq), .qrk(qrk), .qwd(qwd), .qrv(qrv), .qr_data(qr_data), .qr_tag(qr_tag), .qr_beat(qr_beat),
        .l_v(a_l_v), .l_d(a_l_d), .pv_ov(a_pv_ov), .pv_od(a_pv_od),
        .sm_st(a_sm_st), .sm_kind(a_sm_kind), .sm_jid(a_sm_jid), .sm_rv(a_sm_rv), .sm_rp(a_sm_rp), .sm_rj(a_sm_rj),
        .sm_rd(a_sm_rd), .go_o(a_go), .tjob_o(a_tjob), .done(a_done), .tagj(a_tagj), .hcr(a_hcr), .hack(a_hack),
        .fault(a_fault), .fault_code(a_fc), .pio_o(a_pio), .pvo_o(a_pvo), .jc_o(a_jc), .st_o(a_st)
`ifdef OT_SVC_ALLQ
        , .allq_o(a_allq)
`endif
        , .hb_o(a_hb));
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
endmodule
