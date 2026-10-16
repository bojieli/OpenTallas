`timescale 1ns/1ps
// Q-ELEM-CMP (2026-10-16): production-shape bench of the die master qfd_res_train_issue (TRAIN_EDGES = TE).
// Independent reference: every ME instruction (go edge, tiles 1..8, ts, split 0..11, oen) is queued in program order;
// the controller emits 8*tiles result tags per instruction (tag_v && tag_last), spaced as the ME issues bursts; the
// FIRST tag of each instruction must produce exactly one train_start sampled TE edges after the tag edge, carrying
// count = tiles, stride = max(ts, 8), payload = oen, slot_count = 8 (split <= 7) / 4 / 2 / 1 (split 8 / 9 / >= 10).
// Up to 4 instructions are outstanding (the issuer's queue depth); fault must stay 0.  Prints one PASS/FAIL line.
module tb_qfd_res_train_issue;
parameter integer TE=11, MUT=0, NINST=400, SEED=1;
reg ck=0; always #5 ck=~ck;
reg rst_n=0, me_go=0, me_oen=0, tag_v=0, tag_last=0;
reg [17:0] me_tiles=0; reg [23:0] me_ts=0; reg [3:0] me_split=0;
wire train_start, payload_write, fault; wire [3:0] train_count, slot_count; wire [31:0] capture_stride;
qfd_res_train_issue #(.TRAIN_EDGES(TE), .MUT(MUT)) dut(.ck(ck), .rst_n(rst_n), .me_go(me_go), .me_tiles(me_tiles), .me_ts(me_ts),
  .me_split(me_split), .me_oen(me_oen), .tag_v(tag_v), .tag_last(tag_last), .train_start(train_start), .train_count(train_count),
  .capture_stride(capture_stride), .payload_write(payload_write), .slot_count(slot_count), .fault(fault));
// reference: expected start word per edge
localparam integer HZ = 1<<20;
reg [41:0] exp_w [0:HZ-1]; reg exp_v [0:HZ-1];
integer edge_n=0, err=0, nstart=0, nexp=0, i, k, seed;
reg [3:0] q_tiles [0:NINST-1]; reg [31:0] q_stride [0:NINST-1]; reg q_oen [0:NINST-1]; reg [3:0] q_ns [0:NINST-1];
reg [23:0] q_ts [0:NINST-1];
function automatic [3:0] ns_of(input [3:0] sp); ns_of = (sp<=7) ? 4'd8 : (sp==8) ? 4'd4 : (sp==9) ? 4'd2 : 4'd1; endfunction
always @(posedge ck) begin
  edge_n <= edge_n + 1;
  if (rst_n) begin
    if (train_start !== (exp_v[edge_n] === 1'b1)) begin err = err + 1; if (err < 10) $display("ERR edge %0d start=%b exp=%b", edge_n, train_start, exp_v[edge_n]); end
    if (train_start) begin
      nstart = nstart + 1;
      if ({train_count, capture_stride, payload_write, slot_count} !== {exp_w[edge_n][40:37], exp_w[edge_n][36:5], exp_w[edge_n][4], exp_w[edge_n][3:0]}) begin
        err = err + 1; if (err < 10) $display("ERR edge %0d fields", edge_n); end
    end
    if (fault) begin err = err + 1; if (err < 10) $display("ERR edge %0d fault", edge_n); end
  end
end
integer t_go, t_tag, outstanding, issued, popped, ntag;
initial begin
  seed = SEED;
  for (i = 0; i < HZ; i = i + 1) begin exp_v[i] = 0; exp_w[i] = 0; end
  for (i = 0; i < NINST; i = i + 1) begin
    q_tiles[i] = 1 + ($urandom(seed) % 8); seed = seed + 7;
    q_ts[i] = ($urandom % 4 == 0) ? (24'($urandom % 8)) : (24'(8 + $urandom % 200));
    q_oen[i] = $urandom; q_ns[i] = ns_of(4'($urandom % 12));
    q_stride[i] = (q_ts[i] < 8) ? 32'd8 : 32'(q_ts[i]);
  end
  repeat (5) @(negedge ck); rst_n = 1; repeat (3) @(negedge ck);
  // program: each instruction's go, then its 8*tiles tags spaced 1..3 edges apart; the next go may precede the
  // previous tags (queue up to 3 ahead, as the ME pipelines descriptor issue)
  issued = 0; popped = 0;
  while (popped < NINST) begin
    // issue gos while fewer than 3 are queued ahead
    while (issued < NINST && issued - popped < 3) begin
      @(negedge ck); me_go = 1; me_tiles = 18'(q_tiles[issued]); me_ts = q_ts[issued];
      me_split = (q_ns[issued] == 8) ? 4'($urandom % 8) : (q_ns[issued] == 4) ? 4'd8 : (q_ns[issued] == 2) ? 4'd9 : 4'(10 + $urandom % 2);
      me_oen = q_oen[issued]; issued = issued + 1;
      @(negedge ck); me_go = 0;
    end
    // tags of instruction 'popped'
    for (k = 0; k < 8 * q_tiles[popped]; k = k + 1) begin
      repeat ($urandom % 3) @(negedge ck);
      @(negedge ck); tag_v = 1; tag_last = 1;
      if (k == 0) begin
        // tag sampled at the coming posedge (edge index edge_n); start sampled TE edges later
        exp_v[edge_n + TE] = 1;
        exp_w[edge_n + TE] = {1'b0, q_tiles[popped], q_stride[popped], q_oen[popped], q_ns[popped]};
        nexp = nexp + 1;
      end
      @(negedge ck); tag_v = 0; tag_last = 0;
      // a tag_v without tag_last (non-final beat of a burst) must not count
      if ($urandom % 4 == 0) begin @(negedge ck); tag_v = 1; @(negedge ck); tag_v = 0; end
    end
    popped = popped + 1;
  end
  repeat (TE + 20) @(negedge ck);
  if (err == 0 && nstart == nexp && nexp == NINST)
    $display("RTI_BENCH PASS MUT=%0d TE=%0d starts=%0d instructions=%0d errors=0", MUT, TE, nstart, NINST);
  else
    $display("RTI_BENCH FAIL MUT=%0d TE=%0d starts=%0d expected=%0d errors=%0d", MUT, TE, nstart, nexp, err);
  $finish;
end
endmodule
