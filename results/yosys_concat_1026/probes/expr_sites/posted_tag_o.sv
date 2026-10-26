module posted_tag(input [31:0] sel, input [0:0] mt, output [10:0] y);
 assign y = {3'b010,5'd0,({1'(sel/2),1'((sel/2)%1),1'(sel%2)}^3'(mt!=0?1:0))};
endmodule
