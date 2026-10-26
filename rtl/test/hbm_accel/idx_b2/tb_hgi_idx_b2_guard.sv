`timescale 1ns/1ps
module tb_hgi_idx_b2_guard;
 reg [2074:0] rec=0;wire ix,legal;wire[2074:0] out_rec;
 ot_hgi_idx_b2_record_guard dut(rec,ix,legal,out_rec);
 integer n,checks=0;reg [39:0] ab,bb,cb;reg [2074:0] expected;
 task good;
 begin
  rec=0;rec[0]=1;rec[129+8+:40]=262144;rec[385+8+:40]=262144;
  rec[641+8+:40]=262144;rec[897+8+:40]=2048;
  rec[1153+8+:40]=0;rec[1409+8+:40]=512;
  rec[1+64+:12]=512;rec[1+77]=1;rec[1+76]=1;rec[1+98]=1;
  rec[641+48+:20]=2048;rec[641+88+:32]=2048;rec[897+88+:32]=2048;
 end endtask
 task check(input bit want);
 begin #1;if(legal!==want)$fatal(1,"admission expected%0d got%0d",want,legal);checks=checks+1;end endtask
 initial begin
  good;check(1);
  for(n=0;n<1000;n=n+1)begin
   good;ab=262144+8*($urandom%3585);bb=262144+($urandom%32737);cb=262144+($urandom%28673);
   rec[137+:40]=ab;rec[393+:40]=bb;rec[649+:40]=cb;
   expected=rec;expected[137+:40]=ab-262144;expected[393+:40]=bb-262144;expected[649+:40]=cb-262144;
   check(1);if(out_rec!==expected)$fatal(1,"rebase changed field or payload");
  end
  good;rec[137+:40]=262143;check(0);
  good;rec[137+:40]=290824;check(0);
  good;rec[137+:40]=40'h100040000;check(0);
  good;rec[393+:40]=294881;check(0);
  good;rec[649+:40]=290817;check(0);
  good;rec[641+88+:32]=32'h40000800;check(0);
  good;rec[1153+8+:40]=65025;check(0);
  good;rec[1409+8+:40]=65025;check(0);
  good;rec[897+8+:40]=62121;check(0);
  good;rec[897+88+:32]=32'h40000800;check(0);
  good;rec[1+76]=0;rec[897+8+:40]=40'hffffffffff;check(1);
  good;rec[1+98]=0;rec[1409+8+:40]=40'hffffffffff;check(1);
  good;rec[1+77]=0;rec[641+8+:40]=40'hffffffffff;check(1);
  good;rec[1+118+:6]=2;check(1);if(out_rec!==rec)$fatal(1,"packet operation changed");
  $display("PASS IDX_B2_GUARD checks=%0d",checks);$finish;
 end
endmodule
