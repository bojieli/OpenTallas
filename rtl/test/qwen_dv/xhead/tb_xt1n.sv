`timescale 1ns/1ps
// QW-DIEFIX-NFAR XT1n (10-19): the N side of one dv2f16 column piece at its real RTL -- the qfd_dv_slice2 core as dvs_W5
// (sid 0, heads with the ea371ad83 corridor retag) whose four N column-head corridor words cw_n0..3 drive the NEAR band-2
// cluster c16_W5_2 (cid 2, far 0) and, through its bco0..3, the FAR cluster c16_W5_3 (cid 3, far 1), wired exactly as
// dv2f16 out/case/die.v: n_q3h_col_<i>_2 = cw_n<i> -> c16_W5_2.bc<i>; n_q3h_far_W5_2_<i> = c16_W5_2.bco<i> -> c16_W5_3.bc<i>;
// n_dv_rsi_W5_3 = c16_W5_3.rs -> c16_W5_2.rs_i; c16_W5_3.rs_i = 0; slice rs_n = {c16_W5_2.rs_o (far feedthrough), c16_W5_2.rs}.
// Cluster RTL = dv2f16 (regional resets rst_c<c>r<r>, all tied to the bench reset here).  All 32 tiles' code ROMs bound to their strap (ROM_TILE = 16 cid + kslice of tile_id) and loaded from +OT_ROM_DIR.
// Events as tb_xt1 (+EV: 0 cmd_i, 1 hr_i slice layout, 2 st_up_i).  Log: HRGO / CWGO (cw_n) / RS (near rs) / RSO (rs_o) /
// FAULT / END.  Mutants (oldtags = heads without the retag; romswap = masks) are applied to the sources / masks, not here.
module tb_xt1n (input wire ck);
    reg rst_n = 1'b0;
    reg  [115:0]  cmd0;
    reg  [452:0]  hr0;
    reg  [1087:0] swi;
    wire [515:0]  cw_n0, cw_n1, cw_n2, cw_n3, bf0, bf1, bf2, bf3;
    wire [513:0]  rs, rs_o, rs_far;
    wire [106:0]  st;
    qfd_dv_slice2 #(.MUT(0)) u_s (.ck(ck), .rst_n(rst_n), .cmd_i(cmd0), .cmd_o(), .hr_i(hr0), .hr_o(),
        .rs_s(1028'd0), .rs_n({rs_o, rs}), .l9_i(514'd0), .l9_o(),
        .st_up_i(swi), .st_up_o(), .st_dn_i(1088'd0), .st_dn_o(),
        .sc_up_i(48'd0), .sc_up_o(), .sc_dn_i(48'd0), .sc_dn_o(),
        .ch_up_i(1095'd0), .ch_dn_o(), .ch_dn_i(1038'd0), .ch_up_o(),
        .cw_n0(cw_n0), .cw_n1(cw_n1), .cw_n2(cw_n2), .cw_n3(cw_n3), .cw_s0(), .cw_s1(), .cw_s2(), .cw_s3(), .st(st),
        .cc_o(), .ag_up_i(10'd0), .ag_dn_o());
    qfd_c_b16_dv u_cn (.ck_c0r0(ck), .ck_c0r1(ck), .ck_c0r2(ck), .ck_c0r3(ck), .ck_c1r0(ck), .ck_c1r1(ck), .ck_c1r2(ck), .ck_c1r3(ck), .ck_c2r0(ck), .ck_c2r1(ck), .ck_c2r2(ck), .ck_c2r3(ck), .ck_c3r0(ck), .ck_c3r1(ck), .ck_c3r2(ck), .ck_c3r3(ck),
        .rst_c0r0(rst_n), .rst_c0r1(rst_n), .rst_c0r2(rst_n), .rst_c0r3(rst_n), .rst_c1r0(rst_n), .rst_c1r1(rst_n), .rst_c1r2(rst_n), .rst_c1r3(rst_n), .rst_c2r0(rst_n), .rst_c2r1(rst_n), .rst_c2r2(rst_n), .rst_c2r3(rst_n), .rst_c3r0(rst_n), .rst_c3r1(rst_n), .rst_c3r2(rst_n), .rst_c3r3(rst_n),
        .far(1'b0), .cid(12'd2),
        .bc0(cw_n0), .bco0(bf0), .bc1(cw_n1), .bco1(bf1), .bc2(cw_n2), .bco2(bf2), .bc3(cw_n3), .bco3(bf3),
        .rs(rs), .rs_i(rs_far), .rs_o(rs_o), .tie_hi(), .tie_lo());
    qfd_c_b16_dv u_cf (.ck_c0r0(ck), .ck_c0r1(ck), .ck_c0r2(ck), .ck_c0r3(ck), .ck_c1r0(ck), .ck_c1r1(ck), .ck_c1r2(ck), .ck_c1r3(ck), .ck_c2r0(ck), .ck_c2r1(ck), .ck_c2r2(ck), .ck_c2r3(ck), .ck_c3r0(ck), .ck_c3r1(ck), .ck_c3r2(ck), .ck_c3r3(ck),
        .rst_c0r0(rst_n), .rst_c0r1(rst_n), .rst_c0r2(rst_n), .rst_c0r3(rst_n), .rst_c1r0(rst_n), .rst_c1r1(rst_n), .rst_c1r2(rst_n), .rst_c1r3(rst_n), .rst_c2r0(rst_n), .rst_c2r1(rst_n), .rst_c2r2(rst_n), .rst_c2r3(rst_n), .rst_c3r0(rst_n), .rst_c3r1(rst_n), .rst_c3r2(rst_n), .rst_c3r3(rst_n),
        .far(1'b1), .cid(12'd3),
        .bc0(bf0), .bco0(), .bc1(bf1), .bco1(), .bc2(bf2), .bco2(), .bc3(bf3), .bco3(),
        .rs(rs_far), .rs_i(514'd0), .rs_o(), .tie_hi(), .tie_lo());
    // ROM binding (Verilator defparams take constants): ROM_TILE = 16 cid + the slot's tile_id tie bits (tl 0 / th 1)
    defparam u_cn.u_t_0_0.ROM_TILE = 32;
    defparam u_cn.u_t_0_1.ROM_TILE = 34;
    defparam u_cn.u_t_0_2.ROM_TILE = 40;
    defparam u_cn.u_t_0_3.ROM_TILE = 42;
    defparam u_cn.u_t_1_0.ROM_TILE = 33;
    defparam u_cn.u_t_1_1.ROM_TILE = 35;
    defparam u_cn.u_t_1_2.ROM_TILE = 41;
    defparam u_cn.u_t_1_3.ROM_TILE = 43;
    defparam u_cn.u_t_2_0.ROM_TILE = 36;
    defparam u_cn.u_t_2_1.ROM_TILE = 38;
    defparam u_cn.u_t_2_2.ROM_TILE = 44;
    defparam u_cn.u_t_2_3.ROM_TILE = 46;
    defparam u_cn.u_t_3_0.ROM_TILE = 37;
    defparam u_cn.u_t_3_1.ROM_TILE = 39;
    defparam u_cn.u_t_3_2.ROM_TILE = 45;
    defparam u_cn.u_t_3_3.ROM_TILE = 47;
    defparam u_cf.u_t_0_0.ROM_TILE = 48;
    defparam u_cf.u_t_0_1.ROM_TILE = 50;
    defparam u_cf.u_t_0_2.ROM_TILE = 56;
    defparam u_cf.u_t_0_3.ROM_TILE = 58;
    defparam u_cf.u_t_1_0.ROM_TILE = 49;
    defparam u_cf.u_t_1_1.ROM_TILE = 51;
    defparam u_cf.u_t_1_2.ROM_TILE = 57;
    defparam u_cf.u_t_1_3.ROM_TILE = 59;
    defparam u_cf.u_t_2_0.ROM_TILE = 52;
    defparam u_cf.u_t_2_1.ROM_TILE = 54;
    defparam u_cf.u_t_2_2.ROM_TILE = 60;
    defparam u_cf.u_t_2_3.ROM_TILE = 62;
    defparam u_cf.u_t_3_0.ROM_TILE = 53;
    defparam u_cf.u_t_3_1.ROM_TILE = 55;
    defparam u_cf.u_t_3_2.ROM_TILE = 61;
    defparam u_cf.u_t_3_3.ROM_TILE = 63;

    integer fd, lg, cyc, ncyc, ec, ep, r, pre = 0;
    reg [1087:0] ev;
    reg have, hdf, stf, rsf, rof;
    reg [1023:0] evf, lgf;
    wire [3:0] cwgo = {cw_n3[0], cw_n2[0], cw_n1[0], cw_n0[0]};
    task automatic apply(input integer p, input [1087:0] v);
        begin
            if (p == 0) cmd0 = v[115:0];
            else if (p == 1) hr0 = v[452:0];
            else if (p == 2) swi = v;
            else $fatal(1, "bad port %0d", p);
        end
    endtask
    initial begin
        if (!$value$plusargs("EV=%s", evf)) $fatal(1, "+EV");
        if (!$value$plusargs("LOG=%s", lgf)) $fatal(1, "+LOG");
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 4000;
        fd = $fopen(evf, "r"); lg = $fopen(lgf, "w");
        cmd0 = 0; hr0 = 0; swi = 0; cyc = 0; hdf = 0; stf = 0; rsf = 0; rof = 0;
        r = $fscanf(fd, "%d %d %h\n", ec, ep, ev); have = (r == 3);
    end
    always @(negedge ck) begin
        if (pre < 4) begin pre = pre + 1; if (pre == 4) rst_n = 1'b1; end
        else begin
            if (hr0[452]) $fdisplay(lg, "%0d HRGO", cyc);
            if (hr0[1])   $fdisplay(lg, "%0d HRXPF", cyc);
            if (|cwgo)    $fdisplay(lg, "%0d CWGO %h", cyc, cwgo);
            if (rs[512] || rs[513]) $fdisplay(lg, "%0d RS %0d %h", cyc, rs[513], rs[511:0]);
            if (rs_o[512] || rs_o[513]) $fdisplay(lg, "%0d RSO %0d %h", cyc, rs_o[513], rs_o[511:0]);
            if (u_s.hd_fault && !hdf) begin $fdisplay(lg, "%0d FAULT heads", cyc); hdf = 1; end
            if (u_s.stm_fault && !stf) begin $fdisplay(lg, "%0d FAULT stream", cyc); stf = 1; end
            if (rs[513] && !rsf) begin $fdisplay(lg, "%0d FAULT near_cluster", cyc); rsf = 1; end
            if (rs_o[513] && !rof) begin $fdisplay(lg, "%0d FAULT far_cluster", cyc); rof = 1; end
            cmd0 = 0; hr0 = 0; swi = 0;
            while (have && ec == cyc) begin
                apply(ep, ev);
                r = $fscanf(fd, "%d %d %h\n", ec, ep, ev); have = (r == 3);
            end
            if (have && ec < cyc) $fatal(1, "event file not sorted at cycle %0d", ec);
            cyc = cyc + 1;
            if (cyc >= ncyc) begin
                $fdisplay(lg, "%0d END hd_fault %0d stm_fault %0d near_fault %0d far_fault %0d", cyc, u_s.hd_fault, u_s.stm_fault, rsf, rof);
                $fclose(lg);
                $finish;
            end
        end
    end
endmodule
