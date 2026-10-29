module profile_eq(input wire clk,rst_n,v,mut,input wire [31:0] a,b,output wire [1:0] mism);
wire [31:0] mo,mn,ao,an; wire [1:0] meo,men,aeo,aen;wire mvo,mvn,avo,avn;
ot_hdc_fp32_mul_lat5i om(clk,rst_n,v,a,b,mo,meo,mvo);
ot_hdc_fp32_mul_f12_l5 nm(clk,rst_n,v,a,b,mn,men,mvn);
ot_hdc_fp32_add_lat4i oa(clk,rst_n,v,a,b,ao,aeo,avo);
ot_hdc_fp32_add_f12_l4 na(clk,rst_n,v,a,b,an,aen,avn);
assign mism[0]=(mvo!=mvn)||(mvo&&({meo,mo}!={men,mn ^ {31'd0,mut}}));
assign mism[1]=(avo!=avn)||(avo&&({aeo,ao}!={aen,an}));
endmodule
