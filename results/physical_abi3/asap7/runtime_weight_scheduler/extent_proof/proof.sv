module proof(input [31:0] left, input [10:0] row_left, input [9:0] limit,
             input replay, output valid, output equal);
wire [31:0] old_left=replay && {21'b0,row_left}<left?{21'b0,row_left}:left;
wire [9:0] old_words=old_left<{22'b0,limit}?old_left[9:0]:limit;
wire [9:0] chunk=left<{22'b0,limit}?left[9:0]:limit;
wire [9:0] new_words=replay && row_left<{1'b0,chunk}?row_left[9:0]:chunk;
assign valid=limit<=512;
assign equal=old_words==new_words;
endmodule
