`timescale 1ns/1ps
// STW-S81-TOPK-VMUX (10-21): face-latency probe, G8IQ dsdv_bk_sel_vmtx (default) vs vmtx' dsdv_bk_sel_vmtx_n32
// (-DLAT_N32, PlanA n32 build defines).  One reader HDR beat (kind ik 4) on vi_idx at edge 300 and one drain CTL beat on
// vi_n at edge 400 (both values from the k3 tree stimulus); prints the first edge each value is seen at: the TX vi tap,
// the selector core ingress (u_g.vi_s / u_g.vi_n), the core egress u_g.vo_s and the vo_s pin.  Edge convention as
// tb_idx_tree (stimulus for edge e driven before posedge e; probes sampled right after posedge e).
module tb_vmtx_lat;
    localparam integer V = 276;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [V-1:0] vi_idx = 0, vi_n = 0;
    wire [V-1:0] vo_s, vo_n, lo; wire f, fv; wire [15:0] st;
    localparam [V-1:0] BS = 276'h2001555013189;        // reader HDR beat (k3 die 1 edge 927)
    localparam [V-1:0] BN = 276'hc8040054c4555420030be04b800801;   // drain CTL (k3 die 1 edge 18065)
`ifdef LAT_N32
    dsdv_bk_sel_vmtx_n32 u_die (
`else
    dsdv_bk_sel_vmtx u_die (
`endif
        .clk(clk), .rst_n(rst_n), .tap_k(8'h11), .sink_k(8'h10), .ik(3'd4), .ek(3'd5), .uid(8'h5B), .eg_n(1'b0),
        .vi_s({V{1'b0}}), .vo_n(vo_n), .vi_n(vi_n), .vo_s(vo_s), .vi_idx(vi_idx), .ca({V{1'b0}}), .cb({V{1'b0}}),
        .fault(f), .vm_fault(fv), .tl_o(lo), .tx_st(st)
`ifdef LAT_N32
        , .ck_core(clk), .ck_r1(clk), .ck_r2(clk), .ck_r3(clk), .ck_r4(clk), .ck_r5(clk), .ck_r6(clk), .ck_r7(clk), .ck_r8(clk), .ck_r9(clk), .ck_r10(clk), .ck_r11(clk), .ck_r12(clk), .ck_r13(clk), .ck_r14(clk), .ck_r15(clk), .ck_r16(clk), .ck_r17(clk), .ck_r18(clk), .ck_r19(clk), .ck_r20(clk), .ck_r21(clk), .ck_r22(clk), .ck_r23(clk), .ck_r24(clk), .ck_r25(clk), .ck_r26(clk), .ck_r27(clk), .ck_r28(clk), .ck_r29(clk), .ck_r30(clk), .ck_r31(clk), .ck_r32(clk), .ck_r33(clk), .ck_r34(clk), .ck_r35(clk), .ck_r36(clk), .ck_r37(clk), .ck_r38(clk), .rst_n_core(rst_n), .rst_n_r1(rst_n), .rst_n_r2(rst_n), .rst_n_r3(rst_n), .rst_n_r4(rst_n), .rst_n_r5(rst_n), .rst_n_r6(rst_n), .rst_n_r7(rst_n), .rst_n_r8(rst_n), .rst_n_r9(rst_n), .rst_n_r10(rst_n), .rst_n_r11(rst_n), .rst_n_r12(rst_n), .rst_n_r13(rst_n), .rst_n_r14(rst_n), .rst_n_r15(rst_n), .rst_n_r16(rst_n), .rst_n_r17(rst_n), .rst_n_r18(rst_n), .rst_n_r19(rst_n), .rst_n_r20(rst_n), .rst_n_r21(rst_n), .rst_n_r22(rst_n), .rst_n_r23(rst_n), .rst_n_r24(rst_n), .rst_n_r25(rst_n), .rst_n_r26(rst_n), .rst_n_r27(rst_n), .rst_n_r28(rst_n), .rst_n_r29(rst_n), .rst_n_r30(rst_n), .rst_n_r31(rst_n), .rst_n_r32(rst_n), .rst_n_r33(rst_n), .rst_n_r34(rst_n), .rst_n_r35(rst_n), .rst_n_r36(rst_n), .rst_n_r37(rst_n), .rst_n_r38(rst_n)
`endif
    );
    integer cyc = 0;
    integer t_tap = -1, t_ci = -1, t_cn = -1, t_co = -1, t_po = -1, t_tvo = -1;
    always @(negedge clk) begin
        vi_idx <= (cyc == 300) ? BS : '0;
        vi_n   <= (cyc == 400) ? BN : '0;
        if (cyc == 10) rst_n <= 1'b1;
    end
    always @(posedge clk) begin
        #0.1;
        if (t_tap < 0 && u_die.u_tx.vi === BS) t_tap = cyc;
        if (t_ci  < 0 && u_die.u_sel.u_g.vi_s === BS) t_ci = cyc;
        if (t_cn  < 0 && u_die.u_sel.u_g.vi_n === BN) t_cn = cyc;
        if (t_co  < 0 && u_die.u_sel.u_g.vo_s === BN) t_co = cyc;
        if (t_po  < 0 && vo_s === BN) t_po = cyc;
        if (t_tvo < 0 && u_die.u_tx.vo === BN) t_tvo = cyc;
        cyc++;
        if (cyc == 700) begin
            $display("VMTX_LAT %s vi_idx@300 -> tx_vi_tap %0d (+%0d) core_vi_s %0d (+%0d) | vi_n@400 -> core_vi_n %0d (+%0d) core_vo_s %0d (+%0d) vo_s_pin %0d (+%0d) tx_vo_tap %0d (+%0d)",
`ifdef LAT_N32
                "vmtx_n32",
`else
                "vmtx_g8iq",
`endif
                t_tap, t_tap - 300, t_ci, t_ci - 300, t_cn, t_cn - 400, t_co, t_co - 400, t_po, t_po - 400, t_tvo, t_tvo - 400);
            $finish;
        end
    end
endmodule
