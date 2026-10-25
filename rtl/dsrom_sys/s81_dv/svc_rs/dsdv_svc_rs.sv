`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// S81U-SVC (2026-10-17, S81-DV p4h; S81U-SVC4: p4j): dsdv_svc_rs, the REGIONAL SERVICE SLICE (x16 on the 2 x 8 grid above
// the regional controllers dsfd_ctrl_rg2; sid = rsv_NN = 2 column + row, row 1 upper).  One master core dsdv_svc_rs_c;
// two port variants (p4b rule: no open or tied ports on a hardened slice):
//   dsdv_svc_rs_entry the p4j q / P.V ENTRY slices rsv_05 (W half, columns 0-3) and rsv_11 (E half, columns 4-7), under
//                     the slice-column voids: the host endpoint of the half -- job descriptor j / jd, q stream, host
//                     writes hw / hc, the half's fault and its P.V words (pv) come in / go out here (ot_s81_svc_job)
//   dsdv_svc_rs       the other 14 slices (incl. the chain roots rsv_07 / rsv_09, where the q.k fold sits): the stream
//                     arrives on the parent face, status and P.V leave on it
// p4j edges (svc_rs_tree.py): tq = dn stream parent -> child (incl. entry -> chain root 05 -> 07, 11 -> 09); tp = up +
// P.V return child -> parent; tr_07_05 / tr_09_11 = the return lane on the chain-root -> entry edge (`ro` on 07 / 09,
// `ri` on 05 / 11); the q.k partials entry -> root and the fold 07 <-> 09 ride the score exchange (svc_rs_embed.py).
// Content of a slice (one regional clock; every input lands in a flop, every output leaves one):
//   2 x dsfd_svc_pc    (closed, unchanged) the slice's two pseudo-channel faces, abutted to its dsfd_ctrl_rg2
//   dsdv_svc_att       the attention share of head-dim tile t (D = 32 engine, S = 1) + its 2-PC HBM service
//                      (window writer / reader, owned-row fetch, host sector writes, slot-addressed landing)
//   dsdv_svc_sx        the score exchange (q.k balanced 16-tile tree node, scatter, SM-head tap)
//   SE row assembler   the tap's 4 rows x 1 head a beat -> 16-score SE operand rows for the head's SM
//   ot_s81_su_sms     the slice's SM share (S81U-2 smq tap + head subtree; head = tile t): SE rows from the assembler,
//                      parameter / SO rows from SMJ frames, its write rows leave on the SM face
//   dn / up trees      neighbour-only broadcast of {q, hw} from the half's entry (upper row both ways, down each column)
//                      and the reduce of {all done, fault, host credits, host acks} back to it (svc_rs_tree.py role ROM:
//                      parent face, child faces, compiled GO delay gd); 5 cycles a hop (centre register, relay, out pin
//                      flop | in pin flop, relay), as the score exchange
//   hs status          the controller status face hs of the slice's ctrl_rg2 (dsfd_svc_hs's rule, fault half)
// Ports per lanes/S81U-SVC.md: HBM rq 2 x 341 / rk, wd, rv 2 / r_data 2 x 256, r_tag 2 x 17, r_beat 2 x 4 / hs 2;
// score lanes (gather 2,132 b + v, scatter 1,076 b + v) and stream lanes (dn 805 b, up 14 b) on N / E / S / W;
//   P.V return tree    ri / ro (513 b + v a face): the owner slices' P.V words travel child -> parent to the entry in
//                      compiled windows (att drain slot rs_pvslot); every hop 5 cycles; two valid words in one cycle or a
//                      word on a face that is not a child are sticky faults (never arbitrated)
// SM face w_v / w_a 14 / w_m 16 / w_d 512 + status.
// P PATH (TOK-S81-GAPS/SVCP 10-19, die gap G9; GO frame [47:32] PIO != 0, else legacy = PV frame from the host q):
//   the SM's SE e rows (16 FP32 exp of head g = tile, one per 16 positions) are rounded to BF16 (RNE, hdc_golden.to_bf16)
//   into pbuf (40 x 256 b) as they leave the SM.  From share cycle PIO the slice injects one P BEAT every 2 cycles into its
//   score-exchange leaf (beat k = rows 4k .. 4k + 3: head lane g = {P bf16, 16'h0}, every other lane +0, flags 0, row
//   mask = rows < T); the exchange's balanced gather adds x + 0 (exact), so the fold root rsv_09 sees all 16 heads x 4
//   rows a beat (rt).  The root packs the PV frame (header type 5, len ceil(T / 2), the job tag, then word w = rows 2w,
//   2w + 1 x 16 heads BF16) -- one word a cycle -- into its P.V return node: up to its entry rsv_11 (tr_09_11) and across
//   the centre (pout = W face, the abutted lane pr_09_07) to the W chain root rsv_07 (pin = E face), which forwards it to
//   rsv_05 (tr_07_05).  In the P window (share cycles [PIO, PVO)) an entry puts the return-tree words on its dn stream
//   instead of its pv pins: every slice of both halves receives the PV frame exactly as from the host (the owners'
//   p FIFO / static p feed are unchanged).  The tap beats of the P window do not enter the SE assembler.  Static: no
//   credit / ready; sticky fault (lf) on a P beat whose e row is not in pbuf at its cycle, a P beat colliding with an
//   engine score beat, a root beat off the 2-cycle cadence or with a non-BF16 / flagged lane, a pbuf overflow, an
//   injected word colliding with a host q word.  The SO (normalised o) rows go to the on-die SO target (S81-SMWIRE below).
// S81-SMWIRE (10-19): the face is INTERNAL -- the slice's SO target
//   dsdv_sm_so_target (4 SRAM 32x64, tools/s81_dv/sm_target/MODEL.md) takes it; its config comes from the job's SOT
//   q frame (dsdv_svc_sot, type 14), its gather beats leave as 3 words each on this slice's P.V return tree (dsdv_sm_gw,
//   merged with the P.V words: two words in one cycle is the existing fault), its fault joins the slice fault and its
//   booked retire joins the slice done (no END before every configured head retired cleanly).  The entry stamps
//   the booked gather window on the 48 spare bits of its pv lane (pv_x, dsdv_sm_gx).  The w_* ports stay on the core
//   for bench observation only (wrappers expose them under RS_OBS); SMT = 0 builds the pre-SMWIRE slice.
// Entry only: j 33 in, jd 2 out, q 515 in, hw 292 in, hc 9 out, fault out, P.V pv_v + pv_d 513 out.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_rs_c #(
    parameter bit ENTRY = 0,
    parameter integer MUT = 0,
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter bit SRAM_MACRO = 0,
    parameter integer PV_IDENTITY = 0, parameter bit SMT = 1,
    // S81-P9-FACE (10-23): face mask {SO, SI, GO, GI, RO, RI, UO, UI, DO, DI}, 4 b each, bit f = face N / E / S / W
    // (tools/s81_dv/svc_rs/svc_rs_faces.py from the role ROMs).  A face whose bit is 0 has no flop, relay or logic in
    // this core (generate): its input is never read, its output is constant 0 and the port variant
    // (dsdv_svc_rs_fv.sv) does not carry it.  All ones (default) = the pre-mask slice, unchanged.
    parameter logic [39:0] FM = {40{1'b1}},
    // S81/SVCG (2026-10-25, OWNER DECISION 12 / DEC12 FOLD 2-BEAT CONTRACT): F2B = 1 builds the slice for the die whose
    // fold-rung score gather (svc_2k <-> svc_2k+1) travels 2-beat on gh_o / gh_i (dsdv_svc_f2b_tx / _rx in dsdv_svc_sx.sv, +1 cycle a fold hop):
    // the role / drain-slot ROMs are the f2b ones (dsdv_svc_rs_roles_f2b.svh: compiled GO delay gd and P.V slots on
    // the f2b leaf offsets) and FH = {GI 4, GO 4} names this slice's 2-beat gather faces (= sx_fh(sid),
    // dsdv_svc_sx_f2b.svh; a strap sid whose fold faces differ is a sticky fault).  F2B = 0 / FH = 0: unchanged.
    parameter bit F2B = 0,
    parameter logic [7:0] FH = 8'h00
) (
    input  wire              ck,
    input  wire              rst,
    input  wire [3:0]        sid,
    // half host endpoint (ENTRY only)
    input  wire [32:0]       j,
    output wire [1:0]        jd,
    input  wire [514:0]      q,
    input  wire [291:0]      hw,
    output reg  [8:0]        hc,
    output wire              fault,
    output reg  [1:0]        st_rg,        // region status {fault, live} of the half's controllers (ENTRY only)
    // stream tree faces {W, S, E, N} = [3:0]
    input  wire [4*805-1:0]  dn_i,
    output wire [4*805-1:0]  dn_o,
    input  wire [4*16-1:0]   up_i,         // {rg fault, rg live, done, fault, cr 6, ack 6} a face
    output wire [4*16-1:0]   up_o,
    // P.V return tree faces {W, S, E, N}: {d 513, v}
    input  wire [4*514-1:0]  ri,
    output wire [4*514-1:0]  ro,
    // score lanes
    input  wire [3:0]        gi_v,
    input  wire [4*2132-1:0] gi_d,
    output wire [3:0]        go_v,
    output wire [4*2132-1:0] go_d,
    // S81/SVCG: 2-beat fold gather {beat, payload 1,067} a face (faces in FH; others: gh_o = 0, gh_i not read)
    input  wire [4*1068-1:0] gh_i,
    output wire [4*1068-1:0] gh_o,
    input  wire [3:0]        si_v,
    input  wire [4*1076-1:0] si_d,
    output wire [3:0]        so_v,
    output wire [4*1076-1:0] so_d,
    // HBM faces (2 PCs)
    output wire [2*341-1:0]  rq,
    input  wire [1:0]        rk, wd, rv,
    input  wire [2*256-1:0]  r_data,
    input  wire [2*17-1:0]   r_tag,
    input  wire [2*4-1:0]    r_beat,
    input  wire [1:0]        hs,
    // P.V out (ENTRY only: the half's return tree root)
    output reg               pv_v,
    output reg  [512:0]      pv_d,
    output wire [47:0]       pv_x,         // S81-SMWIRE: SO gather-word stamp of the pv word (ENTRY only, else 0)
    // SM face
    output wire              w_v,
    output wire [13:0]       w_a,
    output wire [15:0]       w_m,
    output wire [511:0]      w_d,
    output wire [11:0]       w_st              // {o_rjid 8, o_den, o_alive, o_fo, o_fu}
`ifdef RS_OBS
    // bench observation only (hierarchical bench build: the slice is a hier block): {rt_v, rt_d, se_v, se_d, a_fc, lf}
    , output wire [2678:0]   obs
