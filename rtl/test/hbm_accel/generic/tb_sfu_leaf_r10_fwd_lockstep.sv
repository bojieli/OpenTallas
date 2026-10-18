`timescale 1ns/1ps
`default_nettype none
// HBM-NATIVE 2026-10-17: leaf-level lockstep of ot_hgi_sfu_store_stripe_leaf_r10 (dedicated chain-forward export flops)
// against the CLOSED r10 RTL (ot_hgi_sfu_store_stripe_leaf_r10_ref0 = the hbm_sfu_store_stripe_r10_1017-r10-947bd4836
// source). Both get the same stimulus; EVERY output is compared (4-state, !==) on EVERY rising edge, including the
// reset phases (rst_a is the head's synchronous stage-A relay: the leaf has no asynchronous state).
// Stimulus: random chain writes, half of them well-formed programme words (magic c7a1 + pc tag) so reads produce
// calendars, legal / illegal starts with random spans and loops, random in_cv, write-while-busy faults, mid-run resets.
// Prints SFU_LEAF_FWD_LOCKSTEP PASS edges=<n> ... or SFU_LEAF_FWD_MISMATCH / FAIL.
module tb_sfu_leaf_r10_fwd_lockstep;
  localparam integer AW = 11, PCLO = 234 - AW;
  reg clk = 0; always #0.5 clk = ~clk;
  reg rst_a, in_we, in_start_v, in_legal, in_loops_one, in_cv;
  reg [AW-1:0] in_addr, in_start_base; reg [255:0] in_data; reg [AW:0] in_span; reg [15:0] in_loops;
  wire [AW-1:0] a_addr, b_addr; wire [255:0] a_data, b_data; wire [221:0] a_cal, b_cal;
  wire a_v, a_act, a_done, a_flt, b_v, b_act, b_done, b_flt; wire [31:0] a_ord, b_ord; wire [1:0] a_hz, b_hz; wire a_b26, b_b26;
  ot_hgi_sfu_store_stripe_leaf_r10_ref0 u_ref(.clk(clk), .rst_a(rst_a), .in_we(in_we), .in_addr(in_addr), .in_data(in_data),
    .out_addr(a_addr), .out_data(a_data), .in_start_v(in_start_v), .in_start_base(in_start_base), .in_legal(in_legal),
    .in_span(in_span), .in_loops(in_loops), .in_loops_one(in_loops_one), .in_cv(in_cv), .out_cal(a_cal), .out_v(a_v),
    .out_active(a_act), .out_done(a_done), .out_fault(a_flt), .out_ord(a_ord), .out_hz(a_hz), .out_b26(a_b26));
  ot_hgi_sfu_store_stripe_leaf_r10 u_new(.clk(clk), .rst_a(rst_a), .in_we(in_we), .in_addr(in_addr), .in_data(in_data),
    .out_addr(b_addr), .out_data(b_data), .in_start_v(in_start_v), .in_start_base(in_start_base), .in_legal(in_legal),
    .in_span(in_span), .in_loops(in_loops), .in_loops_one(in_loops_one), .in_cv(in_cv), .out_cal(b_cal), .out_v(b_v),
    .out_active(b_act), .out_done(b_done), .out_fault(b_flt), .out_ord(b_ord), .out_hz(b_hz), .out_b26(b_b26));
  // r10n2 (KH-NATIVE3 10-17): the chain-out pins are the closed RTL's delayed by ONE edge (+1 chain stage: in-face pin flop
  // -> out-face fwd flop); every other output on the same edge. The mutant (OT_SFU_LEAF10_MUT_FWD = r10n 1-edge forward) must fail.
  reg [AW-1:0] a_addr_d; reg [255:0] a_data_d;
  always @(posedge clk) begin a_addr_d <= a_addr; a_data_d <= a_data; end
  wire [600:0] oa = {a_addr_d, a_data_d, a_cal, a_v, a_act, a_done, a_flt, a_ord, a_hz, a_b26};
  wire [600:0] ob = {b_addr, b_data, b_cal, b_v, b_act, b_done, b_flt, b_ord, b_hz, b_b26};
  integer seed, n, edges = 0, errs = 0, nv = 0, ndone = 0, nflt = 0, nwr = 0, nst = 0, nrst = 0, nchain = 0, k;
  always @(posedge clk) begin
    edges <= edges + 1;
    if (oa !== ob) begin
      errs = errs + 1;
      if (errs <= 5) $display("SFU_LEAF_FWD_MISMATCH edge=%0d addr %h/%h data[31:0] %h/%h v %b/%b flt %b/%b", edges,
                              a_addr, b_addr, a_data[31:0], b_data[31:0], a_v, b_v, a_flt, b_flt);
    end
    if (a_v === 1'b1) nv = nv + 1;
    if (a_done === 1'b1) ndone = ndone + 1;
    if (a_flt === 1'b1) nflt = nflt + 1;
    if (a_data !== 256'd0 && a_data !== {256{1'bx}}) nchain = nchain + 1;
  end
  task automatic drive_idle; begin
    in_we = 0; in_start_v = 0; in_legal = 0; in_loops_one = 0; in_cv = $random(seed); in_addr = $random(seed);
    in_data = {$random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed), $random(seed)};
    in_start_base = $random(seed); in_span = $random(seed); in_loops = $random(seed);
  end endtask
  initial begin
    if (!$value$plusargs("SEED=%d", seed)) seed = 1;
    if (!$value$plusargs("N=%d", n)) n = 60000;
    rst_a = 0; drive_idle;
    repeat (4) @(negedge clk) drive_idle;
    rst_a = 1;
    for (k = 0; k < n; k = k + 1) begin
      @(negedge clk);
      drive_idle;
      case (($random(seed) & 32'h7fffffff) % 100)
        0: begin rst_a = 0; nrst = nrst + 1; end                    // mid-run reset (held >= 1 edge)
        1, 2: rst_a = 1;
        3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30: begin
          in_we = 1; nwr = nwr + 1;
          if ($random(seed) & 1) begin                               // well-formed word for pc = in_addr
            in_data[255:240] = 16'hc7a1; in_data[239:234] = 6'd0; in_data[233:PCLO] = in_addr; in_data[PCLO-1:222] = 0;
          end
        end
        31, 32, 33: begin
          in_start_v = 1; nst = nst + 1; in_legal = ($random(seed) % 8) != 0;
          in_span = 1 + (($random(seed) & 32'h7fffffff) % 40); in_loops = 1 + (($random(seed) & 32'h7fffffff) % 3);
          in_loops_one = (in_loops == 16'd1);
          in_start_base = $random(seed) & 11'h7ff;
        end
        default: ;
      endcase
      if (($random(seed) & 255) == 0) rst_a = 1;
    end
    rst_a = 1; repeat (200) @(negedge clk) drive_idle;
    if (errs == 0 && nv > 0 && nwr > 0 && nst > 0 && nchain > 0)
      $display("SFU_LEAF_FWD_LOCKSTEP PASS edges=%0d writes=%0d starts=%0d resets=%0d out_v=%0d done=%0d fault_edges=%0d chain_edges=%0d",
               edges, nwr, nst, nrst, nv, ndone, nflt, nchain);
    else
      $display("SFU_LEAF_FWD_LOCKSTEP FAIL errs=%0d edges=%0d out_v=%0d writes=%0d starts=%0d chain_edges=%0d", errs, edges, nv, nwr, nst, nchain);
    $finish;
  end
endmodule
`default_nettype wire
