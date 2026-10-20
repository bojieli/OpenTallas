`timescale 1ns/1ps
// S81U-2 (2026-10-17): exact bench of the per-slice SM share ot_s81_su_sms (smq tap + smh head subtree) against the
// slab's SM stop: ot_s81_su_smt + two ot_s81_su_smh at the spine's DOP = SRL + 2, i.e. dsfd_sp_su_h g_sm (-DSU_SMU,
// leaf for leaf and station for station the default g_h body whose su_gate run is bit-exact to the golden).
// Production parameters (SM_H 16, SM_LPH 16, S_RD 16, WS 2, NVMAX 40, LM 5, LA 4, SRL 2).  Two DUT shares (heads
// g = 2 TI, 2 TI + 1) get the same jobs as the stop over their serial row ports; the REAL lane / sum / root / divide
// arithmetic runs on both sides (no bench-made e / o events).  Jobs: SE (2 parameter rows, nv = 1..40 score vectors
// with random gaps and -Inf inactive lanes), each followed by an SO (5 parameter rows, 32-pair cos / sin stream,
// 32 P.V vectors) that divides by that SE's den.  Compared, in order, per head: every write row (address, mask, data:
// SE e rows; SO o rows = the stop's full row's masked half) and the final status.  Measured and checked CONSTANT
// (the static schedule): SE first e row after the last score row, SE e rows back to back, SO o row k after P.V row k,
// den after the job's LAST e row, per tree depth lt = clog2(nv) (the row sum's time levels).  Prints "SMS PASS ..." / "SMS FAIL ..." as its LAST line.
module tb_smwire_e2e;
    parameter integer MUT = 0, TI = 5, NJOB = 12, SEED = 1017;
    localparam integer SRL = 2;
    reg clk = 0, rst = 0;
    always #1 clk = ~clk;
    integer cyc = 0;
    always @(posedge clk) cyc <= cyc + 1;

    // ------------------------------------------------------------------ reference: the slab's SM stop
    reg dn_st = 0; reg [3:0] dn_kind = 0; reg [7:0] dn_jid = 0; reg [15:0] dn_v = 0; reg [2559:0] dn_p = 0;
    reg [1023:0] dn_d = 0;                                        // spine slots 2 TI, 2 TI + 1 (the stop's operand rows)
    wire s_v, p_v, c_v, cs_v; wire [6:0] c_nv; wire [2:0] c_lt; wire [31:0] c_scale; wire [63:0] c_sink; wire [4:0] cs_i;
    wire [63:0] cs_d; wire [1:0] w_v; wire [27:0] w_a; wire [31:0] w_m; wire [1023:0] w_d;
    wire t_fu, t_fo, t_al, t_den, t_rdy; wire [7:0] t_rj;
    wire [1:0] he_v, ho_v, hdn; wire [1023:0] he_d; wire [511:0] ho_d; wire [15:0] hf;
    ot_s81_su_smt #(.SM_H(16), .SM_LPH(16), .S_RD(16), .WS(2)) u_t (
        .clk(clk), .rst_in(rst), .cfg_ti(TI[3:0]), .dn_st_i(dn_st), .dn_kind_i(dn_kind), .dn_jid_i(dn_jid), .dn_v_i(dn_v),
        .dn_p_i(dn_p), .s_v(s_v), .p_v(p_v), .c_v(c_v), .c_nv(c_nv), .c_lt(c_lt), .c_scale(c_scale), .c_sink(c_sink),
        .cs_v(cs_v), .cs_i(cs_i), .cs_d(cs_d), .e_v_i(he_v[0]), .e_d_i(he_d), .o_v_i(ho_v[0]), .o_d_i(ho_d),
        .den_v_i(hdn[0]), .f_i(|hf),
        .o_v(w_v), .o_a(w_a), .o_m(w_m), .o_d(w_d), .o_fu(t_fu), .o_fo(t_fo), .o_alive(t_al), .o_den(t_den),
        .o_rdy(t_rdy), .o_rjid(t_rj));
    genvar h;
    generate for (h = 0; h < 2; h = h + 1) begin : g_r
        ot_s81_su_smh #(.SM_NVMAX(40), .LM(5), .LA(4), .SRL(SRL)) u_smh (
            .clk(clk), .rst_in(rst), .s_v(s_v), .p_v(p_v), .c_v(c_v), .c_nv(c_nv), .c_lt(c_lt), .c_scale(c_scale),
            .c_sink(c_sink[32 * h +: 32]), .cs_v(cs_v), .cs_i(cs_i), .cs_d(cs_d), .d(dn_d[512 * h +: 512]),
            .e_v(he_v[h]), .e_d(he_d[512 * h +: 512]), .o_v(ho_v[h]), .o_d(ho_d[256 * h +: 256]), .den_v(hdn[h]),
            .f(hf[8 * h +: 8]));
    end endgenerate

    // ------------------------------------------------------------------ DUT: two per-slice SM shares
    reg q_st = 0; reg [3:0] q_kind = 0; reg [7:0] q_jid = 0; reg r_v = 0, r_p = 0; reg [2:0] r_j = 0;
    reg [511:0] r_d0 = 0, r_d1 = 0;
    wire [1:0] qw_v, q_fu, q_fo, q_al, q_den; wire [27:0] qw_a; wire [31:0] qw_m; wire [1023:0] qw_d; wire [15:0] q_rj;
    generate for (h = 0; h < 2; h = h + 1) begin : g_q
        ot_s81_su_sms #(.MUT(MUT)) u_sms (
            .clk(clk), .rst_in(rst), .cfg_g(4'(2 * TI + h)), .j_st(q_st), .j_kind(q_kind), .j_jid(q_jid),
            .r_v(r_v), .r_p(r_p), .r_j(r_j), .r_d(h ? r_d1 : r_d0),
            .w_v(qw_v[h]), .w_a(qw_a[14 * h +: 14]), .w_m(qw_m[16 * h +: 16]), .w_d(qw_d[512 * h +: 512]),
            .o_fu(q_fu[h]), .o_fo(q_fo[h]), .o_alive(q_al[h]), .o_den(q_den[h]), .o_rjid(q_rj[8 * h +: 8]));
    end endgenerate


    // Independent compiler-owned expectation. Set before SE starts, never from
    // a returned row/address/status. The SO operand generator obeys this base.
    reg cfg_v = 0;
    reg [19:0] target_owner = 0;
    reg [7:0] expected_se = 0, expected_so = 0;
    reg [13:0] target_base = 0;
    wire [1:0] gv, retired, re, tfault;
    wire [13:0] gi;
    wire [2047:0] gd;
    wire [39:0] go_owner, retire_owner;
    wire [1:0] group_o;
    wire [23:0] fc;
    integer target_mut = 0, target_beats = 0, target_retires = 0;
    integer target_bad_retires = 0, target_checks = 0;
    integer ref_count = 0;
    reg [255:0] reference_rows[0:1][0:31];
    reg [7:0] got[0:1];
    reg [13:0] previous_addr[0:1];
    reg [7:0] previous_mask[0:1];
    initial if (!$value$plusargs("TARGET_MUT=%d", target_mut)) target_mut=0;
    // S81-SMWIRE e2e state
    integer smw_mut = 0, smw_route = 1, smw_err = 0, smw_checks = 0;
    initial begin
        if (!$value$plusargs("SMW_MUT=%d", smw_mut)) smw_mut = 0;
        if (!$value$plusargs("SMW_ROUTE=%d", smw_route)) smw_route = 1;
    end
    reg sq_v = 0; reg [511:0] sq_d = 0;
    reg rst_l = 0;
    always @(posedge clk) rst_l <= rst;
    wire [1:0] gw_v, gw_f, sot_f; wire [1025:0] gw_d;
    wire e_cfg_v; wire [1:0] e_route; wire [15:0] e_gw0, e_gw1;
    wire s_cfg_any = g_target[0].s_cfg_v | g_target[1].s_cfg_v;
    generate for (genvar th=0; th<2; th=th+1) begin: g_target
        wire so = qw_m[16*th+:16] != 16'hffff;
        wire inject = so && target_mut != 0;
        wire [15:0] tm = (inject && target_mut==1) ? ~qw_m[16*th+:16] : qw_m[16*th+:16];
        wire [13:0] ta = (inject && target_mut==2) ? (qw_a[14*th+:14] ^ 14'd8) : qw_a[14*th+:14];
        wire [7:0] tj = (inject && target_mut==3) ? (q_rj[8*th+:8] ^ 8'd1) : q_rj[8*th+:8];
        wire tv = qw_v[th] && !(so && target_mut==4);
        wire td = q_den[th] && target_mut != 5;
        // S81-SMWIRE: the config comes from the SOT frame on the q stream (dsdv_svc_sot), never from the bench regs
        wire s_cfg_v; wire [19:0] s_owner; wire [7:0] s_se, s_so; wire [13:0] s_obase;
        wire [15:0] s_first, s_last, s_read, s_ret, s_gw0, s_gw1; wire [1:0] s_route; wire [2:0] s_fc;
        dsdv_svc_sot u_sot (.clk(clk), .rst_n(rst_l), .tile(4'(2*TI+th)), .q_v(sq_v), .q_d(sq_d), .cfg_v(s_cfg_v),
            .cfg_owner(s_owner), .cfg_se_jid(s_se), .cfg_so_jid(s_so), .cfg_obase(s_obase), .cfg_first(s_first),
            .cfg_last(s_last), .cfg_read(s_read), .cfg_retire(s_ret), .route(s_route), .gw_first(s_gw0),
            .gw_last(s_gw1), .fault_code(s_fc));
        dsdv_sm_so_target #(.HEAD(-1)) u_target (
            .clk(clk),.rst_n(rst),.head(4'(2*TI+th)),.cfg_v(s_cfg_v),.cfg_owner(s_owner),
            .cfg_se_jid(s_se),.cfg_so_jid(s_so),.cfg_obase(s_obase),
            .cfg_first(s_first),.cfg_last(s_last),.cfg_read(s_read),.cfg_retire(s_ret),
            .op_st(q_st),.op_kind(q_kind),.op_jid(q_jid),
            .w_v(tv),.w_a(ta),.w_m(tm),.w_d(qw_d[512*th+:512]),
            .w_st({tj,td,q_al[th],q_fo[th],q_fu[th]}),
            .g_v(gv[th]),.g_idx(gi[7*th+:7]),.g_d(gd[1024*th+:1024]),
            .g_owner(go_owner[20*th+:20]),.g_group(group_o[th]),
            .retired(retired[th]),.retire_error(re[th]),.retire_owner(retire_owner[20*th+:20]),
            .fault(tfault[th]),.fault_code(fc[12*th+:12]));
        dsdv_sm_gw u_gw (.clk(clk), .rst_n(rst_l), .head(4'(2*TI+th)), .g_v(gv[th]), .g_idx(gi[7*th+:7]),
            .g_d(gd[1024*th+:1024]), .g_owner(go_owner[20*th+:20]), .g_group(group_o[th]), .gw_v(gw_v[th]),
            .gw_d(gw_d[513*th+:513]), .fault(gw_f[th]));
        assign sot_f[th] = |s_fc;
        if (th == 0) begin : g_ent
            assign e_cfg_v = s_cfg_v; assign e_route = s_route; assign e_gw0 = s_gw0; assign e_gw1 = s_gw1;
        end
    end endgenerate
    // ---- return-tree stand-in: head 1 is one hop (5 edges) below the entry; two words in one cycle FAIL
    reg [513:0] hop1 [0:4];
    integer hk;
    always @(posedge clk) begin
        hop1[0] <= {gw_d[1025:513], gw_v[1]};
        for (hk = 1; hk < 5; hk = hk + 1) hop1[hk] <= hop1[hk-1];
    end
    wire t1_v = hop1[4][0]; wire [512:0] t1_d = hop1[4][513:1];
    reg rm_v = 0; reg [512:0] rm_d = 0; reg pv_v = 0; reg [512:0] pv_d = 0;
    always @(posedge clk) begin
        if (gw_v[0] && t1_v) begin smw_err = smw_err + 1; $display("SMWIRE MISMATCH tree collision at %0d", cyc); end
        rm_v <= gw_v[0] || t1_v; rm_d <= gw_v[0] ? gw_d[512:0] : t1_d;
        pv_v <= rm_v; pv_d <= rm_d;
    end
    wire [47:0] pv_x;
    dsdv_sm_gx u_gx (.clk(clk), .rst_n(rst_l), .cfg_v(e_cfg_v), .route(e_route), .gw_first(e_gw0),
        .gw_last((smw_mut == 3) ? e_gw1 - 16'd80 : e_gw1), .w_v(rm_v), .pv_x(pv_x));
    // ---- the 562-b pv lane (2 relay stages) and its landing on the C3 slice root (forwarded clock +300 ps)
    reg [561:0] ln0 = 0, ln1 = 0;
    wire [561:0] lw0 = {pv_x, pv_d, pv_v};
    reg [561:0] lw;
    always @(*) begin
        lw = lw0;
        if (smw_mut == 2 && lw0[561] && !lw0[513]) lw[512:257] = ~lw0[512:257];   // data words corrupted on the lane
        if (smw_mut == 4) lw[558:557] = 2'd0;
        if (smw_mut == 5 && lw0[561] && lw0[513]) lw[1] = ~lw0[1];
    end
    always @(posedge clk) begin ln0 <= lw; ln1 <= ln0; end
    reg ckf = 0;
    always @(clk) ckf <= #0.3 clk;
    wire [1103:0] bi_w; wire land_f;
    dsfd_dvland_pvrd u_land (.ck_f(ckf), .i(ln1), .ck(clk), .rs(rst_l), .k(3'd2), .nw(8'd160), .rb(10'd0),
        .o(bi_w), .fault(land_f));
    // ---- C3 control plane (band port B) and four ring stops
    wire [2:0] ci_dir; wire [1103:0] ci_b; wire xr_f;
    ot_s81sl_xr #(.HB(1)) u_xr (.clk(clk), .rst_n(rst_l), .sid(4'd6), .dl_ev(1'b0), .dl_e(1104'd0), .dl_wv(1'b0),
        .dl_w(1104'd0), .dl_vv(1'b0), .dl_vb(276'd0), .ci_dir(ci_dir), .ci_b(ci_b), .bi(bi_w), .bo(),
        .c_v(), .c_d(), .sw_v(), .sw_a(), .sw_m(), .sw_d(), .lo_v(5'd0), .lo_d(1280'd0), .p_v(5'd0), .p_d(160'd0),
        .rb_v(), .rb_d(), .e_v(5'd0), .e_c(10'd0), .e_d(480'd0), .eg_v(1'b0), .eg_c(2'd0), .eg_d(32'd0),
        .g_v(), .g_c(), .g_d(), .x_go(), .x_mode(), .x_eps(), .x_scale(), .x_sv(), .x_si(), .x_s(),
        .x_rbv(1'b0), .x_rbd(32'd0), .is_v(), .is_d(), .cfg_v(), .cfg_d(), .fault(xr_f));
    wire [1103:0] s3_roe, s3_row, s4_roe, s4_row, s2_roe, s2_row, n3_roe, n3_row;
    wire [275:0] s3_vo, s4_vo, s2_vo, n3_vo;
    wire [2:0] s3_gv, s4_gv, s2_gv, n3_gv, s3_gf, s4_gf, s2_gf, n3_gf;
    wire [20:0] s3_gi, s4_gi, s2_gi, n3_gi; wire [3071:0] s3_gd, s4_gd, s2_gd, n3_gd;
    wire [3:0] rs_f;
    ot_s81sl_rstop u_s3 (.clk(clk), .rst_n(rst_l), .sid(4'd6), .ri_w(1104'd0), .ri_e(1104'd0), .ro_e(s3_roe), .ro_w(s3_row),
        .vi(276'd0), .vo(s3_vo), .xf_v(5'd0), .xf_s(5'd0), .xf(1380'd0), .nx_wi(), .nx_ei(), .nx_eo(173'd0), .nx_wo(173'd0),
        .g_v(s3_gv), .g_fam(s3_gf), .g_idx(s3_gi), .g_d(s3_gd), .dl_ev(), .dl_e(), .dl_wv(), .dl_w(), .dl_vv(), .dl_vb(),
        .ci_dir(ci_dir), .ci_b(ci_b), .fault(rs_f[0]));
    ot_s81sl_rstop u_s4 (.clk(clk), .rst_n(rst_l), .sid(4'd8), .ri_w(s3_roe), .ri_e(1104'd0), .ro_e(s4_roe), .ro_w(s4_row),
        .vi(276'd0), .vo(s4_vo), .xf_v(5'd0), .xf_s(5'd0), .xf(1380'd0), .nx_wi(), .nx_ei(), .nx_eo(173'd0), .nx_wo(173'd0),
        .g_v(s4_gv), .g_fam(s4_gf), .g_idx(s4_gi), .g_d(s4_gd), .dl_ev(), .dl_e(), .dl_wv(), .dl_w(), .dl_vv(), .dl_vb(),
        .ci_dir(3'd0), .ci_b(1104'd0), .fault(rs_f[1]));
    ot_s81sl_rstop u_s2 (.clk(clk), .rst_n(rst_l), .sid(4'd4), .ri_w(1104'd0), .ri_e(s3_row), .ro_e(s2_roe), .ro_w(s2_row),
        .vi(276'd0), .vo(s2_vo), .xf_v(5'd0), .xf_s(5'd0), .xf(1380'd0), .nx_wi(), .nx_ei(), .nx_eo(173'd0), .nx_wo(173'd0),
        .g_v(s2_gv), .g_fam(s2_gf), .g_idx(s2_gi), .g_d(s2_gd), .dl_ev(), .dl_e(), .dl_wv(), .dl_w(), .dl_vv(), .dl_vb(),
        .ci_dir(3'd0), .ci_b(1104'd0), .fault(rs_f[2]));
    ot_s81sl_rstop u_n3 (.clk(clk), .rst_n(rst_l), .sid(4'd7), .ri_w(1104'd0), .ri_e(1104'd0), .ro_e(n3_roe), .ro_w(n3_row),
        .vi(s3_vo), .vo(n3_vo), .xf_v(5'd0), .xf_s(5'd0), .xf(1380'd0), .nx_wi(), .nx_ei(), .nx_eo(173'd0), .nx_wo(173'd0),
        .g_v(n3_gv), .g_fam(n3_gf), .g_idx(n3_gi), .g_d(n3_gd), .dl_ev(), .dl_e(), .dl_wv(), .dl_w(), .dl_vv(), .dl_vb(),
        .ci_dir(3'd0), .ci_b(1104'd0), .fault(rs_f[3]));
    // ---- gather-port checks (bit-exact vs the reference operator rows)
    integer gat_n [0:3]; integer gat_lat [0:7]; integer gat_latbad = 0, gat_extra = 0;
    reg [7:0] gat_seen [0:3][0:1];
    integer tb_cyc [0:1][0:7];
    initial begin : smw_init
        integer hi0;
        for (hi0 = 0; hi0 < 8; hi0 = hi0 + 1) begin gat_n[hi0 / 2] = 0; gat_lat[hi0] = -1; end
    end
    task gat(input integer st, input integer src, input [2:0] gvv, input [2:0] gff, input [20:0] gii, input [3071:0] gdd);
        integer hh, bi2, rr2; reg [1023:0] want2; reg [6:0] ix;
        begin
            if (gvv[src]) begin
                ix = gii[7*src +: 7];
                hh = (ix / 8 == (2*TI) % 8) ? 0 : (ix / 8 == (2*TI+1) % 8) ? 1 : -1;
                bi2 = ix % 8;
                if (!gff[src] || hh < 0) begin smw_err = smw_err + 1; $display("SMWIRE MISMATCH gather family/idx st %0d idx %0d", st, ix); end
                else begin
                    for (rr2 = 0; rr2 < 4; rr2 = rr2 + 1) want2[256*rr2 +: 256] = reference_rows[hh][4*bi2+rr2];
                    if (gdd[1024*src +: 1024] !== want2) begin smw_err = smw_err + 1; $display("SMWIRE MISMATCH gather data st %0d idx %0d", st, ix); end
                    if (gat_seen[st][hh][bi2]) begin smw_err = smw_err + 1; $display("SMWIRE MISMATCH duplicate st %0d idx %0d", st, ix); end
                    gat_seen[st][hh][bi2] = 1'b1;
                    if (gat_lat[2*st+hh] < 0) gat_lat[2*st+hh] = cyc - tb_cyc[hh][bi2];
                    else if (cyc - tb_cyc[hh][bi2] != gat_lat[2*st+hh]) gat_latbad = gat_latbad + 1;
                    gat_n[st] = gat_n[st] + 1; smw_checks = smw_checks + 1024;
                end
            end
        end
    endtask
    always @(posedge clk) if (rst) begin : smw_mon
        integer hm;
        for (hm = 0; hm < 2; hm = hm + 1) if (gv[hm]) tb_cyc[hm][gi[7*hm +: 7] % 8] = cyc;
        if (s_cfg_any) for (hm = 0; hm < 4; hm = hm + 1) begin gat_seen[hm][0] = 0; gat_seen[hm][1] = 0; end
        gat(0, 0, s3_gv, s3_gf, s3_gi, s3_gd);
        gat(1, 1, s4_gv, s4_gf, s4_gi, s4_gd);
        gat(2, 2, s2_gv, s2_gf, s2_gi, s2_gd);
        gat(3, 0, n3_gv, n3_gf, n3_gi, n3_gd);
        if (s3_gv[2:1] != 0 || s4_gv[0] || s4_gv[2] || s2_gv[1:0] != 0 || n3_gv[2:1] != 0) gat_extra = gat_extra + 1;
    end
    // Reference rows are from the independently instantiated real slab SM
    // operator, not the DUT target input and never a golden data responder.
    always @(posedge clk) if (rst) begin: target_monitor
        integer hh, bi, rr;
        reg [1023:0] want;
        if (s_cfg_any) begin
            ref_count=0; got[0]=0; got[1]=0;
        end
        if (dn_kind==5 && w_v[0]) begin
            if (ref_count >= 32) fail("target reference overflow",ref_count);
            else begin
                reference_rows[0][ref_count]=w_d[255:0];
                reference_rows[1][ref_count]=w_d[511:256];
                ref_count=ref_count+1;
            end
        end
        for (hh=0;hh<2;hh=hh+1) begin
            if (gv[hh]) begin
                target_beats=target_beats+1;
                bi=gi[7*hh+:7] % 8;
                if (target_mut != 0) fail("target mutant emitted healthy beat",target_mut);
                if (ref_count != 32 || got[hh][bi]) fail("target missing/duplicate identities",bi);
                got[hh][bi]=1;
                for (rr=0;rr<4;rr=rr+1) want[256*rr+:256]=reference_rows[hh][4*bi+rr];
                if (gd[1024*hh+:1024] !== want) fail("target real operator gather order",bi);
                if (gi[7*hh+:7] != 8*((2*TI+hh)%8)+bi ||
                    group_o[hh] != (2*TI+hh>=8) || go_owner[20*hh+:20] !== target_owner)
                    fail("target independent owner/group/index",hh);
                target_checks=target_checks+64;
            end
            if (retired[hh]) begin
                target_retires=target_retires+1;
                if (re[hh]) target_bad_retires=target_bad_retires+1;
                if (retire_owner[20*hh+:20] !== target_owner) fail("target retire owner",hh);
                if (target_mut==0 && (re[hh] || got[hh] != 8'hff || tfault[hh]))
                    begin fail("target base retirement",hh); $display("TARGET fault=%h",fc); end
                if (target_mut!=0 && (!re[hh] || !tfault[hh])) fail("target missed causal fault",target_mut);
            end
        end
    end

    // ------------------------------------------------------------------ logs
    integer err = 0, nchk = 0;
    reg [1023:0] tq_w [$]; reg [1023:0] hq_w0 [$], hq_w1 [$];
    integer wc0 [$];                                              // DUT head-0 write cycles
    integer den_cyc [$];                                          // DUT head-0 o_den rising cycles
    reg pden = 0;
    integer k;
    always @(posedge clk) if (rst) begin
        for (k = 0; k < 2; k = k + 1) if (w_v[k]) tq_w.push_back({w_a[14 * k +: 14], w_m[16 * k +: 16], w_d[512 * k +: 512]});
        if (qw_v[0]) begin hq_w0.push_back({qw_a[13:0], qw_m[15:0], qw_d[511:0]}); wc0.push_back(cyc); end
        if (qw_v[1]) hq_w1.push_back({qw_a[27:14], qw_m[31:16], qw_d[1023:512]});
        if (q_den[0] && !pden) den_cyc.push_back(cyc);
        pden <= q_den[0];
    end

    // ------------------------------------------------------------------ stimulus
    function [31:0] rscore(input integer dummy);       // moderate fp32, both signs; ~1/16 the -Inf inactive sentinel
        begin
            if ($urandom % 16 == 0) rscore = 32'hff800000;
            else rscore = {1'($urandom), 8'(124 + $urandom % 8), 23'($urandom)};
        end
    endfunction
    function [31:0] rval(input integer dummy);
        rval = {1'($urandom), 8'(118 + $urandom % 14), 23'($urandom)};
    endfunction
    function [511:0] rrow(input integer sc);
        integer i; begin for (i = 0; i < 16; i = i + 1) rrow[32 * i +: 32] = sc ? rscore(0) : rval(0); end
    endfunction
    function [2:0] clog2(input integer n);
        integer v; begin clog2 = 0; v = 1; while (v < n) begin v = v * 2; clog2 = clog2 + 1; end end
    endfunction
    reg [511:0] prm [0:4];
    integer j, b, nv, np, kind, seed, jj;
    integer se_last [$];                                          // per SE: cycle the last score row is at the DUT pins
    integer se_nv [$];
    integer pv_cyc [$];                                           // per SO P.V row: cycle at the DUT pins
    integer kinds [$];
    reg [511:0] x0, x1;
    task tick; begin @(posedge clk); #0.1; end endtask
    // compiler encoding (tools/s81_dv/sm_target/smwire_cal.py sot_frame): WIN_LOAD header (tag, user) then the SOT frame
    task send_sot(input integer jx);
        reg [511:0] h; integer t, rd;
        begin
            h = 0; h[511:508] = 4'd2; h[503] = 1'b1; h[502:495] = 8'(target_owner[7:0] ^ ((smw_mut == 1) ? 1 : 0));
            h[458:449] = target_owner[17:8];
            sq_v = 1; sq_d = h; tick;
            h = 0; h[511:508] = 4'd14; h[503] = 1'b1; h[491:480] = 12'd2; h[502:495] = target_owner[7:0];
            h[19:0] = target_owner; h[27:20] = expected_se; h[35:28] = expected_so; h[49:36] = target_base;
            h[51:50] = 2'(smw_route); h[67:52] = 16'd1300; h[83:68] = 16'd1420;
            sq_d = h; tick;
            h = 0; for (t = 0; t < 16; t = t + 1) h[32*t +: 32] = {16'd1200, 16'd0};
            sq_d = h; tick;
            h = 0; for (t = 0; t < 16; t = t + 1) begin rd = 1300 + 40 * (t % 2); h[32*t +: 32] = {16'(rd + 50), 16'(rd)}; end
            sq_d = h; tick;
            sq_v = 0; sq_d = 0; repeat (3) tick;
        end
    endtask
    task job(input integer kd, input integer nvv);
        begin
            if (kd==4) begin
                target_owner=20'h54100+jj;
                expected_se=jj; expected_so=jj+1;
                target_base=14'h300+14'(512*j);
                send_sot(jj);
            end
            np = (kd == 5) ? 5 : 2;
            for (b = 0; b < 5; b = b + 1) prm[b] = rrow(0);
            prm[0][13:0] = $urandom; prm[0][64 +: 7] = nvv; prm[0][128 +: 3] = clog2(nvv);
            prm[0][96 +: 32] = {1'b0, 8'(121 + $urandom % 4), 23'($urandom)};       // scale
            if(kd==5) prm[0][13:0]=target_base;
            kinds.push_back(kd);
            dn_st = 1; dn_kind = kd; dn_jid = jj; q_st = 1; q_kind = kd; q_jid = jj; tick; jj = jj + 1;
            dn_st = 0; q_st = 0;
            dn_v = (16'd1 << np) - 16'd1;
            for (b = 0; b < 5; b = b + 1) dn_p[512 * b +: 512] = prm[b];
            r_v = 1; r_p = 1; r_j = 0; r_d0 = prm[0]; r_d1 = prm[0]; tick;
            dn_v = 0;
            for (b = 1; b < np; b = b + 1) begin r_j = b; r_d0 = prm[b]; r_d1 = prm[b]; tick; end
            r_v = 0; r_p = 0;
            if (kd == 5) repeat (40) tick;                         // the cos / sin stream (32 pairs) reaches the engines
            else repeat (2 + $urandom % 3) tick;
            for (b = 0; b < ((kd == 5) ? 32 : nvv); b = b + 1) begin
                x0 = rrow(kd == 4); x1 = rrow(kd == 4);
                dn_v = 16'hFFFF; dn_d = {x1, x0}; r_v = 1; r_p = 0; r_d0 = x0; r_d1 = x1;
                if (kd == 5) pv_cyc.push_back(cyc); else if (b == nvv - 1) begin se_last.push_back(cyc); se_nv.push_back(nvv); end
                tick;
                dn_v = 0; r_v = 0;
                if (kd == 4 && $urandom % 3 == 0) repeat (1 + $urandom % 2) tick;
            end
            repeat (400) tick;                                     // results drain before the next job
            if(kd==5) repeat(650) tick;
        end
    endtask
    initial begin
        seed = SEED; seed = $urandom(seed); jj = 0;
        repeat (4) tick;
        rst = 1;
        repeat (6) tick;
        for (j = 0; j < NJOB; j = j + 1) begin
            nv = (j == 0) ? 40 : (j == 1) ? 1 : 1 + $urandom % 40;
            job(4, nv);
            job(5, 0);
        end
        repeat (12) tick;
        check;
    end

    task fail(input [8*48-1:0] what, input integer i);
        begin if (err < 12) $display("SMS MISMATCH %0s at %0d", what, i); err = err + 1; end
    endtask
    integer l_se, l_so, nse, nso;
    integer l_dn [0:7];
    task check;
        integer i, q, w, jx, x, lt; reg [1023:0] t; reg [541:0] r0, r1;
        begin
            if (hq_w0.size() != hq_w1.size()) fail("head row counts", 0);
            nse = 0; nso = 0;
            for (i = 0; i < hq_w0.size() && i < hq_w1.size(); i = i + 1) begin
                t = hq_w0[i]; r0 = t[541:0]; t = hq_w1[i]; r1 = t[541:0];
                nchk = nchk + 1;
                if (r0[527:512] == 16'hFFFF) begin                 // SE: the stop writes head 0 then head 1 (slots 0, 1)
                    nse = nse + 1;
                    if (tq_w.size() < 2) fail("stop SE rows short", i);
                    else begin
                        t = tq_w.pop_front(); if (t[541:0] != r0) fail("SE row head 0", i);
                        t = tq_w.pop_front(); if (t[541:0] != r1) fail("SE row head 1", i);
                    end
                end else begin                                     // SO: one stop row = the two masked halves
                    nso = nso + 1;
                    if (tq_w.size() < 1) fail("stop SO rows short", i);
                    else begin
                        t = tq_w.pop_front();
                        if (r0[541:528] != t[541:528] || r1[541:528] != t[541:528]) fail("SO row addr", i);
                        if (r0[527:512] != 16'h00FF || r1[527:512] != 16'hFF00) fail("SO row mask", i);
                        if ({r1[511:256], r0[255:0]} != t[511:0]) fail("SO row data", i);
                    end
                end
            end
            if (tq_w.size() != 0) fail("stop rows left", tq_w.size());
            if (q_fu != {t_fu, t_fu} || q_fo != {t_fo, t_fo} || q_den != {t_den, t_den} || t_fo || t_fu)
                begin fail("status", 0); $display("status stop fu%b fo%b den%b share fu%b fo%b den%b", t_fu, t_fo, t_den, q_fu, q_fo, q_den); end
            // fixed latencies (DUT head 0): walk the jobs in order over the write cycles
            w = 0; l_se = -1; l_so = -1; for (i = 0; i < 8; i = i + 1) l_dn[i] = -1;
            for (jx = 0; jx < kinds.size(); jx = jx + 1) begin
                if (kinds[jx] == 4) begin
                    x = se_last.pop_front(); q = se_nv.pop_front();
                    if (w >= wc0.size()) fail("SE rows missing", jx);
                    else begin
                        if (l_se < 0) l_se = wc0[w] - x; else if (wc0[w] - x != l_se) fail("SE latency varies", jx);
                        for (i = 1; i < q; i = i + 1) if (wc0[w + i] != wc0[w] + i) fail("SE rows not back to back", jx);
                        x = wc0[w + q - 1];                           // the job's last e row
                        w = w + q;
                    end
                    if (den_cyc.size() == 0) fail("den missing", jx);
                    else begin
                        i = den_cyc.pop_front(); lt = clog2(q);
                        if (l_dn[lt] < 0) l_dn[lt] = i - x; else if (i - x != l_dn[lt]) fail("den latency varies", jx);
                    end
                end else begin
                    for (i = 0; i < 32; i = i + 1) begin
                        x = pv_cyc.pop_front();
                        if (w >= wc0.size()) begin fail("SO rows missing", jx); i = 32; end
                        else begin
                            if (l_so < 0) l_so = wc0[w] - x; else if (wc0[w] - x != l_so) fail("SO latency varies", jx);
                            w = w + 1;
                        end
                    end
                end
            end
            if (w != wc0.size()) fail("extra rows", wc0.size() - w);
            if (nchk < 400) fail("too few checks", nchk);
            $display("SMS stats MUT=%0d jobs=%0d se_rows=%0d so_rows=%0d checks=%0d", MUT, kinds.size(), nse, nso, nchk);
            $display("SMS latency (cycles at the share's pins): SE first e row = last score row + %0d, e rows back to back; SO o row k = P.V row k + %0d",
                     l_se, l_so);
            for (i = 0; i < 8; i = i + 1) if (l_dn[i] >= 0) $display("SMS latency: o_den = last e row + %0d at lt = clog2(nv) = %0d", l_dn[i], i);
            // the static schedule's published constants (lanes/S81U-2.md; the svc slice schedules its write window from them)
            if (l_se != 106) fail("SE latency != 106", l_se);
            if (l_so != 54) fail("SO latency != 54", l_so);
            for (i = 0; i < 8; i = i + 1) if (l_dn[i] >= 0 && l_dn[i] != 46 + 5 * i) fail("den latency != 46 + 5 lt", i);
            if(target_retires != 2*NJOB) fail("target retire count",target_retires);
            if(target_mut==0 && target_beats != 16*NJOB) fail("target fullshape beat count",target_beats);
            if(target_mut!=0 && target_bad_retires != 2*NJOB) fail("target mutant retirement count",target_bad_retires);
            $display("TARGET stats mut=%0d beats=%0d retires=%0d bad_retires=%0d operator_elements=%0d",target_mut,target_beats,target_retires,target_bad_retires,target_checks);
            if(err==0 && target_mut!=0) $display("TARGET CAUGHT mut=%0d fault_code=%h",target_mut,fc);
            if (target_mut == 0) begin
                if (smw_route == 1 && (gat_n[0] != 16*NJOB || gat_n[1] != 16*NJOB || gat_n[2] != 16*NJOB || gat_n[3] != 0))
                    begin smw_err = smw_err + 1; $display("SMWIRE MISMATCH line-route gather counts %0d %0d %0d %0d", gat_n[0], gat_n[1], gat_n[2], gat_n[3]); end
                if (smw_route == 2 && (gat_n[0] != 0 || gat_n[1] != 0 || gat_n[2] != 0 || gat_n[3] != 16*NJOB))
                    begin smw_err = smw_err + 1; $display("SMWIRE MISMATCH V-route gather counts %0d %0d %0d %0d", gat_n[0], gat_n[1], gat_n[2], gat_n[3]); end
                if (gat_latbad != 0 || gat_extra != 0) begin smw_err = smw_err + 1; $display("SMWIRE MISMATCH latency varies %0d / stray beats %0d", gat_latbad, gat_extra); end
                if (sot_f != 0 || gw_f != 0 || land_f || xr_f || rs_f != 0 || tfault != 0)
                    begin smw_err = smw_err + 1; $display("SMWIRE MISMATCH faults sot %b gw %b land %b xr %b rstop %b target %b", sot_f, gw_f, land_f, xr_f, rs_f, tfault); end
            end
            $display("SMWIRE stats mut=%0d route=%0d gather s3=%0d s4=%0d s2=%0d n3=%0d lat(head0 beat -> port) s3=%0d s4=%0d s2=%0d n3=%0d head1 +tree hop: s3=%0d checks=%0d faults sot %b gw %b land %b xr %b rstop %b",
                     smw_mut, smw_route, gat_n[0], gat_n[1], gat_n[2], gat_n[3], gat_lat[0], gat_lat[2], gat_lat[4], gat_lat[6], gat_lat[1],
                     smw_checks, sot_f, gw_f, land_f, xr_f, rs_f);
            if (smw_err == 0 && err == 0) $display("SMWIRE PASS mut=%0d route=%0d", smw_mut, smw_route);
            else $display("SMWIRE FAIL mut=%0d route=%0d errors=%0d", smw_mut, smw_route, smw_err + err);
            if (err == 0) $display("SMS PASS MUT=%0d checks=%0d", MUT, nchk);
            else $display("SMS FAIL MUT=%0d errors=%0d checks=%0d", MUT, err, nchk);
            $finish;
        end
    endtask
endmodule
