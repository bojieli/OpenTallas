module writer_miter(input[7:0]v,input[119:0]a,input[63:0]mask,input[2047:0]d,output mismatch);
wire[15:0]wg,wn;wire[175:0]ag,an;wire[511:0]dg,dn;wire cg,cn;
writer_gold gold(v,a,mask,d,wg,ag,dg,cg);
writer_regional gate({v,v},{a,a},{mask,mask},{d,d},wn,an,dn,cn);
assign mismatch=|({wg,ag,dg,cg}^{wn,an,dn,cn});
endmodule
