`timescale 1ns/1ps
// struct-close 2026-10-09: ot_su12_sfu RSTPIPE=1 (registered lane reset) in LOCK-STEP with RSTPIPE=0 (the closed lane).
// Same reset (held 12 edges), idle inputs for 8 edges after release, then NCYC edges of random broadcast / command /
// response inputs (both instances get identical stimulus); every output is compared on every edge.  MUT=1 never
// releases the RSTPIPE=1 instance from reset, which must mismatch.  Reset windows (and 40 idle drain edges before each) are
// not compared: RSTPIPE=1 enters and leaves reset one edge later, by design.
module tb_sfu_reset_tree;
    parameter integer NCYC = 4000, SEED = 1, MUT = 0;
    reg clk = 0; always #0.5 clk = ~clk;
    reg rst_n = 0, rst_n_m = 0;
    reg ld, ld_bank, emit, bank, cpair, cx_arnd, cx_arelu, cx_amin, cx_cclip, co_rnd;
    reg [1199:0] ld_c; reg [23:0] o_v, i_v, no, ni, krow, obase, aibase; reg [3:0] ls, lvw; reg [119:0] vb;
    reg [1:0] aind, dst, cm_m2, ce_e2, co_dst; reg [4:0] gsh; reg [7:0] srcs;
    reg [31:0] vi_q, cx_imm3, cp_imm1, cm_imm1, ca_imm2, cs_imm2, ce_imm1, side_y; reg [127:0] rd_q;
    reg [2:0] cp_m1, cm_m1, cm_qm, ca_ad, ci_sfu, cs_sfu, cs_e1;
    wire [400:0] oa, ob;
    `define SFU_INST(NAME, R, RST, OUT) \
    ot_su12_sfu #(.GSH(1), .KIMM(1), .DENR(1), .DRING(3), .RSTPIPE(R)) NAME (.clk(clk), .rst_n(RST), .ld(ld), .ld_bank(ld_bank), \
      .ld_c(ld_c), .emit(emit), .bank(bank), .o_v(o_v), .i_v(i_v), .no(no), .ni(ni), .ls(ls), .lvw(lvw), .vb(vb), .krow(krow), \
      .obase(obase), .aibase(aibase), .aind(aind), .gsh(gsh), .cpair(cpair), .dst(dst), .srcs(srcs), .vi_re(OUT[0]), \
      .vi_addr(OUT[24:1]), .vi_q(vi_q), .rd_addr(OUT[120:25]), .rd_re(OUT[124:121]), .rd_src(OUT[132:125]), .rd_q(rd_q), \
      .cx_arnd(cx_arnd), .cx_arelu(cx_arelu), .cx_amin(cx_amin), .cx_cclip(cx_cclip), .cx_imm3(cx_imm3), .cp_m1(cp_m1), \
      .cp_imm1(cp_imm1), .cm_m1(cm_m1), .cm_m2(cm_m2), .cm_qm(cm_qm), .cm_imm1(cm_imm1), .ca_ad(ca_ad), .ca_imm2(ca_imm2), \
      .ci_sfu(ci_sfu), .cs_sfu(cs_sfu), .cs_e1(cs_e1), .cs_imm2(cs_imm2), .ce_e2(ce_e2), .ce_imm1(ce_imm1), .co_rnd(co_rnd), \
      .co_dst(co_dst), .vm_we(OUT[133]), .vm_waddr(OUT[157:134]), .vm_wdata(OUT[189:158]), .kv_we(OUT[190]), \
      .kv_waddr(OUT[214:191]), .kv_wdata(OUT[246:215]), .ro_v(OUT[247]), .ro_x(OUT[279:248]), .fault(OUT[280]), \
      .coll(OUT[281]), .side_v(OUT[282]), .side_x(OUT[314:283]), .side_y(side_y));
    `SFU_INST(u_ref, 0, rst_n, oa)
    `SFU_INST(u_cl, 1, (MUT ? rst_n_m : rst_n), ob)
    assign oa[400:315] = 0; assign ob[400:315] = 0;
    integer c, bad = 0, s, k, active = 0;
    task idle; begin
        ld = 0; ld_bank = 0; emit = 0; bank = 0; cpair = 0; cx_arnd = 0; cx_arelu = 0; cx_amin = 0; cx_cclip = 0; co_rnd = 0;
        ld_c = 0; o_v = 0; i_v = 0; no = 0; ni = 0; krow = 0; obase = 0; aibase = 0; ls = 0; lvw = 0; vb = 0; aind = 0; dst = 0;
        cm_m2 = 0; ce_e2 = 0; co_dst = 0; gsh = 0; srcs = 0; vi_q = 0; cx_imm3 = 0; cp_imm1 = 0; cm_imm1 = 0; ca_imm2 = 0;
        cs_imm2 = 0; ce_imm1 = 0; side_y = 0; rd_q = 0; cp_m1 = 0; cm_m1 = 0; cm_qm = 0; ca_ad = 0; ci_sfu = 0; cs_sfu = 0; cs_e1 = 0;
    end endtask
    task rnd; begin
        ld = $random(s); ld_bank = $random(s); emit = $random(s); bank = $random(s); cpair = $random(s); cx_arnd = $random(s);
        cx_arelu = $random(s); cx_amin = $random(s); cx_cclip = $random(s); co_rnd = $random(s);
        for (k = 0; k < 1200; k = k + 32) ld_c[k +: 32] = $random(s);
        o_v = $random(s); i_v = $random(s); no = $random(s); ni = $random(s); krow = $random(s); obase = $random(s);
        aibase = $random(s); ls = $random(s); lvw = $random(s); for (k = 0; k < 120; k = k + 30) vb[k +: 30] = $random(s);
        aind = $random(s); dst = $random(s); cm_m2 = $random(s); ce_e2 = $random(s); co_dst = $random(s); gsh = $random(s);
        srcs = $random(s); vi_q = $random(s); cx_imm3 = $random(s); cp_imm1 = $random(s); cm_imm1 = $random(s);
        ca_imm2 = $random(s); cs_imm2 = $random(s); ce_imm1 = $random(s); side_y = $random(s);
        for (k = 0; k < 128; k = k + 32) rd_q[k +: 32] = $random(s);
        cp_m1 = $random(s); cm_m1 = $random(s); cm_qm = $random(s); ca_ad = $random(s); ci_sfu = $random(s); cs_sfu = $random(s);
        cs_e1 = $random(s);
    end endtask
    // compare what a consumer can observe: each output word only when its own valid / enable is high (+ the flags)
    function [400:0] obs(input [400:0] o);
        obs = {o[400:315], o[282] ? o[314:283] : 32'd0, o[282:280], o[247] ? o[279:248] : 32'd0, o[247],
               o[190] ? o[246:191] : 56'd0, o[190], o[133] ? o[189:134] : 56'd0, o[133],
               (|o[124:121]) ? o[132:25] : 108'd0, o[0] ? o[24:1] : 24'd0, o[0]};
    endfunction
    always @(negedge clk) if (active && obs(oa) !== obs(ob)) begin bad = bad + 1; if (bad < 4) $display("MISMATCH t=%0t", $time); end
    initial begin
        s = SEED; idle;
        repeat (12) @(negedge clk);
        rst_n = 1; if (!MUT) rst_n_m = 1;                // mutant: the RSTPIPE instance is never released from reset
        repeat (8) @(negedge clk);
        active = 1;
        for (c = 0; c < NCYC; c = c + 1) begin
            if (c % 97 == 50) begin active = 0; idle; repeat (40) @(negedge clk); rst_n = 0; rst_n_m = 0; repeat (12) @(negedge clk);
                rst_n = 1; if (!MUT) rst_n_m = 1; repeat (10) @(negedge clk); active = 1; end
            rnd; @(negedge clk);
        end
        if (bad == 0) $display("SU12_RSTPIPE PASS cycles=%0d", NCYC); else $display("SU12_RSTPIPE FAIL mismatches=%0d", bad);
        $finish;
    end
endmodule
