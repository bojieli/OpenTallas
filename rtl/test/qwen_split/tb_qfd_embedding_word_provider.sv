`timescale 1ns/1ps
// ELEM-CENSUS 2026-10-16: standalone self-checking bench of qfd_embedding_word_provider (compute-die embedding row store,
// Q-NETLIST ab5f73bcc; until now exercised only as a child of tb_qfd_sys_face).  Drives the provider exactly as
// qfd_sys_face does under the static E calendar: fill_begin (FILL class) on its own edge, then one 512-b row word per
// edge (EMBW class: expected slot + word / scale identity coincident with the actual D2D word), then core_start and the
// sequencer's embed_code / embed_scale ROM-port reads.  No ready / credit: every event is a fixed edge.
//   EXACT part: NROW rows (random token / epoch / 64 code words / BF16 scale, words in a random order, the scale header
//               first as on the D2D link), every code word read back through the mapped ot_sram_1r1w_64x512_m1_r2c2 model
//               and compared bit-exact, the scale read compared, fault must stay 0.
//   DETECTION part (each after its own reset): a word whose actual token differs from the compiler slot, a word with no
//               slot, a core_start on an incomplete row, a read with the wrong row identity -- each must raise fault.
// Pass line: EMB_PROVIDER_PASS rows=<n> compared=<words> checks=<detections>; any miss prints EMB_PROVIDER_FAIL.
module tb_qfd_embedding_word_provider;
  localparam integer NROW = 6;
  reg ck = 0; always #0.5 ck = ~ck;
  reg rst_n = 0;
  reg word_v = 0; reg [511:0] word_data = 0; reg [17:0] word_token = 0; reg [5:0] word_index = 0; reg word_scale = 0;
  reg [15:0] word_epoch = 0;
  reg expected_word_slot = 0; reg [17:0] expected_token = 0; reg [5:0] expected_word = 0; reg expected_scale = 0;
  reg [15:0] expected_epoch = 0;
  reg fill_begin = 0; reg [17:0] fill_token = 0; reg [15:0] fill_epoch = 0;
  reg core_start = 0; reg [17:0] core_token = 0; reg [15:0] core_epoch = 0;
  reg embed_code_re = 0; reg [23:0] embed_code_addr = 0; wire [511:0] embed_code_q;
  reg embed_scale_re = 0; reg [17:0] embed_scale_addr = 0; wire [15:0] embed_scale_q;
  wire fault;
  qfd_embedding_word_provider dut (.ck(ck), .rst_n(rst_n), .word_v(word_v), .word_data(word_data), .word_token(word_token),
    .word_index(word_index), .word_scale(word_scale), .word_epoch(word_epoch), .expected_word_slot(expected_word_slot),
    .expected_token(expected_token), .expected_word(expected_word), .expected_scale(expected_scale),
    .expected_epoch(expected_epoch), .fill_begin(fill_begin), .fill_token(fill_token), .fill_epoch(fill_epoch),
    .core_start(core_start), .core_token(core_token), .core_epoch(core_epoch), .embed_code_re(embed_code_re),
    .embed_code_addr(embed_code_addr), .embed_code_q(embed_code_q), .embed_scale_re(embed_scale_re),
    .embed_scale_addr(embed_scale_addr), .embed_scale_q(embed_scale_q), .fault(fault));

  integer errs = 0, compared = 0, checks = 0, r, w, k, t;
  reg [511:0] row [0:63];
  reg [15:0] scale;
  reg [17:0] tok; reg [15:0] ep;
  integer order [0:63];

  task automatic idle;
    begin word_v = 0; expected_word_slot = 0; word_scale = 0; expected_scale = 0; fill_begin = 0; core_start = 0;
          embed_code_re = 0; embed_scale_re = 0; end
  endtask
  task automatic edge_; begin @(negedge ck); end endtask
  task automatic do_reset;
    begin idle; rst_n = 0; repeat (3) edge_; rst_n = 1; edge_; end
  endtask
  // one row word on one edge: actual D2D word + coincident compiler slot (identity may be corrupted by the caller)
  task automatic put_word(input integer idx, input bit is_scale, input [17:0] atok, input bit slot);
    begin
      word_v = 1; word_token = atok; word_epoch = ep; word_scale = is_scale; word_index = is_scale ? 6'd0 : idx[5:0];
      word_data = is_scale ? {496'd0, scale} : row[idx];
      expected_word_slot = slot; expected_token = tok; expected_epoch = ep; expected_scale = is_scale;
      expected_word = is_scale ? 6'd0 : idx[5:0];
      edge_; idle;
    end
  endtask
  task automatic new_row;
    begin
      tok = $urandom % 151936; ep = $urandom; scale = $urandom;
      for (k = 0; k < 64; k = k + 1) begin
        row[k] = {$urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom,
                  $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom, $urandom};
        order[k] = k;
      end
      for (k = 63; k > 0; k = k - 1) begin t = $urandom % (k + 1); w = order[k]; order[k] = order[t]; order[t] = w; end
    end
  endtask
  task automatic fill_row;   // FILL edge, a gap edge, the scale header, 64 code words, two drain edges
    begin
      fill_begin = 1; fill_token = tok; fill_epoch = ep; edge_; idle; edge_;
      put_word(0, 1, tok, 1);
      for (k = 0; k < 64; k = k + 1) put_word(order[k], 0, tok, 1);
      edge_; edge_;
    end
  endtask
  task automatic expect_fault(input [8*40-1:0] what);
    begin
      checks = checks + 1;
      repeat (3) edge_;
      if (fault !== 1'b1) begin errs = errs + 1; $display("ERR %0s: fault not raised", what); end
    end
  endtask

  initial begin
    // ------------------------------------------------------------------ EXACT
    do_reset;
    for (r = 0; r < NROW; r = r + 1) begin
      new_row; fill_row;
      core_start = 1; core_token = tok; core_epoch = ep; edge_; idle; edge_;
      for (w = 0; w < 64; w = w + 1) begin
        embed_code_re = 1; embed_code_addr = {tok, w[5:0]}; edge_; idle;   // SRAM samples here, rd_out one edge later
        @(posedge ck); #0.1;
        if (embed_code_q !== row[w]) begin
          errs = errs + 1; if (errs < 8) $display("ERR row %0d word %0d data mismatch", r, w); end
        compared = compared + 1;
        @(negedge ck);
      end
      embed_scale_re = 1; embed_scale_addr = tok; edge_; idle;
      @(posedge ck); #0.1;
      if (embed_scale_q !== scale) begin errs = errs + 1; $display("ERR row %0d scale %h != %h", r, embed_scale_q, scale); end
      compared = compared + 1;
      @(negedge ck);
      if (fault !== 1'b0) begin errs = errs + 1; $display("ERR row %0d: fault on an exact row", r); end
    end
    // ------------------------------------------------------------------ DETECTION
    // (1) actual word token differs from the compiler slot's token
    do_reset; new_row;
    fill_begin = 1; fill_token = tok; fill_epoch = ep; edge_; idle; edge_;
    put_word(0, 1, tok, 1); put_word(5, 0, tok ^ 18'd1, 1);
    expect_fault("wrong word token");
    // (2) an actual word with no compiler slot
    do_reset; new_row;
    fill_begin = 1; fill_token = tok; fill_epoch = ep; edge_; idle; edge_;
    put_word(0, 1, tok, 1); put_word(3, 0, tok, 0);
    expect_fault("word without slot");
    // (3) core_start on an incomplete row (word 63 missing)
    do_reset; new_row;
    fill_begin = 1; fill_token = tok; fill_epoch = ep; edge_; idle; edge_;
    put_word(0, 1, tok, 1);
    for (k = 0; k < 63; k = k + 1) put_word(k, 0, tok, 1);
    edge_; core_start = 1; core_token = tok; core_epoch = ep; edge_; idle;
    expect_fault("core_start on incomplete row");
    // (4) a read with the wrong row identity
    do_reset; new_row; fill_row;
    core_start = 1; core_token = tok; core_epoch = ep; edge_; idle; edge_;
    embed_code_re = 1; embed_code_addr = {tok ^ 18'd2, 6'd9}; edge_; idle;
    expect_fault("read with wrong row identity");

    if (errs == 0 && compared == NROW * 65 && checks == 4)
      $display("EMB_PROVIDER_PASS rows=%0d compared=%0d checks=%0d", NROW, compared, checks);
    else begin
      $display("EMB_PROVIDER_FAIL errors=%0d compared=%0d checks=%0d", errs, compared, checks);
      $fatal(1);
    end
    $finish;
  end
endmodule
