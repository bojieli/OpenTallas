module reset_depth(input clk,rst_n,output eq);
  (* keep *) reg [0:0] rst_n__ot_rl0;
  always @(posedge clk) rst_n__ot_rl0 <= rst_n;
  (* keep *) reg [0:0] rst_n__ot_rl1;
  always @(posedge clk) rst_n__ot_rl1 <= rst_n__ot_rl0;
  (* keep *) reg [14:0] rst_n__ot_rlc;
  always @(posedge clk) rst_n__ot_rlc <= {15{rst_n}};
  wire [15:0] rst_n__ot_rlv = {rst_n__ot_rlc, rst_n__ot_rl1};
  (* keep *) reg [0:0] orig__ot_rl0;
  always @(posedge clk) orig__ot_rl0 <= rst_n;
  (* keep *) reg [0:0] orig__ot_rl1;
  always @(posedge clk) orig__ot_rl1 <= orig__ot_rl0;

assign eq=(rst_n__ot_rlv == {16{orig__ot_rl1}});
endmodule
