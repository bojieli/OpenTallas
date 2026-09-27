`timescale 1ns/1ps
module tb_hdc_matvec_memory_tile_wide;
`ifdef TILE_W4
  localparam integer W=4;
`else
  localparam integer W=8;
`endif
  localparam integer G=4, AW=16, NW=8;
  localparam integer NOUT=G*W;
  reg clk=0;
  always #1 clk=~clk;
  reg rst_n=0, go=0, kv_load=0, x_load=0;
  reg [9:0] kv_load_addr=0, x_load_addr=0;
  reg [AW-1:0] wbase=0, xbase=0;
  reg [G*W*32-1:0] kv_load_data=0;
  reg [G*32-1:0] x_load_data=0;
  wire kv_load_commit, x_load_commit;
  wire ready_a, idle_a, ov_a, am_any_a, mx_we_a, fault_a;
  wire ready_b, idle_b, ov_b, am_any_b, mx_we_b, fault_b;
  wire [G-1:0] o_we_a,o_we_b;
  wire [G*AW-1:0] o_addr_a,o_addr_b;
  wire [G*W-1:0] o_mask_a,o_mask_b;
  wire [G*W*32-1:0] o_data_a,o_data_b;
  wire [NW-1:0] am_idx_a,am_idx_b;
  wire [31:0] am_val_a,am_val_b;
  wire [AW-1:0] mx_addr_a,mx_addr_b;
  wire [W-1:0] mx_mask_a,mx_mask_b;
  wire [W*32-1:0] mx_data_a,mx_data_b;
  wire [15:0] progress_a,progress_b;
  wire wrom_re_b,kv_re_b;
  wire [AW-1:0] wrom_addr_b;
  wire [G*AW-1:0] kv_addr_b,x_addr_b;
  wire [G-1:0] x_re_b;
  reg [G*W*16-1:0] wrom_q_b=0;
  reg [G*W*32-1:0] kv_q_b=0;
  reg [G*32-1:0] x_q_b=0;
  reg [W*32-1:0] kv_mem[0:G-1][0:1];
  reg [31:0] x_mem[0:G-1][0:1];
  integer g;
  always @(posedge clk) begin
    // Independent flat behavioral bank model. It writes on acceptance; reads
    // are synchronous like the macros. All reads begin after DUT commit.
    if (kv_load) for (integer j=0;j<G;j=j+1)
      kv_mem[j][kv_load_addr] <= kv_load_data[j*W*32 +: W*32];
    if (x_load) for (integer j=0;j<G;j=j+1)
      x_mem[j][x_load_addr] <= x_load_data[j*32 +: 32];
    if (kv_re_b) for (integer j=0;j<G;j=j+1)
      kv_q_b[j*W*32 +: W*32] <= kv_mem[j][kv_addr_b[j*AW +: 10]];
    for (integer j=0;j<G;j=j+1) if (x_re_b[j])
      x_q_b[j*32 +: 32] <= x_mem[j][x_addr_b[j*AW +: 10]];
    if (wrom_re_b) wrom_q_b <= '0;
  end
  ot_hdc_matvec_memory_tile_wide #(.W(W),.G(G),.AW(AW),.NW(NW)) a (
    .clk(clk),.rst_n(rst_n),.go(go),.ready(ready_a),.idle(idle_a),
    .i_nout(NOUT[NW-1:0]),.i_tiles(8'd1),.i_k(8'd1),.i_wsrc(1'b1),
    .i_wbase(wbase),.i_ts(16'd0),.i_ks(16'd0),.i_js(16'd0),
    .i_xbase(xbase),.i_xks(16'd0),.i_xjs(16'd0),.i_xcs(16'd0),
    .i_jsh(3'd0),.i_split(4'd0),.i_wcs(16'd0),.i_round(1'b0),
    .i_obase(16'd0),.i_ots(16'd0),.i_ojs(16'd0),
    .i_mmode(1'b0),.i_oen(1'b1),.i_amax(1'b0),.i_rmax(1'b0),.i_mbase(16'd0),
    .kv_load(kv_load),.x_load(x_load),.kv_load_addr(kv_load_addr),.x_load_addr(x_load_addr),
    .kv_load_data(kv_load_data),.x_load_data(x_load_data),
    .kv_load_commit(kv_load_commit),.x_load_commit(x_load_commit),
    .ov(ov_a),.o_we(o_we_a),.o_addr(o_addr_a),.o_mask(o_mask_a),.o_data(o_data_a),
    .am_idx(am_idx_a),.am_val(am_val_a),.am_any(am_any_a),
    .mx_we(mx_we_a),.mx_addr(mx_addr_a),.mx_mask(mx_mask_a),.mx_data(mx_data_a),
    .progress(progress_a),.fault(fault_a)
  );
  ot_hdc_matvec #(.W(W),.G(G),.IL(8),.AW(AW),.NW(NW)) b (
    .clk(clk),.rst_n(rst_n),.go(go),.ready(ready_b),.idle(idle_b),
    .i_nout(NOUT[NW-1:0]),.i_tiles(8'd1),.i_k(8'd1),.i_wsrc(1'b1),
    .i_wbase(wbase),.i_ts(16'd0),.i_ks(16'd0),.i_js(16'd0),
    .i_xbase(xbase),.i_xks(16'd0),.i_xjs(16'd0),.i_xcs(16'd0),
    .i_jsh(3'd0),.i_split(4'd0),.i_wcs(16'd0),.i_round(1'b0),
    .i_obase(16'd0),.i_ots(16'd0),.i_ojs(16'd0),
    .i_mmode(1'b0),.i_oen(1'b1),.i_amax(1'b0),.i_rmax(1'b0),.i_mbase(16'd0),
    .wrom_re(wrom_re_b),.wrom_addr(wrom_addr_b),.wrom_q(wrom_q_b),
    .kv_re(kv_re_b),.kv_addr(kv_addr_b),.kv_q(kv_q_b),
    .x_re(x_re_b),.x_addr(x_addr_b),.x_q(x_q_b),
    .ov(ov_b),.o_we(o_we_b),.o_addr(o_addr_b),.o_mask(o_mask_b),.o_data(o_data_b),
    .am_idx(am_idx_b),.am_val(am_val_b),.am_any(am_any_b),
    .mx_we(mx_we_b),.mx_addr(mx_addr_b),.mx_mask(mx_mask_b),.mx_data(mx_data_b),
    .progress(progress_b),.fault(fault_b)
  );
  integer cycles=0, slots=0, nonzero=0;
  reg compare=0;
  always @(posedge clk) begin
    cycles <= cycles+1;
    if (compare) begin
      if ({ready_a,idle_a,ov_a,o_we_a,o_addr_a,o_mask_a,o_data_a,
           am_idx_a,am_val_a,am_any_a,mx_we_a,mx_addr_a,mx_mask_a,mx_data_a,
           progress_a,fault_a} !==
          {ready_b,idle_b,ov_b,o_we_b,o_addr_b,o_mask_b,o_data_b,
           am_idx_b,am_val_b,am_any_b,mx_we_b,mx_addr_b,mx_mask_b,mx_data_b,
           progress_b,fault_b})
        $fatal(1,"banked tile divergence cycle=%0d slots=%0d",cycles,slots);
      if (ov_a) begin
        slots <= slots+1;
        if (o_data_a != '0) nonzero <= nonzero+1;
      end
    end
  end
  initial begin
    for (integer j=0;j<G;j=j+1) for (integer a=0;a<2;a=a+1) begin
      kv_mem[j][a]='0; x_mem[j][a]='0;
    end
    repeat (3) @(negedge clk); rst_n=1;
    @(negedge clk);
    kv_load=1; x_load=1;
    for (integer j=0;j<G;j=j+1) begin
      x_load_data[j*32 +: 32] = 32'h3f800000;
      for (integer k=0;k<W;k=k+1)
        kv_load_data[(j*W+k)*32 +: 32] = 32'h3f800000 + (j << 23);
    end
    @(negedge clk);
    if (kv_load_commit || x_load_commit) $fatal(1,"premature ingress commit");
    kv_load_addr=1; x_load_addr=1;
    for (integer j=0;j<G;j=j+1) begin
      x_load_data[j*32 +: 32] = 32'h40000000;
      for (integer k=0;k<W;k=k+1)
        kv_load_data[(j*W+k)*32 +: 32] = 32'h3f800000 + (j << 23);
    end
    @(negedge clk);
    if (!kv_load_commit || !x_load_commit) $fatal(1,"first ingress commit missing");
    kv_load=0; x_load=0;
    @(negedge clk);
    if (!kv_load_commit || !x_load_commit) $fatal(1,"second ingress commit missing");
    @(negedge clk);
    if (kv_load_commit || x_load_commit) $fatal(1,"stale ingress commit");
    if (!ready_a || !ready_b) $fatal(1,"matvec not ready");
    compare=1; go=1;
    @(negedge clk); go=0;
    repeat (150) @(negedge clk);
    if (slots != 8 || nonzero != 8) $fatal(1,"missing/nonzero output slots: %0d, %0d",slots,nonzero);
    if (!idle_a || !idle_b || fault_a || fault_b) $fatal(1,"matvec not drained");
    // Address 1 was loaded in the immediately following ingress cycle.
    // Re-run the same matvec from that address and compare all eight slots.
    wbase=1; xbase=1; go=1;
    @(negedge clk); go=0;
    repeat (150) @(negedge clk);
    if (slots != 16 || nonzero != 16) $fatal(1,"second banked address diverged: %0d, %0d",slots,nonzero);
    if (!idle_a || !idle_b || fault_a || fault_b) $fatal(1,"second matvec not drained");
    $display("PASS G4/W%0d independent bank model; 16 exact output slots of %0d lanes across 2 addresses and ingress commits",W,G*W);
    $finish;
  end
endmodule
