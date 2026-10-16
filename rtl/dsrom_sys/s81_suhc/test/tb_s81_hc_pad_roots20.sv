`timescale 1ns/1ps
module tb_s81_hc_pad_roots20;
 reg ck=0;always #5 ck=~ck;
 reg rst=0;reg [3:0] runck=15;
 wire[3:0] pck={4{ck}}&runck;
 reg[2155:0]di;reg[1127:0]fd;reg[6:0]fv;
 wire[2155:0]a,b;wire[1127:0]af,bf;wire[6:0]av,bv;
 ot_s81_hc_cpad_split #(.RF(5),.RW(2),.HALF(1),.RLY(2),.DW(6),.RET_EXTRA(1),.FWD_TRIM(3)) refpad(
 .sk(ck),.srs(rst),.crd_i(di),.crd_o(a),.fd_i(fd),.fd_o(af),.fv_i(fv),.fv_o(av));
 ot_s81_hc_cpad_roots20 #(.RF(5),.RW(2),.HALF(1),.RLY(2),.DW(6),.RET_EXTRA(1),.FWD_TRIM(3)) dut(
 .sk(ck),.sk_pad(pck),.srs(rst),.crd_i(di),.crd_o(b),.fd_i(fd),.fd_o(bf),.fv_i(fv),.fv_o(bv));
 integer checks=0,errors=0,mut=0;
 initial begin
  if($value$plusargs("MUT=%d",mut))begin end
  for(integer cyc=0;cyc<500;cyc=cyc+1)begin
   @(negedge ck);rst=(cyc>=5&&!(cyc>=200&&cyc<209));
   for(integer i=0;i<2156;i=i+1)di[i]=$random;
   for(integer i=0;i<1128;i=i+1)fd[i]=$random;
   fv=$random;
   if(mut>0&&cyc>300)runck[mut-1]=0;
   @(posedge ck);#1;
   if(cyc>35&&!(cyc>=200&&cyc<245))begin
    checks=checks+1;
    if({a,af,av}!=={b,bf,bv})errors=errors+1;
   end
  end
  $display("PADROOTS20 checks=%0d errors=%0d mutant=%0d",checks,errors,mut);
  if(errors)$fatal(1,"PADROOTS20_FAIL");
  $display("PADROOTS20_PASS");$finish;
 end
endmodule
