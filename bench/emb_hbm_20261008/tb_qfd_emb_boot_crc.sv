`timescale 1ns/1fs
module tb_qfd_emb_boot_crc;
 parameter integer MUT=0;
 reg clk=0;always #0.4166666665 clk=~clk;
 reg rst_n=0,i_v=0;reg[24:0]i_e=0;reg[255:0]i_data=0;
 wire busy,o_v;wire[31:0]o_crc;
 ot_qfd_emb_boot_crc #(.MUT(MUT))dut(.*);
 reg[319:0]messages[0:255];reg[31:0]gold[0:255];integer sent=0,received=0,cycles=0,last_accept=0,last_commit=0;
 reg[31:0]sum=0,expected_sum=0;reg end_pending=0,end_done=0;
 always @(posedge clk)if(rst_n)begin
 cycles<=cycles+1;
 if(i_v)begin gold[sent]=messages[sent][319:288];sent<=sent+1;last_accept<=cycles;end
 if(o_v)begin if(o_crc!==gold[received])$fatal(1,"CRC mismatch message=%0d got=%h golden=%h",received,o_crc,gold[received]);sum<=sum+o_crc;expected_sum<=expected_sum+gold[received];received<=received+1;last_commit<=cycles;end
 if(end_pending&&!busy&&!i_v)begin if(received!=256||sum!==expected_sum)$fatal(1,"BOOT_END before committed sum");end_done<=1;end
 end
 integer i;initial begin
 $readmemh("messages.mem",messages);repeat(4)@(negedge clk);rst_n=1;
 for(i=0;i<256;i=i+1)begin
 if(i%17==0)begin i_v=0;repeat(3)@(negedge clk);end
 i_e=messages[i][24:0];i_data=messages[i][287:32];i_v=1;@(negedge clk);
 end
 i_v=0;end_pending=1;
 repeat(5)@(negedge clk);
 if(!end_done||received!=256||last_commit-last_accept!=2)$fatal(1,"drain latency or count");
 $display("PASS256 zlib CRCs bubbles/back-to-back modularsum=%h thirdedge+2cycles BOOT_END drain actual833.333333ps",sum);$finish;
 end
endmodule
