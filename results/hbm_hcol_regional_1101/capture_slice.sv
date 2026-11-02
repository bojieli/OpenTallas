module capture_gold # (parameter MUT=0)(input clk,input[1:0]clk_pair,rn,input[1:0]qv_r,input[1135:0]q_r,input[1087:0]key_r,input qv_b,input[567:0]q_b,input[543:0]key,output[2225:0]captured);localparam QW=568,KW=544;genvar r;generate for(r=0;r<2;r=r+1)begin:g_rgn wire ck=clk_pair[r];wire rn_p=rn[r];reg qv_p;reg[QW-1:0]q_p;reg[KW-1:0]key_p;
always @(posedge ck) begin qv_p <= qv_b && rn_p; q_p <= q_b; key_p <= key; end
assign captured[r*1113+:1113]={qv_p,q_p,key_p};end endgenerate endmodule
module capture_new # (parameter MUT=0)(input clk,input[1:0]clk_pair,rn,input[1:0]qv_r,input[1135:0]q_r,input[1087:0]key_r,input qv_b,input[567:0]q_b,input[543:0]key,output[2225:0]captured);localparam QW=568,KW=544;genvar r;generate for(r=0;r<2;r=r+1)begin:g_rgn wire ck=clk_pair[r];wire rn_p=rn[r];reg qv_p;reg[QW-1:0]q_p;reg[KW-1:0]key_p;
always @(posedge ck) begin qv_p <= qv_r[r] && rn_p; q_p <= q_r[r*QW +: QW]; key_p <= key_r[r*KW +: KW]; end
assign captured[r*1113+:1113]={qv_p,q_p,key_p};end endgenerate endmodule
