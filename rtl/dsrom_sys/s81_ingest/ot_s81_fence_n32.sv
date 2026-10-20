`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_fence_n32 (S81-SHLK12 s10e, 2026-10-20): native-32 form of ot_s81_ingest_visibility_fence for dsdv_sh_lk
// (ENABLE 1, PROTECT 0, PIPE 2, ck == clk_h, no OT_S81_HOST_PHASESAFE).  Same ports, same values on the same edges.
// Structural changes only:
//   * snapshot loads commits whenever the handshake is idle (req == ac2) and no commit fault -- when commits == snapshot
//     that is the same value, so the 32-bit compare leaves the enable (it only decides the req toggle); the enable and
//     the commits enable come from kept clones of fc / req / ac2 (one replica per 16-bit half);
//   * the completion queue (8 x 64) is WRITE-BEHIND: in_d staged every edge, the entry written one edge later through
//     registered per-16-bit-slice enables; the release check (hr_now) reads the staged word through registered bypass
//     clones while its entry is in flight; a pop is always >= 1 edge after the write, so out_d never needs the bypass;
//   * head reads through kept one-hot read-pointer copies; out_d / landed load through pop / handshake REPLICAS computed
//     from kept clones (hr_q, credits != 0, fh, fc2 / rc2, ack_host, snap_lt_q).
// MUT (bench negative controls): OT_FENCE_N32_MUT_BYP (release check never bypasses: a fresh head is read stale).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_fence_n32 (
    input  wire        rst_n, ck, clk_h,
    input  wire [7:0]  ack_n,
    input  wire        in_v,
    input  wire [63:0] in_d,
    output reg         in_cr,
    output reg         out_v,
    output reg  [63:0] out_d,
    input  wire        out_cr,
    output wire        fault,
    output wire [31:0] landed_debug
);
    integer i, j;
    // ---------------------------------------------------------------- ck: commits / snapshot / req
    reg [31:0] commits, snapshot;
    reg        req, ac1, ac2, fc;
    reg        ack_host;
    (* keep *) reg [2:0] fc_c;                           // commits lo / hi, snapshot replica support
    (* keep *) reg [1:0] req_c, ac2_c;
    wire [32:0] add = {1'b0, commits} + ack_n;
    wire        fc_nx = fc | add[32];
    wire        hs_idle = (req == ac2);
    wire        req_nx = (!fc && hs_idle && commits != snapshot) ? ~req : req;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin commits <= 0; snapshot <= 0; req <= 0; ac1 <= 0; ac2 <= 0; fc <= 0; fc_c <= 0; req_c <= 0; ac2_c <= 0; end
        else begin
            ac1 <= ack_host; ac2 <= ac1; ac2_c <= {2{ac1}};
            fc <= fc_nx; fc_c <= {3{fc_nx}};
            req <= req_nx; req_c <= {2{req_nx}};
            if (!fc_c[0]) commits[15:0]  <= add[15:0];
            if (!fc_c[1]) commits[31:16] <= add[31:16];
            if (!fc_c[2] && req_c[0] == ac2_c[0]) snapshot[15:0]  <= commits[15:0];
            if (!fc_c[2] && req_c[1] == ac2_c[1]) snapshot[31:16] <= commits[31:16];
        end
    // ---------------------------------------------------------------- clk_h: landed / queue / credits
    reg rc1, rc2, fc1, fc2;
    reg [31:0] landed;
    reg fh, snap_lt_q, hr_q;
    reg [63:0] q [0:7];
    reg [2:0] wp, rp, host_credits;
    reg [3:0] count;
    always @(posedge clk_h) snap_lt_q <= snapshot < landed;
    wire ok = !fh && !fc2;
    wire hs = rc2 != ack_host;
    wire wr_ok = ok && in_v && count != 4'd8;
    // head: one-hot read copies 0, 1 (out_d halves), 2, 3 (release check: head[31:0] / head[63:56]); bypass copies 0..2
    (* keep *) reg [31:0] roh_c;
    (* keep *) reg [2:0]  byp_c;
    (* keep *) reg [31:0] we_c;                          // [e*4 + s]
    reg [63:0] in_q;
    wire [63:0] h01, h23;
    for (genvar g = 0; g < 2; g = g + 1) begin : g_h
        wire [7:0] oa = roh_c[8*g +: 8], ob = roh_c[16 + 8*g +: 8];
        reg [31:0] va, vb; integer k;
        always @* begin
            va = 32'd0; vb = 32'd0;
            for (k = 0; k < 8; k = k + 1) begin va = va | ({32{oa[k]}} & q[k][32*g +: 32]); vb = vb | ({32{ob[k]}} & q[k][32*g +: 32]); end
        end
        assign h01[32*g +: 32] = va; assign h23[32*g +: 32] = vb;
    end
`ifdef OT_FENCE_N32_MUT_BYP
    wire [31:0] hc_lo = h23[31:0];                                                   // mutant: no bypass
    wire [7:0]  hc_hi = h23[63:56];
