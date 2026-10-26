`timescale 1ns/1ps
// KVJ-SMALL b2 2026-10-17 (KVJ-C3 open: the shared boot bus of qkd_kv_es_fan_root + qkd_embedding_static_join4_cal had
// no producer): qkd_static_kv_boot_dispatch ESCFG=1, image targets 12 (1024 PC player words) and 13 (8 beat segments)
// from tools/qwen_kv_die/kv_static_programme.es_cfg_words (= kvjc3_pc_chain.boot_words).
// Reference: kvjc3 boot.memh (the C3 gate's own bus stream, {addr8, data64} per word).
// SCN 0: targets 1..9, 12, 13, 0: the dispatcher's es_cfg stream equals boot.memh word for word (1026 writes, then the
//        6 unused segments {len 0, off 0}), setup_ready, no fault.
// SCN 1: no targets 12/13 (1..9 then 0): ISA refused (code 6), never setup_ready.
// SCN 2: a target-12 word with data[40] set: fault code 5.     SCN 3: a target-12 word whose stack field != a[9:8]: code 5.
// SCN 4: ESCFG=0: target 12 after 9 is refused (code 3), no es_cfg write.
// SCN 5: a target-13 word with data[63:62] = 0: code 5.      SCN 6: as SCN 0 with LINKCFG=1 (order 1..9, 11, 12, 13, 0).
// MUT (dispatcher): 7 pc/reg swapped address, 8 segment 1 dropped (SCN 0 must FAIL).
module tb_kv_es_cfg_boot #(parameter integer SCN = 0, parameter integer MUT = 0);
 localparam integer ESCFG = (SCN == 4) ? 0 : 1, LINKCFG = (SCN == 6) ? 1 : 0;
 reg ck = 0; always #5 ck = ~ck;
 reg rst_n = 0;
 reg [142:0] pr = 0; reg [3:0] target = 1; reg ready = 0, active = 0;
 reg [15:0] epoch = 77; reg [63:0] digest = 0; reg [159:0] applied = 0; reg [2:0] configured = 0;
 wire lw, ww, ow; wire [8:0] la; wire [7:0] wa, ga; wire [1:0] oa; wire [63:0] ld, wd, gd, cd; wire [31:0] od, lwe, fwe;
 wire [127:0] cwe, last; wire [7:0] ca; wire [31:0] flast; wire setup, dfault; wire [7:0] code; wire [15:0] ie; wire [63:0] id;
 wire dwe; wire [7:0] dad; wire [63:0] dda; wire ltx, lrx; wire [5:0] laddr; wire [31:0] ldata;
 wire ewe; wire [7:0] eaddr; wire [63:0] edata;
 qkd_static_kv_boot_dispatch #(.MUT(MUT), .DIECFG(0), .LINKCFG(LINKCFG), .ESCFG(ESCFG)) disp (.ck(ck), .rst_n(rst_n),
  .boot_pr(pr), .boot_image_target(target), .boot_image_ready(ready), .boot_image_fault(1'b0), .boot_image_epoch(epoch),
  .boot_image_digest(digest), .execution_active(active), .sink_applied(applied), .local_configured(configured),
  .sink_fault(1'b0), .diecfg_sealed(1'b0), .diecfg_fault(1'b0),
  .layer_we(lw), .layer_addr(la), .layer_data(ld), .writer_we(ww), .writer_addr(wa), .writer_data(wd), .ownership_we(ow),
  .ownership_addr(oa), .ownership_data(od), .landing_we(lwe), .front_we(fwe), .group_addr(ga), .group_data(gd),
  .controller_we(cwe), .controller_addr(ca), .controller_data(cd), .controller_last(last), .front_last(flast),
  .diecfg_we(dwe), .diecfg_addr(dad), .diecfg_data(dda),
  .link_cfg_tx_we(ltx), .link_cfg_rx_we(lrx), .link_cfg_addr(laddr), .link_cfg_data(ldata),
  .es_cfg_we(ewe), .es_cfg_addr(eaddr), .es_cfg_data(edata),
  .setup_ready(setup), .fault(dfault), .fault_code(code), .installed_epoch(ie), .installed_isa_digest(id));
 reg [71:0] stream [0:2047]; integer nd = 0;
 always @(posedge ck) if (ewe) begin stream[nd] <= {eaddr, edata}; nd <= nd + 1; end
 reg [63:0] t12 [0:1023]; reg [63:0] t13 [0:7]; reg [71:0] ref_bus [0:1025];
 integer errors = 0, t, a, n;
 function automatic [63:0] value(input integer t, input integer a); value = (t == 3) ? 64'(a) : 64'h1234567800000000 ^ (64'(t) << 32) ^ 64'(a); endfunction
 task tick; begin @(negedge ck); end endtask
 task word(input [3:0] tg, input integer a, input [63:0] d); begin target = tg; pr = 0; pr[74] = 1; pr[73:64] = 10'(a); pr[63:0] = d; tick(); pr = 0; end endtask
 task image_done(input [3:0] tg); begin pr = 0; tick(); ready = 1; target = tg; tick(); tick(); ready = 0; tick(); end endtask
 initial begin
  $readmemh("target12.hex", t12); $readmemh("target13.hex", t13); $readmemh("boot.memh", ref_bus);
  repeat (3) tick(); rst_n = 1; repeat (4) tick();
  for (t = 1; t <= 9; t = t + 1) begin
   case (t) 1: n = 327; 2: n = 181; 3: n = 4; 4, 5: n = 192; default: n = 1024; endcase
   for (a = 0; a < n; a = a + 1) word(4'(t), a, value(t, a));
   image_done(4'(t));
  end
  if (LINKCFG != 0) begin for (a = 0; a < 66; a = a + 1) word(11, a, 64'(a)); image_done(11); end
  if (SCN != 1) begin
   for (a = 0; a < 1024; a = a + 1)
    word(12, a, (SCN == 2 && a == 300) ? (t12[a] | 64'h100_0000_0000) : (SCN == 3 && a == 600) ? (t12[a] ^ 64'h3_0000) : t12[a]);
   image_done(12);
   if (SCN != 4) begin
    for (a = 0; a < 8; a = a + 1) word(13, a, (SCN == 5 && a == 1) ? (t13[a] & 64'h3fff_ffff_ffff_ffff) : t13[a]);
    image_done(13);
   end
  end
  target = 0; tick(); ready = 1; digest = 64'h0fedcba987654321; configured = 7; applied = {160{1'b1}}; tick(); tick(); tick();
  case (SCN)
   0, 6: begin
    if (!setup || dfault) begin $display("BAD setup_ready %0d fault %0d code %h", setup, dfault, code); errors++; end
    if (nd != 1032) begin $display("BAD es cfg writes %0d (1032 expected)", nd); errors++; end
    for (a = 0; a < 1026 && a < nd; a = a + 1)
     if (stream[a] !== ref_bus[a]) begin if (errors < 8) $display("BAD es cfg write %0d %h, kvjc3 boot.memh %h", a, stream[a], ref_bus[a]); errors++; end
    for (a = 1026; a < 1032 && a < nd; a = a + 1)
     if (stream[a] !== {8'(a - 1024), 64'h4000_0000_0000_0000}) begin $display("BAD padding segment write %0d %h", a, stream[a]); errors++; end
   end
   1: if (setup || !dfault || !code[6]) begin $display("BAD missing 12/13 not refused: setup %0d fault %0d code %h", setup, dfault, code); errors++; end
   2, 3, 5: if (setup || !dfault || !code[5]) begin $display("BAD malformed word not refused: setup %0d fault %0d code %h", setup, dfault, code); errors++; end
   4: if (setup || !dfault || !code[3] || nd != 0) begin $display("BAD ESCFG=0 accepted target 12: setup %0d fault %0d code %h writes %0d", setup, dfault, code, nd); errors++; end
  endcase
  if (errors) begin $display("FAIL kv_es_cfg_boot scn%0d mut%0d errors%0d", SCN, MUT, errors); $fatal(1); end
  $display("PASS kv_es_cfg_boot scn%0d mut%0d writes%0d", SCN, MUT, nd);
  $finish;
 end
 initial begin #50000000; $display("FAIL kv_es_cfg_boot timeout"); $fatal(1); end
endmodule
