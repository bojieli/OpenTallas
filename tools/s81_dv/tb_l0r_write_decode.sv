`timescale 1ns/1ps
module tb_l0r_write;
reg clk=0;always #0.5 clk=~clk;
reg rst=0,av=0,bv=0,bank=0,go=0,gb=0;reg[4:0]a=0,b=0,acc=0;reg[191:0]ad=0,bd=0;
wire[1:0]v,f;wire[1:0][3:0]ri;wire[1:0][4:0]ra;wire[1:0][319:0]rd;
legacy_l0r l(.clk(clk),.rst_n(rst),.wr_av(av),.wr_bv(bv),.wr_b(bank),.wr_agh(a),.wr_bgh(b),.wr_ad(ad),.wr_bd(bd),.go_a(go),.go_acc(acc),.go_b(gb),.r_v(v[0]),.r_f(f[0]),.r_i(ri[0]),.r_acc(ra[0]),.r_d(rd[0]));
dsdv_gunit_l0r #(.WRITE_DECODE(1)) n(.clk(clk),.rst_n(rst),.wr_av(av),.wr_bv(bv),.wr_b(bank),.wr_agh(a),.wr_bgh(b),.wr_ad(ad),.wr_bd(bd),.go_a(go),.go_acc(acc),.go_b(gb),.r_v(v[1]),.r_f(f[1]),.r_i(ri[1]),.r_acc(ra[1]),.r_d(rd[1]));
integer t,j,err=0,beats=0,collisions=0,writes=0;
initial begin
 for(t=0;t<1100;t=t+1) begin
  @(negedge clk);rst=(t>=8 && !(t>=700&&t<704));
  a=5'(t);b=t%3==0?a:5'(t*13+7);bank=t[5];
  av=(t>=16 && t%7!=0);bv=(t>=16 && t%5!=0);
  ad={6{32'(t*137+19)}};bd={6{32'(t*31+9001)}};
  go=(t>=100 &&t%41==0);acc=5'(t/41);gb=t[6];
  if(rst&&av&&bv&&a==b)collisions++;
  if(rst&&(av||bv))writes++;
  #0.1;
  if(t>16)begin
   for(j=0;j<384;j++)if(l.rs[j]!==n.rs[j])begin err++;if(err<5)$display("STORE_DIFF edge%0d word%0d",t,j);end
   if(v[0]!==v[1]||f[0]!==f[1])begin err++;if(err<5)$display("CONTROL_DIFF %0d",t);end
   if(v[0])begin beats++;if({ri[0],ra[0],rd[0]}!=={ri[1],ra[1],rd[1]})begin err++;if(err<5)$display("OUTPUT_DIFF %0d",t);end end
  end
 end
 if(beats<100||collisions<100||writes<900)begin err++;$display("VACUOUS beats%0d collisions%0d writes%0d",beats,collisions,writes);end
 if(err)begin $display("L0R_WRITE FAIL %0d",err);$fatal(1,"miter");end
 $display("L0R_WRITE PASS beats%0d collisions%0d writes%0d",beats,collisions,writes);$finish;
end
endmodule
