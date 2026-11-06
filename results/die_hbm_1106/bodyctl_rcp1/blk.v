// old vs new RCP1 blocks, extracted from ot_hfd_coll_q3_body_ctl.sv (_229667_ and _229719_)
module old_blk(input clk_issue, input rcp7, input adv_x, input take_x, output [18:0] adv_c, output [30:0] tk_c);
  reg [18:0] _229667_;
  always @(posedge clk_issue, negedge rcp7)
    if (!rcp7) _229667_ <= 19'h00000;
    else _229667_ <= {19{adv_x}};
  assign adv_c = _229667_;
  reg [30:0] _229719_;
  always @(posedge clk_issue) _229719_ <= {31{take_x}};
  assign tk_c = _229719_;
endmodule
module new_blk(input clk_issue, input rcp7, input adv_x, input take_x, output [18:0] adv_c, output [30:0] tk_c);
  reg [0:0] _229667_;
  always @(posedge clk_issue, negedge rcp7)
    if (!rcp7) _229667_ <= 1'b0;
    else _229667_ <= `M1;
  assign adv_c = `M2;
  reg [0:0] _229719_;
  always @(posedge clk_issue) _229719_ <= `M3;
  assign tk_c = `M4;
endmodule
module miter(input clk_issue, input rcp7, input adv_x, input take_x, output ok);
  wire [18:0] a0, a1; wire [30:0] t0, t1;
  old_blk o(clk_issue, rcp7, adv_x, take_x, a0, t0);
  new_blk n(clk_issue, rcp7, adv_x, take_x, a1, t1);
  assign ok = (a0 == a1) && (t0 == t1);
endmodule
