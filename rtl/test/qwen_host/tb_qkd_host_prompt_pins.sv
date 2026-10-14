`timescale 1ns/1ps
module tb_qkd_host_prompt_pins;
parameter integer MUT=0;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0,we=0,re=0;reg[12:0]waddr=0,raddr=0;reg[17:0]wdata=0;
wire[17:0]q;wire fault;
qkd_host_prompt_pins #(.MUT(MUT))dut(.*);
reg[17:0]refmem[0:8191],expected0,expected1,expected2,hold;
reg wr_q=0,rd_q=0,valid0=0,valid1=0,valid2=0;reg[12:0]wa_q=0,ra_q=0;reg[17:0]wd_q=0;
integer checks=0,errors=0,ecc_checks=0,i,j,k,lane;
reg checking=1;reg[255:0]inject;reg[23:0]code;
always @(posedge ck)begin
 if(!rst_n)begin wr_q<=0;rd_q<=0;valid0<=0;valid1<=0;valid2<=0;hold<=0;end
 else if(checking)begin
  // Independent reference: request register; read-before-write macro edge;
  // one final response-pin stage. Simultaneous writes preserve other lanes.
  wr_q<=we;rd_q<=re;wa_q<=waddr;ra_q<=raddr;wd_q<=wdata;
  valid0<=rd_q;if(rd_q)expected0<=refmem[ra_q];
  if(wr_q)refmem[wa_q]<=wd_q;
  valid1<=valid0;expected1<=expected0;
  #0.01;
  if(valid1)begin checks=checks+1;if(q!==expected1 || fault)begin errors=errors+1;if(errors<4)$display("MISMATCH q=%h expected=%h",q,expected1);end end
 end
end
 task cycle(input wr,input rr,input[12:0]wa,input[12:0]ra,input[17:0]wd);begin
 @(negedge ck);we=wr;re=rr;waddr=wa;raddr=ra;wdata=wd;
 end endtask
 task ecc_case(input integer l,input integer bit0,input integer bit1);begin
 @(negedge ck);rst_n=0;we=0;re=0;repeat(3)@(negedge ck);rst_n=1;raddr=l;re=1;
 inject=0;inject[l*32+:24]=code^(24'b1<<bit0)^((bit1<0)?24'b0:(24'b1<<bit1));
 force dut.u_core.rd=inject;
 repeat(5)@(negedge ck);
 ecc_checks=ecc_checks+1;
 if(bit1<0)begin if(q!==18'h2b123 || fault!==0)errors=errors+1;end
 else begin if(q!==0 || fault!==1)errors=errors+1;end
 release dut.u_core.rd;re=0;
 end endtask
initial begin
 repeat(4)@(negedge ck);rst_n=1;
 for(i=0;i<8192;i=i+1)cycle(1,0,i,0,18'((i*73)^18'h2bb23));
 cycle(0,0,0,0,0);cycle(0,0,0,0,0);
 for(i=0;i<8192;i=i+1)cycle(0,1,0,i,0);
 for(i=0;i<4096;i=i+1)cycle(1,1,(i*23)%8192,(i%3==0)?(i*23)%8192:((i*23)%8192)^3,18'(i^18'h33456));
 for(i=0;i<8192;i=i+1)cycle(0,1,0,i,0);
 repeat(5)cycle(0,0,0,0,0);
 checking=0;code=dut.u_core.encode(18'h2b123);
 for(lane=0;lane<8;lane=lane+1)begin
  for(j=0;j<24;j=j+1)ecc_case(lane,j,-1);
  for(j=0;j<24;j=j+1)for(k=j+1;k<24;k=k+1)ecc_case(lane,j,k);
 end
 if(errors!=0)$fatal(1,"prompt pin exact failed errors=%d checks=%d ecc=%d",errors,checks,ecc_checks);
 $display("PASS prompt pin8192x18 exact mask/read-before-write latency3 ECC correction/double-error checks=%d ecc=%d",checks,ecc_checks);$finish;
end
endmodule
