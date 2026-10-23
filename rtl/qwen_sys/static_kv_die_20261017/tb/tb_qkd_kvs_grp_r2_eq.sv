`timescale 1ns/1ps
// KDIE5-RTL 2026-10-22: lockstep equivalence of qkd_kvs_grp_r2 (define GRP_H: qkd_kvs_grp_h_r2) against the UNCHANGED
// release module (qkd_kvs_tiles_hroot_ff_k_hl_mu_ba_n32_pj.sv) fed the same random inputs with the successor's documented
// delays: u_core i_ctl +LOC edges (LOC = 1 + 4 * tap, tap = 7 - depth of the strap +GRP=n), the four cf1 fault bits
// i_pc<q>[290] +2.  Checked every edge after the flush: rsp / krsp / af__fault / o_pc* equal on the same edge;
// o_dn = rotated i_ctl +4 (grp_h +2); o_ctl[143:18] = i_up[125:0] +4; own o_ctl[17:0] = reference own +3 (grp_h: all 8
// copies); y__* = x__* +2.  One line 'GRP_R2 PASS|FAIL ...'.  Mutants: compile with +define+KVS_GRP_R2_MUTn (must FAIL).
module tb;
`ifdef GRP_H
    localparam H = 1;
`else
    localparam H = 0;
`endif
    reg ck = 0, hck = 0;
    always #5 ck = ~ck;
    always #6.4 hck = ~hck;
    reg rst_n = 0, hrst_n = 0;
    reg [2:0] grp;
    reg [0:0] afk, afv, afu;
    reg [37:0] kreq; reg [14:0] vreq; reg [12:0] x__est; reg [17:0] x__tok; reg [15:0] x__tep;
    reg [270:0] i_ctl; reg [304:0] i_pc0, i_pc1, i_pc2, i_pc3; reg [143:0] i_up;
    wire [1055:0] rsp_d, rsp_r; wire [1061:0] krsp_d, krsp_r; wire [0:0] af_d, af_r;
    wire [0:0] ye_d, ye_r; wire [17:0] yt_d, yt_r; wire [15:0] yp_d, yp_r;
    wire [127:0] p0_d, p1_d, p2_d, p3_d, p0_r, p1_r, p2_r, p3_r;
    wire [270:0] dn_d, dn_r; wire [143:0] oc_d, oc_r;
    // reference input delay lines
    reg [270:0] ctl_h [0:40]; reg [3:0] flt_h [0:4]; reg [143:0] up_h [0:8]; reg [34:0] x_h [0:4]; reg [17:0] own_h [0:4];
    integer LOC, i;
    function [2:0] tap_of(input [2:0] n);
        case (n) 3'd7: tap_of = 7; 3'd6: tap_of = 6; 3'd3: tap_of = 5; 3'd2: tap_of = 4; 3'd1: tap_of = 3; 3'd0: tap_of = 2;
                 3'd5: tap_of = 1; default: tap_of = 0; endcase
    endfunction
    wire [270:0] ctl_ref = ctl_h[LOC - 1];
    wire [3:0] flt_ref = flt_h[1];
    wire [304:0] r_pc0 = {i_pc0[304:291], flt_ref[0], i_pc0[289:0]};
    wire [304:0] r_pc1 = {i_pc1[304:291], flt_ref[1], i_pc1[289:0]};
    wire [304:0] r_pc2 = {i_pc2[304:291], flt_ref[2], i_pc2[289:0]};
    wire [304:0] r_pc3 = {i_pc3[304:291], flt_ref[3], i_pc3[289:0]};
