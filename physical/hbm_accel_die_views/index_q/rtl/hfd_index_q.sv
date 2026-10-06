`timescale 1ps/1fs
`default_nettype none
// CLAUDE HBM-ABSTRACTS (svcidx) 2026-10-06: INTERIM die view of the r16g index quarter (hfd_index_q), NOT CLOSED and
// NOT the indexer.  Default-off: nothing instantiates it outside physical/hbm_accel_die_views/index_q.
// The index RTL (rtl/hbm_accel/index/ot_hbm_accel_index_path, unchanged) cannot be placed in this slot: its scorer
// alone is ~5.9 mm2 of cells per quarter (results/uarch/hbm_index_path_20261005/model.json: 23.67 mm2 / 4) against a
// 930 x 5530 um = 5.14 mm2 slot (the generator sized the slot at 100 % of the model ledger), and its ports (64-lane
// 34,816-bit key edge, VM query read / response, external selector and candidate memories) have no die nets.  This
// shell is the die-facing boundary the placement needs: every die input lands in a flop, every die output leaves a
// flop, with wire stages (<= 430 um) across the slot:
//   a0..a3 (attention row outputs, 529 b, bit 0 = valid) -> t_su lane 0 = a0 | a1, lane 1 = a2 | a3 (round robin,
//     4-deep FIFO per row; the real merge of the attention outputs toward the SU);
//   k (index keys 1024 b + 2 forwarded clocks) -> two-clock FIFOs (ot_hbm_accel_cdc_fifo, 8 deep: a continuous
//     stream needs the 2+2-period pointer round trip covered; 4 deep overflows in the bench) -> key register ->
//     t_vm = PLACEHOLDER (key[511:0] ^ key[1023:512]) where the selector result would leave; no scoring.
module hfd_index_q #(parameter integer A_ST = 6, K_ST = 14) (   // wire stages: a0/a3 -> t_su 3.02 mm, k -> t_vm 6.28 mm
    input wire [528:0] a0,
    input wire [528:0] a1,
    input wire [528:0] a2,
    input wire [528:0] a3,
    input wire [0:0] ck,
    input wire [1025:0] k,
    input wire [0:0] rst,
    output wire [1057:0] t_su,
    output wire [511:0] t_vm
);
  wire c = ck[0];
  reg rs1, rs2;
  always @(posedge c or negedge rst[0]) if (!rst[0]) {rs2, rs1} <= 2'b00; else {rs2, rs1} <= {rs1, 1'b1};
  wire rn = rs2;
  // ---------------------------------------------------------------- attention rows -> SU (two lanes)
  wire [528:0] ai [0:3];
  assign ai[0] = a0; assign ai[1] = a1; assign ai[2] = a2; assign ai[3] = a3;
  wire [3:0] sv, ne; wire [527:0] sd [0:3], fd [0:3];
  wire [1:0] lv; wire [527:0] ld [0:1];
  reg [1:0] last;
  wire [3:0] take;
  genvar g;
  generate for (g = 0; g < 4; g = g + 1) begin : gr
    reg v; reg [527:0] d;
    always @(posedge c or negedge rn) if (!rn) v <= 1'b0; else v <= ai[g][0];
    always @(posedge c) d <= ai[g][528:1];
    ot_svc_vpipe #(.W(528), .N(A_ST)) u_p (.ck(c), .rst_n(rn), .v(v), .d(d), .qv(sv[g]), .q(sd[g]));
    wire rdy_;
    ot_svc_fifo #(.W(528), .AW(2), .AF(0)) u_f (.ck(c), .rst_n(rn), .we(sv[g]), .wd(sd[g]), .rdy(rdy_),
      .re(take[g]), .rd(fd[g]), .ne(ne[g]));
  end endgenerate
  generate for (g = 0; g < 2; g = g + 1) begin : gl
    wire pick1 = ne[2*g+1] && (!ne[2*g] || last[g] == 1'b0);
    assign take[2*g] = ne[2*g] && !pick1;
    assign take[2*g+1] = pick1;
    reg v; reg [527:0] d;
    always @(posedge c or negedge rn)
      if (!rn) begin v <= 1'b0; last[g] <= 1'b1; end
      else begin v <= ne[2*g] || ne[2*g+1]; if (ne[2*g] || ne[2*g+1]) last[g] <= pick1; end
    always @(posedge c) d <= pick1 ? fd[2*g+1] : fd[2*g];
    assign lv[g] = v; assign ld[g] = d;
  end endgenerate
  assign t_su = {ld[1], lv[1], ld[0], lv[0]};
  // ---------------------------------------------------------------- index keys (forwarded) -> placeholder t_vm
  wire [511:0] kh [0:1]; wire [1:0] ke;
  generate for (g = 0; g < 2; g = g + 1) begin : gk
    wire full_; wire [2:0] fr_;
    ot_hbm_accel_cdc_fifo #(.W(512), .AW(3)) u_x (.wclk(~k[1024+g]), .wrst_n(rst[0]), .we(1'b1),
      .wdata(k[g*512 +: 512]), .full(full_), .rd_freed(fr_), .rclk(c), .rrst_n(rn), .re(1'b1), .rdata(kh[g]),
      .empty(ke[g]));
  end endgenerate
  reg kv; reg [511:0] kf;
  always @(posedge c or negedge rn) if (!rn) kv <= 1'b0; else kv <= !ke[0] && !ke[1];
  always @(posedge c) kf <= kh[0] ^ kh[1];
  wire pv; wire [511:0] pq;
  ot_svc_vpipe #(.W(512), .N(K_ST)) u_kp (.ck(c), .rst_n(rn), .v(kv), .d(kf), .qv(pv), .q(pq));
  reg [511:0] vm;
  always @(posedge c) if (pv) vm <= pq;
  assign t_vm = vm;
endmodule
`default_nettype wire
