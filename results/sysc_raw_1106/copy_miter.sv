module m(input clk,input d,output bad);
reg original59;reg[5:0]old;reg[6:0]fresh;
always @(posedge clk)begin original59<=d;old<={old[4:0],original59};
`ifdef MUTANT
 fresh<={fresh[5:0],original59};
`else
 fresh<={fresh[5:0],d};
`endif
end
assign bad=old[5]!=fresh[6];
endmodule
