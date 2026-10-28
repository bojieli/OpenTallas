module product_base #(parameter B_BF16=1)(input clk,rst_n,valid,input[15:0] a_h,input[31:0] b_word,output[31:0] y);
reg[31:0] rh,rk,hp,kp,ha,ha2,hb,hb2;
always @(posedge clk)begin
 rh<={a_h,16'b0};rk<=B_BF16?{b_word[31:16],16'b0}:b_word;
 hp<=rh;kp<=rk;ha<=hp;ha2<=hp;hb<=kp;hb2<=kp;
end
wire[31:0] y2;wire[1:0] err;wire vo;
ot_s81sl_ve_fmul u(clk,rst_n,valid,ha,ha2,hb,hb2,y,y2,err,vo);
endmodule
