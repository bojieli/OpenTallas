module split_count_miter #(parameter integer MUT=0)(input wire[54:0]roots,input wire last_chunk,output wire eq);
wire[54:0]v=roots&{~{6{last_chunk}},49'h1ffffffffffff};
wire[4:0]a,b;wire[27:0]ra=v[27:0] ^ (MUT ? (28'd1<<17) & {28{v[17]}} : 28'd0);
ot_s81_kp4_count28 u_a(.bits({4'd0,ra}),.count(a));
ot_s81_kp4_count28 u_b(.bits({5'd0,v[54:28]}),.count(b));
reg[6:0]pt[0:126];integer i;
always@*begin
for(i=0;i<64;i=i+1)pt[63+i]=(i<55)?{6'd0,(roots[i]&&!(i>=49&&last_chunk))}:7'd0;
for(i=62;i>=0;i=i-1)pt[i]=pt[2*i+1]+pt[2*i+2];end
assign eq=({1'b0,a}+{1'b0,b})==pt[0][5:0];endmodule

module split_acc_miter(input[5:0]acc,input[4:0]pa,pb,output eq);
wire[5:0]a={1'b0,pa},b={1'b0,pb};
wire[5:0]s=acc^a^b,c0=(acc&a)|(acc&b)|(a&b);
wire[5:0]c={c0[4:0],1'b0};
wire[5:0]want=acc+a+b,got=s+c;
assign eq=want==got;endmodule
