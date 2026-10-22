`timescale 1ns/1ps
module tb_math;
    function automatic [16:0] sp_add16(input [15:0] a,b,input ci);
        reg [15:0] g[0:4],p[0:4]; reg [16:0] z; integer l,i;
        begin
            g[0]=a&b; p[0]=a^b;
            for(l=0;l<4;l=l+1) for(i=0;i<16;i=i+1)
                if(i>=(1<<l)) begin
                    g[l+1][i]=g[l][i]|(p[l][i]&g[l][i-(1<<l)]);
                    p[l+1][i]=p[l][i]&p[l][i-(1<<l)];
                end else begin g[l+1][i]=g[l][i];p[l+1][i]=p[l][i];end
            z[0]=p[0][0]^ci;
            for(i=1;i<16;i=i+1)z[i]=p[0][i]^(g[4][i-1]|(p[4][i-1]&ci));
            z[16]=g[4][15]|(p[4][15]&ci); sp_add16=z;
        end
    endfunction
    function automatic [159:0] sp_reduce10(input [319:0] x);
        reg [31:0] a[0:9],b[0:6],c[0:4];integer i;
        begin
            for(i=0;i<10;i=i+1)a[i]=x[i*32+:32];
            for(i=0;i<3;i=i+1)begin
                b[2*i]=a[3*i]^a[3*i+1]^a[3*i+2];
                b[2*i+1]=((a[3*i]&a[3*i+1])|(a[3*i]&a[3*i+2])|(a[3*i+1]&a[3*i+2]))<<1;
            end
            b[6]=a[9];
            for(i=0;i<2;i=i+1)begin
                c[2*i]=b[3*i]^b[3*i+1]^b[3*i+2];
                c[2*i+1]=((b[3*i]&b[3*i+1])|(b[3*i]&b[3*i+2])|(b[3*i+1]&b[3*i+2]))<<1;
            end
            c[4]=b[6];sp_reduce10={c[4],c[3],c[2],c[1],c[0]};
        end
    endfunction
    function automatic [63:0] sp_reduce5(input [159:0] x);
        reg [31:0] a[0:4],b[0:3],c[0:2],z0,z1;integer i;
        begin
            for(i=0;i<5;i=i+1)a[i]=x[i*32+:32];
            b[0]=a[0]^a[1]^a[2];b[1]=((a[0]&a[1])|(a[0]&a[2])|(a[1]&a[2]))<<1;b[2]=a[3];b[3]=a[4];
            c[0]=b[0]^b[1]^b[2];c[1]=((b[0]&b[1])|(b[0]&b[2])|(b[1]&b[2]))<<1;c[2]=b[3];
            z0=c[0]^c[1]^c[2];z1=((c[0]&c[1])|(c[0]&c[2])|(c[1]&c[2]))<<1;
            sp_reduce5={z1,z0};
        end
    endfunction
reg[319:0]x;reg[159:0]s1;reg[63:0]s2;reg[16:0]lo,hi;reg[31:0]expected,actual,poisoned,legacy;integer k,j;
initial begin
 for(k=0;k<16384;k=k+1)begin
  expected=0;
  for(j=0;j<10;j=j+1)begin
   x[j*32+:32]=$random;
   if(k==0)x[j*32+:32]=0;
   if(k==1)x[j*32+:32]=32'hffffffff;
   if(k==2)x[j*32+:32]=32'hffff;
   if(k==3)x[j*32+:32]=32'h80000000;
   expected=expected+x[j*32+:32];
  end
  s1=sp_reduce10(x);s2=sp_reduce5(s1);lo=sp_add16(s2[15:0],s2[47:32],0);hi=sp_add16(s2[31:16],s2[63:48],lo[16]);actual={hi[15:0],lo[15:0]};
  if(actual!==expected)$fatal(1,"SPIPE6_ARITH_FAIL vector=%0d actual=%h expected=%h",k,actual,expected);
 end
 for(j=0;j<32;j=j+1)begin
  legacy=32'h12345678;legacy[j]=1'bx;poisoned=32'h12345678^{32{(^legacy)^(^legacy)}};
  if(!$isunknown(poisoned))$fatal(1,"SPIPE6_KNOWNNESS_FAIL bit=%0d",j);
 end
 $display("SPIPE6_ARITH_BOUNDED_PASS vectors=16384 fourstate_positions=32 source_functions=verbatim no_universal_claim=1");$finish;
end
endmodule
