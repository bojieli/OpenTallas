module tb;
reg ck=0;always #5 ck=~ck;
reg rst_n=0;reg [137:0] zi=0;reg [14:0] tc=0;reg fi=0;
wire[137:0] a,b,m,ha,hb,hm;wire af,bf,mf,haf,hbf,hmf;
qkd_astk_zn u0(ck,rst_n,4'd0,tc,zi,a,fi,af);
qkd_astk_zn_r4 u1(ck,rst_n,4'd0,tc,zi,b,fi,bf);
qkd_astk_zn_r4 #(.READ_MUT(1)) um(ck,rst_n,4'd0,tc,zi,m,fi,mf);
qkd_astk_zn_head_p h0(ck,rst_n,tc,zi,ha,haf);
qkd_astk_zn_head_p_r4 h1(ck,rst_n,tc,zi,hb,hbf);
qkd_astk_zn_head_p_r4 #(.READ_MUT(1)) hmut(ck,rst_n,tc,zi,hm,hmf);
integer n,k,checks=0,mut=0,valids=0;
initial begin
 for(n=0;n<5060;n=n+1)begin
 @(negedge ck);rst_n=n>=4;tc={14'd16383,(n==8)};zi=0;
 if(n>=64)begin
 k=(n-64)%32;zi[0]=1;zi[5:2]=k%16;zi[9:6]=k>=16?1:0;zi[1]=(n/32)%2;
 zi[41:10]=32'h3f000000+((n/32)%128)*4096+(k%16)*32768;
 zi[73:42]=32'h40000000+((n/32)%128)*4096+(k%16)*32768;
 zi[105:74]=32'h40800000+((n/32)%128)*4096+(k%16)*32768;
 zi[137:106]=32'h41000000+((n/32)%128)*4096+(k%16)*32768;
 end
 @(posedge ck);#1;
 if(n>=64)begin
 checks=checks+2;
 if(a!==b||af!==bf||ha!==hb||haf!==hbf)$fatal(1,"MISMATCH cycle%0d",n);
 if(a[0])begin valids=valids+1;if(a!==m)mut=mut+1;end
 if(ha[0]&&ha!==hm)mut=mut+1;
 end
 end
 if(mut<100||valids<100)$fatal(1,"weak mutant mut=%0d valids=%0d",mut,valids);
 $display("PASS ASTK_R4 checks=%0d valid=%0d mutant_mismatches=%0d added_cycles=0",checks,valids,mut);$finish;
end
endmodule