`endif
);
`include "dsdv_svc_rs_roles.svh"
`include "dsdv_svc_rs_faces.svh"
`include "dsdv_svc_rs_roles_f2b.svh"
`include "dsdv_svc_sx_f2b.svh"
    localparam integer DW = 805, UW = 16;
    localparam logic [3:0] FM_DI = FM[3:0], FM_DO = FM[7:4], FM_UI = FM[11:8], FM_UO = FM[15:12], FM_RI = FM[19:16],
                           FM_RO = FM[23:20], FM_GI = FM[27:24], FM_GO = FM[31:28], FM_SI = FM[35:32], FM_SO = FM[39:36];
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
`ifdef OT_SVC_ALLQ
    wire [1:0] a_st;                                  // stack position (dsdv_svc_att: CFG [31:30] or the parameter ST)
    // RTLGAP-SO (10-21): CFG [54] ALLQ -> every slice drains its tile's P.V in its all-owner window (rs_pvslot_all)
    reg [21:0] role; reg [9:0] pvs; reg [7:0] pf; wire a_allq;
    always @(posedge ck or negedge rn) if (!rn) begin role <= '0; pvs <= 10'd1023; pf <= 8'h00; end
        else begin role <= F2B ? rs_role_f2b(sid) : rs_role(sid);
            pvs <= a_allq ? (F2B ? rs_pvslot_all_f2b(sid) : rs_pvslot_all(sid)) : {2'b00, (F2B ? rs_pvslot_f2b(a_st, sid) : rs_pvslot(a_st, sid))};
            pf <= rs_pface(sid); end
`else
    reg [21:0] role; reg [7:0] pvs, pf;
    wire [1:0] a_st;                                  // stack position (dsdv_svc_att: CFG [31:30] or the parameter ST)
    always @(posedge ck or negedge rn) if (!rn) begin role <= '0; pvs <= 8'd255; pf <= 8'h00; end
        else begin role <= F2B ? rs_role_f2b(sid) : rs_role(sid); pvs <= F2B ? rs_pvslot_f2b(a_st, sid) : rs_pvslot(a_st, sid);
            pf <= rs_pface(sid); end
`endif
    wire [3:0] tile = role[3:0], chm = role[7:4];
    wire [2:0] par = role[10:8];
`ifdef RS_MUT_GD
    wire [7:0] gd = role[21:14] + 8'(sid == 4'd0);    // bench negative control: one slice starts a cycle late
`else
    wire [7:0] gd = role[21:14];
`endif
    genvar f;

    // P path state used by the dn tree's entry mux (defined with the P path below)
    wire [15:0] pio, pvo_j, jcs;
    wire pon = pio != 16'd0;                          // the job's P path is compiled (GO [47:32])
    wire pwin = pon && jcs >= pio && jcs < pvo_j;     // P window: tap beats are P beats, return-tree words are P words
    localparam integer RW = 514;
    reg rm_v; reg [RW-2:0] rm_d; reg r_f;
    wire pinj = ENTRY && rm_v && pwin;                // entry: the return-tree word goes on the dn stream (q part)
    // ------------------------------------------------------------------ dn tree: faces in (pin flop + relay)
    wire [DW-1:0] dfi [0:3];
    generate for (f = 0; f < 4; f = f + 1) begin : g_di
      if (FM_DI[f]) begin : g_on
        reg [DW-1:0] p0, p1;
        always @(posedge ck or negedge rn) if (!rn) begin p0[0] <= 1'b0; p0[513] <= 1'b0; p1[0] <= 1'b0; p1[513] <= 1'b0; end
            else begin p0[0] <= dn_i[DW*f]; p0[513] <= dn_i[DW*f + 513]; p1[0] <= p0[0]; p1[513] <= p0[513]; end
        always @(posedge ck) begin p0[512:1] <= dn_i[DW*f + 1 +: 512]; p0[DW-1:514] <= dn_i[DW*f + 514 +: DW - 514];
                                   p1[512:1] <= p0[512:1]; p1[DW-1:514] <= p0[DW-1:514]; end
        assign dfi[f] = p1;
      end else begin : g_off
        assign dfi[f] = '0;                           // not a parent face of this variant: no pin flops
      end
    end endgenerate
    // entry: host pins (pin flop) -> job gate (same cycle) -> relay
    wire [DW-1:0] hst;
    wire [1:0] jdc; wire jf;
    reg [513:0] rad;                                  // synthetic END result word {data 512, v} (a0 tap of the job tile)
    generate if (ENTRY) begin : g_host
        reg [514:0] qp; reg [291:0] hp; reg [32:0] jp;
        always @(posedge ck or negedge rn) if (!rn) begin qp[0] <= 1'b0; hp[0] <= 1'b0; end
            else begin qp[0] <= q[0]; hp[0] <= hw[0]; end
        always @(posedge ck) begin qp[514:1] <= q[514:1]; hp[291:1] <= hw[291:1]; end
        wire [514:0] cq;
        ot_s81_svc_job #(.MUT(0)) u_job (.ck(ck), .rs_n(rn), .j_cmd(j), .j_dn(jdc), .q(qp), .core_q(cq),
            .ad({513'd0, rad[512:0]}), .xd({512'd0, 1'b0, 1'b1}), .od({512'd0, 1'b0, 1'b1}));
        // S81/H23 (10-24, COORD H3): the on-die SEL_IDS producer's entry leg.  Class-3 host-write words (the seqhost SEL
        // relay, dsdv_sh_selr) never go down the hw stream; dsdv_svc_selq turns each pair into one SEL_IDS q frame
        // (header + 1 payload word) injected on the q part in the compiled window (a q word from the job gate in the
        // same cycle = sticky fault, never arbitrated).
        wire sq_v, sq_f, hp_sel; wire [511:0] sq_d;
        dsdv_svc_selq u_selq (.ck(ck), .rn(rn), .hw(hp), .q_v(sq_v), .q_d(sq_d), .hw_sel(hp_sel), .cq_v(cq[0]), .fault(sq_f));
        reg [DW-1:0] r1;
        always @(posedge ck or negedge rn) if (!rn) begin r1[0] <= 1'b0; r1[513] <= 1'b0; end
            else begin r1[0] <= cq[0] | sq_v; r1[513] <= hp[0] && !hp_sel; end
        always @(posedge ck) begin r1[512:1] <= sq_v ? sq_d : cq[512:1]; r1[DW-1:514] <= hp[291:1]; end
        assign hst = r1;
        assign jf = sq_f;
    end else begin : g_nohost
        assign hst = '0; assign jdc = 2'b00; assign jf = 1'b0;
    end endgenerate
    // centre register
    reg [DW-1:0] cs;
    wire [DW-1:0] cin = (par == 3'd0) ? (pinj ? {hst[DW-1:513], rm_d[511:0], 1'b1} : hst) : dfi[par - 3'd1];
    always @(posedge ck or negedge rn) if (!rn) begin cs[0] <= 1'b0; cs[513] <= 1'b0; end
        else begin cs[0] <= cin[0]; cs[513] <= cin[513]; end
    always @(posedge ck) begin cs[512:1] <= cin[512:1]; cs[DW-1:514] <= cin[DW-1:514]; end
    // faces out (relay + pin flop) to the children
    generate for (f = 0; f < 4; f = f + 1) begin : g_do
      if (FM_DO[f]) begin : g_on
        reg [DW-1:0] o0, o1;
        always @(posedge ck or negedge rn) if (!rn) begin o0[0] <= 1'b0; o0[513] <= 1'b0; o1[0] <= 1'b0; o1[513] <= 1'b0; end
            else begin o0[0] <= cs[0] && chm[f]; o0[513] <= cs[513] && chm[f]; o1[0] <= o0[0]; o1[513] <= o0[513]; end
        always @(posedge ck) begin o0[512:1] <= cs[512:1]; o0[DW-1:514] <= cs[DW-1:514];
                                   o1[512:1] <= o0[512:1]; o1[DW-1:514] <= o0[DW-1:514]; end
        assign dn_o[DW*f +: DW] = o1;
      end else begin : g_off
        assign dn_o[DW*f +: DW] = '0;                 // not a child face of this variant (port absent)
      end
    end endgenerate
    // stray stream valid on a face that is not this slice's parent (static-schedule check)
    reg dstray;
    always @(posedge ck or negedge rn) if (!rn) dstray <= 1'b0;
        else for (int i = 0; i < 4; i++) if ((dfi[i][0] || dfi[i][513]) && par != 3'(i + 1)) dstray <= 1'b1;

    // ------------------------------------------------------------------ attention share + 2 PC faces
    wire [2*341-1:0] qrq; wire [1:0] qrk, qwd, qrv; wire [2*256-1:0] qr_data; wire [2*17-1:0] qr_tag; wire [2*4-1:0] qr_beat;
    generate for (f = 0; f < 2; f = f + 1) begin : g_pc
        dsfd_svc_pc u_pc (.ck(ck), .rst(rst), .qrq(qrq[341*f +: 341]), .rq(rq[341*f +: 341]), .rk(rk[f]), .qrk(qrk[f]),
            .wd(wd[f]), .qwd(qwd[f]), .rv(rv[f]), .r_data(r_data[256*f +: 256]), .r_tag(r_tag[17*f +: 17]),
            .r_beat(r_beat[4*f +: 4]), .qrv(qrv[f]), .qr_data(qr_data[256*f +: 256]), .qr_tag(qr_tag[17*f +: 17]),
            .qr_beat(qr_beat[4*f +: 4]));
    end endgenerate
    wire l_v; wire [2131:0] l_d; wire a_pv_v; wire [512:0] a_pv_d;
    wire sm_st, sm_rv, sm_rp; wire [3:0] sm_kind; wire [7:0] sm_jid; wire [2:0] sm_rj; wire [511:0] sm_rd;
    wire go, done; wire [9:0] tjob; wire [7:0] tagj; wire [1:0] hcr, hack; wire a_f; wire [31:0] a_fc;
    dsdv_svc_att #(.MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .PV_IDENTITY(PV_IDENTITY)) u_att (
        .clk(ck), .rst_n(rn), .sid(sid), .tile(tile), .gd(gd), .pvs(pvs), .root(ENTRY),
        .q_v(cs[0]), .q_d(cs[512:1]), .hw_v(cs[513]), .hw_d(cs[DW-1:514]),
        .qrq(qrq), .qrk(qrk), .qwd(qwd), .qrv(qrv), .qr_data(qr_data), .qr_tag(qr_tag), .qr_beat(qr_beat),
        .l_v(l_v), .l_d(l_d), .pv_ov(a_pv_v), .pv_od(a_pv_d),
        .sm_st(sm_st), .sm_kind(sm_kind), .sm_jid(sm_jid), .sm_rv(sm_rv), .sm_rp(sm_rp), .sm_rj(sm_rj), .sm_rd(sm_rd),
        .go_o(go), .tjob_o(tjob), .done(done), .tagj(tagj), .hcr(hcr), .hack(hack), .fault(a_f), .fault_code(a_fc),
`ifdef OT_SVC_ALLQ
        .pio_o(pio), .pvo_o(pvo_j), .jc_o(jcs), .st_o(a_st), .allq_o(a_allq));
