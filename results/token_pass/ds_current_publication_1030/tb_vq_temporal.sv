`timescale 1ps/1fs
module tb_vq_temporal;
reg ck=0,rs=0;always #416.5 ck=~ck;
reg yv=0,mv=0;reg[2:0]yi=0,k=0;reg[127:0]y=0;reg[7:0]idx=0;
wire[2:0]kp=k==0?3'd2:k==1?3'd0:k==2?3'd1:k;
wire[1:0]v,s,f;wire[275:0]d[0:1];
for(genvar g=0;g<2;g=g+1)begin:G
 ot_s81sl_vq #(.AQ_XMEM(2))q(.clk(ck),.rst_n(rs),.y_v(yv),.y_i(yi),.y(y),.u_v(1'b0),.u_i(3'd0),.u(256'd0),.sid(4'd9),.k(g==0?k:kp),.m_v(mv),.m_q(1'b1),.m_b(1'b1),.m_i(idx),.um_v(1'b0),.um_q(1'b0),.um_b(1'b0),.um_i(8'd0),.xf_v(v[g]),.xf_s(s[g]),.xf(d[g]),.fault(f[g]));
end
integer cycle=0,vec=0,j,l,g,checks=0,errors=0,bad_payload=0,bad_age=0,n[0:1],dates[0:1][0:7];reg[276:0]words[0:1][0:7];integer delta,expected;
always @(posedge ck)begin #1;cycle=cycle+1;if(rs)for(integer a=0;a<2;a=a+1)if(v[a])begin if(n[a]<8)begin words[a][n[a]]={s[a],d[a]};dates[a][n[a]]=cycle;end n[a]=n[a]+1;end end
initial begin
bad_payload=$test$plusargs("bad_payload");bad_age=$test$plusargs("bad_age");n[0]=0;n[1]=0;
repeat(64)@(negedge ck);rs=1;repeat(16)@(negedge ck);
for(vec=0;vec<40;vec=vec+1)begin
 @(negedge ck);k=3'(vec%5);idx=8'(128+vec);n[0]=0;n[1]=0;mv=1;
 @(negedge ck);mv=0;
 repeat(3)@(negedge ck);
 for(j=0;j<8;j=j+1)begin yv=1;yi=3'(j);for(l=0;l<8;l=l+1)y[16*l+:16]=16'(16'h3e80+vec*2+j*8+l);@(negedge ck);end
 yv=0;repeat(100)@(negedge ck);
 delta=4*(int'(kp)-int'(k));if(n[0]!=8||n[1]!=8||f)begin errors=errors+1;$display("BAD_COUNTS vec=%0d n=%0d/%0d fault=%b",vec,n[0],n[1],f);end
 for(j=0;j<8;j=j+1)begin checks=checks+1;expected=dates[0][j]+delta+(bad_age?1:0);if((words[0][j]^(bad_payload?277'd1:277'd0))!==words[1][j]||dates[1][j]!=expected)begin errors=errors+1;if(errors<5)$display("BAD_FRAGMENT vec=%0d frag=%0d age_delta=%0d want=%0d",vec,j,dates[1][j]-dates[0][j],delta);end end
end
$display("VQ_TEMPORAL %s vectors=%0d fragments=%0d errors=%0d source_fault=%b clock_ps=833 mapping20134",errors==0?"PASS":"FAIL",vec,checks,errors,f);
if(errors)$fatal(1,"temporal payload/date control");$finish;end
endmodule
