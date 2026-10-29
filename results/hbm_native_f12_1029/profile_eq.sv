module profile_eq(input wire clk,rst_n,v,input wire [1:0] mut,input wire [31:0] a,b,output wire [3:0] mismatch);
wire [31:0] ag,an,m4g,m4n,m5g,m5n;wire afg,afn,f4g,f4n,f5g,f5n;
ot_hdc_qadd_lat_gold #(.KEEP(1),.LAT(4)) ga(clk,rst_n,v,a,b,ag,afg);
ot_hdc_qadd_lat #(.KEEP(1),.LAT(4)) ca(clk,rst_n,v,a,b,an,afn);
ot_hdc_qmul_lat_gold #(.LAT(4)) gm4(clk,rst_n,v,a,b,m4g,f4g);
ot_hdc_qmul_lat #(.LAT(4)) cm4(clk,rst_n,v,a,b,m4n,f4n);
ot_hdc_qmul_lat_gold #(.LAT(5)) gm5(clk,rst_n,v,a,b,m5g,f5g);
ot_hdc_qmul_lat #(.LAT(5)) cm5(clk,rst_n,v,a,b,m5n,f5n);
reg [31:0] delayed_m4;reg delayed_f4,delayed_v4;
always @(posedge clk or negedge rst_n)if(!rst_n)begin delayed_m4<=0;delayed_f4<=0;delayed_v4<=0;end else begin delayed_m4<=m4g;delayed_f4<=f4g;delayed_v4<=gm4.vo;end
assign mismatch[0]=(ga.vo!=ca.vo)||(afg!=afn)||(ga.vo&& (ag!=(an^{31'b0,mut==1})));
assign mismatch[1]=(gm4.vo!=cm4.vo)||(f4g!=f4n)||(gm4.vo&&(m4g!=m4n));
assign mismatch[2]=(gm5.vo!=cm5.vo)||(f5g!=f5n)||(gm5.vo&&(m5g!=m5n));
assign mismatch[3]=mut==2 ? ((gm4.vo!=cm5.vo)||(f4g!=f5n)||(gm4.vo&&(m4g!=m5n))) : ((delayed_v4!=cm5.vo)||(delayed_f4!=f5n)||(delayed_v4&&(delayed_m4!=m5n)));
endmodule