`else
        .pio_o(pio), .pvo_o(pvo_j), .jc_o(jcs), .st_o(a_st));
`endif

    // ------------------------------------------------------------------ score exchange
    wire rt_v, t_v, x_f; wire [2131:0] rt_d; wire [19:0] t_tag; wire [127:0] t_y; wire [3:0] t_f;
    reg pl_v; reg [2131:0] pl_d;                     // P beat (registered), muxed onto the engine's score-beat port
`ifndef SVC_F2B_MUT
`define SVC_F2B_MUT 0
`endif
    dsdv_svc_sx #(.MUT(0), .FM_GI(FM_GI), .FM_GO(FM_GO), .FM_SI(FM_SI), .FM_SO(FM_SO), .FH_GO(FH[3:0]), .FH_GI(FH[7:4]),
                  .F2B_MUT(`SVC_F2B_MUT)) u_sx (.ck(ck), .rst(rst), .sid(sid), .l_v(l_v || pl_v), .l_d(pl_v ? pl_d : l_d),
        .gi_v(gi_v), .gi_d(gi_d), .go_v(go_v), .go_d(go_d), .gh_i(gh_i), .gh_o(gh_o), .si_v(si_v), .si_d(si_d), .so_v(so_v), .so_d(so_d),
        .rt_v(rt_v), .rt_d(rt_d), .t_v(t_v), .t_tag(t_tag), .t_y(t_y), .t_f(t_f), .fault(x_f));

    // ------------------------------------------------------------------ SE row assembler (tap -> 16-score SE rows)
    reg [511:0] se_acc, se_d; reg se_v, se_flag;
    wire [15:0] t_row = t_tag[19:4]; wire [3:0] t_m = t_tag[3:0];
    wire [2:0] t_n = 3'(t_m[0]) + 3'(t_m[1]) + 3'(t_m[2]) + 3'(t_m[3]);
    wire t_last = (t_row[3:2] == 2'd3) || (32'(t_row) + 32'(t_n) >= 32'(tjob));
    reg [511:0] se_nxt;
    always @(*) begin
        se_nxt = se_acc;
        for (int i = 0; i < 4; i++) if (t_m[i]) se_nxt[32 * (4 * t_row[3:2] + i) +: 32] = t_y[32*i +: 32];
            else se_nxt[32 * (4 * t_row[3:2] + i) +: 32] = 32'd0;
    end
    wire t_vs = t_v && !pwin;                         // P-window tap beats are P, not scores
    always @(posedge ck) begin
        if (t_vs) se_acc <= t_last ? 512'd0 : se_nxt;
        if (t_vs && t_last) se_d <= se_nxt;
    end
    always @(posedge ck or negedge rn)
        if (!rn) begin se_v <= 1'b0; se_flag <= 1'b0; end
        else begin
            se_v <= t_vs && t_last;
            if (go) se_flag <= 1'b0; else if (t_vs && |(t_f & t_m)) se_flag <= 1'b1;
        end

    // ------------------------------------------------------------------ SM head (S81U-2: smq tap + hardened smh)
    wire r_v = se_v || sm_rv;
    wire r_p = se_v ? 1'b0 : sm_rp;
    wire [2:0] r_j = se_v ? 3'd0 : sm_rj;
    wire [511:0] r_d = se_v ? se_d : sm_rd;
    reg rcol;
    always @(posedge ck or negedge rn) if (!rn) rcol <= 1'b0; else if (se_v && sm_rv) rcol <= 1'b1;
    wire o_fu, o_fo, o_alive, o_den; wire [7:0] o_rjid;
    // the slice's SM share (S81U-2 ot_s81_su_sms: smq tap + head subtree; -DSU_SMU_T = hardened regional clusters)
    ot_s81_su_sms u_sms (.clk(ck), .rst_in(rst), .cfg_g(tile), .j_st(sm_st), .j_kind(sm_kind), .j_jid(sm_jid),
        .r_v(r_v), .r_p(r_p), .r_j(r_j), .r_d(r_d),
        .w_v(w_v), .w_a(w_a), .w_m(w_m), .w_d(w_d), .o_fu(o_fu), .o_fo(o_fo), .o_alive(o_alive), .o_den(o_den),
        .o_rjid(o_rjid));
    assign w_st = {o_rjid, o_den, o_alive, o_fo, o_fu};

    // ------------------------------------------------------------------ P path (TOK-S81-GAPS/SVCP; header above)
    // (1) SE e rows -> BF16 -> pbuf (row oc = positions 16 oc .. 16 oc + 15 of head g)
    function automatic [15:0] bf16(input [31:0] x);
        reg [31:0] y;