`else
    wire [31:0] hc_lo = {byp_c[1] ? in_q[31:16] : h23[31:16], byp_c[0] ? in_q[15:0] : h23[15:0]};
    wire [7:0]  hc_hi = byp_c[2] ? in_q[63:56] : h23[63:56];
`endif
    wire is_done = hc_hi == 8'h01;
    wire hr_now = count != 4'd0 && (!is_done || landed >= hc_lo);
    wire pop = hr_q && host_credits != 3'd0 && ok;
    wire cr_ovf = ok && out_cr && host_credits == 3'd4 && !pop;
    wire fh_nx = fh | (hs && snap_lt_q) | (ok && in_v && count == 4'd8) | cr_ovf;
    wire [2:0] wp_nx = wr_ok ? wp + 3'd1 : wp;
    wire [2:0] rp_nx = pop ? rp + 3'd1 : rp;
    wire [3:0] count_nx = count + (wr_ok ? 4'd1 : 4'd0) - (pop ? 4'd1 : 4'd0);
    wire [2:0] hc_nx = host_credits + ((ok && out_cr && !cr_ovf) ? 3'd1 : 3'd0) - (pop ? 3'd1 : 3'd0);
    wire hr_q_nx = hr_now && !pop;
    // replica clones (D = the master's next state)
    (* keep *) reg [3:0] hrq_c, hcnz_c, fh_c, fc2_c;     // pop replicas (out_d 16-bit quarters)
    (* keep *) reg [1:0] rc2_c, ackh_c, slt_c;           // handshake replicas (landed halves)
    wire [3:0] pop_c = hrq_c & hcnz_c & ~fh_c & ~fc2_c;
    wire [1:0] land_c = (rc2_c ^ ackh_c) & ~slt_c;
    always @(posedge clk_h) in_q <= in_d;
    always @(posedge clk_h or negedge rst_n)
        if (!rst_n) begin
            rc1 <= 0; rc2 <= 0; ack_host <= 0; fc1 <= 0; fc2 <= 0; landed <= 0; fh <= 0; hr_q <= 0;
            wp <= 0; rp <= 0; count <= 0; host_credits <= 3'd4; in_cr <= 0; out_v <= 0; out_d <= 0;
            roh_c <= {4{8'd1}}; byp_c <= 0; we_c <= 0;
            hrq_c <= 0; hcnz_c <= 4'hf; fh_c <= 0; fc2_c <= 0; rc2_c <= 0; ackh_c <= 0; slt_c <= 0;
        end else begin
            rc1 <= req; rc2 <= rc1; fc1 <= fc; fc2 <= fc1;
            if (hs) ack_host <= rc2;
            if (land_c[0]) landed[15:0] <= snapshot[15:0];
            if (land_c[1]) landed[31:16] <= snapshot[31:16];
            fh <= fh_nx; hr_q <= hr_q_nx;
            wp <= wp_nx; rp <= rp_nx; count <= count_nx; host_credits <= hc_nx;
            in_cr <= pop; out_v <= pop;
            for (i = 0; i < 4; i = i + 1) if (pop_c[i]) out_d[16*i +: 16] <= h01[16*i +: 16];
            roh_c <= {4{8'd1 << rp_nx}};
            byp_c <= {3{wr_ok && wp == rp_nx}};
            for (i = 0; i < 8; i = i + 1) for (j = 0; j < 4; j = j + 1) we_c[i*4 + j] <= wr_ok && wp == i;
            hrq_c <= {4{hr_q_nx}}; hcnz_c <= {4{hc_nx != 3'd0}}; fh_c <= {4{fh_nx}}; fc2_c <= {4{fc1}};
            rc2_c <= {2{rc1}}; ackh_c <= {2{hs ? rc2 : ack_host}}; slt_c <= {2{snapshot < landed}};
        end
    always @(posedge clk_h)
        for (i = 0; i < 8; i = i + 1) for (j = 0; j < 4; j = j + 1) if (we_c[i*4 + j]) q[i][16*j +: 16] <= in_q[16*j +: 16];
    assign fault = fc2 | fh;
    assign landed_debug = landed;
`ifndef SYNTHESIS
    always @(posedge clk_h) if (rst_n && (pop_c != {4{pop}} || land_c != {2{hs && !snap_lt_q}}))
        $fatal(1, "ot_s81_fence_n32: replica diverged");
`endif
endmodule
