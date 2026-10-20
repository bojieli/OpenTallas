`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_chain5: ot_v41_chain4 (PD = 1) in native-partition form (S81-QXPQ3 2026-10-20, SAFE item 3: no driver above
// 32 loads).  Same terms, same adds, same output cycle (zero added cycles), bit-identical sums; the q element uses it
// for NP = 1.  Changes against chain4:
//   * the accumulator read acc[slot] is an AND-OR over a decoded slot, one decode per 16-bit half from its own kept
//     copy of the lane's slot field (slot_k: the lane's last tag stage in kept copies), not a binary 16:1 select;
//   * the accumulator writes use the registered one-hot of the leaving slot (two kept copies, one per half) and two
//     kept copies of the write condition (adder valid copies vk, kept copies of the last-term bit's final stage);
//   * first_r and the forward selects in ND kept copies, one per 1/ND of the operand bundle; the slot pipeline ps is a
//     kept register (two chains on the same lane tag never merge it);
//   * the adder is ot_v41_fadd_np (EXT0: step 0 from the PD bundle); the parent gets kept copies of the sum (osum_k)
//     and of the chunk-valid (ovk) for its pair adder / pass-through mux.
// Resets: NR regional leaves (each <= 32 loads).
// ---------------------------------------------------------------------------
module ot_v41_chain5 #(
    parameter integer ND = 8,
    parameter integer NCH = 16,
    parameter integer TW = 8,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer LAT = 8,
    parameter integer NR = 4
) (
    input  wire                     clk,
    input  wire [NR-1:0]            rst_n,
    input  wire                     v,
    input  wire [$clog2(NCH)-1:0]   slot,
    input  wire [3*$clog2(NCH)-1:0] slot_k,     // three kept copies of slot: 0 acc read bits 15:0, 1 bits 31:16 + flag, 2 compares
    input  wire                     first,
    input  wire                     last,
    input  wire [31:0]              term,
    input  wire                     term_f,
    input  wire [TW-1:0]            tag,
    output wire                     ov,
    output wire [1:0]               ovk,        // kept-copy forms of ov (parent mux halves)
    output wire [31:0]              osum,
    output wire [31:0]              osum_k,     // kept copy of osum (the parent's pair adder / pass-through)
    output wire                     of,
    output wire [TW-1:0]            otag,
    output reg                      fault
);
    localparam integer SW = $clog2(NCH);
`ifndef SYNTHESIS
    initial if (LAT != 8) $fatal(1, "ot_v41_chain5: LAT 8 only");