`ifdef RS_MUT_P
        y = x;                                        // bench negative control: truncation instead of RNE
`else
        y = x + 32'h7fff + 32'(x[16]);
`endif
        bf16 = y[31:16];
    endfunction
    reg sek; reg [5:0] pb_n; reg [255:0] pbuf [0:39]; reg p_f;
    wire pb_w = w_v && sek && pb_n != 6'd40;
    always @(posedge ck) if (pb_w) for (int i = 0; i < 16; i++) pbuf[pb_n][16*i +: 16] <= bf16(w_d[32*i +: 32]);
    // (2) P beats into the score exchange from PIO, one every 2 cycles (aligned like the engine's score beats: gd)
    reg [7:0] pk;
    wire [9:0] nbt = (tjob + 10'd3) >> 2;
    wire pfire = pon && 10'(pk) < nbt && jcs == pio + {7'd0, pk, 1'b0};
    wire [9:0] prow = {pk, 2'b00};
    wire [255:0] prw = pbuf[pk[7:2]];
    always @(posedge ck) begin
        pl_d <= '0;
        pl_d[2131:2116] <= 16'(prow);
        for (int i = 0; i < 4; i++) if (32'(prow) + i < 32'(tjob)) begin
            pl_d[2112 + i] <= 1'b1;
            pl_d[64 + (16*i + 32'(tile))*32 +: 32] <= {prw[16*(4*pk[1:0] + i) +: 16], 16'h0000};
        end
    end
    // (3) fold root: rt P beats -> PV frame words (header, then A = rows 0 / 1, B = rows 2 / 3 of each beat)
    function automatic [1023:0] pbeat(input [2131:0] b);
        for (int jj = 0; jj < 4; jj++) for (int h = 0; h < 16; h++) pbeat[16*(16*jj + h) +: 16] = b[64 + 32*(16*jj + h) + 16 +: 16];
    endfunction
    function automatic bad_beat(input [2131:0] b);
        bad_beat = |b[63:0];
        for (int l = 0; l < 64; l++) if (b[64 + 32*l +: 16] != 16'h0000) bad_beat = 1'b1;
    endfunction
    wire [9:0] pn = (tjob + 10'd1) >> 1;              // words of the job's PV frame
    wire rtp = rt_v && pwin;
    reg [1:0] pph; reg phd; reg [9:0] pwc; reg pp_v; reg [512:0] pp_d; reg [1023:0] phold;
    always @(posedge ck or negedge rn)
        if (!rn) begin sek <= 1'b0; pb_n <= 6'd0; pk <= 8'd0; pl_v <= 1'b0; pph <= 2'd0; phd <= 1'b0; pwc <= 10'd0; pp_v <= 1'b0; p_f <= 1'b0; end
        else begin
            if (sm_st) begin sek <= sm_kind == 4'd4; if (sm_kind == 4'd4) pb_n <= 6'd0; end
            else if (pb_w) pb_n <= pb_n + 1'b1;
            if (w_v && sek && pb_n == 6'd40) p_f <= 1'b1;                          // more e rows than pbuf holds
            pl_v <= pfire;
            if (go) pk <= 8'd0; else if (pfire) pk <= pk + 1'b1;
            if (pfire && {2'b00, pb_n} <= {2'b00, pk[7:2]}) p_f <= 1'b1;             // the beat's e row is not in pbuf yet
            if (pl_v && l_v) p_f <= 1'b1;                                           // a P beat on an engine score beat
            pp_v <= 1'b0;
            if (go) begin pph <= 2'd0; phd <= 1'b0; pwc <= 10'd0; end
            else if (rtp) begin
                if (bad_beat(rt_d)) p_f <= 1'b1;                                    // a lane that is not an exact BF16
                if (!phd) begin pp_v <= 1'b1; phd <= 1'b1; pph <= 2'd1; end         // header
                else if (pph == 2'd2) begin pp_v <= pwc < pn; pwc <= pwc + 1'b1; pph <= 2'd1; end
                else p_f <= 1'b1;                                                   // off the 2-cycle cadence
            end else if (pph == 2'd1) begin pp_v <= pwc < pn; pwc <= pwc + 1'b1; pph <= 2'd2; end
            else if (pph == 2'd2) begin pp_v <= pwc < pn; pwc <= pwc + 1'b1; pph <= 2'd0; end
            if (pinj && hst[0]) p_f <= 1'b1;                                        // an injected word on a host q word
        end
    always @(posedge ck) begin
        if (rtp) phold <= pbeat(rt_d);
        if (rtp && !phd) pp_d <= {1'b0, 4'd5, 1'b0, 4'b0001, tagj, 3'd0, 12'(pn), 480'd0};
        else if (pph == 2'd1) pp_d <= {1'b0, phold[511:0]};
        else pp_d <= {1'b0, phold[1023:512]};
    end

    // ------------------------------------------------------------------ S81-SMWIRE: SO target, config source, gather words
    wire zt_cfg_v; wire [19:0] zt_owner; wire [7:0] zt_se, zt_so; wire [13:0] zt_obase; wire [15:0] zt_first, zt_last, zt_read, zt_ret;
    wire [1:0] zt_route; wire [15:0] zt_gw0, zt_gw1; wire [2:0] sot_fc;
    wire zt_gv, zt_ggrp, zt_ret_v, zt_ret_e, zt_f; wire [6:0] zt_gidx; wire [1023:0] zt_gd; wire [19:0] zt_gown, zt_rown;
    wire [11:0] zt_fc; wire gw_v, gw_f; wire [512:0] gw_d;
    reg so_pend;
    generate if (SMT) begin : g_smt
        dsdv_svc_sot u_sot (.clk(ck), .rst_n(rn), .tile(tile), .q_v(cs[0]), .q_d(cs[512:1]), .cfg_v(zt_cfg_v),
            .cfg_owner(zt_owner), .cfg_se_jid(zt_se), .cfg_so_jid(zt_so), .cfg_obase(zt_obase), .cfg_first(zt_first),
            .cfg_last(zt_last), .cfg_read(zt_read), .cfg_retire(zt_ret), .route(zt_route), .gw_first(zt_gw0), .gw_last(zt_gw1),
            .fault_code(sot_fc));
        dsdv_sm_so_target #(.HEAD(-1)) u_tgt (.clk(ck), .rst_n(rst), .head(tile), .cfg_v(zt_cfg_v), .cfg_owner(zt_owner),
            .cfg_se_jid(zt_se), .cfg_so_jid(zt_so), .cfg_obase(zt_obase), .cfg_first(zt_first), .cfg_last(zt_last),
            .cfg_read(zt_read), .cfg_retire(zt_ret), .op_st(sm_st), .op_kind(sm_kind), .op_jid(sm_jid),
            .w_v(w_v), .w_a(w_a), .w_m(w_m), .w_d(w_d), .w_st(w_st), .g_v(zt_gv), .g_idx(zt_gidx), .g_d(zt_gd),
            .g_owner(zt_gown), .g_group(zt_ggrp), .retired(zt_ret_v), .retire_error(zt_ret_e), .retire_owner(zt_rown),
            .fault(zt_f), .fault_code(zt_fc));
        dsdv_sm_gw u_gw (.clk(ck), .rst_n(rn), .head(tile), .g_v(zt_gv), .g_idx(zt_gidx), .g_d(zt_gd), .g_owner(zt_gown),
            .g_group(zt_ggrp), .gw_v(gw_v), .gw_d(gw_d), .fault(gw_f));
        // joined completion: a configured SO keeps the slice's done low until its booked retire is clean
        always @(posedge ck or negedge rn)
            if (!rn) so_pend <= 1'b0;
            else if (zt_cfg_v) so_pend <= 1'b1;
            else if (zt_ret_v && !zt_ret_e) so_pend <= 1'b0;
    end else begin : g_nosmt
        assign zt_cfg_v = 1'b0; assign zt_route = 2'd0; assign zt_gw0 = 16'd0; assign zt_gw1 = 16'd0; assign sot_fc = 3'd0;
        assign zt_f = 1'b0; assign zt_ret_v = 1'b0; assign zt_ret_e = 1'b0; assign gw_v = 1'b0; assign gw_f = 1'b0;
        assign gw_d = '0;
        always @(posedge ck) so_pend <= 1'b0;
    end endgenerate
`ifdef RS_OBS
    assign obs = {rt_v, rt_d, se_v, se_d, a_fc, lf};
