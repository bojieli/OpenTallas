module clone_miter(input clk, input selector_d, input [31:0] bank0, bank1, output bad);
  reg original;
  (* keep = 1 *) reg [3:0] copies;
  always @(posedge clk) begin
    original <= selector_d;
    copies <= {4{selector_d}};
`ifdef MUTANT
    copies[0] <= ~selector_d;
`endif
  end
  wire [31:0] baseline = original ? bank1 : bank0;
  wire [31:0] revised;
  genvar k;
  generate for(k=0;k<4;k=k+1) begin:g
    assign revised[8*k+:8] = copies[k] ? bank1[8*k+:8] : bank0[8*k+:8];
  end endgenerate
  assign bad = baseline != revised;
endmodule