`endif
    wire r_c = rst_n[0], r_f = rst_n[1], r_ay = rst_n[2], r_ak = rst_n[3];
    reg [31:0] acc [0:NCH-1];
    reg [NCH-1:0] accf;
    wire [SW-1:0] sk0 = slot_k[0 +: SW], sk1 = slot_k[SW +: SW], sk2 = slot_k[2*SW +: SW];
    reg  [NCH-1:0] dec0, dec1;
    always @* for (int s = 0; s < NCH; s++) begin dec0[s] = sk0 == s; dec1[s] = sk1 == s; end
    reg  [31:0] acc_rd; reg accf_rd;
    always @* begin
        acc_rd = '0; accf_rd = 1'b0;
        for (int s = 0; s < NCH; s++) begin
            if (dec0[s]) acc_rd[15:0] = acc_rd[15:0] | acc[s][15:0];
            if (dec1[s]) begin acc_rd[31:16] = acc_rd[31:16] | acc[s][31:16]; accf_rd = accf_rd | accf[s]; end
        end
    end
    reg          v_r, last_r, termf_r, accf_r;
    reg [31:0]   term_r, acc_r;
    reg [TW-1:0] tag_r;
    wire [SW-1:0] slot_r;
    ot_v41_kreg #(.W(SW)) u_sr (.clk(clk), .arst_n(1'b1), .d(sk2), .q(slot_r));
    wire [ND-1:0] first_k;
    for (genvar g = 0; g < ND; g = g + 1) begin : g_fk
        ot_v41_kreg #(.W(1)) u_f (.clk(clk), .arst_n(1'b1), .d(first), .q(first_k[g]));
    end
    always @(posedge clk or negedge r_c) if (!r_c) v_r <= 1'b0; else v_r <= v;
    always @(posedge clk) begin
        last_r <= last; term_r <= term; termf_r <= term_f; tag_r <= tag; acc_r <= acc_rd; accf_r <= accf_rd;
    end
    // slot pipeline (kept: never merged with the other chain's)
    wire [SW*LAT-1:0] psv;
    ot_v41_kreg #(.W(SW * LAT)) u_ps (.clk(clk), .arst_n(1'b1), .d({psv[SW*(LAT-1)-1:0], slot_r}), .q(psv));
    wire [SW-1:0] ps [0:LAT-1];
    for (genvar k = 0; k < LAT; k = k + 1) begin : g_ps
        assign ps[k] = psv[SW*k +: SW];
    end
    reg [LAT-1:0] pv, pl;
    reg hazard;
    always @* begin
        hazard = 1'b0;
        for (int k = 0; k < LAT - 1; k++) if (pv[k] && ps[k] == slot_r) hazard = 1'b1;
    end
    // the adder (step 0 from the PD bundle)
    wire [31:0] sum;
    wire [1:0]  err;
    wire        sv;
    wire [31:0] yk;
    wire [2:0]  vk;
    wire [104:0] o0_ext;
    ot_v41_fadd_np #(.CUT(CUT), .EXT0(1), .NYK(1), .NVK(3)) u_add (.clk(clk), .rst_v(r_f), .rst_y(r_ay), .rst_k(r_ak), .valid_in(v_r),
        .a(32'd0), .b(term_r), .o0_ext(o0_ext), .y(sum), .err(err), .valid_out(sv), .yk(yk), .vk(vk));
    // tag line: LAT - 1 stages, the last stage as a register plus two kept copies of its last-term bit
    wire [TW+2:0] dt1;
    ot_hdc_delay #(.W(TW + 3), .D(LAT - 1)) u_t (.clk(clk), .rst_n(1'b1), .d({tag_r, last_r, af | termf_r, 1'b0}), .q(dt1));
    reg  [TW+2:0] dt;
    always @(posedge clk) dt <= dt1;
    wire [2:0] dlk;
    for (genvar g = 0; g < 3; g = g + 1) begin : g_dl
        ot_v41_kreg #(.W(1)) u_d (.clk(clk), .arst_n(1'b1), .d(dt1[2]), .q(dlk[g]));
    end
    wire af;
    wire d_last = dt[2];
    wire d_f = dt[1] | (err != 2'd0);
    reg          sp_v, sp_f;
    reg [31:0]   sp_val;
    // forward decisions a cycle ahead (as chain4), ND kept copies
    wire [ND-1:0] fwd5, fwd6;
    wire fwd5_d = pv[LAT-2] && !pl[LAT-2] && ps[LAT-2] == sk2;
    wire fwd6_d = sv && !d_last && ps[LAT-1] == sk2;
    for (genvar g = 0; g < ND; g = g + 1) begin : g_fw
        ot_v41_kreg #(.W(2), .AR(1), .RV(2'b00)) u_f (.clk(clk), .arst_n(r_f), .d({fwd6_d, fwd5_d}), .q({fwd6[g], fwd5[g]}));
    end
    always @(posedge clk) pl <= {pl[LAT-2:0], last_r};
    wire [104:0] c5, c6, ca, cz;
    ot_v41_fadd_s0 u_s5 (.valid_in(v_r), .a(sum),    .b(term_r), .o0(c5));
    ot_v41_fadd_s0 u_s6 (.valid_in(v_r), .a(sp_val), .b(term_r), .o0(c6));
    ot_v41_fadd_s0 u_sa (.valid_in(v_r), .a(acc_r),  .b(term_r), .o0(ca));
    ot_v41_fadd_s0 u_sz (.valid_in(v_r), .a(32'd0),  .b(term_r), .o0(cz));
    // fadd_np takes {v, fields}: bits 104:32 (its code is re-formed from the fields)
    assign o0_ext[31:0] = 32'd0;
    for (genvar g = 0; g < ND; g = g + 1) begin : g_sel
        localparam integer LO = 32 + (73 * g) / ND, HI = 32 + (73 * (g + 1)) / ND;
`ifdef OT_NP_CHAIN_MUT
        assign o0_ext[HI-1:LO] = first_k[g] ? cz[HI-1:LO] : (fwd5[g] ? c6[HI-1:LO] : (fwd6[g] ? c5[HI-1:LO] : ca[HI-1:LO]));   // negative control: forward candidates swapped
`else
        assign o0_ext[HI-1:LO] = first_k[g] ? cz[HI-1:LO] : (fwd5[g] ? c5[HI-1:LO] : (fwd6[g] ? c6[HI-1:LO] : ca[HI-1:LO]));
`endif
    end
    assign af = first_k[0] ? 1'b0 : (fwd5[0] ? d_f : (fwd6[0] ? sp_f : accf_r));
    // accumulator writes: registered one-hot of the leaving slot (two copies), write condition from kept copies
    wire [NCH-1:0] wsk [0:2];          // 0 acc bits 15:0, 1 acc bits 31:16, 2 the flag
    reg  [NCH-1:0] ws_d;
    always @* for (int s = 0; s < NCH; s++) ws_d[s] = ps[LAT-2] == s;
    for (genvar g = 0; g < 3; g = g + 1) begin : g_ws
        ot_v41_kreg #(.W(NCH)) u_w (.clk(clk), .arst_n(1'b1), .d(ws_d), .q(wsk[g]));
    end
    wire wv0 = vk[0] && !dlk[0];
    wire wv1 = vk[1] && !dlk[1];
    wire wv2 = vk[2] && !dlk[2];
    always @(posedge clk or negedge r_c) begin
        if (!r_c) begin
            pv <= '0; fault <= 1'b0; accf <= '0; sp_v <= 1'b0;
        end else begin
            pv <= {pv[LAT-2:0], v_r};
            if (v_r && hazard) fault <= 1'b1;
            for (int s = 0; s < NCH; s++) if (wv2 && wsk[2][s]) accf[s] <= d_f;
            sp_v <= sv && !d_last;
        end
    end
    always @(posedge clk) begin
        for (int s = 0; s < NCH; s++) begin
            if (wv0 && wsk[0][s]) acc[s][15:0] <= sum[15:0];
            if (wv1 && wsk[1][s]) acc[s][31:16] <= sum[31:16];
        end
        sp_val <= sum; sp_f <= d_f;
    end
    assign ov = sv && d_last;
    assign ovk = {vk[1] && dlk[1], vk[0] && dlk[0]};
    assign osum = sum;
    assign osum_k = yk;
    assign of = d_f;
    assign otag = dt[TW+2:3];
endmodule
