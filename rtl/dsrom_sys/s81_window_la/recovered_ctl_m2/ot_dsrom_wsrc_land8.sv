`timescale 1ns/1ps
// ot_dsrom_wsrc_land8 (el1011-ds-misc 2026-10-11): one hardened landing sub-tile of ot_dsrom_window_source_ctl
// MARGIN 3 -- NL accepted-beat lanes of the staging neighbour.  It is the MARGIN2 per-lane path of
// ot_dsrom_window_source_ctl.g_acc (pin capture) + ot_dsrom_window_stream_la_s81 (slot range / scale-sector /
// poison landing checks), cycle for cycle:
//   e1  pin flops v / tag / beat / data (only v reset)
//   e2  s1 = {tag,00} + beat, poison partial ORs pca / psa from the captured data, v1
//   e3..e6  x2 / mm / t4 / k16 slot arithmetic, poison and range delayed alongside, v2..v5
//   e7  bad = |(v5 & (rng5 | (k16_5 ? ps5 : pc5)))  (== |bad_q over these lanes), nb = popcount(v4) (== nbp)
// Outputs are flops; the leaf has no reset on any datapath register (the reset reaches 5*NL valid bits + 6).
// The b input feeds only the simulation channel-ownership assertion (sim_bad), as pc_sim_bad did.
// ---------------------------------------------------------------------------
module ot_dsrom_wsrc_land8 #(
    parameter integer NL = 8, LANE0 = 0, NPC = 32, AW = 30, TAGW = 13, BEATW = 4
) (
    input  wire                 clk, rst_n,
    input  wire [AW-1:0]        b,
    input  wire [NL-1:0]        acc_v,
    input  wire [NL*TAGW-1:0]   acc_tag,
    input  wire [NL*BEATW-1:0]  acc_beat,
    input  wire [NL*256-1:0]    acc_data,
    output reg                  bad,
    output reg  [3:0]           nb,
    output reg                  sim_bad
);
    localparam integer PITCH = 17, NSECT = 128 * PITCH;
    localparam integer LPC = $clog2(NPC);
    function [LPC-1:0] pc_of(input [AW-1:0] s);
        pc_of = s[2 +: LPC] ^ s[2 + LPC +: LPC] ^ s[2 + 2 * LPC +: LPC];
    endfunction
    function poison_codes64(input [63:0] c);
        integer z;
        begin
            poison_codes64 = 1'b0;
            for (z = 0; z < 8; z = z + 1) if (c[8*z +: 7] == 7'h7f) poison_codes64 = 1'b1;
        end
    endfunction
    function poison_scales64(input [63:0] s);
        integer z;
        begin
            poison_scales64 = 1'b0;
            for (z = 0; z < 8; z = z + 1) if (s[8*z +: 8] == 8'hff) poison_scales64 = 1'b1;
        end
    endfunction
    // ---- e1: pin capture ----
    reg [NL-1:0] v_q; reg [NL*TAGW-1:0] t_q; reg [NL*BEATW-1:0] b_q; reg [NL*256-1:0] d_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) v_q <= '0; else v_q <= acc_v;
    always @(posedge clk) begin t_q <= acc_tag; b_q <= acc_beat; d_q <= acc_data; end
    // ---- landing pipeline ----
    reg [NL-1:0] v1, v2, v3, v4, v5;
    reg [NL-1:0] rng2, rng3, rng4, rng5, k16_5, pc2, pc3, pc4, pc5, ps2, ps3, ps4, ps5;
    reg [11:0] s1 [0:NL-1], s2 [0:NL-1], s3 [0:NL-1], t4 [0:NL-1];
    reg [23:0] x2 [0:NL-1];
    reg [6:0] sl3 [0:NL-1], sl4 [0:NL-1];
    reg [3:0] pca [0:NL-1]; reg [1:0] psa [0:NL-1];
    wire [23:0] x2_c [0:NL-1], mm_c [0:NL-1];
    wire [11:0] t4_c [0:NL-1], k16d_c [0:NL-1];
    genvar pg;
    generate for (pg = 0; pg < NL; pg = pg + 1) begin : g_land
        ot_hdc_ksadd_k #(.W(24)) u_x2 (.a({12'd0, s1[pg]} << 12), .b(~({12'd0, s1[pg]} << 8)), .cin(1'b1),
            .s(x2_c[pg]), .cout());
        ot_hdc_ksadd_k #(.W(24)) u_mm (.a(x2[pg]), .b({12'd0, s2[pg]} << 4), .cin(1'b0), .s(mm_c[pg]), .cout());
        ot_hdc_ksadd_k #(.W(12)) u_t4 (.a(s3[pg]), .b(~{1'b0, sl3[pg], 4'b0000}), .cin(1'b1), .s(t4_c[pg]), .cout());
        ot_hdc_ksadd_k #(.W(12)) u_k16 (.a(t4[pg]), .b(~{5'd0, sl4[pg]}), .cin(1'b1), .s(k16d_c[pg]), .cout());
    end endgenerate
    integer p, pq;
    reg [23:0] mm;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin v1 <= 0; v2 <= 0; v3 <= 0; v4 <= 0; v5 <= 0; end
        else begin v1 <= v_q; v2 <= v1; v3 <= v2; v4 <= v3; v5 <= v4; end
    always @(posedge clk)
        for (p = 0; p < NL; p = p + 1) begin
            s1[p] <= {t_q[p*TAGW +: TAGW], 2'b00} + b_q[p*BEATW +: BEATW];
            x2[p] <= x2_c[p];
            s2[p] <= s1[p]; rng2[p] <= s1[p] >= NSECT;
            mm = mm_c[p];
            sl3[p] <= mm[22:16]; s3[p] <= s2[p]; rng3[p] <= rng2[p];
            t4[p] <= t4_c[p]; sl4[p] <= sl3[p]; rng4[p] <= rng3[p];
            k16_5[p] <= k16d_c[p] == 12'd16; rng5[p] <= rng4[p];
            for (pq = 0; pq < 4; pq = pq + 1) pca[p][pq] <= poison_codes64(d_q[p*256 + 64*pq +: 64]);
            for (pq = 0; pq < 2; pq = pq + 1) psa[p][pq] <= poison_scales64(d_q[p*256 + 64*pq +: 64]);
            pc2[p] <= |pca[p]; pc3[p] <= pc2[p]; pc4[p] <= pc3[p]; pc5[p] <= pc4[p];
            ps2[p] <= |psa[p]; ps3[p] <= ps2[p]; ps4[p] <= ps3[p]; ps5[p] <= ps4[p];
        end
    // ---- e7: registered lane-group outputs ----
`ifdef OT_LAND8_MUTANT
    wire [NL-1:0] bad_beat = v5 & (rng5 | pc5);         // negative control: scale-sector poison check dropped
`else
    wire [NL-1:0] bad_beat = v5 & (rng5 | ((k16_5 & ps5) | (~k16_5 & pc5)));
`endif
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin bad <= 1'b0; nb <= 4'd0; end
        else begin bad <= |bad_beat; nb <= 4'($countones(v4)); end
    // simulation-only channel ownership check (pc_sim_bad of the stream engine); 0 in synthesis
    always @(posedge clk or negedge rst_n)
        if (!rst_n) sim_bad <= 1'b0;
        else begin
`ifndef SYNTHESIS
            for (p = 0; p < NL; p = p + 1) if (v1[p] && pc_of(b + s1[p]) != LPC'(LANE0 + p)) sim_bad <= 1'b1;
`endif
        end
endmodule
