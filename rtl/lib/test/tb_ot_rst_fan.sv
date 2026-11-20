`timescale 1ns/1ps
// RST-FAN-1 unit bench (iverilog -g2012): ot_rst_fan + ot_rst_relay_tree3m.
//  (1) ot_rst_fan LEVELS 1..4, proportional and explicit maps: every leaf releases on the SAME edge, exactly LEVELS
//      rising edges after rst_n_in deasserts; assertion is asynchronous (all leaves low before the next clock edge).
//  (2) ot_rst_relay_tree3m (irregular groups, 3 root copies) == ot_rst_relay_tree3 on every output, every sample.
//  -DOT_RST_FAN_MUT_SKEW (leaf 0 skips its parents) must FAIL.
// Run: iverilog -g2012 -o x rtl/lib/ot_rst_fan.sv rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_rst_relay_tree3m.sv
//      rtl/lib/test/tb_ot_rst_fan.sv && vvp x
module tb_ot_rst_fan;
  reg clk = 0; always #5 clk = ~clk;
  reg rin = 0;
  localparam integer NL = 11;
  wire [NL-1:0] f1, f2, f3, f4, f4x, f3x, f5x;
  ot_rst_fan #(.LEAVES(NL), .LEVELS(1)) u_f1(.clk(clk), .rst_n_in(rin), .rst_n(f1));
  ot_rst_fan #(.LEAVES(NL), .LEVELS(2)) u_f2(.clk(clk), .rst_n_in(rin), .rst_n(f2));
  ot_rst_fan #(.LEAVES(NL), .LEVELS(3), .N1(3)) u_f3(.clk(clk), .rst_n_in(rin), .rst_n(f3));
  ot_rst_fan #(.LEAVES(NL), .LEVELS(4), .N1(2), .N2(4)) u_f4(.clk(clk), .rst_n_in(rin), .rst_n(f4));
  // explicit maps: leaf -> n2 {3,0,1,2,3,0,1,2,2,1,0}, n2 -> n1 {1,0,1,0}
  ot_rst_fan #(.LEAVES(NL), .LEVELS(4), .N1(2), .N2(4), .MAPX(1),
    .PL({8'd0, 8'd1, 8'd2, 8'd2, 8'd1, 8'd0, 8'd3, 8'd2, 8'd1, 8'd0, 8'd3}), .PM({8'd0, 8'd1, 8'd0, 8'd1}))
    u_f4x(.clk(clk), .rst_n_in(rin), .rst_n(f4x));
  ot_rst_fan #(.LEAVES(NL), .LEVELS(3), .N1(3), .MAPX(1),
    .PL({8'd2, 8'd2, 8'd1, 8'd0, 8'd0, 8'd1, 8'd2, 8'd0, 8'd1, 8'd2, 8'd0}))
    u_f3x(.clk(clk), .rst_n_in(rin), .rst_n(f3x));
  // LEVELS 5, explicit maps: leaf -> n3 {0..4}, n3 -> n2 {2,1,0,1,0}, n2 -> n1 {1,0,1}
  ot_rst_fan #(.LEAVES(NL), .LEVELS(5), .N1(2), .N2(3), .N3(5), .MAPX(1),
    .PL({8'd4, 8'd3, 8'd2, 8'd1, 8'd0, 8'd4, 8'd3, 8'd2, 8'd1, 8'd0, 8'd4}), .PM({8'd1, 8'd0, 8'd1}),
    .PQ({8'd0, 8'd1, 8'd0, 8'd1, 8'd2}))
    u_f5x(.clk(clk), .rst_n_in(rin), .rst_n(f5x));
  localparam integer NR = 100;
  wire [NR-1:0] t3, t3m, t3r;
  ot_rst_relay_tree3 #(.REGIONS(NR)) u_t3(.clk(clk), .rst_n_in(rin), .rst_n(t3));
  // groups start at 0,5,6,30,62,70,90 (sizes 5,1,24,32,8,20,10); roots {0,2,1,1,0,2,0}
  ot_rst_relay_tree3m #(.REGIONS(NR), .GROUPS(7), .ROOTS(3),
    .GS({16'd90, 16'd70, 16'd62, 16'd30, 16'd6, 16'd5, 16'd0}), .RM({4'd0, 4'd2, 4'd0, 4'd1, 4'd1, 4'd2, 4'd0}))
    u_t3m(.clk(clk), .rst_n_in(rin), .rst_n_rt(3'b000), .rst_n(t3m));
  // RIN 1: each root copy on its own input (here three same-edge copies of rin)
  wire [2:0] rins = {3{rin}};
  ot_rst_relay_tree3m #(.REGIONS(NR), .GROUPS(7), .ROOTS(3), .RIN(1),
    .GS({16'd90, 16'd70, 16'd62, 16'd30, 16'd6, 16'd5, 16'd0}), .RM({4'd0, 4'd2, 4'd0, 4'd1, 4'd1, 4'd2, 4'd0}))
    u_t3r(.clk(clk), .rst_n_in(1'b0), .rst_n_rt(rins), .rst_n(t3r));

  integer err = 0, cyc = 0, rel = -1, trial;
  integer up1, up2, up3, up4, up4x, up3x, up5x;
  always @(posedge clk) cyc <= cyc + 1;
  task automatic chk_uniform(input [NL-1:0] v, input [8*8-1:0] nm);
    if (v != {NL{1'b0}} && v != {NL{1'b1}}) begin
      if (err < 20) $display("FAIL %0s leaves not uniform %b at cyc %0d", nm, v, cyc); err = err + 1;
    end
  endtask
  // sample between rising edges
  always @(negedge clk) begin
    chk_uniform(f1, "f1"); chk_uniform(f2, "f2"); chk_uniform(f3, "f3"); chk_uniform(f4, "f4");
    chk_uniform(f4x, "f4x"); chk_uniform(f3x, "f3x"); chk_uniform(f5x, "f5x");
    if (t3 !== t3r) begin if (err < 20) $display("FAIL tree3m RIN %h != tree3 %h at cyc %0d", t3r, t3, cyc); err = err + 1; end
    if (t3 !== t3m) begin if (err < 20) $display("FAIL tree3m %h != tree3 %h at cyc %0d", t3m, t3, cyc); err = err + 1; end
    if (rin && rel >= 0) begin
      if (f1[0] && up1 < 0) up1 = cyc - rel; if (f2[0] && up2 < 0) up2 = cyc - rel;
      if (f3[0] && up3 < 0) up3 = cyc - rel; if (f4[0] && up4 < 0) up4 = cyc - rel;
      if (f4x[0] && up4x < 0) up4x = cyc - rel; if (f3x[0] && up3x < 0) up3x = cyc - rel;
      if (f5x[0] && up5x < 0) up5x = cyc - rel;
    end
  end
  initial begin
    for (trial = 0; trial < 40; trial = trial + 1) begin
      @(posedge clk); #($urandom % 9 + 0.5); rin = 0;     // async assert inside a cycle
      #0.2;
      if (f1 !== 0 || f2 !== 0 || f3 !== 0 || f4 !== 0 || f4x !== 0 || f3x !== 0 || f5x !== 0 || t3m !== 0 || t3 !== 0) begin
        $display("FAIL assertion not asynchronous (trial %0d)", trial); err = err + 1; end
      repeat ($urandom % 4 + 6) @(negedge clk);
      #0.1 rin = 1; rel = cyc; up1 = -1; up2 = -1; up3 = -1; up4 = -1; up4x = -1; up3x = -1; up5x = -1;   // synchronous release
      if (trial % 5 == 4) repeat (2) @(negedge clk); else repeat (12) @(negedge clk);       // sometimes re-assert early
      if (trial % 5 != 4 && (up1 != 1 || up2 != 2 || up3 != 3 || up4 != 4 || up4x != 4 || up3x != 3 || up5x != 5)) begin
        $display("FAIL release edges f1 %0d f2 %0d f3 %0d f4 %0d f4x %0d f3x %0d f5x %0d (expect 1 2 3 4 4 3 5)", up1, up2, up3, up4, up4x, up3x, up5x);
        err = err + 1;
      end
    end
    if (err == 0) $display("RST_FAN PASS (40 trials: uniform leaves, depth = LEVELS, async assert, tree3m == tree3)");
    else $display("RST_FAN FAIL errors=%0d", err);
    $finish;
  end
endmodule
