module tkshadow_formal(input clk,input rst_n,input[31:0] native_d,output reg[31:0] tick,shadow);
always @(posedge clk or negedge rst_n)
 if(!rst_n) begin tick<=0;shadow<=32'hffffff67;end
 else begin
  tick<=native_d;
`ifdef MUTANT
  shadow<=native_d-32'd154;
`else
  shadow<=native_d-32'd153;
`endif
 end
`ifdef FORMAL
always @* begin
 if($initstate) assume(!rst_n);
 assert(shadow==tick-32'd153);
end
`endif
endmodule
