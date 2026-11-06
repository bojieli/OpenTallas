module baseline(input [7:0] a,b,output [15:0] y);assign y={ a[7] , a[6] , a[5] , a[4] , a[3] , a[2] , a[1] , a[0]  } * { b[7] , b[6] , b[5] , b[4] , b[3] , b[2] , b[1] , b[0]  };endmodule
module candidate(input [7:0] a,b,output [15:0] y);
function automatic [15:0] ot_q3ctl_mul8_csa(input [7:0] a,b);
 reg [15:0] r[0:7];reg [15:0] s0,c0,s1,c1,s2,c2,s3,c3,s4,c4,s5,c5;
 reg [15:0] p,g,cc;reg [3:0] pg,gg;reg [4:0] gc;integer i,j;
 begin
  for(i=0;i<8;i=i+1) r[i]=({8'd0,a}&{16{b[i]}})<<i;
  s0=r[0]^r[1]^r[2];c0=((r[0]&r[1])|(r[0]&r[2])|(r[1]&r[2]))<<1;
  s1=r[3]^r[4]^r[5];c1=((r[3]&r[4])|(r[3]&r[5])|(r[4]&r[5]))<<1;
  s2=s0^c0^s1;c2=((s0&c0)|(s0&s1)|(c0&s1))<<1;
  s3=c1^r[6]^r[7];c3=((c1&r[6])|(c1&r[7])|(r[6]&r[7]))<<1;
  s4=s2^c2^s3;c4=((s2&c2)|(s2&s3)|(c2&s3))<<1;
  s5=s4^c4^c3;c5=((s4&c4)|(s4&c3)|(c4&c3))<<1;
  p=s5^c5;g=s5&c5;
  for(j=0;j<4;j=j+1)begin
   pg[j]=&p[4*j+:4];
   gg[j]=g[4*j+3]|(p[4*j+3]&g[4*j+2])|(p[4*j+3]&p[4*j+2]&g[4*j+1])|(p[4*j+3]&p[4*j+2]&p[4*j+1]&g[4*j]);
  end
  gc[0]=0;gc[1]=gg[0];gc[2]=gg[1]|(pg[1]&gg[0]);
  gc[3]=gg[2]|(pg[2]&gg[1])|(pg[2]&pg[1]&gg[0]);
  gc[4]=gg[3]|(pg[3]&gg[2])|(pg[3]&pg[2]&gg[1])|(pg[3]&pg[2]&pg[1]&gg[0]);
  for(j=0;j<4;j=j+1)begin
   cc[4*j]=gc[j];cc[4*j+1]=g[4*j]|(p[4*j]&gc[j]);
   cc[4*j+2]=g[4*j+1]|(p[4*j+1]&g[4*j])|(p[4*j+1]&p[4*j]&gc[j]);
   cc[4*j+3]=g[4*j+2]|(p[4*j+2]&g[4*j+1])|(p[4*j+2]&p[4*j+1]&g[4*j])|(p[4*j+2]&p[4*j+1]&p[4*j]&gc[j]);
  end
  ot_q3ctl_mul8_csa=p^cc;
 end
endfunction
assign y=ot_q3ctl_mul8_csa(a,b);endmodule
