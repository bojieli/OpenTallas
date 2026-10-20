module ve5_native_top(input wire clk,rst_n,valid_in,input wire[31:0] a,b,output wire[31:0] ya,ya2,ym,ym2,output wire[1:0]ea,em,output wire va,vm);
(*keep*) reg[31:0] aa,aa2,bb,bb2;reg vr;
always @(posedge clk) begin aa<=a;aa2<=a;bb<=b;bb2<=b;vr<=valid_in;end
ot_s81sl_ve_fadd u_add(.clk(clk),.rst_n(rst_n),.valid_in(vr),.a(aa),.a2(aa2),.b(bb),.b2(bb2),.y(ya),.y2(ya2),.err(ea),.valid_out(va));
ot_s81sl_ve_fmul u_mul(.clk(clk),.rst_n(rst_n),.valid_in(vr),.a(aa),.a2(aa2),.b(bb),.b2(bb2),.y(ym),.y2(ym2),.err(em),.valid_out(vm));
endmodule
