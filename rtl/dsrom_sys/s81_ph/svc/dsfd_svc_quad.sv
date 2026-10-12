`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// dsfd_svc_quad (CLAUDE s81die-1011/ctrl svch, 2026-10-11): the hardened QUADRANT tile of the S81 scan-service slab
// dsfd_svc_c (composition physical/s81_ph_views/svc/composition.json: 4 quadrants 2,125 x 756 um side by side,
// quadrant g above its PC tiles u_pc[8g .. 8g+7]; N face q in, od / a0 out to the IO hub; S face abutted to the PC
// tiles).  Replaces the flat ot_s81_svcq_slab (one clock tree / one arbiter over the whole 8.5-mm slab).
// Content of quadrant g (one local clock tree; every pin a flop):
//   ot_s81_svch_attq   a QUARTER of the attention: head_dim split, dims 128 g .. 128 g + 127 (exact, see its header)
//   8 x dsfd_svch_pcs  the quadrant's own pipelined arbiter, one hardened slice per PC (above u_pc[8g + i]; A idx /
//                      B window / G routed requesters) + ot_s81_svch_ghub (G request steering / response collection)
//   lane endpoints     A lanes from dsfd_svc_idx, B / G / window / fetched-row lanes from the home (quadrant 2)
//   q.k combine        Q1: (Q0 + Q1);  Q2: (Q2 + Q3) and the root ((Q0 + Q1) + (Q2 + Q3)) -- ot_s81_svch_comb
//   QID 2 only         ot_s81_svch_home (window source, owned-row fetch, G router, result emitter on od / a0)
// Seams (all latency-insensitive, sender credits = receiver depth DEP(nr) = 2 nr + 8 for nr relay stages, every
// incoming valid-only lane signal captured by a pin flop): NRH0/1/3 = relay stages between quadrant 2 and quadrant
// 0/1/3, NRI = between dsfd_svc_idx and this quadrant, NRS = between neighbouring quadrants' score ports.  Port
// groups own_* are this quadrant's ends; h_* are the home's ends (used in quadrant 2 only; index 2 of every h_*
// bundle is internal there).  Ports a quadrant does not use are driven 0 / ignored.
// Mutant SVCH_MUT_ORDER (gate: must FAIL): the root becomes ((Q0 + Q1) + Q2) + Q3.
// ---------------------------------------------------------------------------------------------------------------
module dsfd_svc_quad #(
    parameter integer QID = 0,
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter integer NRH0 = 9, NRH1 = 5, NRH3 = 5,
    parameter integer NRI = 3,
    parameter integer NRS = 5,
    parameter integer NG = 13,
    parameter integer DRA = 64,
    parameter integer DRB = 64,
    parameter bit SRAM_MACRO = 0,
    // port widths that exist only where used (home bundles in quadrant 2, score ports per tree position)
    parameter integer HB = (QID == 2) ? 24 : 1,          // remote PCs 0..15, 24..31 (index k: PC k < 16 ? k : k + 8)
    parameter integer HQ = (QID == 2) ? 3 : 1,           // remote quadrants 0, 1, 3 (index r: quadrant r < 2 ? r : 3)
    parameter integer OBN = (QID == 2) ? 1 : 8,          // own home-lane ports (unused in quadrant 2: internal)
    parameter integer OGQ = (QID == 2) ? 1 : 344,
    parameter integer OGR = (QID == 2) ? 1 : 276,
    parameter integer OGW = (QID == 2) ? 1 : NG,
    parameter integer OWB = (QID == 2) ? 1 : 4228,
    parameter integer OFB = (QID == 2) ? 1 : 607,
    parameter integer OPV = (QID == 2) ? 1 : 513,
    parameter integer SOW = (QID != 2) ? 2132 : 1,
    parameter integer SAW = (QID == 1 || QID == 2) ? 2132 : 1,
    parameter integer SBW = (QID == 2) ? 2132 : 1,
    parameter integer HHW = (QID == 2) ? 291 : 1,
    parameter integer HHC = (QID == 2) ? 9 : 1
) (
    input  wire [0:0]          ck,
    input  wire [0:0]          rst,
    input  wire [514:0]        q,
    output wire [0:0]          od_v,  output wire [511:0] od_d,  input wire [0:0] od_r,
    output wire [0:0]          a0_v,  output wire [511:0] a0_d,  input wire [0:0] a0_r,
    // PC tiles (N faces of u_pc[8 QID .. 8 QID + 7])
    output wire [8*341-1:0]    qrq,
    input  wire [7:0]          qrk, qwd, qrv,
    input  wire [8*256-1:0]    qr_data,
    input  wire [8*17-1:0]     qr_tag,
    input  wire [8*4-1:0]      qr_beat,
    // own A lanes (index reader)
    input  wire [7:0]          aq_v,  input wire [8*50-1:0]  aq_d,  output wire [7:0] aq_c,
    output wire [7:0]          ar_v,  output wire [8*276-1:0] ar_d, input wire [7:0] ar_c,
    // own B lanes (home window stream)
    input  wire [OBN-1:0]      bq_v,  input wire [OBN*46-1:0]  bq_d,  output wire [OBN-1:0] bq_c,
    output wire [OBN-1:0]      br_v,  output wire [OBN*272-1:0] br_d, input wire [OBN-1:0] br_c,
    // own G lane (home router) + write completions
    input  wire [0:0]          gq_v,  input wire [OGQ-1:0] gq_d,  output wire [0:0] gq_c,
    output wire [0:0]          gr_v,  output wire [OGR-1:0] gr_d, input wire [0:0] gr_c,
    output wire [OGW-1:0]      gwd,
    // own window-beat lane / fetched-row broadcast
    input  wire [0:0]          wb_v,  input wire [OWB-1:0] wb_d, output wire [0:0] wb_c,
    input  wire [0:0]          fb_v,  input wire [OFB-1:0] fb_d,
    // score lanes: out (Q0 -> Q1, Q1 -> Q2, Q3 -> Q2), in a (Q1 <- Q0, Q2 <- Q1), in b (Q2 <- Q3)
    output wire [0:0]          so_v,  output wire [SOW-1:0] so_d, input wire [0:0] so_c,
    input  wire [0:0]          sa_v,  input wire [SAW-1:0] sa_d,  output wire [0:0] sa_c,
    input  wire [0:0]          sb_v,  input wire [SBW-1:0] sb_d,  output wire [0:0] sb_c,
    // p.v lane out (to the home) and fault out
    output wire [0:0]          po_v,  output wire [OPV-1:0] po_d,  input wire [0:0] po_c,
    output wire [0:0]          fo,
    // home ends (QID 2)
    output wire [HB-1:0]       h_bq_v, output wire [HB*46-1:0] h_bq_d, input wire [HB-1:0] h_bq_c,
    input  wire [HB-1:0]       h_br_v, input wire [HB*272-1:0] h_br_d, output wire [HB-1:0] h_br_c,
    output wire [HQ-1:0]       h_gq_v, output wire [HQ*344-1:0] h_gq_d, input wire [HQ-1:0] h_gq_c,
    input  wire [HQ-1:0]       h_gr_v, input wire [HQ*276-1:0] h_gr_d, output wire [HQ-1:0] h_gr_c,
    input  wire [HQ*NG-1:0]    h_gwd,
    output wire [HQ-1:0]       h_wb_v, output wire [HQ*4228-1:0] h_wb_d, input wire [HQ-1:0] h_wb_c,
    output wire [HQ-1:0]       h_fb_v, output wire [HQ*607-1:0] h_fb_d,
    input  wire [HQ-1:0]       h_pv_v, input wire [HQ*513-1:0] h_pv_d, output wire [HQ-1:0] h_pv_c,
    input  wire [HQ-1:0]       h_flt,
    // per-stack host write face (quadrant 2: the home's G port 12): hw without v / {ack 8, cr}
    input  wire [0:0]          h_hw_v, input wire [HHW-1:0] h_hw_d,
    output wire [HHC-1:0]      h_hc
);
    function automatic integer dep(input integer nr); dep = 2 * nr + 8; endfunction
    function automatic integer nrh(input integer d); nrh = (d == 0) ? NRH0 : (d == 1) ? NRH1 : (d == 3) ? NRH3 : 0; endfunction
    localparam integer DH = dep(nrh(QID));                // this quadrant's lanes to / from the home
    localparam bit HOME = (QID == 2);
`ifdef SVCQ_ENG_FG3
    localparam integer FX = 3, F12 = 0;
