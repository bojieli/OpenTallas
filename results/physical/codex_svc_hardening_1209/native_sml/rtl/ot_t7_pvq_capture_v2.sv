// MEM v2 (S81 svc fit 2026-11-03): ot_t7_pvq_capture_candidate with 17 x ot_sram_1r1w_32x128_m1_r0c0 (existing view)
// instead of 34 x ot_sram_1r1w_32x64_m1. Each pair of old 64-bit banks has the same read enable and both addresses;
// the per-bit write mask keeps the pair independent (w_ce = OR of the pair mask; a zero mask bit keeps its bit).
module ot_t7_pvq_capture_v2(input clk,dr_on,input[2:0]p_i,ra,wa,input[2119:0]wd,wm,input[47:0]provenance,output wire[512:0]out);
wire[63:0]q[0:33];
for(genvar n=0;n<16;n=n+1)begin:b
 wire[127:0]d=wd[64+128*n+:128],m=wm[64+128*n+:128];wire[127:0]qq;
 ot_sram_1r1w_32x128_m1_r0c0 s(clk,dr_on&&(p_i==1+n/4),{2'd0,ra},qq,|m,{2'd0,wa},d,m);
 assign q[2*n]=qq[63:0];assign q[2*n+1]=qq[127:64];
end
wire[127:0]q0;
ot_sram_1r1w_32x128_m1_r0c0 s0(clk,dr_on&&(p_i==0),{2'd0,ra},q0,|{wm[2119:2112],wm[63:0]},{2'd0,wa},
 {56'd0,wd[2119:2112],wd[63:0]},{56'd0,wm[2119:2112],wm[63:0]});
assign q[32]=q0[63:0];assign q[33]={56'd0,q0[71:64]};
reg[2:0]kind;reg[47:0]prov_q;
always @(posedge clk)if(dr_on)begin kind<=(p_i==0)?3'd4:p_i-1'b1;if(p_i==0)prov_q<=provenance;end
wire[511:0]dataq[0:3];
for(genvar k=0;k<4;k=k+1)begin:g
 for(genvar j=0;j<8;j=j+1)assign dataq[k][64*j+:64]=q[8*k+j];
end
assign out=(kind==4)?{1'b1,392'd0,prov_q,q[33][7:0],q[32]}:{1'b0,dataq[kind[1:0]]};
endmodule
