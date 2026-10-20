// L2H-IDXSEL s3: lp.py tb_stimulus for the landed-selector lockstep bench (tb_ot_hidx_s3_flat_lp): a real selector
// programme instead of random words, so the reset-epoch mutants act on state that outlives the reset.
//  * op2 ingests of lines 0..170 run from cycle 4, ACROSS the reset release (cycle 16): the first word a landing ring
//    accepts writes an SRAM line (the quadrant's SRAM write enables are not reset-gated) -- MUT 5 (ring released one edge
//    late) loses one more line than the reference;
//  * op1 (k load) comes after the ingest, then the pass-0/1/2 choose runs and the op6 compaction scan: MUT 4 (ctl reset
//    run held mut4_stages longer) misses op1 and the first choose steps.
// Lines: valid lanes, id = q*2736 + a*16 + l, BF16 scores from a fixed hash; presented 5 edges after their op2 slot
// (registered_s3: sel_in 7 - sel_in_line 2).  Spacing as the compiler (drain 4, sel_choose_rt 8).
function automatic [591:0] s3_line(input integer q, input integer a);
  reg [591:0] v; integer l, id; reg [31:0] h;
  begin
    v = 0;
    for (l = 0; l < 16; l = l + 1) begin
      id = q * 2736 + a * 16 + l;
      h = (id * 32'h9E3779B1) ^ (id >> 3) ^ 32'h5bd1e995;
      h = h ^ (h >> 15); h = h * 32'h2c1b3c6d; h = h ^ (h >> 12);
      v[l*37 +: 37] = {20'(id), 1'b0, h[6:0], 8'(h[15:8]), 1'b1};   // [36:17] id, [16:1] bf16 (positive, finite), [0] valid
    end
    s3_line = v;
  end
endfunction
integer s3_c = 0;
integer s3_a [0:7];
task automatic s3_tick(input integer o, input integer ad, input integer p, input integer la);
  integer j;
  begin
    @(negedge clk);
    fi_op = 4'(o); fi_addr = 8'(ad); fi_pass = 2'(p);
    for (j = 7; j > 0; j = j - 1) s3_a[j] = s3_a[j - 1];
    s3_a[0] = la;
    if (s3_a[5] >= 0) begin
      fi_in_line_0 = s3_line(0, s3_a[5]); fi_in_line_1 = s3_line(1, s3_a[5]);
      fi_in_line_2 = s3_line(2, s3_a[5]); fi_in_line_3 = s3_line(3, s3_a[5]);
    end
    s3_c = s3_c + 1;
    if (s3_c == 16) rst = 1'b1;
  end
endtask
initial begin : s3_prog
  integer a, b, p, j;
  for (j = 0; j < 8; j = j + 1) s3_a[j] = -1;
  fi_op = 0; fi_pass = 0; fi_addr = 0; fi_k = 10'd512;
  fi_in_line_0 = 0; fi_in_line_1 = 0; fi_in_line_2 = 0; fi_in_line_3 = 0;
  rst = 1'b0;
  repeat (4) s3_tick(0, 0, 0, -1);
  for (a = 0; a < 171; a = a + 1) s3_tick(2, a, 0, a);
  repeat (4) s3_tick(0, 0, 0, -1);
  s3_tick(1, 0, 0, -1);
  repeat (4) s3_tick(0, 0, 0, -1);
  for (b = 31; b >= 0; b = b - 1) s3_tick(5, b, 0, -1);
  repeat (9) s3_tick(0, 0, 0, -1);
  for (p = 1; p < 3; p = p + 1) begin
    s3_tick(3, 0, p, -1);
    for (a = 0; a < 171; a = a + 1) s3_tick(4, a, p, -1);
    repeat (4) s3_tick(0, 0, p, -1);
    for (b = (p == 2 ? 63 : 31); b >= 0; b = b - 1) s3_tick(5, b, p, -1);
    repeat (9) s3_tick(0, 0, p, -1);
  end
  for (a = 0; a < 171; a = a + 1) s3_tick(6, a, 2, -1);
  repeat (40) s3_tick(0, 0, 2, -1);
  lp_finish("idx s3 programme");
end