`else
    localparam integer FX = 5, F12 = 1;
`endif
    wire clk = ck[0];
    reg [1:0] rs;
    always @(posedge clk or negedge rst[0]) if (!rst[0]) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    (* keep *) reg [3:0] rn_c;                          // regional reset copies (control flops only)
    always @(posedge clk or negedge rst[0]) if (!rst[0]) rn_c <= 4'b0; else rn_c <= {4{rs[1]}};
    wire rn_a = rn_c[0], rn_p = rn_c[1], rn_l = rn_c[2], rn_h = rn_c[3];
    genvar gp, gd;

    // ---------------- pin flops on the incoming valid-only lane signals ----------------
    
    reg gq_vq, gr_cq, wb_vq, fb_vq, so_cq, sa_vq, sb_vq, po_cq;
    reg [343:0] gq_dq; reg [4227:0] wb_dq; reg [606:0] fb_dq; reg [2131:0] sa_dq, sb_dq;
    reg qv_q; reg [513:0] qd_q;
    always @(posedge clk or negedge rn_l)
        if (!rn_l) begin gq_vq <= 0; gr_cq <= 0; wb_vq <= 0; fb_vq <= 0;
                         so_cq <= 0; sa_vq <= 0; sb_vq <= 0; po_cq <= 0; qv_q <= 0; end
        else begin gq_vq <= gq_v[0]; gr_cq <= gr_c[0];
                   wb_vq <= wb_v[0]; fb_vq <= fb_v[0]; so_cq <= so_c[0]; sa_vq <= sa_v[0]; sb_vq <= sb_v[0];
                   po_cq <= po_c[0]; qv_q <= q[0]; end
    always @(posedge clk) begin
        gq_dq <= gq_d; wb_dq <= wb_d; fb_dq <= fb_d; sa_dq <= 2132'(sa_d); sb_dq <= 2132'(sb_d);
        qd_q <= q[514:1];
    end
    reg in_fault;
    always @(posedge clk or negedge rn_l)
        if (!rn_l) in_fault <= 1'b0; else if (qd_q[513] || (qv_q && !qd_q[512])) in_fault <= 1'b1;

    // ---------------- attention quarter ----------------
    wire w_v, w_ready; wire [4227:0] w_d;
    wire l_v; wire [606:0] l_d;
    wire s_v, s_r; wire [2131:0] s_d;
    wire p_v, p_r; wire [512:0] p_d;
    wire go, wj_v; wire [7:0] tagj, wcount, wj_count; wire [20:0] posj, npub, wj_first; wire [9:0] userj, nsel, wj_user;
    wire [29:0] rbase, rcount; wire [511:0] held; wire [9:0] own_count, own_idx, own_rank; wire own_done; wire [20:0] own_gid;
    wire at_fault; wire [15:0] at_fc;
    ot_s81_svch_attq #(.QID(QID), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO)) u_att (
        .clk(clk), .rst_n(rn_a), .q_v(qv_q), .q_d(qd_q[511:0]),
        .w_v(w_v), .w_ready(w_ready), .w_m(w_d[4227:4224]), .w_sl(w_d[4223:0]),
        .l_v(l_v), .l_rank(l_d[606:597]), .l_gid(l_d[596:576]), .l_sl(l_d[575:0]),
        .s_v(s_v), .s_r(s_r), .s_d(s_d), .p_ov(p_v), .p_or(p_r), .p_od(p_d),
        .go(go), .tagj(tagj), .posj(posj), .userj(userj), .wcount(wcount), .nsel(nsel), .rbase(rbase), .rcount(rcount),
        .npub(npub), .wj_v(wj_v), .wj_user(wj_user), .wj_first(wj_first), .wj_count(wj_count), .held(held),
        .own_count(own_count), .own_done(own_done), .own_idx(own_idx), .own_rank(own_rank), .own_gid(own_gid),
        .fault(at_fault), .fault_code(at_fc));

    // window beats / fetched rows: from the own lane, or (home) from the home's internal lane 2
    wire wl_v; wire [4227:0] wl_d; wire wl_c; wire w_ovf;
    wire [3:0] hw_v; wire [4*4228-1:0] hw_d; wire [3:0] hw_c;
    wire [3:0] hf_v; wire [4*607-1:0] hf_d;
    assign wl_v = HOME ? hw_v[2] : wb_vq;
    assign wl_d = HOME ? hw_d[2*4228 +: 4228] : wb_dq;
    ot_s81_svch_crx #(.W(4228), .DEPTH(DH)) u_wrx (.clk(clk), .rst_n(rn_l), .i_v(wl_v), .i_d(wl_d), .o_v(w_v),
        .o_r(w_ready), .o_d(w_d), .c_out(wl_c), .ovf(w_ovf));
    assign wb_c[0] = HOME ? 1'b0 : wl_c;
    reg fl_v; reg [606:0] fl_d;
    always @(posedge clk or negedge rn_l) if (!rn_l) fl_v <= 1'b0; else fl_v <= HOME ? hf_v[2] : fb_vq;
    always @(posedge clk) fl_d <= HOME ? hf_d[2*607 +: 607] : fb_dq;
    assign l_v = fl_v; assign l_d = fl_d;

    // ---------------- PC service: 8 hardened per-PC slices + the G hub ----------------
    wire [7:0] bi_v; wire [8*46-1:0] bi_d; wire [7:0] bi_c;
    wire [7:0] pbr_v; wire [8*272-1:0] pbr_d; wire [7:0] pbr_c;
    wire g_v, g_r; wire [343:0] g_d; wire g_ovf;
    wire go_v, go_r; wire [275:0] go_d;
    // home loop for its own PCs: home B lanes 16..23 straight into this quadrant's slices
    wire [31:0] hbq_v; wire [32*46-1:0] hbq_d; wire [31:0] hbq_c;
    wire [31:0] hbr_v; wire [32*272-1:0] hbr_d; wire [31:0] hbr_c;
    assign bi_v = HOME ? hbq_v[16 +: 8] : 8'(bq_v);
    assign bi_d = HOME ? hbq_d[16*46 +: 8*46] : (8*46)'(bq_d);
    assign bq_c = HOME ? '0 : bi_c;
    assign pbr_c = HOME ? hbr_c[16 +: 8] : 8'(br_c);
    wire [3:0] hgq_v; wire [4*344-1:0] hgq_d; wire [3:0] hgq_c;
    wire [3:0] hgr_v; wire [4*276-1:0] hgr_d; wire [3:0] hgr_c;
    wire gin_v = HOME ? hgq_v[2] : gq_vq;
    wire [343:0] gin_d = HOME ? hgq_d[2*344 +: 344] : gq_dq;
    wire gin_c;
    ot_s81_svch_crx #(.W(344), .DEPTH(DH)) u_grx (.clk(clk), .rst_n(rn_l), .i_v(gin_v), .i_d(gin_d), .o_v(g_v), .o_r(g_r),
        .o_d(g_d), .c_out(gin_c), .ovf(g_ovf));
    assign gq_c[0] = HOME ? 1'b0 : gin_c;
    wire [7:0] sq_v, sq_c, sr_v, sr_c, s_fo; wire [8*344-1:0] sq_d; wire [8*276-1:0] sr_d; wire [8*NG-1:0] swd;
    wire [NG-1:0] gwd_i; wire hub_f;
    ot_s81_svch_ghub #(.QID(QID), .NG(NG), .DG(dep(0))) u_ghub (.clk(clk), .rst_n(rn_p), .i_v(g_v), .i_r(g_r), .i_d(g_d),
        .sq_v(sq_v), .sq_d(sq_d), .sq_c(sq_c), .sr_v(sr_v), .sr_d(sr_d), .sr_c(sr_c), .swd(swd),
        .o_v(go_v), .o_r(go_r), .o_d(go_d), .gwd(gwd_i), .fault(hub_f));
    generate for (gp = 0; gp < 8; gp = gp + 1) begin : g_pcs
        dsfd_svch_pcs #(.QID(QID), .PCL(gp), .NG(NG), .DA(dep(NRI)), .DB(DH), .DG(dep(0)), .DRA(DRA), .DRB(DRB)) u_s (
            .ck(ck), .rst(rst),
            .qrq(qrq[341*gp +: 341]), .qrk(qrk[gp]), .qwd(qwd[gp]), .qrv(qrv[gp]), .qr_data(qr_data[256*gp +: 256]),
            .qr_tag(qr_tag[17*gp +: 17]), .qr_beat(qr_beat[4*gp +: 4]),
            .aq_v(aq_v[gp]), .aq_d(aq_d[50*gp +: 50]), .aq_c(aq_c[gp]), .ar_v(ar_v[gp]), .ar_d(ar_d[276*gp +: 276]), .ar_c(ar_c[gp]),
            .bq_v(bi_v[gp]), .bq_d(bi_d[46*gp +: 46]), .bq_c(bi_c[gp]), .br_v(pbr_v[gp]), .br_d(pbr_d[272*gp +: 272]), .br_c(pbr_c[gp]),
            .gq_v(sq_v[gp]), .gq_d(sq_d[344*gp +: 344]), .gq_c(sq_c[gp]), .gr_v(sr_v[gp]), .gr_d(sr_d[276*gp +: 276]), .gr_c(sr_c[gp]),
            .gwd(swd[NG*gp +: NG]), .fo(s_fo[gp]));
    end endgenerate
    wire pc_fault = hub_f | (|s_fo);
    assign br_v = HOME ? '0 : pbr_v;
    assign br_d = pbr_d;
    assign gwd = HOME ? '0 : gwd_i;
    // G responses out (credit lane to the home's receiver for this quadrant)
    wire gro_v; wire [275:0] gro_d;
    ot_s81_svch_ctx #(.W(276), .DEPTH(DH)) u_gtx (.clk(clk), .rst_n(rn_l), .i_v(go_v), .i_r(go_r), .i_d(go_d),
        .o_v(gro_v), .o_d(gro_d), .c_in(HOME ? hgr_c[2] : gr_cq));
    assign gr_v[0] = HOME ? 1'b0 : gro_v;
    assign gr_d = gro_d;

    // ---------------- q.k combine levels ----------------
    wire sc_v, sc_r; wire [2131:0] sc_d;                 // root (home)
    wire c_fault;
    generate if (QID == 0 || QID == 3) begin : g_leafq
        ot_s81_svch_ctx #(.W(2132), .DEPTH(dep(NRS))) u_stx (.clk(clk), .rst_n(rn_l), .i_v(s_v), .i_r(s_r), .i_d(s_d),
            .o_v(so_v[0]), .o_d(so_d), .c_in(so_cq));
        assign sa_c[0] = 1'b0; assign sb_c[0] = 1'b0; assign c_fault = 1'b0;
        assign sc_v = 1'b0; assign sc_d = '0;
    end else if (QID == 1) begin : g_q01
        wire x_v, x_r; wire [2131:0] x_d; wire xa_v, xa_r; wire [2131:0] xa_d; wire ovf, cf;
        ot_s81_svch_crx #(.W(2132), .DEPTH(dep(NRS))) u_sarx (.clk(clk), .rst_n(rn_l), .i_v(sa_vq), .i_d(sa_dq),
            .o_v(xa_v), .o_r(xa_r), .o_d(xa_d), .c_out(sa_c[0]), .ovf(ovf));
        ot_s81_svch_comb #(.FX(FX), .F12(F12)) u_c01 (.clk(clk), .rst_n(rn_l), .a_v(xa_v), .a_r(xa_r), .a_d(xa_d),
            .b_v(s_v), .b_r(s_r), .b_d(s_d), .o_v(x_v), .o_r(x_r), .o_d(x_d), .fault(cf));
        ot_s81_svch_ctx #(.W(2132), .DEPTH(dep(NRS))) u_stx (.clk(clk), .rst_n(rn_l), .i_v(x_v), .i_r(x_r), .i_d(x_d),
            .o_v(so_v[0]), .o_d(so_d), .c_in(so_cq));
        assign sb_c[0] = 1'b0; assign c_fault = ovf | cf;
        assign sc_v = 1'b0; assign sc_d = '0;
    end else begin : g_root
        wire xa_v, xa_r, xb_v, xb_r, m_v, m_r; wire [2131:0] xa_d, xb_d, m_d; wire ova, ovb, c1, c2;
        ot_s81_svch_crx #(.W(2132), .DEPTH(dep(NRS))) u_sarx (.clk(clk), .rst_n(rn_l), .i_v(sa_vq), .i_d(sa_dq),
            .o_v(xa_v), .o_r(xa_r), .o_d(xa_d), .c_out(sa_c[0]), .ovf(ova));
        ot_s81_svch_crx #(.W(2132), .DEPTH(dep(NRS))) u_sbrx (.clk(clk), .rst_n(rn_l), .i_v(sb_vq), .i_d(sb_dq),
            .o_v(xb_v), .o_r(xb_r), .o_d(xb_d), .c_out(sb_c[0]), .ovf(ovb));
