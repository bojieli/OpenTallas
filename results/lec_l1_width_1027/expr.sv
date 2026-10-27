module expr(input [6:0] nseen,nsc,input av,bv,take,input [8:0] jne,output y);
assign y = nseen + av + bv == (take ? 7'((jne + 9'd6)/9'd7) : nsc);
endmodule
