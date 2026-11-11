`timescale 1ns/1ps
// STM-DQ (DIE-QC-97 11-10) old-vs-new bench: the stm stream half as qfd_dv_s6_stm builds it, before and after the form.
//   OLD = qfd_dv_s5_rst2 u_rl (2 landing stages) -> qfd_dv_stream_tile_old (the unchanged 5333b7dca83 tile, renamed by
//         run_tile_stmdq.sh) -- exactly the default qfd_dv_s6_stm u_rl / u_stream pair;
//   NEW = qfd_dv_stream_tile compiled with +define+OT_QC_STMDQ, fed the RAW rst_n (the OT_QC_STMDQ qfd_dv_s6_stm branch).
// The form adds no edge, so EVERY output port is compared on EVERY edge, including the reset edges and the first edges
// after each release (no settle window), plus the per-edge fault causes pbad / bad inside both.
// Traffic: 200,000 edges, ~1,000 resets of random length (1..6 edges, asserted at random phases), cfg_v on the first
// released edge half the time and at random otherwise, two SIDs, random pass words both directions (own SID / broadcast /
// other, undefined kinds late), own writes in four modes: back-to-back full 8-lane packs on one beat, random lane
// subsets, duplicate slot addresses (two lanes on one slot in one cycle), lane-0-off / mixed-beat (beat fault) writes,
// and idle gaps.  PASS line: STMDQ_EQ PASS ...; first mismatch: $fatal STMDQ_MISMATCH <port> edge MUT.
// MUT (new tile only): 0 positive; 41 we_b never loads, 42 dup partial 3 one edge late, 43 own-write reset group one edge
// late -- each must FAIL.
module qfd_dv_s5_rst2_tb (input wire ck, input wire rst_n, output wire rst);   // = qfd_dv_s5_rst2 (s5 leaves), verbatim
    reg rs1, rs2;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin rs1 <= 1'b0; rs2 <= 1'b0; end
        else begin rs1 <= 1'b1; rs2 <= rs1; end
    assign rst = rs2;
endmodule

module tb_stream_tile_stmdq #(parameter integer MUT = 0, parameter integer EDGES = 200000);
 reg ck = 0, rst_n = 0; always #5 ck = ~ck;
 reg [3:0] sid = 3; reg cfg = 0; reg [1:0] dir = 3; reg [27:0] tag = 28'h1234567;
 reg [1087:0] sw = 0, se = 0; reg [7:0] we = 0; reg [191:0] addr = 0; reg [255:0] data = 0;
 wire rst_l;
 qfd_dv_s5_rst2_tb u_rl (.ck(ck), .rst_n(rst_n), .rst(rst_l));
 wire [1087:0] oe, ow, ne, nw; wire otw, oxv, oxb, of, ntw, nxv, nxb, nf; wire [1:0] ok, nk; wire [23:0] oa, oxa, na, nxa;
 wire [511:0] odl, odh, oxl, oxh, ndl, ndh, nxl, nxh;
 qfd_dv_stream_tile_old #(.MUT(0)) u_o (.ck(ck), .rst_n(rst_l), .sid(sid), .cfg_v(cfg), .cfg_dir(dir), .cfg_tag(tag),
  .sw_lo(sw[543:0]), .sw_v(sw[1087]), .sw_hi(sw[1086:544]), .se_lo(se[543:0]), .se_v(se[1087]), .se_hi(se[1086:544]),
  .so_e(oe), .so_w(ow), .xw_we(we), .xw_addr(addr), .xw_data(data),
  .tw_we(otw), .tw_kind(ok), .tw_addr(oa), .tw_data_lo(odl), .tw_data_hi(odh),
  .xt_v(oxv), .xt_a(oxa), .xt_d_lo(oxl), .xt_d_hi(oxh), .xt_bad(oxb), .fault(of));
 qfd_dv_stream_tile #(.MUT(MUT)) u_n (.ck(ck), .rst_n(rst_n), .sid(sid), .cfg_v(cfg), .cfg_dir(dir), .cfg_tag(tag),
  .sw_lo(sw[543:0]), .sw_v(sw[1087]), .sw_hi(sw[1086:544]), .se_lo(se[543:0]), .se_v(se[1087]), .se_hi(se[1086:544]),
  .so_e(ne), .so_w(nw), .xw_we(we), .xw_addr(addr), .xw_data(data),
  .tw_we(ntw), .tw_kind(nk), .tw_addr(na), .tw_data_lo(ndl), .tw_data_hi(ndh),
  .xt_v(nxv), .xt_a(nxa), .xt_d_lo(nxl), .xt_d_hi(nxh), .xt_bad(nxb), .fault(nf));
 // power-up: reset for the first 8 edges; comparison starts at edge 12 (past the power-up X of the reset-free pipeline
 // words in a 4-state simulator), then runs on every edge including every later reset edge
 reg [31:0] seed = 32'h5f3a9c21; integer cycle = 0, rlen = 8, gap = 40, mode = 0, beat = 0;
 integer nrst = 0, nfault = 0, ndup = 0, nbb = 0, nfull = 0, nemit = 0, nxt = 0, ntwc = 0, npass = 0, ncfg0 = 0;
 reg prev_rst = 0;
 function automatic [31:0] step(input [31:0] x);
  reg [31:0] y; begin y = x ^ (x << 13); y = y ^ (y >> 17); step = y ^ (y << 5); end
 endfunction
 task automatic hdr(inout [1087:0] w, input integer p);
  reg [31:0] r;
  begin
   for (integer bb = 0; bb < 1088; bb = bb + 32) begin seed = step(seed); w[bb +: 32] = seed; end
   seed = step(seed); r = seed;
   w[1087] = (r[7:0] < p);
   w[1086:1084] = (cycle > EDGES - 20000 && r[31:22] == 0) ? 3'(4 + r[9:8]) : 3'(r[11:10]);
   w[1083:1080] = (r[14:12] < 3) ? sid : (r[14:12] < 6) ? 4'hF : 4'(r[19:16]);
  end
 endtask
 task automatic own;
  reg [31:0] r; reg [15:0] bt; reg [5:0] sl;
  begin
   seed = step(seed); r = seed;
   if (cycle % 512 == 0) begin seed = step(seed); mode = seed[1:0]; end
   we = 0; addr = 0;
   for (integer bb = 0; bb < 256; bb = bb + 32) begin seed = step(seed); data[bb +: 32] = seed; end
   case (mode)
    0: begin   // back-to-back full packs: 8 lanes x 8 slots, slot group beat % 8, beat advances every 8 edges
         we = 8'hFF; bt = 16'(beat / 8);
         for (integer l = 0; l < 8; l = l + 1) addr[24*l +: 24] = {2'b01, bt, 6'(8 * (beat % 8) + l)};
         beat = beat + 1;
       end
    1: begin   // random lane subsets, one beat, random slots (duplicates arise)
         seed = step(seed); we = (r[3:0] < 5) ? seed[7:0] : 8'd0; bt = 16'(r[31:24] & 8'h3);
         for (integer l = 0; l < 8; l = l + 1) begin seed = step(seed); addr[24*l +: 24] = {2'b01, bt, seed[5:0]}; end
       end
    2: begin   // forced duplicates: lanes l and l+1 on one slot, lane 0 always on (no beat fault)
         seed = step(seed); we = (r[2:0] == 0) ? (seed[7:0] | 8'h01) : 8'd0; sl = seed[13:8];
         for (integer l = 0; l < 8; l = l + 1) begin seed = step(seed); addr[24*l +: 24] = {2'b01, 16'h0007, (l == 2 || l == 3) && r[5:4] == 0 ? sl : 6'(8 * l + seed[2:0])}; end
       end
    default: begin   // beat faults: lane 0 off with others on, or mixed beat addresses
         seed = step(seed); we = (r[3:0] < 3) ? (r[4] ? (seed[7:0] & 8'hFE) : seed[7:0]) : 8'd0;
         for (integer l = 0; l < 8; l = l + 1) begin seed = step(seed); addr[24*l +: 24] = {2'b01, (l == 5 && r[6]) ? 16'h0013 : 16'h0011, 6'(8 * l + seed[2:0])}; end
       end
   endcase
  end
 endtask
 always @(negedge ck) begin
  seed = step(seed);
  // reset: random length 1..6 edges, every 40..440 edges
  if (rlen > 0) begin rlen = rlen - 1; rst_n = 0; end
  else if (gap == 0) begin rlen = 1 + (seed[2:0] % 6); rst_n = 0; nrst = nrst + 1; seed = step(seed); gap = 40 + seed[8:0] % 400; end
  else begin rst_n = 1; gap = gap - 1; end
  if (cycle == EDGES / 2) sid = 9;
  seed = step(seed);
  cfg = (rst_n && !prev_rst && seed[0]) || seed[12:9] == 0;     // first released edge (half the time) + random
  if (cfg) begin seed = step(seed); dir = seed[1:0]; tag = 28'(step(seed)); if (rst_n && !prev_rst) ncfg0 = ncfg0 + 1; end
  prev_rst = rst_n;
  hdr(sw, 70); hdr(se, 50);
  own;
  cycle = cycle + 1;
  if (cycle == EDGES) begin
   $display("STMDQ_EQ PASS edges%0d MUT%0d resets %0d cfg_at_release %0d fault_edges %0d dup_edges %0d beatbad_edges %0d full_beats %0d own_emits %0d xt %0d tw %0d pass %0d",
            EDGES, MUT, nrst, ncfg0, nfault, ndup, nbb, nfull, nemit, nxt, ntwc, npass);
   $finish;
  end
 end
 // compare on every edge (posedge + 1)
 always @(posedge ck) #1 if (cycle >= 12) begin
  if (oe !== ne) $fatal(1, "STMDQ_MISMATCH so_e edge %0d MUT%0d", cycle, MUT);
  if (ow !== nw) $fatal(1, "STMDQ_MISMATCH so_w edge %0d MUT%0d", cycle, MUT);
  if ({otw, ok, oa, odh, odl} !== {ntw, nk, na, ndh, ndl}) $fatal(1, "STMDQ_MISMATCH tw edge %0d MUT%0d", cycle, MUT);
  if ({oxv, oxa, oxh, oxl} !== {nxv, nxa, nxh, nxl}) $fatal(1, "STMDQ_MISMATCH xt edge %0d MUT%0d", cycle, MUT);
  if (oxb !== nxb) $fatal(1, "STMDQ_MISMATCH xt_bad edge %0d MUT%0d", cycle, MUT);
  if (of !== nf) $fatal(1, "STMDQ_MISMATCH fault edge %0d MUT%0d", cycle, MUT);
  if (u_o.pbad !== u_n.pbad) $fatal(1, "STMDQ_MISMATCH pbad(internal) edge %0d MUT%0d", cycle, MUT);
  if (u_o.bad !== u_n.bad) $fatal(1, "STMDQ_MISMATCH bad(internal) edge %0d MUT%0d", cycle, MUT);
  nfault = nfault + (u_o.pbad ? 1 : 0); ndup = ndup + (u_o.dupq ? 1 : 0); nbb = nbb + (u_o.bbq ? 1 : 0);
  nfull = nfull + ((|u_o.complete_k) ? 1 : 0); nemit = nemit + ((oe[1087] && u_o.ie_e[78]) || (ow[1087] && u_o.ie_w[78]) ? 1 : 0);
  nxt = nxt + (oxv ? 1 : 0); ntwc = ntwc + (otw ? 1 : 0); npass = npass + (oe[1087] ? 1 : 0);
 end
endmodule
