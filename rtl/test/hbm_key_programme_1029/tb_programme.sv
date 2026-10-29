`timescale 1ps/1fs
module tb_programme;
 parameter integer MUT=0;
 reg clk=0;always #416.5 clk=~clk;
 reg rst=0,cfg=0,start=0;reg[10:0]addr=0;reg[255:0]data=0;reg[15:0]loops=64;reg[52:0]ctx=0;
 wire[134:0]word;wire[52:0]wc;wire[15:0]it;wire last,v,active,done,fault;wire[31:0]ordinal;
 ot_smh_calendar_static_x #(.W(135),.AW(11),.XW(53),.MUT(MUT)) cal(.clk(clk),.rst_n(rst),.cfg_we(cfg),.cfg_addr(addr),.cfg_data(data),.start_v(start),.start_base(11'd32),.start_limit(12'd36),.start_loops(loops),.start_ctx(ctx),.calendar(word),.calendar_ctx(wc),.calendar_iter(it),.calendar_lastit(last),.calendar_v(v),.ordinal(ordinal),.active(active),.done(done),.fault(fault));
 wire[33:0]rp;wire[82:0]cmd;wire retire;
 actual_key_reloc rel(clk,word,wc,it,last,v,ordinal,rp,cmd,retire);
 reg[255:0]words[0:3];integer reads=0,commands=0,retires=0,cyc=0,go=0,firstread=-1,prevread=-1,total=0;reg armed=0;
 always @(posedge clk)cyc<=cyc+1;
 always @(negedge clk)if(armed)begin
  if(fault)$fatal(1,"PROGRAMME_CALENDAR_FAULT");
  if(rp[0])begin
   if(rp[23:18]!==6'(reads)||rp[33:24]!==10'(640+reads)||rp[17:2]!==16'd17)$fatal(1,"PROGRAMME_RELOCATION reads=%0d row=%0d tag=%0d",reads,rp[23:18],rp[33:24]);
   if(prevread>=0&&cyc-prevread!=4)$fatal(1,"PROGRAMME_SLOT_GAP");
   if(firstread<0)firstread=cyc;prevread=cyc;reads=reads+1;
  end
  if(cmd[29])begin
   if(cmd[39:30]!==10'(640+commands)||cmd[25]||cmd[82:40]!=0)$fatal(1,"PROGRAMME_COMMAND");
   commands=commands+1;
  end
  if(retire)begin if(reads!=loops)$fatal(1,"PROGRAMME_RETIRE_EARLY");retires=retires+1;end
 end
 initial begin
  $readmemh("programme.hex",words);
  repeat(5)@(posedge clk);@(negedge clk);rst=1;
  for(integer p=0;p<4;p=p+1)begin @(negedge clk);cfg=1;addr=11'(32+p);data=words[p];end
  @(negedge clk);cfg=0;repeat(5)@(posedge clk);
  for(integer n=0;n<2;n=n+1)begin
   @(negedge clk);loops=(n==0)?64:43;ctx={7'd0,12'd0,10'd640,16'd17,1'b0,4'd1,1'b0,2'd0};start=1;go=cyc;armed=1;reads=0;commands=0;retires=0;firstread=-1;prevread=-1;
   @(negedge clk);start=0;
   repeat(280)@(posedge clk);
   @(negedge clk);armed=0;
   if(reads!=loops||commands!=loops||retires!=1)$fatal(1,"PROGRAMME_COUNTS r=%0d c=%0d retire=%0d want=%0d",reads,commands,retires,loops);
   $display("KEY_PROGRAMME_CASE rows=%0d first_read_from_go=%0d reads=%0d commands=%0d retires=%0d",loops,firstread-go,reads,commands,retires);total=total+reads;
  end
  if(MUT!=0)$fatal(1,"PROGRAMME_MUTANT_MISSED");
  $display("KEY_PROGRAMME_PASS total_reads=%0d gap=4 row_tag_exact=1 arithmetic_issue=0 SRAM=ACTUAL",total);$finish;
 end
endmodule
