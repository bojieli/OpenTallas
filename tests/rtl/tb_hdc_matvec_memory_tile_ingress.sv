`timescale 1ns/1ps
module tb_hdc_matvec_memory_tile_ingress;
  reg clk = 0;
  always #1 clk = ~clk;
  reg rst_n = 0, go = 0, kv_load = 0, x_load = 0;
  reg [9:0] kv_load_addr = 0, x_load_addr = 0;
  reg [255:0] kv_load_data = 0, x_load_data = 0;
  wire kv_load_commit, x_load_commit;
  wire ready_a, idle_a, ov_a, am_any_a, mx_we_a, fault_a;
  wire ready_b, idle_b, ov_b, am_any_b, mx_we_b, fault_b;
  wire [1:0] o_we_a, o_we_b;
  wire [31:0] o_addr_a, o_addr_b, am_val_a, am_val_b;
  wire [7:0] o_mask_a, o_mask_b, am_idx_a, am_idx_b;
  wire [255:0] o_data_a, o_data_b;
  wire [15:0] mx_addr_a, mx_addr_b, progress_a, progress_b;
  wire [3:0] mx_mask_a, mx_mask_b;
  wire [127:0] mx_data_a, mx_data_b;

  // A uses the registered load ingress. B is the pinned direct-load tile.
  ot_hdc_matvec_memory_tile a (
    .clk(clk), .rst_n(rst_n), .go(go), .ready(ready_a), .idle(idle_a),
    .i_nout(8'd8), .i_tiles(8'd1), .i_k(8'd1), .i_wsrc(1'b1),
    .i_wbase(16'd0), .i_ts(16'd0), .i_ks(16'd0), .i_js(16'd0),
    .i_xbase(16'd0), .i_xks(16'd0), .i_xjs(16'd0), .i_xcs(16'd0),
    .i_jsh(3'd0), .i_split(4'd0), .i_wcs(16'd0), .i_round(1'b0),
    .i_obase(16'd0), .i_ots(16'd0), .i_ojs(16'd0),
    .i_mmode(1'b0), .i_oen(1'b1), .i_amax(1'b0), .i_rmax(1'b0), .i_mbase(16'd0),
    .kv_load(kv_load), .x_load(x_load), .kv_load_addr(kv_load_addr),
    .x_load_addr(x_load_addr), .kv_load_data(kv_load_data), .x_load_data(x_load_data),
    .kv_load_commit(kv_load_commit), .x_load_commit(x_load_commit),
    .ov(ov_a), .o_we(o_we_a), .o_addr(o_addr_a), .o_mask(o_mask_a), .o_data(o_data_a),
    .am_idx(am_idx_a), .am_val(am_val_a), .am_any(am_any_a),
    .mx_we(mx_we_a), .mx_addr(mx_addr_a), .mx_mask(mx_mask_a), .mx_data(mx_data_a),
    .progress(progress_a), .fault(fault_a)
  );
  ot_hdc_matvec_memory_tile_baseline b (
    .clk(clk), .rst_n(rst_n), .go(go), .ready(ready_b), .idle(idle_b),
    .i_nout(8'd8), .i_tiles(8'd1), .i_k(8'd1), .i_wsrc(1'b1),
    .i_wbase(16'd0), .i_ts(16'd0), .i_ks(16'd0), .i_js(16'd0),
    .i_xbase(16'd0), .i_xks(16'd0), .i_xjs(16'd0), .i_xcs(16'd0),
    .i_jsh(3'd0), .i_split(4'd0), .i_wcs(16'd0), .i_round(1'b0),
    .i_obase(16'd0), .i_ots(16'd0), .i_ojs(16'd0),
    .i_mmode(1'b0), .i_oen(1'b1), .i_amax(1'b0), .i_rmax(1'b0), .i_mbase(16'd0),
    .kv_load(kv_load), .x_load(x_load), .kv_load_addr(kv_load_addr),
    .x_load_addr(x_load_addr), .kv_load_data(kv_load_data), .x_load_data(x_load_data),
    .ov(ov_b), .o_we(o_we_b), .o_addr(o_addr_b), .o_mask(o_mask_b), .o_data(o_data_b),
    .am_idx(am_idx_b), .am_val(am_val_b), .am_any(am_any_b),
    .mx_we(mx_we_b), .mx_addr(mx_addr_b), .mx_mask(mx_mask_b), .mx_data(mx_data_b),
    .progress(progress_b), .fault(fault_b)
  );
  integer cycles = 0, slots = 0;
  reg compare = 0;
  always @(posedge clk) begin
    cycles <= cycles + 1;
    if (compare) begin
      if ({ready_a,idle_a,ov_a,o_we_a,o_addr_a,o_mask_a,o_data_a,
           am_idx_a,am_val_a,am_any_a,mx_we_a,mx_addr_a,mx_mask_a,mx_data_a,
           progress_a,fault_a} !==
          {ready_b,idle_b,ov_b,o_we_b,o_addr_b,o_mask_b,o_data_b,
           am_idx_b,am_val_b,am_any_b,mx_we_b,mx_addr_b,mx_mask_b,mx_data_b,
           progress_b,fault_b}) $fatal(1, "tile divergence at cycle %0d", cycles);
      if (ov_a) slots <= slots + 1;
    end
  end
  initial begin
    repeat (3) @(negedge clk);
    rst_n = 1;
    @(negedge clk);
    kv_load = 1; x_load = 1;
    kv_load_addr = 0; x_load_addr = 0;
    kv_load_data = {8{32'h3f800000}}; // BF16 1.0 in high half of each lane
    x_load_data = {8{32'h3f800000}};
    @(negedge clk);
    if (kv_load_commit || x_load_commit) $fatal(1, "premature commit");
    kv_load_addr = 1; x_load_addr = 1;
    kv_load_data = {8{32'h40000000}};
    x_load_data = {8{32'h40000000}};
    @(negedge clk);
    if (!kv_load_commit || !x_load_commit) $fatal(1, "first commit missing");
    kv_load = 0; x_load = 0;
    @(negedge clk);
    if (!kv_load_commit || !x_load_commit) $fatal(1, "second commit missing");
    @(negedge clk);
    if (kv_load_commit || x_load_commit) $fatal(1, "commit held");
    if (!ready_a || !ready_b) $fatal(1, "tile not ready");
    compare = 1;
    go = 1;
    @(negedge clk);
    go = 0;
    repeat (90) @(negedge clk);
    if (slots != 8) $fatal(1, "expected 8 output slots, got %0d", slots);
    if (!idle_a || !idle_b || fault_a || fault_b) $fatal(1, "tile not drained cleanly");
    $display("PASS ingress commits one cycle after acceptance; 8 matched output slots");
    $finish;
  end
endmodule
