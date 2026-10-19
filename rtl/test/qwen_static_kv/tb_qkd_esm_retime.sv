`timescale 1ns/1ps
// KVJ-G2b 10-17: the embedding endpoint's return re-timing (qkd_embedding_static_pc_strap RETIME=1).  The controller
// word er arrives D edges BEFORE the compiled return_slot (D = 0..6, the elastic HBM side early) -> the beat at the slot
// carries that word, no fault.  Negative cases (each must fault): the word one edge AFTER the slot (late), two words for
// one read, a word with no read pending.  With RETIME=0 (+define+RT0) every D > 0 case must fault (the exact endpoint).
module tb_qkd_esm_retime;
`ifdef RT0
  localparam integer RT = 0;
`else
  localparam integer RT = 1;
`endif
  reg ck = 0, rst_n = 0; always #1 ck = ~ck;
  reg issue_v = 0, return_slot = 0; reg [17:0] token = 18'd777; reg [5:0] word_index = 6'd5; reg [260:0] er = 0;
  wire [1:0] mstack; wire [4:0] mpc, mb, mc; wire [18:0] mrow; wire [24:0] msec; wire mvalid;
  qkd_embedding_static_map u_ref (.token(token), .word_index(word_index), .half(1'b0), .scale(1'b0), .logical_sector(msec),
    .stack(mstack), .pc(mpc), .bank(mb), .col(mc), .row(mrow), .valid_address(mvalid));
  wire [287:0] es; wire beat_v; wire [255:0] beat_data; wire [17:0] beat_token; wire [5:0] beat_word;
  wire beat_half, beat_scale, corrected, fault, outstanding; wire [15:0] beat_epoch;
  qkd_embedding_static_pc_strap #(.RETIME(RT)) dut (.ck(ck), .rst_n(rst_n), .boot_ready(1'b1), .strap_stack(mstack),
    .strap_pc(mpc), .issue_v(issue_v), .token(token), .word_index(word_index), .half(1'b0), .scale(1'b0), .epoch(16'd9),
    .return_slot(return_slot), .es(es), .er(er), .beat_v(beat_v), .beat_data(beat_data), .beat_token(beat_token),
    .beat_word(beat_word), .beat_half(beat_half), .beat_scale(beat_scale), .beat_epoch(beat_epoch), .corrected(corrected),
    .fault(fault), .outstanding(outstanding));
  integer errors = 0, d, k, got;
  reg [255:0] want;
  task automatic edge_; begin @(negedge ck); end endtask
  task automatic reset_; begin rst_n = 0; issue_v = 0; return_slot = 0; er = 0; repeat (3) edge_; rst_n = 1; edge_; end endtask
  // one read: issue, the word at slot-D (D<0: after the slot), the slot SLOT edges after the issue; extra = 2nd word
  task automatic read_(input integer D, input integer extra, input integer noissue, output integer ok, output integer f);
    integer t; begin
      want = {8{32'h5a000000 | 32'(D + 64)}}; ok = 0;
      if (!noissue) begin issue_v = 1; edge_; issue_v = 0; end
      for (t = 1; t <= 20; t = t + 1) begin
        er = 0; return_slot = 0;
        if (t == 12 - D || (extra && t == 12 - D - 1)) begin er[0] = 1; er[256:1] = want; end
        if (t == 12) return_slot = 1;
        edge_;
        if (beat_v && beat_data == want) ok = 1;
      end
      er = 0; return_slot = 0; edge_; f = fault;
    end endtask
  integer ok, f;
  initial begin
    for (d = 0; d <= 6; d = d + 1) begin
      reset_; read_(d, 0, 0, ok, f);
      if (RT && (!ok || f)) begin errors = errors + 1; $display("FAIL early D=%0d ok=%0d fault=%0d", d, ok, f); end
      if (!RT && d > 0 && !f) begin errors = errors + 1; $display("FAIL RT0 early D=%0d not faulted", d); end
      if (!RT && d == 0 && (!ok || f)) begin errors = errors + 1; $display("FAIL RT0 exact"); end
    end
    reset_; read_(-1, 0, 0, ok, f); if (!f) begin errors = errors + 1; $display("FAIL late word not faulted"); end
    reset_; read_(3, 1, 0, ok, f);  if (!f) begin errors = errors + 1; $display("FAIL double word not faulted"); end
    reset_; read_(3, 0, 1, ok, f);  if (!f) begin errors = errors + 1; $display("FAIL word without a read not faulted"); end
    // back-to-back reads (two tokens, early words both): exact beats, no fault
    reset_; read_(5, 0, 0, ok, f); got = ok; read_(2, 0, 0, ok, f);
    if (RT && (!got || !ok || f)) begin errors = errors + 1; $display("FAIL back-to-back"); end
    $display("%s ESM_RETIME RETIME=%0d errors=%0d", errors == 0 ? "PASS" : "FAIL", RT, errors);
    $finish;
  end
endmodule
