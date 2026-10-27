module finish_wp(input [5:0] slot, input en, input [31:0] data, output [38:0] y);
 assign y = {en,en?5'(slot>>1):5'd0,en?slot[0]:1'b0,data};
endmodule
