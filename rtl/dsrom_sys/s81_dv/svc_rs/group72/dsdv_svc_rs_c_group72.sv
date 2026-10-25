`timescale 1ns/1ps
`default_nettype none
module dsdv_svc_rs_c_group72 #(
    parameter bit ENTRY = 0,
    parameter integer MUT = 0,
    parameter integer DIE_ID = 0,
    parameter integer ST = 0,
    parameter bit SRAM_MACRO = 0,
    parameter bit SMT = 1, parameter bit PMEM = 1
) (
    input wire ck, ck_sm, ck_att,
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
`include "dsdv_svc_rs_roles_group72.svh"
    localparam integer DW = 805, UW = 16;
    reg [1:0] rs;
    always @(posedge ck or negedge rst) if (!rst) rs <= 2'b00; else rs <= {rs[0], 1'b1};
    wire rn = rs[1];
    reg [21:0] role; reg [7:0] pvs, pf;
    wire [1:0] a_st;                                  // stack position (dsdv_svc_att: CFG [31:30] or the parameter ST)
    always @(posedge ck or negedge rn) if (!rn) begin role <= '0; pvs <= 8'd255; pf <= 8'h00; end
        else begin role <= rs_role(sid); pvs <= rs_pvslot(a_st, sid); pf <= rs_pface(sid); end
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
        reg [DW-1:0] p0, p1;
        always @(posedge ck or negedge rn) if (!rn) begin p0[0] <= 1'b0; p0[513] <= 1'b0; p1[0] <= 1'b0; p1[513] <= 1'b0; end
            else begin p0[0] <= dn_i[DW*f]; p0[513] <= dn_i[DW*f + 513]; p1[0] <= p0[0]; p1[513] <= p0[513]; end
        always @(posedge ck) begin p0[512:1] <= dn_i[DW*f + 1 +: 512]; p0[DW-1:514] <= dn_i[DW*f + 514 +: DW - 514];
                                   p1[512:1] <= p0[512:1]; p1[DW-1:514] <= p0[DW-1:514]; end
        assign dfi[f] = p1;
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
        reg [DW-1:0] r1;
        always @(posedge ck or negedge rn) if (!rn) begin r1[0] <= 1'b0; r1[513] <= 1'b0; end
            else begin r1[0] <= cq[0]; r1[513] <= hp[0]; end
        always @(posedge ck) begin r1[512:1] <= cq[512:1]; r1[DW-1:514] <= hp[291:1]; end
        assign hst = r1;
        assign jf = 1'b0;
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
        reg [DW-1:0] o0, o1;
        always @(posedge ck or negedge rn) if (!rn) begin o0[0] <= 1'b0; o0[513] <= 1'b0; o1[0] <= 1'b0; o1[513] <= 1'b0; end
            else begin o0[0] <= cs[0] && chm[f]; o0[513] <= cs[513] && chm[f]; o1[0] <= o0[0]; o1[513] <= o0[513]; end
        always @(posedge ck) begin o0[512:1] <= cs[512:1]; o0[DW-1:514] <= cs[DW-1:514];
                                   o1[512:1] <= o0[512:1]; o1[DW-1:514] <= o0[DW-1:514]; end
        assign dn_o[DW*f +: DW] = o1;
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
    dsdv_svc_attw_n1_f_lp #(.AMUT(MUT), .DIE_ID(DIE_ID), .ST(ST), .SRAM_MACRO(SRAM_MACRO), .PMEM(PMEM), .ROOT(ENTRY), .TLX(6), .ROLE_EXT(1)) u_att (
        .ck_c(ck), .ck_t0(ck_att), .rst(rst), .sid(sid), .role_i(role), .pvs_i(pvs),
        .cs(cs),
        .qrq(qrq), .qrk(qrk), .qwd(qwd), .qrv(qrv), .qr_data(qr_data), .qr_tag(qr_tag), .qr_beat(qr_beat),
        .l_v(l_v), .l_d(l_d), .pv_ov(a_pv_v), .pv_od(a_pv_d),
        .sm_st(sm_st), .sm_kind(sm_kind), .sm_jid(sm_jid), .sm_rv(sm_rv), .sm_rp(sm_rp), .sm_rj(sm_rj), .sm_rd(sm_rd),
        .go_o(go), .tjob_o(tjob), .done(done), .tagj(tagj), .hcr(hcr), .hack(hack), .fault(a_f), .fault_code(a_fc),
        .pio_o(pio), .pvo_o(pvo_j), .jc_o(jcs), .st_o(a_st));

    // ------------------------------------------------------------------ score exchange
    wire rt_v, t_v, x_f; wire [2131:0] rt_d; wire [19:0] t_tag; wire [127:0] t_y; wire [3:0] t_f;
    reg pl_v; reg [2131:0] pl_d;                     // P beat (registered), muxed onto the engine's score-beat port
    dsdv_svc_sx #(.MUT(0)) u_sx (.ck(ck), .rst(rst), .sid(sid), .l_v(l_v || pl_v), .l_d(pl_v ? pl_d : l_d),
        .gi_v(gi_v), .gi_d(gi_d), .go_v(go_v), .go_d(go_d), .si_v(si_v), .si_d(si_d), .so_v(so_v), .so_d(so_d),
        .rt_v(rt_v), .rt_d(rt_d), .t_v(t_v), .t_tag(t_tag), .t_y(t_y), .t_f(t_f), .gh_i(4272'd0), .gh_o(), .fault(x_f));

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
    wire sm_rn;
    ot_reset_sync #(.ASYNC_STAGES(2)) u_sm_rst (.clk(ck_sm), .async_rst_n(rst), .sync_rst_n(sm_rn));
    wire [533:0] sm_ci, sm_co;
    wire [554:0] sm_ri, sm_ro;
    assign sm_ci = {tile, sm_st, sm_kind, sm_jid, r_v, r_p, r_j, r_d};
    dsdv_svc_face72 #(.W(534)) u_sm_cmd (.ck_w(ck), .ck_r(ck_sm), .rst_w(rn), .rst_r(sm_rn), .i(sm_ci), .o(sm_co));
    wire sw_v; wire [13:0] sw_a; wire [15:0] sw_m; wire [511:0] sw_d;
    wire sf_u, sf_o, sf_alive, sf_den; wire [7:0] sf_jid;
    ot_s81_su_sms u_sms (.clk(ck_sm), .rst_in(sm_rn), .cfg_g(sm_co[533:530]), .j_st(sm_co[529]), .j_kind(sm_co[528:525]), .j_jid(sm_co[524:517]),
        .r_v(sm_co[516]), .r_p(sm_co[515]), .r_j(sm_co[514:512]), .r_d(sm_co[511:0]),
        .w_v(sw_v), .w_a(sw_a), .w_m(sw_m), .w_d(sw_d), .o_fu(sf_u), .o_fo(sf_o), .o_alive(sf_alive), .o_den(sf_den), .o_rjid(sf_jid));
    assign sm_ri = {sw_v, sw_a, sw_m, sw_d, sf_jid, sf_den, sf_alive, sf_o, sf_u};
    dsdv_svc_face72 #(.W(555)) u_sm_ret (.ck_w(ck_sm), .ck_r(ck), .rst_w(sm_rn), .rst_r(rn), .i(sm_ri), .o(sm_ro));
    assign {w_v, w_a, w_m, w_d, o_rjid, o_den, o_alive, o_fo, o_fu} = sm_ro;
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
        reg p0v, p1v; reg [RW-2:0] p0d, p1d;
        always @(posedge ck or negedge rn) if (!rn) begin p0v <= 1'b0; p1v <= 1'b0; end
            else begin p0v <= ri[RW*f]; p1v <= p0v; end
        always @(posedge ck) begin p0d <= ri[RW*f + 1 +: RW - 1]; p1d <= p0d; end
        assign rfi[f] = {p1d, p1v};
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
    always @(posedge ck) begin
        rm_d <= gw_v ? gw_d : pp_v ? pp_d : a_pv_d;
        for (int i = 0; i < 4; i++) if (rfi[i][0] && chr[i]) rm_d <= rfi[i][RW-1:1];
    end
    generate for (f = 0; f < 4; f = f + 1) begin : g_ro
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
    wire lf = a_f | x_f | rcol | o_fo | dstray | r_f | p_f | zt_f | (|sot_fc) | gw_f | (zt_ret_v && zt_ret_e);
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
    dsdv_svc_rs_up #(.UW(UW)) u_up (.ck(ck), .rn(rn), .chm(chm), .par(par), .done(done && !so_pend), .fl(hs_f), .hcr(hcr), .hack(hack),
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
`default_nettype wire
