`timescale 1ns/1ps
module tb_controller_hbm_calendar;
 parameter integer MUT=0;
 reg ck=0;always #0.512 ck=~ck;
 reg rn=0,we=0,seal=0,go=0;reg[4:0]addr=0;reg[63:0]data=0;reg[15:0]epoch=0;reg[5:0]layer=0;
 wire owner,rd,sr,wr,raw,fault,idle;wire[42:0]cmd;wire[15:0]oe;
 qkd_controller_hbm_calendar #(.MUT(MUT))dut(ck,rn,we,addr,data,seal,go,epoch,layer,owner,cmd,rd,sr,wr,oe,raw,fault,idle);
 reg[127:0]image[0:15];reg[63:0]expected[0:4095];integer cycle,checks=0,reads=0;
 string image_path,expect_path;
 initial begin
 if(!$value$plusargs("IMAGE=%s",image_path)||!$value$plusargs("EXPECT=%s",expect_path))$fatal(1,"missing independent image");
 $readmemh(image_path,image);$readmemh(expect_path,expected);
 repeat(6)@(negedge ck);rn=1;repeat(6)@(negedge ck);
 for(integer i=0;i<32;i++)begin we=1;addr=5'(i);data=i<16?image[i][63:0]:image[i-16][127:64];@(negedge ck);end
 we=0;repeat(3)@(negedge ck);seal=1;@(negedge ck);seal=0;repeat(3)@(negedge ck);
 for(integer frame=0;frame<36;frame++)begin
 layer=6'(frame);epoch=16'(100+frame);go=1;
 @(posedge ck);#0.001; // captured go edge, reference edge zero
 for(cycle=0;cycle<4096;cycle++)begin
 if(cycle>0)begin @(posedge ck);#0.001;end
 if(cycle==0)begin @(negedge ck);go=0;end
 else begin
 if({raw,wr,sr,rd,cmd}!==expected[cycle][46:0])$fatal(1,"FAIL controller calendar frame%0d edge%0d actual%h expected%h",frame,cycle,{raw,wr,sr,rd,cmd},expected[cycle][46:0]);
 if((rd||sr||wr||cmd[0])&&oe!==16'(100+frame))$fatal(1,"FAIL epoch");
 if(fault)$fatal(1,"FAIL legal image fault");
 checks++;if(rd)reads++;
 end
 end
 repeat(3)@(negedge ck);
 end
 // Sealed image tamper must fault, without replacing the programme.
 we=1;addr=0;data=64'hdead;@(negedge ck);we=0;repeat(3)@(negedge ck);
 if(!fault)$fatal(1,"FAIL sealed image write escaped");
 $display("PASS controller calendar checks=%0d reads=%0d frames=36 sealed_tamper=1",checks,reads);$finish;
 end
endmodule
