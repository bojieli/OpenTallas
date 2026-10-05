`timescale 1ns/1ps
// Cross-check: the same near-HBM KV stream (1 MiB per layer per stack, sequential) through the
// repository's EXISTING behavioural HBM3E timing models with NPC = 32 at a 1.024 ns clock:
//   MODEL 0: rtl/hdc/kv/ot_hdc_hbm_model.sv (FR-FCFS, REFab staggered), one request port,
//            LEN 32 reads (1 KB per request per cycle);
//   MODEL 1: rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv REFPB = 3 (refresh-aware REFpb), one request
//            port per PC, LEN 4 (each 128 B group lies in one PC under that model's XOR map);
//   MODEL 2: the same with REFPB = 0 (REFab).
// Layers start every PERIOD_CYC cycles.  Every returned sector is compared with the source
// value written into the model's backing array; the layer time is first request to last
// sector returned (an in-order consumer finishes no earlier).
module tb_hbm_stream_existing_models;
  parameter integer MODEL = 0;
  parameter integer PCRDY = 0;                // MODEL 0: ot_hdc_hbm_model PC_RDY (0: ready only if every queue has 32 free)
  parameter integer LAYERS = 8;
  parameter integer PERIOD_CYC = 5111;        // 5,234 ns layer period at 1.024 ns
  localparam integer NPC = 32, SPL = 32768, AW = 21, MW = 1 << 18;
  localparam integer LENW = (MODEL == 0) ? 6 : 3;
  reg clk = 0, rst_n = 0;
  always #0.512 clk = ~clk;
  function automatic [255:0] src(input integer s);
    for (integer w = 0; w < 8; w++) src[32*w +: 32] = (32'(s) * 32'd8 + 32'(w)) * 32'h9E3779B1 ^ 32'h5bd1e995;
  endfunction
  function automatic integer pc_of(input integer s);
    pc_of = ((s >> 2) ^ (s >> 7) ^ (s >> 12)) & 31;
  endfunction
  wire [NPC-1:0] rsp_v; wire [NPC*16-1:0] rsp_tag; wire [NPC*5-1:0] rsp_beat; wire [NPC*256-1:0] rsp_data;
  longint cyc = 0;
  longint got = 0, bad = 0;
  longint layer_start [0:LAYERS-1], layer_end [0:LAYERS-1]; longint layer_got [0:LAYERS-1];
  // request side
  reg req_v1 = 0; wire req_rdy1; reg [AW-1:0] req_addr1 = 0; reg [15:0] req_tag1 = 0;
  reg [NPC-1:0] req_vp = 0; wire [NPC-1:0] req_rdyp; reg [NPC*AW-1:0] req_addrp = 0; reg [NPC*16-1:0] req_tagp = 0;
  generate if (MODEL == 0) begin : m0
    ot_hdc_hbm_model #(.NPC(NPC), .AW(AW), .MEM_WORDS(MW), .LENW(6), .BEATW(5), .CLK_PS(1024), .PC_RDY(PCRDY)) hbm (
      .clk(clk), .rst_n(rst_n), .req_v(req_v1), .req_rdy(req_rdy1), .pc_room(), .req_we(1'b0),
      .req_addr(req_addr1), .req_len(6'd32), .req_tag(req_tag1), .req_wdata(256'b0),
      .rsp_v(rsp_v), .rsp_rdy({NPC{1'b1}}), .rsp_tag(rsp_tag), .rsp_beat(rsp_beat), .rsp_data(rsp_data));
    initial for (int s = 0; s < MW; s++) hbm.mem[s] = src(s);
  end else begin : m1
    wire [NPC*4-1:0] beat4;
    ot_hdc_v41x_idx_hbm #(.NPC(NPC), .AW(AW), .MEM_WORDS(MW), .LENW(3), .BEATW(4), .CLK_PS(1024),
      .REFPB(MODEL == 1 ? 3 : 0), .MEM_MODE(0)) hbm (
      .clk(clk), .rst_n(rst_n), .req_v(req_vp), .req_rdy(req_rdyp), .req_addr(req_addrp),
      .req_len({NPC{3'd4}}), .req_tag(req_tagp), .req_we({NPC{1'b0}}), .req_wdata({NPC*256{1'b0}}),
      .req_wstrb({NPC*32{1'b0}}), .wr_done(), .rsp_v(rsp_v), .rsp_rdy({NPC{1'b1}}), .rsp_tag(rsp_tag),
      .rsp_beat(beat4), .rsp_data(rsp_data));
    for (genvar p = 0; p < NPC; p++) assign rsp_beat[p*5 +: 5] = {1'b0, beat4[p*4 +: 4]};
    initial for (int s = 0; s < MW; s++) hbm.mem[s] = src(s);
  end endgenerate
  // per-PC queues of 4-sector groups (MODEL 1/2) in stream order; tag = group index within layer
  int q [0:NPC-1][$];
  integer layer = -1; integer next_req = 0;   // MODEL 0: next 32-sector request within layer
  always @(posedge clk) if (rst_n) begin
    // responses
    for (int p = 0; p < NPC; p++) if (rsp_v[p]) begin
      automatic int tag = rsp_tag[p*16 +: 16], bt = rsp_beat[p*5 +: 5];
      automatic int L = tag >> 13;             // tag = layer<<13 | group (MODEL 1/2) or layer<<10 | req (MODEL 0)
      automatic int s;
      if (MODEL == 0) begin L = tag >> 10; s = L * SPL + (tag & 1023) * 32 + bt; end
      else s = L * SPL + (tag & 8191) * 4 + bt;
      if (rsp_data[p*256 +: 256] !== src(s)) begin if (bad < 5) $display("MISMATCH s=%0d", s); bad++; end
      got++; layer_got[L]++; layer_end[L] = cyc;
    end
    // requests
    req_v1 <= 0; req_vp <= 0;
    if (layer + 1 < LAYERS && cyc >= longint'(layer + 1) * PERIOD_CYC + 64 &&
        (layer < 0 || (MODEL == 0 ? next_req == 1024 : 1))) begin
      layer = layer + 1; layer_start[layer] = cyc; next_req = 0;
      if (MODEL != 0) for (int g = 0; g < 8192; g++) q[pc_of(layer * SPL + g * 4)].push_back(layer * 8192 + g);
    end
    if (MODEL == 0) begin
      if (layer >= 0 && next_req < 1024 && !(req_v1 && !req_rdy1)) begin
        if (req_v1 && req_rdy1) next_req = next_req + 1;
      end
      if (layer >= 0 && next_req < 1024) begin
        req_v1 <= 1; req_addr1 <= AW'(layer * SPL + next_req * 32); req_tag1 <= 16'((layer << 10) | next_req);
      end
    end else begin
      for (int p = 0; p < NPC; p++) begin
        if (req_vp[p] && req_rdyp[p]) void'(q[p].pop_front());
        if (q[p].size() != 0 && !(req_vp[p] && req_rdyp[p] && q[p].size() == 1)) begin end
      end
      for (int p = 0; p < NPC; p++) if (q[p].size() != 0) begin
        automatic int gi = q[p][0];
        req_vp[p] <= 1; req_addrp[p*AW +: AW] <= AW'((gi >> 13) * SPL + (gi & 8191) * 4);
        req_tagp[p*16 +: 16] <= 16'(gi);
      end
    end
    cyc <= cyc + 1;
    if (layer == LAYERS - 1 && layer_got[LAYERS-1] == SPL) begin : fin
      longint worst = 0, sum = 0;
      for (int L = 0; L < LAYERS; L++) begin
        automatic longint t = (layer_end[L] + 1 - layer_start[L]) * 1024;
        $display("LAYER %0d stream_ps=%0d", L, t); if (t > worst) worst = t; sum += t;
      end
      $display("SUMMARY model=%0d pcrdy=%0d worst_stream_ps=%0d mean_stream_ps=%0d worst_Bps=%0d mean_Bps=%0d got=%0d bad=%0d verdict=%s",
               MODEL, PCRDY, worst, sum / LAYERS, longint'(1048576.0 / (real'(worst) * 1e-12)),
               longint'(1048576.0 / (real'(sum) / LAYERS * 1e-12)), got, bad,
               (bad == 0 && got == longint'(LAYERS) * SPL) ? "PASS" : "FAIL");
      $finish;
    end
  end
  initial begin
    for (int L = 0; L < LAYERS; L++) layer_got[L] = 0;
    repeat (4) @(posedge clk); rst_n = 1;
  end
endmodule