`ifdef SVCH_MUT_ORDER
        ot_s81_svch_comb #(.FX(FX), .F12(F12)) u_c23 (.clk(clk), .rst_n(rn_l), .a_v(xa_v), .a_r(xa_r), .a_d(xa_d),
            .b_v(s_v), .b_r(s_r), .b_d(s_d), .o_v(m_v), .o_r(m_r), .o_d(m_d), .fault(c1));
        ot_s81_svch_comb #(.FX(FX), .F12(F12)) u_root (.clk(clk), .rst_n(rn_l), .a_v(m_v), .a_r(m_r), .a_d(m_d),
            .b_v(xb_v), .b_r(xb_r), .b_d(xb_d), .o_v(sc_v), .o_r(sc_r), .o_d(sc_d), .fault(c2));
`else
        ot_s81_svch_comb #(.FX(FX), .F12(F12)) u_c23 (.clk(clk), .rst_n(rn_l), .a_v(s_v), .a_r(s_r), .a_d(s_d),
            .b_v(xb_v), .b_r(xb_r), .b_d(xb_d), .o_v(m_v), .o_r(m_r), .o_d(m_d), .fault(c1));
        ot_s81_svch_comb #(.FX(FX), .F12(F12)) u_root (.clk(clk), .rst_n(rn_l), .a_v(xa_v), .a_r(xa_r), .a_d(xa_d),
            .b_v(m_v), .b_r(m_r), .b_d(m_d), .o_v(sc_v), .o_r(sc_r), .o_d(sc_d), .fault(c2));
