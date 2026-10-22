`timescale 1ns/1ps
// STW-S81-TOPK-VMUX (10-21): vmtx' = the dsdv_bk_sel_vmtx successor on the landed PlanA n32 parent (see
// dsdv_idx_vmux_n32.sv header).  Ports = dsdv_bk_sel_vmtx + the parent's 39 regional clocks / resets (the die drives
// them; vmux_n32, vdly and tx run on clk = the S-face region beside the parent's r37 entry relay u_rs).
// VDLY = TX vi-tap delay (edges) = parent face latency added against the flat dsdv_bk_sel (28, measured).
// Latency vs G8IQ dsdv_bk_sel_vmtx (fixed, compiler-booked): vi_s / vi_idx / ca / cb pin -> selector core +14,
// core -> vo_s / vo_n +14, vi_n -> vo_s pass +28; tl_o (TX grid) +28 for the same vi_n CTL edge; the PlanA control
// selection tail 640 -> 796 (+156 a TOPK selection, already booked by STW-S81-TOPK) comes on top.
module dsdv_bk_sel_vmtx_n32 #(
    parameter integer V      = 276,
    parameter integer MUT    = 0,     // parent MUT (dsdv_bk_sel_pa_n32_lp)
    parameter integer VM_MUT = 0,     // dsdv_idx_vmux_n32 MUT
    parameter integer DL_MUT = 0,     // dsdv_idx_vdly MUT
    parameter integer TX_MUT = 0,
    parameter bit     TX_SRAM = 1,
    parameter integer VDLY   = 28
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [7:0]    tap_k,
    input  wire [7:0]    sink_k,
    input  wire [2:0]    ik,
    input  wire [2:0]    ek,
    input  wire [7:0]    uid,
    input  wire          eg_n,
    input  wire [V-1:0]  vi_s,
    output wire [V-1:0]  vo_n,
    input  wire [V-1:0]  vi_n,
    output wire [V-1:0]  vo_s,
    input  wire [V-1:0]  vi_idx,
    input  wire [V-1:0]  ca,
    input  wire [V-1:0]  cb,
    output wire          fault,
    output wire          vm_fault,
    output wire [V-1:0]  tl_o,
    output wire [15:0]   tx_st,
    input  wire          ck_core,
    input  wire          ck_r1,
    input  wire          ck_r2,
    input  wire          ck_r3,
    input  wire          ck_r4,
    input  wire          ck_r5,
    input  wire          ck_r6,
    input  wire          ck_r7,
    input  wire          ck_r8,
    input  wire          ck_r9,
    input  wire          ck_r10,
    input  wire          ck_r11,
    input  wire          ck_r12,
    input  wire          ck_r13,
    input  wire          ck_r14,
    input  wire          ck_r15,
    input  wire          ck_r16,
    input  wire          ck_r17,
    input  wire          ck_r18,
    input  wire          ck_r19,
    input  wire          ck_r20,
    input  wire          ck_r21,
    input  wire          ck_r22,
    input  wire          ck_r23,
    input  wire          ck_r24,
    input  wire          ck_r25,
    input  wire          ck_r26,
    input  wire          ck_r27,
    input  wire          ck_r28,
    input  wire          ck_r29,
    input  wire          ck_r30,
    input  wire          ck_r31,
    input  wire          ck_r32,
    input  wire          ck_r33,
    input  wire          ck_r34,
    input  wire          ck_r35,
    input  wire          ck_r36,
    input  wire          ck_r37,
    input  wire          ck_r38,
    input  wire          rst_n_core,
    input  wire          rst_n_r1,
    input  wire          rst_n_r2,
    input  wire          rst_n_r3,
    input  wire          rst_n_r4,
    input  wire          rst_n_r5,
    input  wire          rst_n_r6,
    input  wire          rst_n_r7,
    input  wire          rst_n_r8,
    input  wire          rst_n_r9,
    input  wire          rst_n_r10,
    input  wire          rst_n_r11,
    input  wire          rst_n_r12,
    input  wire          rst_n_r13,
    input  wire          rst_n_r14,
    input  wire          rst_n_r15,
    input  wire          rst_n_r16,
    input  wire          rst_n_r17,
    input  wire          rst_n_r18,
    input  wire          rst_n_r19,
    input  wire          rst_n_r20,
    input  wire          rst_n_r21,
    input  wire          rst_n_r22,
    input  wire          rst_n_r23,
    input  wire          rst_n_r24,
    input  wire          rst_n_r25,
    input  wire          rst_n_r26,
    input  wire          rst_n_r27,
    input  wire          rst_n_r28,
    input  wire          rst_n_r29,
    input  wire          rst_n_r30,
    input  wire          rst_n_r31,
    input  wire          rst_n_r32,
    input  wire          rst_n_r33,
    input  wire          rst_n_r34,
    input  wire          rst_n_r35,
    input  wire          rst_n_r36,
    input  wire          rst_n_r37,
    input  wire          rst_n_r38
);
    // One raw-reset consumer; the unchanged component reset chains release after three total edges.
    wire common_reset_n;
    dsdv_topk_reset_entry u_reset_entry (.ck(clk), .rst_n(rst_n), .q(common_reset_n));
    wire [V-1:0] vi_m, vi_t;
    dsdv_idx_vmux_n32 #(.V(V), .MUT(VM_MUT)) u_vm (.ck(clk), .rst(common_reset_n), .i_r(vi_s), .i_s(vi_idx), .i_a(ca), .i_b(cb),
        .o(vi_m), .fault(vm_fault));
    dsdv_bk_sel_pa_n32_lp #(.MUT(MUT)) u_sel (.tap_k(tap_k), .sink_k(sink_k), .ik(ik), .ek(ek), .uid(uid), .eg_n(eg_n),
        .vi_s(vi_m), .vi_n(vi_n), .vo_n(vo_n), .vo_s(vo_s), .fault(fault),
        .ck_core(ck_core), .ck_r1(ck_r1), .ck_r2(ck_r2), .ck_r3(ck_r3), .ck_r4(ck_r4), .ck_r5(ck_r5), .ck_r6(ck_r6), .ck_r7(ck_r7), .ck_r8(ck_r8), .ck_r9(ck_r9), .ck_r10(ck_r10), .ck_r11(ck_r11), .ck_r12(ck_r12), .ck_r13(ck_r13), .ck_r14(ck_r14), .ck_r15(ck_r15), .ck_r16(ck_r16), .ck_r17(ck_r17), .ck_r18(ck_r18), .ck_r19(ck_r19), .ck_r20(ck_r20), .ck_r21(ck_r21), .ck_r22(ck_r22), .ck_r23(ck_r23), .ck_r24(ck_r24), .ck_r25(ck_r25), .ck_r26(ck_r26), .ck_r27(ck_r27), .ck_r28(ck_r28), .ck_r29(ck_r29), .ck_r30(ck_r30), .ck_r31(ck_r31), .ck_r32(ck_r32), .ck_r33(ck_r33), .ck_r34(ck_r34), .ck_r35(ck_r35), .ck_r36(ck_r36), .ck_r37(ck_r37), .ck_r38(ck_r38), .rst_n_core(rst_n_core), .rst_n_r1(rst_n_r1), .rst_n_r2(rst_n_r2), .rst_n_r3(rst_n_r3), .rst_n_r4(rst_n_r4), .rst_n_r5(rst_n_r5), .rst_n_r6(rst_n_r6), .rst_n_r7(rst_n_r7), .rst_n_r8(rst_n_r8), .rst_n_r9(rst_n_r9), .rst_n_r10(rst_n_r10), .rst_n_r11(rst_n_r11), .rst_n_r12(rst_n_r12), .rst_n_r13(rst_n_r13), .rst_n_r14(rst_n_r14), .rst_n_r15(rst_n_r15), .rst_n_r16(rst_n_r16), .rst_n_r17(rst_n_r17), .rst_n_r18(rst_n_r18), .rst_n_r19(rst_n_r19), .rst_n_r20(rst_n_r20), .rst_n_r21(rst_n_r21), .rst_n_r22(rst_n_r22), .rst_n_r23(rst_n_r23), .rst_n_r24(rst_n_r24), .rst_n_r25(rst_n_r25), .rst_n_r26(rst_n_r26), .rst_n_r27(rst_n_r27), .rst_n_r28(rst_n_r28), .rst_n_r29(rst_n_r29), .rst_n_r30(rst_n_r30), .rst_n_r31(rst_n_r31), .rst_n_r32(rst_n_r32), .rst_n_r33(rst_n_r33), .rst_n_r34(rst_n_r34), .rst_n_r35(rst_n_r35), .rst_n_r36(rst_n_r36), .rst_n_r37(rst_n_r37), .rst_n_r38(rst_n_r38));
    dsdv_idx_vdly #(.W(V), .N(VDLY), .MUT(DL_MUT)) u_dl (.ck(clk), .rst(common_reset_n), .i(vi_m), .o(vi_t));
    dsdv_idx_tx_n32 #(.V(V), .IK(4), .EK(5), .UID(8'h5C), .SRAM_MACRO(TX_SRAM), .MUT(TX_MUT)) u_tx (
        .ck(clk), .rst(common_reset_n), .vi(vi_t), .vo(vo_s), .lo(tl_o), .st(tx_st));
endmodule

// One actual asynchronous entry register precedes the existing two-edge local chains.
// MUT=1 is a missing-stage negative control for the release-age witness only.
(* keep_hierarchy="yes" *)
module dsdv_topk_reset_entry #(parameter integer MUT=0)(
    input wire ck, rst_n, output wire q
);
    generate if (MUT == 0) begin:g_real
        (* keep *) reg entry_n;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) entry_n <= 1'b0;
            else entry_n <= 1'b1;
        assign q = entry_n;
    end else begin:g_missing
        assign q = rst_n;
    end endgenerate
endmodule
