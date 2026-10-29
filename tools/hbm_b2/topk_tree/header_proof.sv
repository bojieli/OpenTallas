// No assumptions: low sequence bits are the lane for all ranks, groups and
// wraparound, so extracting them as wires cannot change a defined emission.
module header_proof #(parameter MUT=0)(input[7:0]rank,gbase,
 input[3:0]group,input[1:0]lane,output bad);
 wire[15:0]seq_word=16'((int'(rank)-int'(gbase))*64+int'(group)*4+int'(lane));
 assign bad=(seq_word[1:0]!=(lane^(MUT?2'd1:2'd0)));
endmodule
