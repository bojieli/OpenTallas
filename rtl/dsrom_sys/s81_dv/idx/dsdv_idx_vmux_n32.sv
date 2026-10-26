`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// STW-S81-TOPK-VMUX (10-21): N32 successors for the dsdv_bk_sel_vmtx die master (G8IQ stand-in) -- opt-in, the
// original dsdv_idx_vmux / dsdv_bk_sel_vmtx stay unchanged.
//
//   dsdv_idx_vmux_n32   = dsdv_idx_vmux (dsdv_idx_tree.sv), same ports, same function, same cycles (pin -> pin 2 edges).
//                         Structural fix (SAFE 3 fanout): the original lands each input's valid bit r_*[0] in ONE flop
//                         that gates all 275 data bits of that input (native census: 275 loads > 32).  Here each input
//                         valid pin lands in the original flop (o[0] OR + fault check, 5 loads) PLUS NC = 10 KEPT copies,
//                         each gating one <= 28-bit data slice (pin i_*[0]: 11 loads).  Reset: 2-flop landing rs, the
//                         second stage in 3 KEPT copies (<= 16 reset loads each); copies reset like the original flop.
//   dsdv_idx_vdly       fixed-latency 276-b delay line (N edges, pin -> pin), data in 3 x ot_sram_1r1w_32x128_m1 (SAFE 5:
//                         N x 276 b > 2 kb), valid bit in an N-flop reset chain (no SRAM power-up dependence).
//                         Same edge convention as an N-flop shift register: o after edge t = i sampled at edge t - N + 1.
//                         3 <= N <= 33.
//   dsdv_bk_sel_vmtx_n32  vmtx' = vmux_n32 + the landed PlanA n32 parent dsdv_bk_sel_pa_n32_lp (39 clock / reset
//                         regions, ports passed through) + dsdv_idx_tx_n32 on the taps.  TAP ALIGNMENT: the parent adds
//                         rung_input 14 + rung_output 14 = 28 edges on the vi_s -> core -> vo_s faces against the flat
//                         dsdv_bk_sel (timing_ledger.json rung_forward 28; measured here, see lanes/STW-S81-TOPK-VMUX.md),
//                         so the TX vi tap goes through dsdv_idx_vdly #(N = VDLY = 28): TX sees vi -> vo exactly as on the
//                         flat selector.  The TX job CTL (vi_n -> vo_s, PIN_TO_PIN 2 -> 30) and therefore the TX slot grid
//                         move +28 with vo_s; the control's own selection tail (640 -> 796, +156) is booked separately.
// MUT (bench negative controls only; 0 in every kit):
//   vmux_n32: 1 kept copy 3 of lane a lands i_b[0] (wrong lane), 2 kept copy 5 of lane s one edge late (lands r_s[0]),
//             3 the o[0] valid OR misses lane b.
//   vdly:     1 one edge short (N - 1), 2 valid chain one edge long (data / valid skew).
// ---------------------------------------------------------------------------------------------------------------------

module dsdv_idx_vmux_n32 #(
    parameter integer V = 276,
    parameter integer NC = 10,        // kept valid copies per input (data slice <= ceil((V-1)/NC) = 28 loads)
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [V-1:0]  i_r,
    input  wire [V-1:0]  i_s,
    input  wire [V-1:0]  i_a,
    input  wire [V-1:0]  i_b,
    output reg  [V-1:0]  o,
    output reg           fault
);
    localparam integer SL = (V - 1 + NC - 1) / NC;            // data bits a copy
    // ---- reset landing: rs[0], then 3 kept copies of the second stage
    reg rs0;
    wire [2:0] rnk;
    always @(posedge ck or negedge rst) if (!rst) rs0 <= 1'b0; else rs0 <= 1'b1;
    genvar k;
    generate for (k = 0; k < 3; k = k + 1) begin : g_rn
        dsdv_vmx_copy #(.W(1), .ID(100 + k)) u_rn (.ck(ck), .rn(rs0), .d(rs0), .q(rnk[k]));
    end endgenerate

    // ---- valid pins: original landing flop (o[0], fault) on rnk[0]
    reg [V-1:0] r_r, r_s, r_a, r_b;
    always @(posedge ck or negedge rnk[0])
        if (!rnk[0]) begin r_r[0] <= 1'b0; r_s[0] <= 1'b0; r_a[0] <= 1'b0; r_b[0] <= 1'b0; o[0] <= 1'b0; fault <= 1'b0; end
        else begin
            r_r[0] <= i_r[0]; r_s[0] <= i_s[0]; r_a[0] <= i_a[0]; r_b[0] <= i_b[0];
            o[0] <= r_r[0] | r_s[0] | r_a[0] | ((MUT == 3) ? 1'b0 : r_b[0]);
            if ((r_r[0] + r_s[0] + r_a[0] + r_b[0]) > 3'd1) fault <= 1'b1;
        end

    // ---- kept valid copies (same edge as r_*[0]); copies 0..4 on rnk[1], 5..9 on rnk[2] (4 x 5 = 20 loads each)
    // each copy = its own kept hierarchy (distinct ID): Yosys opt_merge cannot fold the copies back (a plain
    // (* keep *) reg is merged: census 277 with keep-only copies, 10-21)
    wire [NC-1:0] vk_r, vk_s, vk_a, vk_b;
    generate for (k = 0; k < NC; k = k + 1) begin : g_vk
        wire rnc = (k < NC / 2) ? rnk[1] : rnk[2];
        dsdv_vmx_copy #(.W(4), .ID(k)) u_vk (.ck(ck), .rn(rnc),
            .d({i_b[0], (MUT == 1 && k == 3) ? i_b[0] : i_a[0], (MUT == 2 && k == 5) ? r_s[0] : i_s[0], i_r[0]}),
            .q({vk_b[k], vk_a[k], vk_s[k], vk_r[k]}));
    end endgenerate

    // ---- data: pin flops, then the OR merge per slice under its own copies
    always @(posedge ck) begin
        r_r[V-1:1] <= i_r[V-1:1]; r_s[V-1:1] <= i_s[V-1:1]; r_a[V-1:1] <= i_a[V-1:1]; r_b[V-1:1] <= i_b[V-1:1];
    end
    generate for (k = 0; k < NC; k = k + 1) begin : g_sl
        localparam integer LO = 1 + k * SL;
        localparam integer HI = (LO + SL - 1 > V - 1) ? V - 1 : LO + SL - 1;
        if (LO <= V - 1) begin : g_on
            always @(posedge ck)
                o[HI:LO] <= (vk_r[k] ? r_r[HI:LO] : '0) | (vk_s[k] ? r_s[HI:LO] : '0) |
                            (vk_a[k] ? r_a[HI:LO] : '0) | (vk_b[k] ? r_b[HI:LO] : '0);
        end
    end endgenerate
`ifndef SYNTHESIS
    initial if (NC < 2 || SL > 32) $fatal(1, "dsdv_idx_vmux_n32: slice > 32 loads");
