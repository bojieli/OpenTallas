module coll_s(input [15:0] bq, input [10:0] i, output [15:0] y);
 
 assign y = {bq[15:13], bq[12:0] + {2'd0, i} + 13'd1};
endmodule
