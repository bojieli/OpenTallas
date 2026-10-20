#!/usr/bin/env python3
"""S81-SMWIRE (10-19): derive the END-TO-END SO wiring bench tb_smwire_e2e from the operator-backed target bench
tb_sm_so_target (itself the unchanged exact SMS bench + target).  The two real SMS DUT heads (heads 2 TI, 2 TI + 1) and
the two independent real slab-reference heads stay; everything after the SM write face is the REAL die RTL:

  q stream (WIN_LOAD + SOT frames, compiler encoding)  -> dsdv_svc_sot x2 (config source, owner check)
  SMS w_* face + SMJ announce                          -> dsdv_sm_so_target x2 (HEAD = -1: head strap pin)
  target beats                                         -> dsdv_sm_gw x2 (3 return-tree words a beat)
  return-tree merge (bench stand-in for the svc_rs P.V tree: head 1 one hop = 5 edges further; two words in one
  cycle FAILS) -> dsdv_sm_gx (entry stamp, the head-0 slice is the entry) -> 2 relay stages (the 562-b pv lane)
  -> dsfd_dvland_pvrd (landing, forwarded clock +300 ps, K 2) -> ot_s81sl_xr HB 1 (C3 band port B, sid 6 = s_3S)
  -> ot_s81sl_rstop x4: s_3S (injector), s_4S (E neighbour), s_2S (W neighbour), s_3N (V partner)

Checked at the x-streamer gather ports (ot_s81sl_xs g_v / g_fam / g_idx / g_d, the WO_A x receiver ABI), bit-exact
against the reference operator rows: route 1 (tier line, +SMW_ROUTE=1, default): every beat once at s_3S (source 0),
s_4S (source 1, from W) and s_2S (source 2, from E), BF16 family, idx 8 (head % 8) + beat, nothing at s_3N; route 2
(+SMW_ROUTE=2): every beat once at s_3N (source 0, V-assembled), nothing on the injector's line.  Plus: no fault
anywhere (sot, target, gw, landing, xr, rstop), fixed latencies (target beat -> gather port) constant per route.
Bench-side mutants (+SMW_MUT=n, one build) must each FAIL:  1 WIN_LOAD tag differs from the SOT owner (config refused),
2 lo / hi words swapped on the lane, 3 entry gather window closes before head 1 (its words land as P.V RD beats),
4 route bits dropped on the lane, 5 header idx bit flipped on the lane.  TARGET_MUT 1..5 (the original causal target
mutants) still apply.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[3]
src = root / 'rtl/dsrom_sys/s81_dv/sm_target/test/tb_sm_so_target.sv'
out = root / 'rtl/dsrom_sys/s81_dv/sm_target/test/tb_smwire_e2e.sv'
s = src.read_text().replace('module tb_sm_so_target;', 'module tb_smwire_e2e;')


def rep(a, b, n=1):
    global s
    assert s.count(a) == n, (s.count(a), a[:80])
    s = s.replace(a, b)


rep('''        dsdv_sm_so_target #(.HEAD(2*TI+th)) u_target (
            .clk(clk),.rst_n(rst),.cfg_v(cfg_v),.cfg_owner(target_owner),
            .cfg_se_jid(expected_se),.cfg_so_jid(expected_so),.cfg_obase(target_base),
            .cfg_first(16'd0),.cfg_last(16'd1200),.cfg_read(16'd1300),.cfg_retire(16'd1350),
            .op_st(q_st),.op_kind(q_kind),.op_jid(q_jid),''',
    '''        // S81-SMWIRE: the config comes from the SOT frame on the q stream (dsdv_svc_sot), never from the bench regs
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
            .op_st(q_st),.op_kind(q_kind),.op_jid(q_jid),''')
rep('''            .fault(tfault[th]),.fault_code(fc[12*th+:12]));
    end endgenerate''', '''            .fault(tfault[th]),.fault_code(fc[12*th+:12]));
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
    end''')
# shared wires / regs before the target generate block
rep('''    initial if (!$value$plusargs("TARGET_MUT=%d", target_mut)) target_mut=0;''',
    '''    initial if (!$value$plusargs("TARGET_MUT=%d", target_mut)) target_mut=0;
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
    wire s_cfg_any = g_target[0].s_cfg_v | g_target[1].s_cfg_v;''')
rep('''        if (cfg_v) begin
            ref_count=0; got[0]=0; got[1]=0;''', '''        if (s_cfg_any) begin
            ref_count=0; got[0]=0; got[1]=0;''')
# SOT / WIN_LOAD frames instead of the bench cfg pulse
rep('''                cfg_v=1; tick; cfg_v=0; repeat(2) tick;''',
    '''                send_sot(jj);''')
rep('''    task tick; begin @(posedge clk); #0.1; end endtask''',
    '''    task tick; begin @(posedge clk); #0.1; end endtask
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
    endtask''')
# final verdict
rep('''            if (err == 0) $display("SMS PASS MUT=%0d checks=%0d", MUT, nchk);''',
    '''            if (target_mut == 0) begin
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
            if (err == 0) $display("SMS PASS MUT=%0d checks=%0d", MUT, nchk);''')
out.write_text(s)
print(out)
