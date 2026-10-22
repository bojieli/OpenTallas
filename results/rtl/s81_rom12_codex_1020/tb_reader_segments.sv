`timescale 1ns/1ps
module tb_reader_segments;
 reg ck=0,rst_n=0,prime=0,stage_start=0;
 always #5 ck=~ck;
 reg [11:0] base=0;reg [12:0] length=0;
 wire [74:0] action;wire active,primed,fault;
 ot_s81_pq_calendar_rom #(.ACTION_BITS(75),.PINREG(1)) dut
 (.ck(ck),.rst_n(rst_n),.prime(prime),.stage_start(stage_start),.base(base),.length(length),.action(action),.active(active),.primed(primed),.fault(fault));
 reg [159:0] issuer[0:49999]; reg [74:0] expected[0:49999];
 integer n,end_cycle,mode=0,events=0;reg [159:0] cmd;
 initial begin
  for(n=0;n<50000;n=n+1)begin issuer[n]=0;expected[n]=0;end
  $readmemh("issuer.hex",issuer);$readmemh("expected.hex",expected);
  if(!$value$plusargs("end=%d",end_cycle))$fatal(1,"missing end");
  if($value$plusargs("mode=%d",mode))begin end
  repeat(8)@(negedge ck);rst_n=1;repeat(16)@(negedge ck);
  for(n=0;n<=end_cycle;n=n+1)begin
   @(negedge ck);cmd=issuer[n];
   prime=cmd[93] && !(mode==1 && n>400);stage_start=cmd[94];base=cmd[106:95];length=cmd[119:107];
   if(mode==2 && prime && n>400)base=base+1;
   @(posedge ck);#1;
   begin
    if(fault)$fatal(1,"reader fault cycle%0d",n);
    if(action!==expected[n])$fatal(1,"action mismatch cycle%0d got%h want%h",n,action,expected[n]);
    if(action!=0)events=events+1;
   end
  end
  if(mode!=0 && !fault)$fatal(1,"mutant escaped reader mode%0d",mode);
  if(mode==0 && active)$fatal(1,"reader active after terminal interval");
  $display("PASS segmented existing reader mode%0d cycles%0d events%0d",mode,end_cycle,events);$finish;
 end
endmodule
