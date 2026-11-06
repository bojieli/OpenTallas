module miter(input ck,input [15:0] sel,input [95:0] xin);
reg [15:0] seen=0;
always @(posedge ck) seen <= seen | sel;
genvar k,c;
generate for(k=0;k<8;k=k+1)begin:g_lane
wire [95:0] a,b;
xlane_old #(.K(k)) u_a(ck,sel,xin,a);
xlane_new #(.K(k)) u_b(ck,sel,xin,b);
for(c=0;c<16;c=c+1)begin:g_chunk
always @* if(seen[c]) assert(a[6*c+:6]==b[6*c+:6]);
end
end endgenerate
wire [17:0] nin=xin[17:0];
wire [17:0] nvec=(nin+7)>>3;
always @* assert(nvec[17:16]==0);
endmodule