`endif

    // ------------------------------------------------------------------ P.V return tree (child -> parent, compiled windows)
    wire [RW-1:0] rfi [0:3];
    wire [3:0] chr = chm | pf[7:4];                   // return-tree children + the P path's extra in face (rsv_07: E)
    generate for (f = 0; f < 4; f = f + 1) begin : g_ri
      if (FM_RI[f]) begin : g_on
        reg p0v, p1v; reg [RW-2:0] p0d, p1d;
        always @(posedge ck or negedge rn) if (!rn) begin p0v <= 1'b0; p1v <= 1'b0; end
            else begin p0v <= ri[RW*f]; p1v <= p0v; end
        always @(posedge ck) begin p0d <= ri[RW*f + 1 +: RW - 1]; p1d <= p0d; end
        assign rfi[f] = {p1d, p1v};
      end else begin : g_off
        assign rfi[f] = '0;                           // not a return-tree child / P-in face of this variant
      end
    end endgenerate
    always @(posedge ck or negedge rn)
        if (!rn) begin rm_v <= 1'b0; r_f <= 1'b0; end
        else begin
            reg [2:0] n;
            n = 3'(a_pv_v) + 3'(pp_v) + 3'(gw_v);             // ROOT4 merge: P path words and SO gather words share the tree
            for (int i = 0; i < 4; i++) begin
                if (rfi[i][0] && chr[i]) n = n + 1'b1;
                if (rfi[i][0] && !chr[i]) r_f <= 1'b1;                     // a P.V word on a face that is not a child
            end
            if (n > 3'd1) r_f <= 1'b1;                                      // two words in one cycle: a schedule fault
            rm_v <= n != 0;
        end
    // PVSO source fence: each tile carries proof of its OWN real SE denominator
    // in otherwise-unused P.V header bits. This is not compiler-asserted proof.
    wire[512:0]a_pv_stamped;
    dsdv_pv_den_stamp #(.ENABLE(PV_IDENTITY)) u_den_stamp(.clk(ck),.rst_n(rn),
      .cfg_v(zt_cfg_v),.cfg_owner(zt_owner),.cfg_se_jid(zt_se),
      .op_st(sm_st),.op_kind(sm_kind),.op_jid(sm_jid),.den(o_den),.result_jid(o_rjid),.error(o_fu||o_fo),
      .pv_d(a_pv_d),.stamped(a_pv_stamped));
    always @(posedge ck) begin
        rm_d <= gw_v ? gw_d : pp_v ? pp_d : a_pv_stamped;
        for (int i = 0; i < 4; i++) if (rfi[i][0] && chr[i]) rm_d <= rfi[i][RW-1:1];
    end
    generate for (f = 0; f < 4; f = f + 1) begin : g_ro
      if (FM_RO[f]) begin : g_on
        reg o0v, o1v; reg [RW-2:0] o0d, o1d;
        always @(posedge ck or negedge rn) if (!rn) begin o0v <= 1'b0; o1v <= 1'b0; end
            else begin o0v <= rm_v && (par == 3'(f + 1) || (pwin && pf[f])); o1v <= o0v; end   // + P out face (rsv_09: W)
`ifdef RS_MUT_RO
        // bench negative control: the chain root's result-out lane toward its entry (tr_07_05 / tr_09_11) flips a bit
        always @(posedge ck) begin o0d <= rm_d ^ {511'd0, (sid == 4'd7 || sid == 4'd9), 1'b0}; o1d <= o0d; end
