`timescale 1ns/1ps
// qfd_dv_stream_tile (rtl/qwen_dv/qfd_dv_stream_tile.sv) against the unchanged qfd_dv_stream reference:
//   reference inputs = tile inputs delayed one edge (the tile's face registers); the SU own-write inputs xw_* three edges
//   (face + the packer's P1 / P2 stages, QW-STREAM2 10-19);
//   reference tap outputs (tw_*, xt_*) delayed one more edge (the tile's interior tap relay);
//   relay outputs and fault compared on the same edge.
// Every output bit is compared on every edge from 20 edges after each reset release, over 10,000 edges with two resets,
// two SIDs, random kinds / destinations (own SID, broadcast, other), pass words in both directions, config changes,
// continuous 8-lane full packs, random lane subsets, duplicate addresses and abandoned beats, and (late) undefined kinds.
// Also compared: the per-edge fault cause (bad, pbad) inside both.
// PASS line: STREAM_TILE_EQ PASS edges10000 ...; any mismatch: $fatal STREAM_TILE_MISMATCH <port> cycle MUT.
module tb_stream_tile #(parameter integer MUT = 0);
 reg ck = 0, rst = 0; always #5 ck = ~ck;
 reg [3:0] sid = 3; reg cfg = 0; reg [1:0] dir = 3; reg [27:0] tag = 28'h1234567;
 reg [1087:0] sw = 0, se = 0; reg [7:0] we = 0; reg [191:0] addr = 0; reg [255:0] data = 0;
 // one-edge delayed reference inputs
 reg [3:0] sid_d = 0; reg cfg_d = 0; reg [1:0] dir_d = 0; reg [27:0] tag_d = 0;
 reg [1087:0] sw_d = 0, se_d = 0; reg [7:0] we_d = 0; reg [191:0] addr_d = 0; reg [255:0] data_d = 0;
 reg [7:0] we_d1 = 0, we_d2 = 0; reg [191:0] addr_d1 = 0, addr_d2 = 0; reg [255:0] data_d1 = 0, data_d2 = 0;
 always @(posedge ck) begin
  sid_d <= sid; cfg_d <= cfg; dir_d <= dir; tag_d <= tag; sw_d <= sw; se_d <= se;
  we_d1 <= we; addr_d1 <= addr; data_d1 <= data; we_d2 <= we_d1; addr_d2 <= addr_d1; data_d2 <= data_d1;
  we_d <= we_d2; addr_d <= addr_d2; data_d <= data_d2;
 end
 wire [1087:0] re, rw; wire rtw, rxv, rxb, rf; wire [1:0] rk; wire [23:0] ra, rxa; wire [1023:0] rd, rxd;
 qfd_dv_stream u_ref (.ck(ck), .rst_n(rst), .sid(sid_d), .cfg_v(cfg_d), .cfg_dir(dir_d), .cfg_tag(tag_d),
  .sw_i(sw_d), .se_i(se_d), .so_e(re), .so_w(rw), .xw_we(we_d), .xw_addr(addr_d), .xw_data(data_d),
  .tw_we(rtw), .tw_kind(rk), .tw_addr(ra), .tw_data(rd), .xt_v(rxv), .xt_a(rxa), .xt_d(rxd), .xt_bad(rxb), .fault(rf));
 // reference taps one more edge
 reg dtw = 0, dxv = 0, dxb = 0; reg [1:0] dk = 0; reg [23:0] da = 0, dxa = 0; reg [1023:0] dd = 0, dxd = 0;
 always @(posedge ck) begin dtw <= rtw; dxv <= rxv; dxb <= rxb; dk <= rk; da <= ra; dxa <= rxa; dd <= rd; dxd <= rxd; end
 wire [1087:0] qe, qw; wire qtw, qxv, qxb, qf; wire [1:0] qk; wire [23:0] qa, qxa; wire [511:0] qdl, qdh, qxl, qxh;
 qfd_dv_stream_tile #(.MUT(MUT)) u_t (.ck(ck), .rst_n(rst), .sid(sid), .cfg_v(cfg), .cfg_dir(dir), .cfg_tag(tag),
  .sw_lo(sw[543:0]), .sw_v(sw[1087]), .sw_hi(sw[1086:544]), .se_lo(se[543:0]), .se_v(se[1087]), .se_hi(se[1086:544]), .so_e(qe), .so_w(qw), .xw_we(we), .xw_addr(addr), .xw_data(data),
  .tw_we(qtw), .tw_kind(qk), .tw_addr(qa), .tw_data_lo(qdl), .tw_data_hi(qdh),
  .xt_v(qxv), .xt_a(qxa), .xt_d_lo(qxl), .xt_d_hi(qxh), .xt_bad(qxb), .fault(qf));
 reg [31:0] seed = 32'h76dc563a; integer cycle = 0, age = 0, mode = 0, nfull = 0, nemit = 0, ntw = 0, nxt = 0, npass = 0, nbad = 0;
 function automatic [31:0] step(input [31:0] x);
  reg [31:0] y; begin y = x ^ (x << 13); y = y ^ (y >> 17); step = y ^ (y << 5); end
 endfunction
 task automatic hdr(inout [1087:0] w, input integer p);
  reg [31:0] r;
  begin
   for (integer bb = 0; bb < 1088; bb = bb + 32) begin seed = step(seed); w[bb +: 32] = seed; end
   seed = step(seed); r = seed;
   w[1087] = rst && age >= 20 && (r[7:0] < p);
   w[1086:1084] = (cycle > 9000 && r[31:22] == 0) ? 3'(4 + r[9:8]) : 3'(r[11:10]);
   w[1083:1080] = (r[14:12] < 3) ? sid : (r[14:12] < 6) ? 4'hF : 4'(r[19:16]);
  end
 endtask
 always @(negedge ck) begin
  rst = !(cycle < 8 || (cycle >= 5000 && cycle < 5008));
  if (cycle == 5004) sid = 9;
  seed = step(seed);
  cfg = rst && (age == 17 || seed[9:0] == 0); if (cfg) begin seed = step(seed); dir = seed[1:0]; tag = 28'(step(seed)); end
  hdr(sw, 70); hdr(se, 50);
  // own writes: segment 0..191 of every 256 edges = continuous full 8-lane packs, rest = random subsets/addresses
  mode = cycle % 256;
  seed = step(seed);
  we = (rst && age >= 20) ? ((mode < 192) ? 8'hff : 8'(seed)) : 8'd0;
  for (integer ll = 0; ll < 8; ll = ll + 1) begin
   addr[24*ll +: 24] = 24'((((age - 20) / 8) << 6) | (((age - 20) % 8) * 8 + ll));
   if (mode >= 192) begin seed = step(seed); addr[24*ll +: 6] = seed[5:0]; if (seed[13:12] == 0) addr[24*ll+6 +: 16] = seed[31:16]; end
   seed = step(seed); data[32*ll +: 32] = seed;
  end
 end
 always @(posedge ck) begin
  cycle = cycle + 1; if (!rst) age = 0; else age = age + 1;
  #1;
  if (age >= 20) begin
   if (qe !== re) $fatal(1, "STREAM_TILE_MISMATCH so_e cycle%0d MUT%0d", cycle, MUT);
   if (qw !== rw) $fatal(1, "STREAM_TILE_MISMATCH so_w cycle%0d MUT%0d", cycle, MUT);
   if (qf !== rf) $fatal(1, "STREAM_TILE_MISMATCH fault cycle%0d MUT%0d", cycle, MUT);
   if ({qtw, qk, qa, qdh, qdl} !== {dtw, dk, da, dd}) $fatal(1, "STREAM_TILE_MISMATCH tw cycle%0d MUT%0d", cycle, MUT);
   if ({qxv, qxa, qxh, qxl, qxb} !== {dxv, dxa, dxd, dxb}) $fatal(1, "STREAM_TILE_MISMATCH xt cycle%0d MUT%0d", cycle, MUT);
   // per-edge fault cause (the sticky fault output only shows the first one): tile bad / pbad == reference bad / pbad
   if (u_t.bad !== u_ref.bad || u_t.pbad !== u_ref.pbad) $fatal(1, "STREAM_TILE_MISMATCH bad cycle%0d MUT%0d", cycle, MUT);
   if (u_ref.bad) nbad = nbad + 1;
   if (u_ref.emit) nemit = nemit + 1;
   if (rtw) ntw = ntw + 1;
   if (rxv) nxt = nxt + 1;
   if (re[1087] || rw[1087]) npass = npass + 1;
  end
  if (cycle == 10000) begin
   if (nemit < 100 || ntw < 500 || nxt < 500 || npass < 2000) $fatal(1, "STREAM_TILE_COVERAGE emit%0d tw%0d xt%0d pass%0d", nemit, ntw, nxt, npass);
   $display("STREAM_TILE_EQ PASS edges10000 resets2 sids2 emits%0d tw%0d xt%0d relay%0d badedges%0d fault%0d xtbad%0d", nemit, ntw, nxt, npass, nbad, rf, rxb);
   $finish;
  end
 end
endmodule
