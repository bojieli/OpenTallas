module posted_tag(input [31:0] sel, input [0:0] mt, output [10:0] y);
 wire signed [31:0] q2=sel/2,q1=(sel/2)%1,q0=sel%2; wire [2:0] word_tag_lo={q2[0],q1[0],q0[0]}^((mt!=0)?3'd1:3'd0);
 assign y = {3'b010,5'd0,word_tag_lo};
endmodule