`endif
endmodule

// ===================================================================================================================
module dsdv_idx_vdly #(
    parameter integer W = 276,
    parameter integer N = 28,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [W-1:0]  i,
    output wire [W-1:0]  o
);
    localparam integer NE = (MUT == 1) ? N - 1 : N;        // effective delay
    localparam integer KR = NE - 3;                          // write -> read distance in entries (pin + macro + out regs)
    localparam integer NV = (MUT == 2) ? NE + 1 : NE;        // valid chain length
    localparam integer NB = (W - 1 + 127) / 128;             // macros for the W-1 data bits
    reg rs0;
    wire [1:0] rn;
    always @(posedge ck or negedge rst) if (!rst) rs0 <= 1'b0; else rs0 <= 1'b1;
    dsdv_vmx_copy #(.W(1), .ID(200)) u_rn0 (.ck(ck), .rn(rst), .d(rs0), .q(rn[0]));
    dsdv_vmx_copy #(.W(1), .ID(201)) u_rn1 (.ck(ck), .rn(rst), .d(rs0), .q(rn[1]));
    // valid: N-flop reset chain (rn[0]); first stage = the valid pin flop
    reg [NV-1:0] vc;
    always @(posedge ck or negedge rn[0]) if (!rn[0]) vc <= '0; else vc <= {vc[NV-2:0], i[0]};
    // data: pin flop -> SRAM ring (write every edge) -> registered read -> output flop
    reg [W-1:1] d_r, q_r;
    reg [4:0] wp;
    always @(posedge ck or negedge rn[1]) if (!rn[1]) wp <= 5'd0; else wp <= wp + 5'd1;
    wire [4:0] rp = wp - 5'(KR);
    wire [NB*128-1:0] wd = {{(NB*128-(W-1)){1'b0}}, d_r}, rd;
    genvar b;
    generate for (b = 0; b < NB; b = b + 1) begin : g_m
        ot_sram_1r1w_32x128_m1 u_m (.clk(ck), .r_ce_in(1'b1), .r_addr_in(rp), .rd_out(rd[b * 128 +: 128]),
            .w_ce_in(1'b1), .w_addr_in(wp), .wd_in(wd[b * 128 +: 128]), .w_mask_in({128{1'b1}}));
    end endgenerate
    always @(posedge ck) begin d_r <= i[W-1:1]; q_r <= rd[W-2:0]; end
    assign o = {q_r, vc[NV-1]};
`ifndef SYNTHESIS
    initial if (NE < 4 || NE > 34) $fatal(1, "dsdv_idx_vdly: N out of range");
`endif
endmodule

// kept same-edge copy flop(s) with async reset; distinct ID = distinct hierarchy (never merged by Yosys)
(* keep_hierarchy = "yes" *)
module dsdv_vmx_copy #(parameter integer W = 1, parameter integer ID = 0) (
    input  wire          ck,
    input  wire          rn,
    input  wire [W-1:0]  d,
    output wire [W-1:0]  q
);
    (* keep *) reg [W-1:0] r;
    always @(posedge ck or negedge rn) if (!rn) r <= '0; else r <= d;
    assign q = r;
endmodule
