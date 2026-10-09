`timescale 1ps/1ps
// hbm-system 2026-10-08: bench of ot_hbm_rope_table against the timed HBM3E stack model holding the golden table.
// tools/hbm_rope_table_bench.py writes table.txt (addr data lines: the entries the run touches, golden values of
// tools/hdc_golden_v41.py rope_cs) and steps.txt (start position, then per step the cycles until the next adv).
// The bench prints every current entry (C pos cos_plain sin_plain cos_yarn sin_yarn cos_yarn1 sin_yarn1) at the
// step's start and the stall count; the script compares with golden.
module tb_hbm_rope_table #(parameter integer MUT = 0);
  reg clk = 0, rst_n = 0; always #512 clk = ~clk;              // the service clock (one bench clock domain)
  wire [31:0] k_v, k_rdy, k_we, k_wr_done, kr_v; reg [31:0] kr_rdy; wire [959:0] k_addr; wire [127:0] k_len, kr_beat;
  wire [543:0] k_tag, kr_tag; wire [8191:0] kr_data;
  reg start = 0, adv = 0; reg [19:0] start_pos;
  wire cur_v; wire [19:0] cur_pos; wire [31:0] stall_cyc;
  wire [1023:0] cp, sp, cy, sy, cy1, sy1;
  wire rq_v, rq_rdy; wire [29:0] rq_addr; wire [3:0] rq_len; wire [7:0] rq_tag;
  reg rs_v; reg [7:0] rs_tag; reg [1:0] rs_beat; reg [255:0] rs_data;
  ot_hbm_rope_table #(.TBASE0(30'd0), .TBASE1(30'd1 << 21), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .start(start),
    .start_pos(start_pos), .adv(adv), .cur_v(cur_v), .cur_pos(cur_pos), .stall_cyc(stall_cyc), .cos_plain(cp),
    .sin_plain(sp), .cos_yarn(cy), .sin_yarn(sy), .cos_yarn1(cy1), .sin_yarn1(sy1), .rq_v(rq_v), .rq_rdy(rq_rdy),
    .rq_addr(rq_addr), .rq_len(rq_len), .rq_tag(rq_tag), .rs_v(rs_v), .rs_tag(rs_tag), .rs_beat(rs_beat), .rs_data(rs_data));
  function automatic integer pc_of(input [29:0] s); pc_of = ((s >> 2) ^ (s >> 7) ^ (s >> 12)) & 31; endfunction
  wire [4:0] rp = pc_of(rq_addr);
  genvar g;
  generate for (g = 0; g < 32; g = g + 1) begin : gp
    assign k_v[g] = rq_v && (rp == g);
    assign k_addr[g*30 +: 30] = rq_addr; assign k_len[g*4 +: 4] = rq_len; assign k_tag[g*17 +: 17] = {9'd0, rq_tag};
  end endgenerate
  assign k_we = 0;
  assign rq_rdy = k_rdy[rp];
  ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(30), .DW(256), .MEM_WORDS(1 << 22), .TAGW(17), .LENW(4), .BEATW(4),
    .QD(64), .REFPB(3), .MEM_MODE(0), .CLK_PS(1024)) u_m (
    .clk(clk), .rst_n(rst_n), .req_v(k_v), .req_rdy(k_rdy), .req_addr(k_addr), .req_len(k_len),
    .req_tag(k_tag), .req_we(k_we), .req_wdata(8192'd0), .req_wstrb(1024'd0), .wr_done(k_wr_done),
    .rsp_v(kr_v), .rsp_rdy(kr_rdy), .rsp_tag(kr_tag), .rsp_beat(kr_beat), .rsp_data(kr_data));
  // one response a clock into the unit (round robin over the PCs)
  integer rr = 0, q, pk;
  always @(posedge clk) begin
    rs_v <= 1'b0; kr_rdy <= 32'd0;
    pk = -1;
    for (q = 0; q < 32; q = q + 1) if (pk < 0 && kr_v[(rr + q) % 32] && !kr_rdy[(rr + q) % 32]) pk = (rr + q) % 32;
    if (pk >= 0) begin
      kr_rdy[pk] <= 1'b1; rs_v <= 1'b1; rs_tag <= kr_tag[pk*17 +: 8]; rs_beat <= kr_beat[pk*4 +: 2];
      rs_data <= kr_data[pk*256 +: 256]; rr = pk + 1;
    end
  end
  integer fo, fi, rc, a, gapc, n, k; reg [255:0] d;
  initial begin
    fi = $fopen("table.txt", "r");
    rc = 2;
    while (rc == 2) begin rc = $fscanf(fi, "%d %h\n", a, d); if (rc == 2) u_m.mem[a] = d; end
    $fclose(fi);
    fo = $fopen("out.txt", "w"); fi = $fopen("steps.txt", "r");
    rc = $fscanf(fi, "%d %d\n", a, n);
    repeat (5) @(posedge clk); rst_n = 1; repeat (5) @(posedge clk);
    start_pos <= a; start <= 1; @(posedge clk); start <= 0;
    for (k = 0; k < n; k = k + 1) begin
      rc = $fscanf(fi, "%d\n", gapc);
      while (!cur_v) @(posedge clk);
      $fdisplay(fo, "C %0d %h %h %h %h %h %h", cur_pos, cp, sp, cy, sy, cy1, sy1);
      repeat (gapc) @(posedge clk);
      adv <= 1; @(posedge clk); adv <= 0; @(posedge clk);
    end
    $fdisplay(fo, "S %0d", stall_cyc);
    $fclose(fo); $finish;
  end
endmodule
