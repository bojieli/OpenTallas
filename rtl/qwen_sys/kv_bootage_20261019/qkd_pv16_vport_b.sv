`timescale 1ns/1ps
// KV-BOOTAGE 2026-10-19 (coordinator decision, lanes/KVR-DERIVE.md "SPEC for the ONE later re-harden"): qkd_pv16_vport
// with BOOT-PROGRAMMABLE static-schedule ages.  Identical to rtl/qwen_sys/static_kv_20261014/qkd_pv16_vport.sv (r6, kept
// byte-identical for its closed kit) except that the request wait DQ and the die round trip RT are no longer RTL
// parameters but a configuration word:
//   cfg_age = {DQ[7:0], RT[7:0]}: a static configuration net from the KV die cfg (qkd_kv_die_cfg_a, pre-boot image
//   target 10, sealed before the first token; POR-held; no handshake, credit or ready).  The die derives the values per
//   instance from its relay plan / netlist (kv_static_params) and the generator FAILS when the boot image value differs.
//   The parameters DQ / RT are now the HARDWARE BOUNDS: the request wait line is DQ deep and the slot / sel line
//   DQ + RT + 1 deep; the word selects the tap.  A word with RT < 1, RT > the bound or DQ > the bound is an invalid
//   schedule: any request seen while it is invalid sets the sticky fault (an unloaded die cfg reads 0 -> invalid).
// Edge for edge this is qkd_pv16_vport #(.DQ(d), .RT(r)) when cfg_age = {d, r} (lockstep bench
// rtl/test/kv_bootage_1019/tb_kvba_vport.sv against the r6 module at several (d, r)).
// The cfg word is registered at its pin (cfg_q) and the tap index one edge later (sl_q); both are static after the seal.
// MUT (bench negative controls): 1-5 as qkd_pv16_vport; 6 = slot tap one edge late (DQ + RT + 2); 7 = DQ tap ignored
// (the request wait reads tap 0); 8 = range check off.
module qkd_pv16_vport_b #(parameter integer MUT = 0, DQ = 15, RT = 31) (
    input wire ck, rst_n,
    input wire [15:0] cfg_age,                                    // {DQ, RT} boot-loaded static schedule ages
    input wire pr_valid, input wire [13:0] pr_t,
    output reg vq0_valid, output reg [13:0] vq0_t, output reg vq1_valid, output reg [13:0] vq1_t,
    input wire in0_valid, input wire in0_vflag, input wire [13:0] in0_t, input wire [15:0] in0_epoch, input wire [1023:0] in0_d,
    input wire in1_valid, input wire in1_vflag, input wire [13:0] in1_t, input wire [15:0] in1_epoch, input wire [1023:0] in1_d,
    output reg out_valid, output reg [13:0] out_t, output reg [15:0] out_epoch,
    output reg [511:0] out_v_lo, output reg [511:0] out_v_hi,
    output reg fault
);
    localparam integer SLM = DQ + RT + 1;                      // deepest slot tap
    generate if (DQ < 0 || RT < 1 || SLM > 255) begin : g_bad
        initial $fatal(1, "qkd_pv16_vport_b: DQ bound %0d / RT bound %0d", DQ, RT);
    end endgenerate
    (* keep *) reg rst_q;
    always @(posedge ck) rst_q <= rst_n;
    wire rn = rst_q;
    // ---- static ages: pin register, tap indices (static after the seal) ----
    reg [15:0] cfg_q;
    always @(posedge ck) cfg_q <= cfg_age;
    wire [7:0] c_rt = cfg_q[7:0], c_dq = cfg_q[15:8];
    reg [7:0] dq_q, sl_q; reg age_bad;
    always @(posedge ck) begin
        dq_q <= (MUT == 7) ? 8'd0 : c_dq;
        sl_q <= c_dq + c_rt + ((MUT == 6) ? 8'd2 : 8'd1);
        age_bad <= (MUT == 8) ? 1'b0 : (c_rt < 8'd1 || c_rt > 8'(RT) || c_dq > 8'(DQ));
    end
    // ---- request: pin register, dq-edge wait, demux onto the group's V get face (output register) ----
    reg pr_v_q; reg [13:0] pr_t_q;
    always @(posedge ck or negedge rn) if (!rn) pr_v_q <= 1'b0; else pr_v_q <= pr_valid;
    always @(posedge ck) pr_t_q <= pr_t;
    reg [DQ:0] qv; reg [14*(DQ+1)-1:0] qt;                      // [0] = the pin register
    always @* begin qv[0] = pr_v_q; qt[13:0] = pr_t_q; end
    genvar w;
    generate for (w = 1; w <= DQ; w = w + 1) begin : g_wait
        always @(posedge ck or negedge rn) if (!rn) qv[w] <= 1'b0; else qv[w] <= qv[w-1];
        always @(posedge ck) qt[14*w +: 14] <= qt[14*(w-1) +: 14];
    end endgenerate
    wire dq_ok = dq_q <= 8'(DQ);
    wire iv = dq_ok && qv[dq_q]; wire [13:0] it = dq_ok ? qt[14*dq_q +: 14] : 14'd0;
    wire ig = it[0] ^ ((MUT == 4) ? 1'b1 : 1'b0);
    always @(posedge ck or negedge rn)
        if (!rn) begin vq0_valid <= 1'b0; vq1_valid <= 1'b0; end
        else begin vq0_valid <= iv && !ig; vq1_valid <= iv && ig; end
    always @(posedge ck) begin vq0_t <= it; vq1_t <= it; end
    // ---- slot / sel: the same request, sl_q edges later (aligned with the rsp words at the in pins) ----
    reg [SLM+1:0] sv, ss;
    always @* begin sv[0] = pr_v_q; ss[0] = pr_t_q[0]; end
    generate for (w = 1; w <= SLM + 1; w = w + 1) begin : g_slot
        always @(posedge ck or negedge rn) if (!rn) sv[w] <= 1'b0; else sv[w] <= sv[w-1];
        always @(posedge ck) ss[w] <= ss[w-1];
    end endgenerate
    wire sl_ok = sl_q <= 8'(SLM + 1);
    wire slot = sl_ok && sv[sl_q], sel = sl_ok && ss[sl_q];
    // ---- input pin registers (every port registered) ----
    reg slot_q, sel_q;
    reg [1:0] val_q, vf_q;
    reg [27:0] t_q; reg [31:0] e_q;
    reg [2047:0] d_q;
    always @(posedge ck or negedge rn)
        if (!rn) begin slot_q <= 1'b0; val_q <= 2'b0; end
        else begin slot_q <= slot; val_q <= {in1_valid, in0_valid}; end
    always @(posedge ck) begin
        sel_q <= sel ^ ((MUT == 1) ? 1'b1 : 1'b0);
        vf_q <= (MUT == 3) ? 2'b11 : {in1_vflag, in0_vflag};
        t_q <= {in1_t, in0_t}; e_q <= {in1_epoch, in0_epoch}; d_q <= {in1_d, in0_d};
    end

    // ---- static select of group {lane, sel} ----
    wire [1:0] vw = val_q & vf_q;
    wire gv = sel_q ? vw[1] : vw[0];
    wire ov = sel_q ? vw[0] : vw[1];
    wire [13:0] t0 = sel_q ? t_q[27:14] : t_q[13:0];
    wire [1023:0] gd = sel_q ? d_q[2047:1024] : d_q[1023:0];
    wire [1023:0] row = (MUT == 2) ? {gd[1023:768], gd[511:256], gd[767:512], gd[255:0]} : gd;
    wire own = t0[0] == sel_q;
    wire bad = (slot_q ? (!gv || ov || !own) : (|vw)) || (pr_v_q && age_bad);

    // ---- output pin registers ----
    always @(posedge ck or negedge rn)
        if (!rn) begin out_valid <= 1'b0; fault <= 1'b0; end
        else begin out_valid <= slot_q; if (bad) fault <= 1'b1; end
    always @(posedge ck) begin out_t <= t0; out_epoch <= (sel_q ^ (MUT == 5)) ? e_q[31:16] : e_q[15:0]; {out_v_hi, out_v_lo} <= row; end
endmodule
