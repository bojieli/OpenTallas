module expr(input [6:0] nseen,input av,bv,take,input [8:0] jne,input [6:0] nsc,output y);
`ifdef NORMALIZE
`ifdef MUT
wire [7:0] sum={1'b0,nseen}+av+bv;
`else
wire [6:0] sum=nseen+av+bv;
`endif
wire [6:0] target=take?7'((jne+9'd6)/9'd7):nsc;
assign y=sum==target;
`else
assign y=nseen+av+bv == (take?7'((jne+9'd6)/9'd7):nsc);
`endif
endmodule
