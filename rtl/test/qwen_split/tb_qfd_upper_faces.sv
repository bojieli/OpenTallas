module tb;
 reg clk=0;always #5 clk=~clk;
 reg reset_q=0;reg[5:0]lnk=0;reg[15:0]lpv=0,lf=0;
 wire[3:0]p,f;
`ifndef MUT
`define MUT 0
`endif
 ot_qfd_band_upper_faces #(.MUT(`MUT)) d(clk,reset_q,lnk,lpv,lf,p,f);
 integer n,u,checks=0;reg[3:0]ep,ef;
 initial begin
 for(n=0;n<2048;n=n+1)begin
  @(negedge clk);reset_q=(n%37!=0);lnk=$random;lpv=$random;lf=$random;
  if(n%4==0)begin lpv=16'hffff;lf=16'h8000;lnk=0;end
  for(u=0;u<4;u=u+1)begin ep[u]=reset_q&lpv[4*u];ef[u]=reset_q&&((&lnk)||(|lf[4*u+:4])||(|(lpv^{16{lpv[0]}})));end
  @(posedge clk);#1;
  if(p!==ep||f!==ef)$fatal(1,"quarter boundary mismatch n=%0d p=%h/%h f=%h/%h",n,p,ep,f,ef);
  if((|f)!==(reset_q&&((&lnk)||(|lf)||(|(lpv^{16{lpv[0]}})))))$fatal(1,"legacy fault union differs");
  checks=checks+1;
 end
 $display("UPPER_FACES PASS checks=%0d",checks);$finish;
 end
endmodule
