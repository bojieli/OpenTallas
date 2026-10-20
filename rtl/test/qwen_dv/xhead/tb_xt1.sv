`timescale 1ns/1ps
// QW-XHEAD XT1 (10-19): one column piece of the dv2f14bi compute die at its real RTL -- the qfd_dv_slice2 core as dvs_W5
// (sid 0) whose four column-head S corridor words cw_s0..3 drive the near band-1 cluster c16_W5_1 (qfd_c_b16_dv, cid 1,
// far 0, rs_i idle: die.v nets n_q3h_col_<i>_1 / n_dv_rs_W5_1_a, no relay between them), every tile's code ROM bound to
// its strap (ROM_TILE = 16 cid + kslice) and loaded from +OT_ROM_DIR (real TP8 rank-0 L0 masks, xt1_prep.py).
// Events (+EV, sorted "cycle port hex"): 0 cmd_i (116 b), 1 hr_i (453 b, the slice's {go, ib 379, xpf 72, v} layout),
// 2 st_up_i (1088-b stream word).  Log (+LOG): HR / CWGO<i> / RS / XT / FAULT lines, edge = negedge cycle index.
// ROMSWAP (bench mutant) is applied to the mask files, not here.
module tb_xt1 (input wire ck);
    parameter integer CID = 1;
    reg rst_n = 1'b0;
    reg  [115:0]  cmd0;
    reg  [452:0]  hr0;
    reg  [1087:0] swi;
    wire [515:0]  cw_s0, cw_s1, cw_s2, cw_s3;
    wire [513:0]  rs, rs_o;
    wire [106:0]  st;
    qfd_dv_slice2 #(.MUT(0)) u_s (.ck(ck), .rst_n(rst_n), .cmd_i(cmd0), .cmd_o(), .hr_i(hr0), .hr_o(),
        .rs_s(1028'd0), .rs_n(1028'd0), .l9_i(514'd0), .l9_o(),
        .st_up_i(swi), .st_up_o(), .st_dn_i(1088'd0), .st_dn_o(),
        .sc_up_i(48'd0), .sc_up_o(), .sc_dn_i(48'd0), .sc_dn_o(),
        .ch_up_i(1095'd0), .ch_dn_o(), .ch_dn_i(1038'd0), .ch_up_o(),
        .cw_n0(), .cw_n1(), .cw_n2(), .cw_n3(), .cw_s0(cw_s0), .cw_s1(cw_s1), .cw_s2(cw_s2), .cw_s3(cw_s3), .st(st),
        .cc_o(), .ag_up_i(10'd0), .ag_dn_o());
    qfd_c_b16_dv u_c (
        .ck_c0r0(ck), .ck_c0r1(ck), .ck_c0r2(ck), .ck_c0r3(ck), .ck_c1r0(ck), .ck_c1r1(ck), .ck_c1r2(ck), .ck_c1r3(ck),
        .ck_c2r0(ck), .ck_c2r1(ck), .ck_c2r2(ck), .ck_c2r3(ck), .ck_c3r0(ck), .ck_c3r1(ck), .ck_c3r2(ck), .ck_c3r3(ck),
        .rst_n(rst_n), .far(1'b0), .cid(12'(CID)),
        .bc0(cw_s0), .bco0(), .bc1(cw_s1), .bco1(), .bc2(cw_s2), .bco2(), .bc3(cw_s3), .bco3(),
        .rs(rs), .rs_i(514'd0), .rs_o(rs_o), .tie_hi(), .tie_lo());
    // ROM binding (CID 1 literals: Verilator defparams take constants only): tile (c, r) strap = {cid, the slot's tie bits} (qfd_c_b16_dv tile_id), ROM_TILE = 16 cid + that kslice
    defparam u_c.u_t_0_0.ROM_TILE = 16;  defparam u_c.u_t_0_1.ROM_TILE = 18;
    defparam u_c.u_t_0_2.ROM_TILE = 24;  defparam u_c.u_t_0_3.ROM_TILE = 26;
    defparam u_c.u_t_1_0.ROM_TILE = 17;  defparam u_c.u_t_1_1.ROM_TILE = 19;
    defparam u_c.u_t_1_2.ROM_TILE = 25;  defparam u_c.u_t_1_3.ROM_TILE = 27;
    defparam u_c.u_t_2_0.ROM_TILE = 20;  defparam u_c.u_t_2_1.ROM_TILE = 22;
    defparam u_c.u_t_2_2.ROM_TILE = 28; defparam u_c.u_t_2_3.ROM_TILE = 30;
    defparam u_c.u_t_3_0.ROM_TILE = 21;  defparam u_c.u_t_3_1.ROM_TILE = 23;
    defparam u_c.u_t_3_2.ROM_TILE = 29; defparam u_c.u_t_3_3.ROM_TILE = 31;

    integer fd, lg, cyc, ncyc, ec, ep, r, i, pre = 0;
    reg [1087:0] ev;
    reg have, hdf, stf, rsf;
    reg [1023:0] evf, lgf;
    wire [3:0] cwgo = {cw_s3[0], cw_s2[0], cw_s1[0], cw_s0[0]};
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
        cmd0 = 0; hr0 = 0; swi = 0; cyc = 0; hdf = 0; stf = 0; rsf = 0;
        r = $fscanf(fd, "%d %d %h\n", ec, ep, ev); have = (r == 3);
    end
    always @(negedge ck) begin
        if (pre < 4) begin pre = pre + 1; if (pre == 4) rst_n = 1'b1; end
        else begin
            if (hr0[452]) $fdisplay(lg, "%0d HRGO", cyc);
            if (hr0[1])   $fdisplay(lg, "%0d HRXPF", cyc);
            if (|cwgo)    $fdisplay(lg, "%0d CWGO %h", cyc, cwgo);
            if (u_s.xt_v) $fdisplay(lg, "%0d XT %h", cyc, u_s.xt_a);
            if (rs[512] || rs[513]) $fdisplay(lg, "%0d RS %0d %h", cyc, rs[513], rs[511:0]);
            // tile (0,0) = strap 16 cid (groups 64 cid .. +3) face trace: tap go + ib, x window, tile output
            if (u_c.tap_0_0[0]) $fdisplay(lg, "%0d TGO %h", cyc, u_c.tap_0_0[379:1]);
            if (|u_c.tap_0_0[507:380]) $fdisplay(lg, "%0d TX %h", cyc, u_c.tap_0_0[507:380]);
            if (u_c.t_out_0_0[512] || u_c.t_out_0_0[513]) $fdisplay(lg, "%0d TOUT %0d %h", cyc, u_c.t_out_0_0[513], u_c.t_out_0_0[511:0]);
            if (u_s.hd_fault && !hdf) begin $fdisplay(lg, "%0d FAULT heads", cyc); hdf = 1; end
            if (u_s.stm_fault && !stf) begin $fdisplay(lg, "%0d FAULT stream", cyc); stf = 1; end
            if (rs[513] && !rsf) begin $fdisplay(lg, "%0d FAULT cluster", cyc); rsf = 1; end
            cmd0 = 0; hr0 = 0; swi = 0;
            while (have && ec == cyc) begin
                apply(ep, ev);
                r = $fscanf(fd, "%d %d %h\n", ec, ep, ev); have = (r == 3);
            end
            if (have && ec < cyc) $fatal(1, "event file not sorted at cycle %0d", ec);
            cyc = cyc + 1;
            if (cyc >= ncyc) begin
                $fdisplay(lg, "%0d END hd_fault %0d stm_fault %0d rs_fault %0d", cyc, u_s.hd_fault, u_s.stm_fault, rsf);
                $fclose(lg);
                $finish;
            end
        end
    end
endmodule