`ifdef GRP_H
    qkd_kvs_grp_h_r2 dut (.ck(ck), .rst_n(rst_n), .afk(afk), .afv(afv), .hck(hck), .hrst_n(hrst_n), .slg__cfg_stack(2'd1),
        .slg__cfg_group(grp), .kreq(kreq), .vreq(vreq), .x__est(x__est), .x__tok(x__tok), .x__tep(x__tep), .rsp(rsp_d),
        .krsp(krsp_d), .af__fault(af_d), .y__est__0_1(ye_d), .y__tok(yt_d), .y__tep(yp_d), .i_ctl(i_ctl), .i_pc0(i_pc0),
        .i_pc1(i_pc1), .i_pc2(i_pc2), .i_pc3(i_pc3), .o_pc0(p0_d), .o_pc1(p1_d), .o_pc2(p2_d), .o_pc3(p3_d), .o_dn(dn_d),
        .o_ctl(oc_d));
    qkd_kvs_grp_h ref0 (.ck(ck), .rst_n(rst_n), .afk(afk), .afv(afv), .hck(hck), .hrst_n(hrst_n), .slg__cfg_stack(2'd1),
        .slg__cfg_group(grp), .kreq(kreq), .vreq(vreq), .x__est(x__est), .x__tok(x__tok), .x__tep(x__tep), .rsp(rsp_r),
        .krsp(krsp_r), .af__fault(af_r), .y__est__0_1(ye_r), .y__tok(yt_r), .y__tep(yp_r), .i_ctl(ctl_ref), .i_pc0(r_pc0),
        .i_pc1(r_pc1), .i_pc2(r_pc2), .i_pc3(r_pc3), .o_pc0(p0_r), .o_pc1(p1_r), .o_pc2(p2_r), .o_pc3(p3_r), .o_dn(dn_r),
        .o_ctl(oc_r));
`else
    qkd_kvs_grp_r2 dut (.ck(ck), .rst_n(rst_n), .afk(afk), .afv(afv), .afu(afu), .hck(hck), .hrst_n(hrst_n), .slg__cfg_stack(2'd1),
        .slg__cfg_group(grp), .kreq(kreq), .vreq(vreq), .x__est(x__est), .x__tok(x__tok), .x__tep(x__tep), .rsp(rsp_d),
        .krsp(krsp_d), .af__fault(af_d), .y__est__0_1(ye_d), .y__tok(yt_d), .y__tep(yp_d), .i_ctl(i_ctl), .i_pc0(i_pc0),
        .i_pc1(i_pc1), .i_pc2(i_pc2), .i_pc3(i_pc3), .o_pc0(p0_d), .o_pc1(p1_d), .o_pc2(p2_d), .o_pc3(p3_d), .o_dn(dn_d),
        .i_up(i_up), .o_ctl(oc_d));
    qkd_kvs_grp ref0 (.ck(ck), .rst_n(rst_n), .afk(afk), .afv(afv), .afu(afu), .hck(hck), .hrst_n(hrst_n), .slg__cfg_stack(2'd1),
        .slg__cfg_group(grp), .kreq(kreq), .vreq(vreq), .x__est(x__est), .x__tok(x__tok), .x__tep(x__tep), .rsp(rsp_r),
        .krsp(krsp_r), .af__fault(af_r), .y__est__0_1(ye_r), .y__tok(yt_r), .y__tep(yp_r), .i_ctl(ctl_ref), .i_pc0(r_pc0),
        .i_pc1(r_pc1), .i_pc2(r_pc2), .i_pc3(r_pc3), .o_pc0(p0_r), .o_pc1(p1_r), .o_pc2(p2_r), .o_pc3(p3_r), .o_dn(dn_r),
        .i_up(144'd0), .o_ctl(oc_r));
`endif
    function [270:0] rot(input [270:0] v); rot = {v[193:183], v[270:194], v[182:0]}; endfunction
    integer cyc, err = 0, checks = 0, E;
    reg [270:0] dn_exp; reg [143:0] oc_exp; reg [34:0] y_exp;
    task automatic randin;
        integer j;
        begin
            afk = $urandom; afv = $urandom; afu = $urandom; kreq = {$urandom, $urandom}; vreq = $urandom;
            x__est = $urandom; x__tok = $urandom; x__tep = $urandom;
            for (j = 0; j < 9; j = j + 1) i_ctl[j * 32 +: 32] = $urandom;
            for (j = 0; j < 10; j = j + 1) begin
                i_pc0[j * 32 +: 32] = $urandom; i_pc1[j * 32 +: 32] = $urandom;
                i_pc2[j * 32 +: 32] = $urandom; i_pc3[j * 32 +: 32] = $urandom;
            end
            for (j = 0; j < 5; j = j + 1) i_up[j * 32 +: 32] = $urandom;
            // sparse strobes (fan word go / cfg we bits) so the calendars run real sequences, not every-edge pulses
            if ($urandom % 4 != 0) i_ctl[193:174] = i_ctl[193:174] & {20{($urandom % 8) == 0}};
        end
    endtask
    initial begin
        if (!$value$plusargs("GRP=%d", grp)) grp = H ? 3'd4 : 3'd7;
        if (!$value$plusargs("EDGES=%d", E)) E = 4000;
        LOC = 1 + 4 * tap_of(grp);
        for (i = 0; i <= 40; i = i + 1) ctl_h[i] = 0;
        for (i = 0; i <= 4; i = i + 1) begin flt_h[i] = 0; x_h[i] = 0; own_h[i] = 0; end
        for (i = 0; i <= 8; i = i + 1) up_h[i] = 0;
        randin();
        for (cyc = 0; cyc < E; cyc = cyc + 1) begin
            @(negedge ck);
            // checks on the settled post-edge state (expected = history BEFORE this edge's shift: index k = k + 1 edges old)
            if (cyc > 64) begin
                dn_exp = rot(H ? ctl_h[1] : ctl_h[3]);
                oc_exp = H ? {8{own_h[2]}} : {up_h[3][125:0], own_h[2]};
                y_exp = x_h[1];
                checks = checks + 1;
                if (rsp_d !== rsp_r || krsp_d !== krsp_r || af_d !== af_r || p0_d !== p0_r || p1_d !== p1_r ||
                    p2_d !== p2_r || p3_d !== p3_r || dn_d !== dn_exp || oc_d !== oc_exp || {yp_d, yt_d, ye_d} !== y_exp) begin
                    if (err < 5) $display("MISMATCH cyc %0d rsp %0d krsp %0d af %0d pc %0d dn %0d oc %0d y %0d", cyc,
                        rsp_d !== rsp_r, krsp_d !== krsp_r, af_d !== af_r, {p0_d, p1_d, p2_d, p3_d} !== {p0_r, p1_r, p2_r, p3_r},
                        dn_d !== dn_exp, oc_d !== oc_exp, {yp_d, yt_d, ye_d} !== y_exp);
                    err = err + 1;
                end
            end
            if (cyc == 48) begin rst_n = 1; hrst_n = 1; end
            randin();
        end
        if (H) $display("GRP_R2 %s tile=grp_h_r2 grp=%0d loc=%0d checks=%0d errors=%0d", err == 0 && checks > 0 ? "PASS" : "FAIL",
                        grp, LOC, checks, err);
        else   $display("GRP_R2 %s tile=grp_r2 grp=%0d loc=%0d checks=%0d errors=%0d", err == 0 && checks > 0 ? "PASS" : "FAIL",
                        grp, LOC, checks, err);
        $finish;
    end
    // history registers shift on the edge with the values the DUT sampled
    always @(posedge ck) begin
        for (i = 40; i > 0; i = i - 1) ctl_h[i] <= ctl_h[i - 1];
        ctl_h[0] <= i_ctl;
        for (i = 4; i > 0; i = i - 1) begin flt_h[i] <= flt_h[i - 1]; x_h[i] <= x_h[i - 1]; own_h[i] <= own_h[i - 1]; end
        flt_h[0] <= {i_pc3[290], i_pc2[290], i_pc1[290], i_pc0[290]};
        x_h[0] <= {x__tep, x__tok, x__est[0]};
        own_h[0] <= oc_r[17:0];
        for (i = 8; i > 0; i = i - 1) up_h[i] <= up_h[i - 1];
        up_h[0] <= i_up;
    end
endmodule
