// DISABLED standalone data-cut candidate; all original queue/control stays outside.
module ot_t7_pvq_capture_candidate(input clk,dr_on,input[2:0]p_i,ra,wa,input[2119:0]wd,wm,input[47:0]provenance,output wire[512:0]out);
wire[63:0]q[0:33];
for(genvar n=0;n<34;n=n+1)begin:b
 wire[63:0]d,m;wire ce;
 if(n<32)begin
  assign d=wd[64+64*n+:64];assign m=wm[64+64*n+:64];
  assign ce=dr_on&&(p_i==1+n/8);
 end else if(n==32)begin
  assign d=wd[63:0];assign m=wm[63:0];assign ce=dr_on&&(p_i==0);
 end else begin
  assign d={56'd0,wd[2119:2112]};assign m={56'd0,wm[2119:2112]};assign ce=dr_on&&(p_i==0);
 end
 ot_sram_1r1w_32x64_m1 s(clk,ce,{2'd0,ra},q[n],|m,{2'd0,wa},d,m);
end
reg[2:0]kind;reg[47:0]prov_q;
always @(posedge clk)if(dr_on)begin kind<=(p_i==0)?3'd4:p_i-1'b1;if(p_i==0)prov_q<=provenance;end
wire[511:0]dataq[0:3];
for(genvar k=0;k<4;k=k+1)begin:g
 for(genvar j=0;j<8;j=j+1)assign dataq[k][64*j+:64]=q[8*k+j];
end
assign out=(kind==4)?{1'b1,392'd0,prov_q,q[33][7:0],q[32]}:{1'b0,dataq[kind[1:0]]};
endmodule
