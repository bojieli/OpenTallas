`timescale 1ns/1ps
// q15 r13: exact cycle equivalence of the BAND relay successor (ot_qfd_band_relay_core) against the predecessor
// qfd_sp_band_lanes (rtl/physical/ot_qwen_band_lanes_slots.sv), both with the real qfd_bl_lane leaves.
// The predecessor runs inside the closed-loop functional bench tb_qfd_band_lanes (BL = 1: three bands, real upper,
// golden lanes, random FP32 ops, NaN fault phase).  Two successors (band 0 with the returned tree-top words, band 1
// without) receive the SAME rst_n / b0 / lnk / tw / c streams as the predecessor bands and the returned tt delayed
// D_TT = 4 edges; every cycle after warm-up every output bit must equal the predecessor's output D_OUT = 4 edges
// earlier (pw[512:0], pw_l0..3, f_up, f) or D_TY = 8 edges earlier (ty: +2 in, +2 out and the lane's round-trip ring
// wait 2 x (+2 lnk), i.e. the band word waits the longer round trip).  MUT (successor bench mutants) 1 / 2 / 3 must FAIL.
module tb_qfd_band_relay_equiv;
    parameter integer MUT = 0, NOPS = 1200, LNK = 1, D_TT = 4, D_OUT = 4, D_TY = 8, WARM = 60;
    tb_qfd_band_lanes #(.NL(16), .NBP(3), .BL(1), .RDMEM(1), .LNK(LNK), .NOPS(NOPS)) u_ref ();
    wire clk = u_ref.clk;
    localparam integer OW = 513 + 4 * 129 + 4 + 4096 + 1;
    genvar b;
    integer errs = 0, cmp = 0, cyc = 0, ones = 0, fones = 0, tyne = 0;
    generate for (b = 0; b < 2; b = b + 1) begin : g_b
        // the predecessor band instance and its port streams
        wire [1537:0] tt_old = u_ref.g_band[b].g_slotb.u_b.tt;
        wire [OW-1:0] o_old = {u_ref.g_band[b].g_slotb.u_b.pw, u_ref.g_band[b].g_slotb.u_b.pw_l0, u_ref.g_band[b].g_slotb.u_b.pw_l1,
                               u_ref.g_band[b].g_slotb.u_b.pw_l2, u_ref.g_band[b].g_slotb.u_b.pw_l3, u_ref.g_band[b].g_slotb.u_b.f_up,
                               u_ref.g_band[b].g_slotb.u_b.ty, u_ref.g_band[b].g_slotb.u_b.f};
        reg [1537:0] tt_d [0:D_TT-1];
        integer j;
        always @(posedge clk) begin
            tt_d[0] <= tt_old;
            for (j = 1; j < D_TT; j = j + 1) tt_d[j] <= tt_d[j-1];
        end
        initial for (j = 0; j < D_TT; j = j + 1) tt_d[j] = 0;
        wire [512:0] pw; wire [128:0] l0, l1, l2, l3; wire [3:0] fu; wire [4095:0] ty; wire f;
        ot_qfd_band_relay_core #(.MUT(MUT)) u_dut (.ck(clk), .ck_l({16{clk}}), .ck_fn({8{clk}}), .ck_fe0(clk), .ck_fe1(clk),
            .ck_st({42{clk}}), .ck_fq({4{clk}}), .ck_fj(clk),
            .rst_n(u_ref.g_band[b].g_slotb.u_b.rst_n), .b0(u_ref.g_band[b].g_slotb.u_b.b0), .lnk(u_ref.g_band[b].g_slotb.u_b.lnk),
            .tw(u_ref.g_band[b].g_slotb.u_b.tw), .c(u_ref.g_band[b].g_slotb.u_b.c), .tt(tt_d[D_TT-1]),
            .pw(pw), .pw_l0(l0), .pw_l1(l1), .pw_l2(l2), .pw_l3(l3), .f_up(fu), .ty(ty), .f(f));
        wire [OW-1:0] o_new = {pw, l0, l1, l2, l3, fu, ty, f};
        reg [OW-1:0] hist [0:D_TY-1];
        wire [OW-1:0] o_exp = {hist[D_OUT-1][OW-1:4097], hist[D_TY-1][4096:1], hist[D_OUT-1][0]};
        always @(negedge clk) begin
            if (u_ref.rst_n && cyc > WARM) begin
                cmp = cmp + 1;
                if (o_new !== o_exp) begin
                    errs = errs + 1;
                    if (errs < 6) $display("MISMATCH band %0d cycle %0d: pw %0d pwv %b/%b f %b/%b f_up %h/%h ty %0d", b, cyc,
                        pw[511:0] !== o_exp[OW-1-1 -: 512], pw[512], o_exp[OW-1], f, o_exp[0],
                        fu, o_exp[4097 +: 4], ty !== o_exp[4096:1]);
                end
                if (o_new[OW-1]) ones = ones + 1;
                if (f) fones = fones + 1;
                if (|ty) tyne = tyne + 1;
            end
            for (j = D_TY-1; j > 0; j = j - 1) hist[j] <= hist[j-1];
            hist[0] <= o_old;
        end
    end endgenerate
    always @(negedge clk) if (u_ref.rst_n) cyc = cyc + 1;
    final begin
        if (errs == 0 && cmp > 1000 && ones > 0 && fones > 0 && tyne > 1000)
            $display("BAND_RELAY_EQUIV PASS MUT=%0d compared_cycles=%0d (2 bands x %0d output bits) valid_cycles=%0d fault_cycles=%0d ty_nonzero_cycles=%0d D_TT=%0d D_OUT=%0d D_TY=%0d",
                MUT, cmp, OW, ones, fones, tyne, D_TT, D_OUT, D_TY);
        else
            $display("BAND_RELAY_EQUIV FAIL MUT=%0d mismatching_cycles=%0d compared=%0d valid_cycles=%0d fault_cycles=%0d", MUT, errs, cmp, ones, fones);
    end
endmodule
