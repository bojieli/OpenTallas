`timescale 1ns/1ps
module tb_s81_pq_calendar_rom;
`ifndef CALENDAR_BITS
`define CALENDAR_BITS 72
`endif
 localparam ACTION_BITS=`CALENDAR_BITS;
 reg ck=0,rst_n=0,prime=0,start=0;always #5 ck=~ck;
 wire[ACTION_BITS-1:0]action;wire active,primed,fault;
 ot_s81_pq_calendar_rom #(.ACTION_BITS(ACTION_BITS)) dut(.ck(ck),.rst_n(rst_n),.prime(prime),.stage_start(start),.base(12'd0),.length(13'd24),
 .action(action),.active(active),.primed(primed),.fault(fault));
 reg[ACTION_BITS+23:0]expected[0:23];integer i,age=-1,seen=0,mode=0;
 initial begin
  if($value$plusargs("mode=%d",mode))begin end
  $readmemh("expected.hex",expected);
  repeat(4)@(negedge ck);rst_n=1;repeat(3)@(negedge ck);
  if(mode!=1)prime=1;@(negedge ck);prime=0;
  // Compiler-owned fixed prefill window. Primed is observed, never waited for.
  repeat(10)@(negedge ck);if(mode!=1&&!primed)$fatal(1,"fixed boot prefill missed");
  start=1;@(negedge ck);start=0;
  repeat(90)@(negedge ck);
  if(mode==1)begin if(!fault)$fatal(1,"missingprime escaped");end
  else if(fault||seen!=24||active)$fatal(1,"calendar fault%0d seen%0d",fault,seen);
  $display("PASS actualpairedROM calendar mode%0d events%0d consecutive/sparse fixedprefill",mode,seen);$finish;
 end
 always @(posedge ck)begin
  if(start)age=-1;
  if(age>=0||start)begin
   age=age+1;#1;
   if(mode!=1)begin
    if(seen<24&&age==expected[seen][ACTION_BITS+23:ACTION_BITS]+1)begin
     if(action!==expected[seen][ACTION_BITS-1:0])$fatal(1,"actual ROM action mismatch edge%0d index%0d",age,seen);seen=seen+1;
    end else if(action!=0)$fatal(1,"unexpected calendar event edge%0d",age);
   end
  end
 end
 initial begin #2000;$fatal(1,"timeout");end
endmodule
