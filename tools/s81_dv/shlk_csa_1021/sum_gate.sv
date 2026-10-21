module sum_gate(input clk,input[31:0]a,b,c,d,output reg[31:0]y);
reg[31:0]ar,br,cr,dr;wire[31:0]v;
always@(posedge clk)begin ar<=a;br<=b;cr<=c;dr<=d;y<=v;end
`ifdef BASELINE
assign v=ar+br+cr+dr;
`else
ot_s81_ing_sum4_csa32 u(.a(ar),.b(br),.c(cr),.d(dr),.y(v));
`endif
endmodule
