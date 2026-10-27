// HBM-MU-QUAD-4 10-27: reduced LEC instances of the sk_en cores (EN_LAND=0, landing register bypassed).
// en1_*: sk_en tied 1  -> must equal the old core flop-for-flop (same next-state + output functions).
// en0_*: sk_en tied 0  -> every flop must hold (no state change).
module en1_step0 (input wire clk, input wire load, input wire [511:0] in_e, input wire pa, pb,
                  output wire [511:0] b_q, output wire bbad_q, abad_q);
  ot_hdc_sk_step0_en #(.EN_LAND(0)) u (.clk(clk), .sk_en_i(1'b1), .load(load), .in_e(in_e), .pa(pa), .pb(pb),
      .b_q(b_q), .bbad_q(bbad_q), .abad_q(abad_q));
endmodule
module en1_steady (input wire clk, rst_n, in_valid, output wire in_ready, load, pa, pb, input wire [511:0] b_q,
                   input wire bbad_q, abad_q, output wire out_valid, output wire [511:0] y, output wire fault, busy);
  ot_hdc_sk_steady_en #(.EN_LAND(0)) u (.clk(clk), .sk_en_i(1'b1), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready),
      .load(load), .pa(pa), .pb(pb), .b_q(b_q), .bbad_q(bbad_q), .abad_q(abad_q), .out_valid(out_valid), .y(y), .fault(fault), .busy(busy));
endmodule
module en0_step0 (input wire clk, input wire load, input wire [511:0] in_e, input wire pa, pb,
                  output wire [511:0] b_q, output wire bbad_q, abad_q);
  ot_hdc_sk_step0_en #(.EN_LAND(0)) u (.clk(clk), .sk_en_i(1'b0), .load(load), .in_e(in_e), .pa(pa), .pb(pb),
      .b_q(b_q), .bbad_q(bbad_q), .abad_q(abad_q));
endmodule
module en0_steady (input wire clk, rst_n, in_valid, output wire in_ready, load, pa, pb, input wire [511:0] b_q,
                   input wire bbad_q, abad_q, output wire out_valid, output wire [511:0] y, output wire fault, busy);
  ot_hdc_sk_steady_en #(.EN_LAND(0)) u (.clk(clk), .sk_en_i(1'b0), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready),
      .load(load), .pa(pa), .pb(pb), .b_q(b_q), .bbad_q(bbad_q), .abad_q(abad_q), .out_valid(out_valid), .y(y), .fault(fault), .busy(busy));
endmodule
// gold wrappers: the OLD cores under the same instance name, so flattened names match flop-for-flop
module gold_step0 (input wire clk, input wire load, input wire [511:0] in_e, input wire pa, pb,
                   output wire [511:0] b_q, output wire bbad_q, abad_q);
  ot_hdc_sk_step0 u (.clk(clk), .load(load), .in_e(in_e), .pa(pa), .pb(pb), .b_q(b_q), .bbad_q(bbad_q), .abad_q(abad_q));
endmodule
module gold_steady (input wire clk, rst_n, in_valid, output wire in_ready, load, pa, pb, input wire [511:0] b_q,
                    input wire bbad_q, abad_q, output wire out_valid, output wire [511:0] y, output wire fault, busy);
  ot_hdc_sk_steady u (.clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_ready(in_ready), .load(load), .pa(pa), .pb(pb),
      .b_q(b_q), .bbad_q(bbad_q), .abad_q(abad_q), .out_valid(out_valid), .y(y), .fault(fault), .busy(busy));
endmodule
