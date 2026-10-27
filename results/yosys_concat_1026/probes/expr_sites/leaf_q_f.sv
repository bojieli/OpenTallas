module leaf_q(input [19:0] incoming, input i_we, input [7:0] i_tag, input [7:0] i_wstrb, input [31:0] b, output [29:0] y);
 
 assign y = {i_we,incoming[14:12]^incoming[19:17],((incoming[1:0]+b[1:0])^incoming[16:15]),incoming[11:7],i_tag,4'(b),i_wstrb};
endmodule
