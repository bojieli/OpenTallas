`timescale 1ns/1ps
module tb_qfd_seq_su_collective_calendar;
 reg ck=0;always #5 ck=~ck;
 reg rsi=0;reg[186:0]dh=0;reg cmd_free=1;wire[49:0]cmd;wire fault,cfg_ready;
 integer omit=0,block=0,seen=0,elapsed=-1,issued=-1,image;
 qfd_seq_su_collective_calendar dut(.*);
 task wr(input[9:0]a,input[63:0]d);
 @(negedge ck);dh[118]=1;dh[117:108]=a;dh[107:44]=d;
 @(negedge ck);dh[118]=0;
 endtask
 always @(posedge ck)if(dh[42])elapsed<=0;else if(elapsed>=0)begin
 elapsed<=elapsed+1;
 if(cmd[49])begin seen<=seen+1;issued<=elapsed;
 if((omit!=2&&cmd[48:17]!=={18'd140123,8'hff,6'd2})||cmd[16]!==1'b0||cmd[15:0]!==16'd256)$fatal(1,"descriptor from real dh PW face");end
 end
 initial begin
 if($value$plusargs("OMIT=%d",omit))begin end
 if($value$plusargs("BLOCK=%d",block))begin end
 repeat(3)@(negedge ck);rsi=1;cmd_free=!block;
 for(image=0;image<2;image=image+1)begin
 wr(0,0);if(cfg_ready)$fatal(1,"stale collective seal after genuinePW0");
 if(omit!=1)wr(944,(64'd256<<32)|8);
 if(omit!=2)wr(945,64'd2);
 wr(946,(64'd1<<49)|12);wr(947,0);wr(960,(64'h434c<<48)|(64'd2<<32)|12);
 if(cfg_ready!==(omit==0))$fatal(1,"collective seal completeness");
 @(negedge ck);dh[35:18]=18'd140123;dh[17:0]=18'd8191;dh[42]=1;@(negedge ck);dh[42]=0;
 repeat(18)@(negedge ck);
 if(fault!==(omit!=0||block!=0))$fatal(1,"calendar integrity fault %0d %0d %b",omit,block,fault);
 if(omit!=1&&(seen!=image+1||issued!=8))$fatal(1,"fixed dh stage-start timeline %0d %0d",seen,issued);
 $display("PASS actual seq dh/PW944 calendar timeline8/stop12 image%0d omit%0d block%0d",image,omit,block);
 end
 $finish;
 end
 initial begin #3000;$fatal(1,"timeout");end
endmodule