`endif
        assign so_v[0] = 1'b0; assign so_d = '0; assign c_fault = ova | ovb | c1 | c2;
    end endgenerate

    // ---------------- p.v lane ----------------
    wire hpv_v, hpv_r; wire [512:0] hpv_d;              // home's p.v input (quadrant ST's words)
    wire pv_ovf;
    generate if (HOME && ST == 2) begin : g_pvl
        assign hpv_v = p_v; assign p_r = hpv_r; assign hpv_d = p_d;
        assign po_v[0] = 1'b0; assign po_d = '0; assign pv_ovf = 1'b0;
    end else begin : g_pvt
        ot_s81_svch_ctx #(.W(513), .DEPTH(DH)) u_ptx (.clk(clk), .rst_n(rn_l), .i_v(p_v), .i_r(p_r), .i_d(p_d),
            .o_v(po_v[0]), .o_d(po_d), .c_in(po_cq));
        if (HOME) begin : g_prx
            reg pv_vq; reg [512:0] pv_dq;
            localparam integer RS = (ST < 2) ? ST : 2;
            always @(posedge clk or negedge rn_l) if (!rn_l) pv_vq <= 1'b0; else pv_vq <= h_pv_v[RS];
            always @(posedge clk) pv_dq <= h_pv_d[RS*513 +: 513];
            wire c;
            ot_s81_svch_crx #(.W(513), .DEPTH(dep(nrh(ST)))) u_prx (.clk(clk), .rst_n(rn_l), .i_v(pv_vq), .i_d(pv_dq),
                .o_v(hpv_v), .o_r(hpv_r), .o_d(hpv_d), .c_out(c), .ovf(pv_ovf));
            assign h_pv_c = 3'(c) << RS;
        end else begin : g_nprx
            assign hpv_v = 1'b0; assign hpv_d = '0; assign pv_ovf = 1'b0;
        end
    end endgenerate

    // ---------------- faults ----------------
    reg flt;
    wire local_fault = in_fault | at_fault | pc_fault | c_fault | w_ovf | g_ovf | pv_ovf;
    always @(posedge clk or negedge rn_l) if (!rn_l) flt <= 1'b0; else if (local_fault) flt <= 1'b1;
    assign fo[0] = flt;

    // ---------------- home (quadrant 2) ----------------
    generate if (HOME) begin : g_home
        // remote lanes: pin flops in
        reg [23:0] hbq_cq, hbr_vq; reg [24*272-1:0] hbr_dq; reg [2:0] hgq_cq, hgr_vq, hwb_cq, hflt_q;
        reg [3*276-1:0] hgr_dq; reg [3*NG-1:0] hgwd_q;
        always @(posedge clk or negedge rn_h)
            if (!rn_h) begin hbq_cq <= 0; hbr_vq <= 0; hgq_cq <= 0; hgr_vq <= 0; hwb_cq <= 0; hflt_q <= 0; hgwd_q <= 0; end
            else begin hbq_cq <= h_bq_c; hbr_vq <= h_br_v; hgq_cq <= h_gq_c; hgr_vq <= h_gr_v; hwb_cq <= h_wb_c;
                       hflt_q <= h_flt; hgwd_q <= h_gwd; end
        always @(posedge clk) begin hbr_dq <= h_br_d; hgr_dq <= h_gr_d; end
        // splice the internal lane 2 (this quadrant's own PCs / lanes) into the home bundles
        wire [31:0] bqc = {hbq_cq[23:16], bi_c, hbq_cq[15:0]};
        wire [31:0] brv = {hbr_vq[23:16], pbr_v, hbr_vq[15:0]};
        wire [32*272-1:0] brd = {hbr_dq[24*272-1:16*272], pbr_d, hbr_dq[16*272-1:0]};
        wire [3:0] gqc = {hgq_cq[2], gin_c, hgq_cq[1:0]};
        wire [3:0] grv = {hgr_vq[2], gro_v, hgr_vq[1:0]};
        wire [4*276-1:0] grd = {hgr_dq[2*276 +: 276], gro_d, hgr_dq[0 +: 2*276]};
        wire [3:0] wbc = {hwb_cq[2], wl_c, hwb_cq[1:0]};
        wire [4*NG-1:0] gwdv = {hgwd_q[2*NG +: NG], gwd_i, hgwd_q[0 +: 2*NG]};
        wire qf = (|hflt_q) | flt;
        wire hf; wire [31:0] hfc;
        reg hw_vq; reg [290:0] hw_dq; wire hcr; wire [7:0] hack;
        always @(posedge clk or negedge rn_h) if (!rn_h) hw_vq <= 1'b0; else hw_vq <= h_hw_v[0];
        always @(posedge clk) hw_dq <= h_hw_d;
        ot_s81_svch_home #(.DIE_ID(DIE_ID), .ST(ST), .NG(NG), .DRB(DRB), .DW0(dep(NRH0)), .DW1(dep(NRH1)), .DW2(dep(0)),
                           .DW3(dep(NRH3)), .SRAM_MACRO(SRAM_MACRO)) u_home (
            .clk(clk), .rst_n(rn_h), .q_v(qv_q), .q_d(qd_q[511:0]),
            .go(go), .tagj(tagj), .posj(posj), .userj(userj), .wcount(wcount), .rbase(rbase), .rcount(rcount), .npub(npub),
            .wj_v(wj_v), .wj_user(wj_user), .wj_first(wj_first), .wj_count(wj_count), .held(held),
            .own_count(own_count), .own_done(own_done), .own_idx(own_idx), .own_rank(own_rank), .own_gid(own_gid),
            .wb_v(hw_v), .wb_d(hw_d), .wb_c(wbc), .fb_v(hf_v), .fb_d(hf_d),
            .bq_v(hbq_v), .bq_d(hbq_d), .bq_c(bqc), .br_v(brv), .br_d(brd), .br_c(hbr_c),
            .gq_v(hgq_v), .gq_d(hgq_d), .gq_c(gqc), .gr_v(grv), .gr_d(grd), .gr_c(hgr_c), .gwd(gwdv),
            .sc_v(sc_v), .sc_r(sc_r), .sc_d(sc_d), .pv_v(hpv_v), .pv_r(hpv_r), .pv_d(hpv_d), .qfault(qf),
            .a0_v(a0_v[0]), .a0_d(a0_d), .a0_r(a0_r[0]), .od_v(od_v[0]), .od_d(od_d), .od_r(od_r[0]),
            .hw_v(hw_vq), .hw_d(hw_dq), .hc_cr(hcr), .hc_ack(hack),
            .fault(hf), .fault_code(hfc));
        reg [8:0] hc_q;
        always @(posedge clk or negedge rn_h) if (!rn_h) hc_q <= 0; else hc_q <= {hack, hcr};
        assign h_hc = hc_q;
        assign h_bq_v = {hbq_v[31:24], hbq_v[15:0]}; assign h_bq_d = {hbq_d[32*46-1:24*46], hbq_d[16*46-1:0]};
        assign h_br_c = {hbr_c[31:24], hbr_c[15:0]};
        assign h_gq_v = {hgq_v[3], hgq_v[1:0]}; assign h_gq_d = {hgq_d[3*344 +: 344], hgq_d[0 +: 2*344]};
        assign h_gr_c = {hgr_c[3], hgr_c[1:0]};
        assign h_wb_v = {hw_v[3], hw_v[1:0]}; assign h_wb_d = {hw_d[3*4228 +: 4228], hw_d[0 +: 2*4228]};
        assign h_fb_v = {hf_v[3], hf_v[1:0]}; assign h_fb_d = {hf_d[3*607 +: 607], hf_d[0 +: 2*607]};
        if (ST == 2) begin : g_pvc0
            assign h_pv_c = 3'd0;
        end
    end else begin : g_nohome
        assign hbq_v = 0; assign hbq_d = 0; assign hbr_c = 0; assign hgq_v = 0; assign hgq_d = 0; assign hgr_c = 0;
        assign hw_v = 0; assign hw_d = 0; assign hf_v = 0; assign hf_d = 0; assign hpv_r = 1'b0;
        assign sc_r = 1'b0; assign own_idx = 0;
        assign h_bq_v = 0; assign h_bq_d = 0; assign h_br_c = 0; assign h_gq_v = 0; assign h_gq_d = 0; assign h_gr_c = 0;
        assign h_wb_v = 0; assign h_wb_d = 0; assign h_fb_v = 0; assign h_fb_d = 0; assign h_pv_c = 0;
        assign a0_v[0] = 1'b0; assign a0_d = 0; assign od_v[0] = 1'b0; assign od_d = 0; assign h_hc = '0;
    end endgenerate
endmodule
