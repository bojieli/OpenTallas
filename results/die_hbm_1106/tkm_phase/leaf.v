module baseline(input[7:0]rank,gb,pf,f8,gbpf,output[7:0]o);
wire[7:0]rk=rank-gb;wire[7:0]pr=rk*pf;assign o=f8-pr;
endmodule
module candidate(input[7:0]rank,gb,pf,f8,gbpf,output[7:0]o);
wire[7:0]pr=rank*pf;assign o=f8+gbpf-pr;
endmodule
module candidate_csa(input[7:0]rank,gb,pf,f8,gbpf,output[7:0]o);
wire[7:0]pr=rank*pf;wire[7:0]d=~pr;
wire[7:0]s=f8^gbpf^d;
wire[7:0]c=((f8&gbpf)|(f8&d)|(gbpf&d))<<1;
wire[7:0]p=s^c;wire[7:0]g=s&c;
wire[7:0]p1,g1,p2,g2,p4,g4;
genvar i;generate for(i=0;i<8;i=i+1)begin
 if(i>=1)begin assign p1[i]=p[i]&p[i-1];assign g1[i]=g[i]|(p[i]&g[i-1]);end else begin assign p1[i]=p[i];assign g1[i]=g[i];end
 if(i>=2)begin assign p2[i]=p1[i]&p1[i-2];assign g2[i]=g1[i]|(p1[i]&g1[i-2]);end else begin assign p2[i]=p1[i];assign g2[i]=g1[i];end
 if(i>=4)begin assign p4[i]=p2[i]&p2[i-4];assign g4[i]=g2[i]|(p2[i]&g2[i-4]);end else begin assign p4[i]=p2[i];assign g4[i]=g2[i];end
 if(i==0)assign o[i]=p[i]^1'b1;else assign o[i]=p[i]^(g4[i-1]|p4[i-1]);
end endgenerate
endmodule
