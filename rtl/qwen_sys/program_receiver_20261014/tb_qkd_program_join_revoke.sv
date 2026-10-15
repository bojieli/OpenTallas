`timescale 1ns/1ps
module tb_qkd_program_join_revoke;
 reg ck=0;always #1 ck=~ck;reg rst_n=0,b=0,a=0,active=0,stores=1;
 reg[1:0]sr=0,sf=0,sc=3;reg[31:0]se={2{16'h4281}};reg[127:0]sd={2{64'h1234567812345678}};
 wire cv,ready,fault,cap;wire[15:0]epoch;wire[63:0]digest;
 qkd_program_commit_join dut(ck,rst_n,b,a,active,stores,16'h4281,64'h1234567812345678,sr,sf,sc,se,sd,cv,ready,fault,cap,epoch,digest);
 task tick(input integer n);repeat(n)@(negedge ck);endtask
 task install;begin rst_n=0;b=0;a=0;sr=0;active=0;stores=1;sc=3;se={2{16'h4281}};sd={2{64'h1234567812345678}};
 tick(3);rst_n=1;b=1;tick(1);b=0;a=1;tick(1);a=0;tick(2);sr=3;tick(2);
 if(!ready||!cap||fault)$fatal(1,"installation");end endtask
 integer mode;
 initial begin
 for(mode=0;mode<5;mode=mode+1)begin
 install();
 case(mode)
 0:sr=1;
 1:begin active=1;sr=2;end
 2:stores=0;
 3:sd[0]=!sd[0];
 4:sc=1;
 endcase
 tick(2);if(ready||cap||((mode==1||mode==3)&&!fault))$fatal(1,"actual sink revocation mode%0d",mode);
 sr=3;stores=1;sc=3;tick(3);if(ready||cap)$fatal(1,"stale receipt silently rearmed");
 $display("PASS actual retained-copy/control-seal revocation mode%0d",mode);
 end
 $finish;
 end
endmodule