`else
        always @(posedge ck) begin o0d <= rm_d; o1d <= o0d; end
`endif
        assign ro[RW*f +: RW] = {o1d, o1v};
      end else begin : g_off
        assign ro[RW*f +: RW] = '0;                   // not a return-tree parent / P-out face of this variant
      end
    end endgenerate
    always @(posedge ck or negedge rn) if (!rn) pv_v <= 1'b0; else pv_v <= ENTRY && rm_v && par == 3'd0 && !pwin;
    always @(posedge ck) pv_d <= rm_d;
    generate if (ENTRY && SMT) begin : g_gx
        dsdv_sm_gx u_gx (.clk(ck), .rst_n(rn), .cfg_v(zt_cfg_v), .route(zt_route), .gw_first(zt_gw0), .gw_last(zt_gw1),
            .w_v(rm_v && par == 3'd0), .pv_x(pv_x));
    end else begin : g_nogx
        assign pv_x = 48'd0;
    end endgenerate

    // ------------------------------------------------------------------ controller status, local fault
    // hs = {fault, live} per PC controller (dsfd_svc_hs's synchroniser and rule: a fault, or live dropping after it
    // rose, is a sticky slice fault; the job-done half of dsfd_svc_hs lives at the entry's job gate, not here)
    // S81-P9-FACE: a strap sid whose role needs a face this variant does not carry is a sticky fault (FM all ones: none)
    wire fm_f;
    generate if (FM != {40{1'b1}}) begin : g_fmchk
        reg fmf; reg [39:0] need;
        always @(posedge ck or negedge rn) if (!rn) begin need <= '0; fmf <= 1'b0; end
            else begin need <= rs_fmask(sid); if (|(need & ~FM)) fmf <= 1'b1; end
        assign fm_f = fmf;
    end else begin : g_nofmchk
        assign fm_f = 1'b0;
    end endgenerate
    // S81/SVCG: an F2B slice whose strap sid has other 2-beat fold faces than FH (sx_fh) is a sticky fault
    wire fh_f;
    generate if (F2B) begin : g_fhchk
        reg fhf; reg [7:0] needh;
        always @(posedge ck or negedge rn) if (!rn) begin needh <= FH; fhf <= 1'b0; end
            else begin needh <= sx_fh(sid); if (needh != FH) fhf <= 1'b1; end
        assign fh_f = fhf;
    end else begin : g_nofhchk
        assign fh_f = 1'b0;
    end endgenerate
    wire lf = a_f | x_f | rcol | o_fo | dstray | r_f | p_f | zt_f | (|sot_fc) | gw_f | (zt_ret_v && zt_ret_e) | fm_f | jf | fh_f;   // jf: S81/H23 SEL injection fault (entry)
    (* async_reg = "true" *) reg [1:0] hs0, hs1;
    reg hs_up, hs_hf, hs_f;
    always @(posedge ck or negedge rn)
        if (!rn) begin hs0 <= 2'b00; hs1 <= 2'b00; hs_up <= 1'b0; hs_hf <= 1'b0; hs_f <= 1'b0; end
        else begin
            hs0 <= hs; hs1 <= hs0;
            if (hs1[0]) hs_up <= 1'b1;
            if (hs1[1] || (hs_up && !hs1[0])) hs_hf <= 1'b1;
            hs_f <= lf | hs_hf;
        end

    // ------------------------------------------------------------------ up tree: {rg fault, rg live, done, fault, cr 6, ack 6}
    // (dsdv_svc_rs_up below; RTL-BUILD-S81 10-18: + the region status {fault, live} of the half's ctrl_rg2 controllers)
    wire [UW-1:0] uc;
    dsdv_svc_rs_up #(.UW(UW), .FM_UI(FM_UI), .FM_UO(FM_UO)) u_up (.ck(ck), .rn(rn), .chm(chm), .par(par), .done(done && !so_pend), .fl(hs_f), .hcr(hcr), .hack(hack),
        .hs_s(hs1), .up_i(up_i), .up_o(up_o), .uc(uc));

    // ------------------------------------------------------------------ entry: job done (END), host credits / acks, fault
    generate if (ENTRY) begin : g_rt
        reg dprev, flt; reg [7:0] crc;
        always @(posedge ck or negedge rn)
            if (!rn) begin dprev <= 1'b0; rad <= '0; crc <= 0; hc <= 0; flt <= 1'b0; end
            else begin
                dprev <= uc[13];
                rad[0] <= uc[13] && !dprev;
                rad[512:1] <= {4'd8, 1'b1, 4'd0, tagj, 3'd0, 12'd0, 480'd0};
                crc <= crc + 8'(uc[11:6]) - 8'(crc != 0);
                hc <= {2'b00, uc[5:0], crc != 0};
                if (uc[12]) flt <= 1'b1;
            end
        assign jd = {jdc[1] | flt, jdc[0]};
        assign fault = flt;
        // region status (residual row 6, the producer of dsdv_seq_host st_rg): the up-tree fold of every controller's
        // hs = {fault, live} in this half: fault = OR, live = AND (all controllers up); registered at the entry
`ifdef RS_MUT_ST
        always @(posedge ck or negedge rn) if (!rn) st_rg <= 2'b00; else st_rg <= {uc[15], hs1[0]};   // NEG CTRL: the entry's own live, children ignored
`else
        always @(posedge ck or negedge rn) if (!rn) st_rg <= 2'b00; else st_rg <= uc[15:14];
`endif
    end else begin : g_nrt
        always @(posedge ck) begin rad <= '0; hc <= '0; st_rg <= 2'b00; end
        assign jd = 2'b00; assign fault = 1'b0;
    end endgenerate
endmodule

// entry slices (rsv_05 W, rsv_11 E): the host endpoint of the half
// S81-SMWIRE (10-19): the SM face is internal (the SO target); w_* are bench observation ports (RS_OBS) only.  The
// entry adds pv_x[47:0] (the 48 spare bits of the 562-b pv lane: the SO gather-word stamp).
module dsdv_svc_rs_entry #(parameter integer MUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0,
                           parameter bit SRAM_MACRO = 0, parameter integer PV_IDENTITY = 0, parameter bit SMT = 1) (
    input  wire ck, rst, input wire [3:0] sid,
    input  wire [32:0] j, output wire [1:0] jd, input wire [514:0] q, input wire [291:0] hw, output wire [8:0] hc,
    output wire fault, output wire [1:0] st_rg,
    input  wire [4*805-1:0] dn_i, output wire [4*805-1:0] dn_o, input wire [4*16-1:0] up_i, output wire [4*16-1:0] up_o,
    input  wire [4*514-1:0] ri, output wire [4*514-1:0] ro,
    input  wire [3:0] gi_v, input wire [4*2132-1:0] gi_d, output wire [3:0] go_v, output wire [4*2132-1:0] go_d,
    input  wire [3:0] si_v, input wire [4*1076-1:0] si_d, output wire [3:0] so_v, output wire [4*1076-1:0] so_d,
    output wire [2*341-1:0] rq, input wire [1:0] rk, wd, rv, input wire [2*256-1:0] r_data, input wire [2*17-1:0] r_tag,
    input  wire [2*4-1:0] r_beat, input wire [1:0] hs,
    output wire pv_v, output wire [512:0] pv_d, output wire [47:0] pv_x
`ifdef RS_OBS
    , output wire w_v, output wire [13:0] w_a, output wire [15:0] w_m, output wire [511:0] w_d, output wire [11:0] w_st
    , output wire [2678:0] obs
`endif
);
    /*verilator hier_block*/
`ifndef RS_OBS
    wire w_v; wire [13:0] w_a; wire [15:0] w_m; wire [511:0] w_d; wire [11:0] w_st;
`endif
    dsdv_svc_rs_c #(.ENTRY(1), .MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .SMT(SMT), .PV_IDENTITY(PV_IDENTITY)) u (.ck(ck),
        .rst(rst), .sid(sid), .j(j), .jd(jd), .q(q), .hw(hw), .hc(hc), .fault(fault), .st_rg(st_rg), .dn_i(dn_i),
        .dn_o(dn_o), .up_i(up_i), .up_o(up_o), .ri(ri), .ro(ro), .gi_v(gi_v), .gi_d(gi_d), .go_v(go_v), .go_d(go_d), .gh_i(4272'd0), .gh_o(),
        .si_v(si_v), .si_d(si_d), .so_v(so_v), .so_d(so_d), .rq(rq), .rk(rk), .wd(wd), .rv(rv), .r_data(r_data),
        .r_tag(r_tag), .r_beat(r_beat), .hs(hs), .pv_v(pv_v), .pv_d(pv_d), .pv_x(pv_x), .w_v(w_v), .w_a(w_a), .w_m(w_m),
        .w_d(w_d), .w_st(w_st)
`ifdef RS_OBS
        , .obs(obs)
`endif
        );
endmodule

// the other 14 slices (incl. the chain roots rsv_07 / rsv_09: their P.V return lane toward the entry is `ro`)
module dsdv_svc_rs #(parameter integer MUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0,
                     parameter bit SRAM_MACRO = 0, parameter integer PV_IDENTITY = 0, parameter bit SMT = 1) (
    input  wire ck, rst, input wire [3:0] sid,
    input  wire [4*805-1:0] dn_i, output wire [4*805-1:0] dn_o, input wire [4*16-1:0] up_i, output wire [4*16-1:0] up_o,
    input  wire [4*514-1:0] ri, output wire [4*514-1:0] ro,
    input  wire [3:0] gi_v, input wire [4*2132-1:0] gi_d, output wire [3:0] go_v, output wire [4*2132-1:0] go_d,
    input  wire [3:0] si_v, input wire [4*1076-1:0] si_d, output wire [3:0] so_v, output wire [4*1076-1:0] so_d,
    output wire [2*341-1:0] rq, input wire [1:0] rk, wd, rv, input wire [2*256-1:0] r_data, input wire [2*17-1:0] r_tag,
    input  wire [2*4-1:0] r_beat, input wire [1:0] hs
`ifdef RS_OBS
    , output wire w_v, output wire [13:0] w_a, output wire [15:0] w_m, output wire [511:0] w_d, output wire [11:0] w_st
    , output wire [2678:0] obs
`endif
);
    /*verilator hier_block*/
`ifndef RS_OBS
    wire w_v; wire [13:0] w_a; wire [15:0] w_m; wire [511:0] w_d; wire [11:0] w_st;
`endif
    wire [1:0] jd; wire [8:0] hc; wire fault; wire pv_v; wire [512:0] pv_d; wire [47:0] pv_x; wire [1:0] st_rg;
    dsdv_svc_rs_c #(.ENTRY(0), .MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .SMT(SMT), .PV_IDENTITY(PV_IDENTITY)) u (.ck(ck),
        .rst(rst), .sid(sid), .j(33'd0), .jd(jd), .q(515'd0), .hw(292'd0), .hc(hc), .fault(fault), .st_rg(st_rg),
        .dn_i(dn_i), .dn_o(dn_o), .up_i(up_i), .up_o(up_o), .ri(ri), .ro(ro), .gi_v(gi_v), .gi_d(gi_d), .go_v(go_v),
        .go_d(go_d), .gh_i(4272'd0), .gh_o(), .si_v(si_v), .si_d(si_d), .so_v(so_v), .so_d(so_d), .rq(rq), .rk(rk), .wd(wd), .rv(rv),
        .r_data(r_data), .r_tag(r_tag), .r_beat(r_beat), .hs(hs), .pv_v(pv_v), .pv_d(pv_d), .pv_x(pv_x), .w_v(w_v),
        .w_a(w_a), .w_m(w_m), .w_d(w_d), .w_st(w_st)
`ifdef RS_OBS
        , .obs(obs)
`endif
        );
endmodule

// S81/SVCG (2026-10-25): the DEC12 die master of the 14 tree slices -- dsdv_svc_rs with the 2-beat fold gather
// (F2B = 1, FH = the slice's fold faces = sx_fh(sid), set per instance by the die / kit generator) and its gh_i / gh_o
// faces {beat, payload 1,067} on the fold rung (lane attnh__svc_A__svc_B).  dsdv_svc_rs is the pre-DEC12 master, kept
// unchanged for the dies / benches not yet re-bound.
module dsdv_svc_rs_f2b #(parameter integer MUT = 0, parameter integer DIE_ID = 0, parameter integer ST = 0,
                         parameter bit SRAM_MACRO = 0, parameter integer PV_IDENTITY = 0, parameter bit SMT = 1,
                         parameter logic [7:0] FH = 8'h00) (
    input  wire ck, rst, input wire [3:0] sid,
    input  wire [4*805-1:0] dn_i, output wire [4*805-1:0] dn_o, input wire [4*16-1:0] up_i, output wire [4*16-1:0] up_o,
    input  wire [4*514-1:0] ri, output wire [4*514-1:0] ro,
    input  wire [3:0] gi_v, input wire [4*2132-1:0] gi_d, output wire [3:0] go_v, output wire [4*2132-1:0] go_d,
    input  wire [4*1068-1:0] gh_i, output wire [4*1068-1:0] gh_o,
    input  wire [3:0] si_v, input wire [4*1076-1:0] si_d, output wire [3:0] so_v, output wire [4*1076-1:0] so_d,
    output wire [2*341-1:0] rq, input wire [1:0] rk, wd, rv, input wire [2*256-1:0] r_data, input wire [2*17-1:0] r_tag,
    input  wire [2*4-1:0] r_beat, input wire [1:0] hs
`ifdef RS_OBS
    , output wire w_v, output wire [13:0] w_a, output wire [15:0] w_m, output wire [511:0] w_d, output wire [11:0] w_st
    , output wire [2678:0] obs
`endif
);
    /*verilator hier_block*/
`ifndef RS_OBS
    wire w_v; wire [13:0] w_a; wire [15:0] w_m; wire [511:0] w_d; wire [11:0] w_st;
`endif
    wire [1:0] jd; wire [8:0] hc; wire fault; wire pv_v; wire [512:0] pv_d; wire [47:0] pv_x; wire [1:0] st_rg;
    dsdv_svc_rs_c #(.ENTRY(0), .MUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .SMT(SMT), .PV_IDENTITY(PV_IDENTITY),
                    .F2B(1), .FH(FH)) u (.ck(ck),
        .rst(rst), .sid(sid), .j(33'd0), .jd(jd), .q(515'd0), .hw(292'd0), .hc(hc), .fault(fault), .st_rg(st_rg),
        .dn_i(dn_i), .dn_o(dn_o), .up_i(up_i), .up_o(up_o), .ri(ri), .ro(ro), .gi_v(gi_v), .gi_d(gi_d), .go_v(go_v),
        .go_d(go_d), .gh_i(gh_i), .gh_o(gh_o), .si_v(si_v), .si_d(si_d), .so_v(so_v), .so_d(so_d), .rq(rq), .rk(rk), .wd(wd), .rv(rv),
        .r_data(r_data), .r_tag(r_tag), .r_beat(r_beat), .hs(hs), .pv_v(pv_v), .pv_d(pv_d), .pv_x(pv_x), .w_v(w_v),
        .w_a(w_a), .w_m(w_m), .w_d(w_d), .w_st(w_st)
`ifdef RS_OBS
        , .obs(obs)
`endif
        );
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// dsdv_svc_rs_up (RTL-BUILD-S81 10-18, factored out of dsdv_svc_rs_c unchanged for bits [13:0]): the up tree node of one
// service slice.  Faces {W, S, E, N} in: pin flop + relay; the fold over the child faces (role ROM chm): done = AND,
// fault = OR, host credits / acks = sum; out on the parent face: register + pin flop (5 cycles a hop with the parent's
// in flops).  Bits [15:14] = the region status of the controllers below and at this slice: fault = OR of hs fault,
// live = AND of hs live (hs_s = this slice's synchronised ctrl_rg2 hs = {fault, live}).  No flow control.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_rs_up #(parameter integer UW = 16, parameter integer UPMUT = 0,   // UPMUT: bench negative control only
                       parameter logic [3:0] FM_UI = 4'hf, FM_UO = 4'hf) (   // S81-P9-FACE face masks (child in / parent out)
    input  wire            ck,
    input  wire            rn,
    input  wire [3:0]      chm,
    input  wire [2:0]      par,
    input  wire            done,
    input  wire            fl,
    input  wire [1:0]      hcr,
    input  wire [1:0]      hack,
    input  wire [1:0]      hs_s,
    input  wire [4*UW-1:0] up_i,
    output wire [4*UW-1:0] up_o,
    output reg  [UW-1:0]   uc
);
    wire [UW-1:0] ufi [0:3];
    genvar f;
    generate for (f = 0; f < 4; f = f + 1) begin : g_ui
      if (FM_UI[f]) begin : g_on
        reg [UW-1:0] p0, p1;
        always @(posedge ck or negedge rn) if (!rn) begin p0 <= '0; p1 <= '0; end
            else begin p0 <= up_i[UW*f +: UW]; p1 <= p0; end
        assign ufi[f] = p1;
      end else begin : g_off
        assign ufi[f] = '0;                           // not a child face of this variant
      end
    end endgenerate
    always @(posedge ck or negedge rn)
        if (!rn) uc <= '0;
        else begin
            reg dn_all, fl_, rgf, rgl; reg [5:0] c6, a6;
            dn_all = done; fl_ = fl; c6 = 6'(hcr); a6 = 6'(hack); rgf = hs_s[1]; rgl = hs_s[0];
            for (int i = 0; i < 4; i++) if (chm[i]) begin
                dn_all = dn_all & ufi[i][13]; fl_ = fl_ | ufi[i][12]; c6 = c6 + ufi[i][11:6]; a6 = a6 + ufi[i][5:0];
                rgf = rgf | ufi[i][15]; rgl = (UPMUT == 1) ? (rgl | ufi[i][14]) : (rgl & ufi[i][14]);
            end
            uc <= {rgf, rgl, dn_all, fl_, c6, a6};
        end
    generate for (f = 0; f < 4; f = f + 1) begin : g_uo
      if (FM_UO[f]) begin : g_on
        reg [UW-1:0] o0, o1;
        always @(posedge ck or negedge rn) if (!rn) begin o0 <= '0; o1 <= '0; end
            else begin o0 <= (par == 3'(f + 1)) ? uc : '0; o1 <= o0; end
        assign up_o[UW*f +: UW] = o1;
      end else begin : g_off
        assign up_o[UW*f +: UW] = '0;                 // not the parent face of this variant
      end
    end endgenerate
endmodule

// The same source-owned SE fence instantiated on every real service tile.
// Observe the current SE's denominator-low phase before accepting its completion;
// a stale high denominator with a reused jid cannot authorize the next token.
module dsdv_pv_den_stamp #(parameter integer ENABLE=0)(
 input wire clk,rst_n,cfg_v,input wire[19:0]cfg_owner,input wire[7:0]cfg_se_jid,
 input wire op_st,input wire[3:0]op_kind,input wire[7:0]op_jid,
 input wire den,input wire[7:0]result_jid,input wire error,
 input wire[512:0]pv_d,output wire[512:0]stamped
);
 generate if(ENABLE==0)begin:g_disabled assign stamped=pv_d;end else begin:g_enabled
 reg seen,live,saw_low;reg[19:0]owner;reg[7:0]jid;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin seen<=0;live<=0;saw_low<=0;owner<=0;jid<=0;end
  else if(cfg_v)begin seen<=0;live<=0;saw_low<=0;owner<=cfg_owner;jid<=cfg_se_jid;end
  else if(op_st)begin
   if(op_kind==4'd4)begin seen<=0;live<=op_jid==jid;saw_low<=0;end
   else live<=0;
  end else if(live)begin
   if(!den)saw_low<=1;
   if(den && saw_low && result_jid==jid && !error)seen<=1;
  end
 end
 assign stamped=pv_d[512]?((pv_d & ~(513'h1ff<<120)) | (513'({jid,seen && owner==pv_d[91:72]})<<120)):pv_d;
 end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// S81/H23 (2026-10-24, COORD H3, attn.gather): dsdv_svc_selq, the svc ENTRY leg of the on-die SEL_IDS producer.
// bk_sel's encoder (dsdv_bk_selids) sends every index word of the final top-k (16 ranks) as 2 relay beats; the seqhost
// (dsdv_sh_selr) puts each on this half's host-write port as a class-3 word {cls 3, we 0, addr, d 256, v}:
//   addr[0] part (0: ranks s_first + 0..7, 1: + 8..15), addr[10:1] s_first, addr[15:11] s_cnt (1..16), addr[19:16] mask,
//   d[32 e +: 32] = the id of rank s_first + 8 part + e (21-b compressed position, zero-extended; 0 past s_cnt).
// Part 0 -> a SEL_IDS header q word {type 7, mask, len 1, [19:10] s_cnt, [9:0] s_first} in the SAME cycle (combinational
// from the hw pin flop, registered by the entry's r1 stage as every q word); part 1 (the next word) -> the payload q word
// {d1, d0}.  So one index word = 2 consecutive q words on the entry's dn stream, in the window the compiler reserved
// (no q word from the job gate there).  Sticky faults (never arbitrated): a q word from the job gate in a relay cycle,
// part 1 without part 0 or with other meta, part 0 while part 1 is owed, s_cnt 0 or > 16.  Reset: the pending bit and
// the fault only.  MUT (bench only): 1 = payload halves swapped.
// ---------------------------------------------------------------------------------------------------------------------
module dsdv_svc_selq #(parameter integer MUT = 0) (
    input  wire         ck, rn,
    input  wire [291:0] hw,            // the entry's hw pin flop
    input  wire         cq_v,          // a q word from the job gate this cycle
    output wire         hw_sel,        // this hw word is a SEL relay word (kept off the hw stream)
    output wire         q_v,
    output wire [511:0] q_d,
    output reg          fault
);
    wire [31:0] a = hw[288:257];
    assign hw_sel = hw[0] && hw[291:290] == 2'b11;
    reg pend; reg [255:0] d0; reg [18:0] m0;
    wire p0 = hw_sel && !a[0], p1 = hw_sel && a[0];
    wire [511:0] hdr = {4'd7, 1'b0, a[19:16], 8'd0, 3'd0, 12'd1, 480'd0} | {492'd0, 5'd0, a[15:11], a[10:1]};
    assign q_v = hw_sel;
    assign q_d = p0 ? hdr : ((MUT == 1) ? {d0, hw[256:1]} : {hw[256:1], d0});
    always @(posedge ck) if (p0) begin d0 <= hw[256:1]; m0 <= a[19:1]; end
    always @(posedge ck or negedge rn)
        if (!rn) begin pend <= 1'b0; fault <= 1'b0; end
        else begin
            pend <= p0;
            if (hw_sel && cq_v) fault <= 1'b1;                                  // relay word in a job-gate q cycle
            if (p1 && (!pend || a[19:1] != m0)) fault <= 1'b1;                  // part 1 without its part 0
            if (p0 && pend) fault <= 1'b1;                                      // part 0 while part 1 is owed
            if (pend && !p1) fault <= 1'b1;                                     // part 1 not on the next edge
            if (p0 && (a[15:11] == 5'd0 || a[15:11] > 5'd16)) fault <= 1'b1;
        end
endmodule
