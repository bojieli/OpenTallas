module split_count_miter #(parameter integer MUT=0, parameter integer SPLIT=1)(input wire[54:0]roots,input wire last_chunk,output wire eq);
wire[54:0]v=roots&{~{6{last_chunk}},49'h1ffffffffffff};
wire[4:0]a,b;wire[27:0]ra=v[27:0] ^ (MUT ? (28'd1<<17) & {28{v[17]}} : 28'd0);
generate if(SPLIT==1)begin:g_halves
ot_s81_kp4_count28 u_a(.bits({4'd0,ra}),.count(a));
ot_s81_kp4_count28 u_b(.bits({5'd0,v[54:28]}),.count(b));
end else begin:g_quarters
wire[3:0]n0,n1,n2,n3;wire[54:0]rv=v ^ (MUT ? (55'd1<<17) & {55{v[17]}} : 55'd0);
ot_s81_kp4_count14 u0(.bits({2'd0,rv[13:0]}),.count(n0));
ot_s81_kp4_count14 u1(.bits({2'd0,rv[27:14]}),.count(n1));
ot_s81_kp4_count14 u2(.bits({2'd0,rv[41:28]}),.count(n2));
ot_s81_kp4_count14 u3(.bits({3'd0,rv[54:42]}),.count(n3));
assign a={1'b0,n0}+{1'b0,n1};assign b={1'b0,n2}+{1'b0,n3};
end endgenerate
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

module split_acc4_miter(input[5:0]a,input[3:0]p0,p1,p2,p3,output eq);
wire[5:0]b={2'd0,p0},c={2'd0,p1},d={2'd0,p2},e={2'd0,p3};
wire[5:0]s1=a^b^c,c1=((a&b)|(a&c)|(b&c))<<1;
wire[5:0]s2=s1^d^e,c2=((s1&d)|(s1&e)|(d&e))<<1;
wire[5:0]s3=s2^c1^c2,c3=((s2&c1)|(s2&c2)|(c1&c2))<<1;
wire[5:0]want=a+b+c+d+e,got=s3+c3;assign eq=want==got;
endmodule
