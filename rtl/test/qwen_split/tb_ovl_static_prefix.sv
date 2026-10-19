`timescale 1ns/1ps
module tb_ovl_static_prefix;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,go=0,halt=0;wire[11:0]addr;reg[31:0]q;
 reg[31:0]mem[0:4095];wire start,seg,running,fault;wire[1:0]user_id;
 ot_qwen_d2d_list_play #(.AW(12),.WRAP_BASE(MUT==1?0:1),.MUT_HALT_REWIND(MUT==2)) dut(
 .ck(ck),.rst_n(rst_n),.go(go),.halt(halt),.rom_addr(addr),.rom_q(q),.start(start),.seg(seg),.user(user_id),.running(running),.fault(fault));
 always @(posedge ck)q<=mem[addr];
 integer edge_n=0,anchor=0,count=0;reg checking=0;
 always @(posedge ck)edge_n<=edge_n+1;
 always @(negedge ck)if(checking)begin:score
 integer t;reg expect_start;reg[2:0]expect_tag;
 t=edge_n-anchor;expect_start=(t==5)||(t>=12&&((t-12)%27==0))||(t>=21&&((t-21)%27==0));
 expect_tag=(t==5)?3'b100:((t>=12&&((t-12)%27==0))?3'b001:3'b010);
 if(start!==expect_start||(start&&{seg,user_id}!==expect_tag)||fault)begin
  $display("STATICPREFIX_FAIL MUT%0d t%0d start%0d expected%0d tag%0d fault%0d",MUT,t,start,expect_start,{seg,user_id},fault);$fatal(1);
 end
 if(start)count++;
 end
 task automatic launch;
 @(negedge ck);go=1;anchor=edge_n+1;
 @(negedge ck);go=0;checking=1;
 endtask
 initial begin
 for(integer i=0;i<4096;i++)mem[i]=0;
 mem[0]=(5<<12)|(1<<11)|(1<<10); // once-per-epoch prefix user0
 mem[1]=(7<<12)|(1<<11)|(1<<8); // steady user1; wrap destination1
 mem[2]=(9<<12)|(1<<11)|(2<<8); // steady user2
 mem[3]=(11<<12)|(1<<7); // fixed wrap to1; steady recurrence27
 repeat(3)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);
 launch();repeat(183)@(negedge ck);
 checking=0;halt=1;repeat(5)@(negedge ck);halt=0;repeat(8)@(negedge ck);
 launch();repeat(183)@(negedge ck);checking=0;
 $display("STATICPREFIX_PASS MUT%0d starts%0d onceprefix/cyclic27/haltreplay",MUT,count);$finish;
 end
endmodule
