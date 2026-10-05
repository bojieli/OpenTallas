`timescale 1ns/1ps
module tb_v41x_window_retention;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,inv=0,drained=1,pending=0,qdone=0,qok=1,rows=1,pv=0,pok=1,wrap=0;
 reg[319:0] qkey=320'h1234,pkey=320'h1234;
 reg[15:0] qgen=10,pgen=11;
 wire rv,hit,armed;wire[15:0] gen;
 ot_chip_v41x_window_retention #(.ENABLE(1)) dut(
 .clk(clk),.rst_n(rst_n),.invalidate(inv),.drained(drained),.mutation_pending(pending),
 .qk_complete(qdone),.qk_cacheable(qok),.all_rows_valid(rows),.qk_content_key(qkey),.qk_generation(qgen),
 .pv_request(pv),.pv_cacheable(pok),.pv_content_key(pkey),.pv_generation(pgen),.generation_wrap(wrap),
 .response_valid(rv),.retained_hit(hit),.response_generation(gen),.armed(armed));
 task tick;begin @(posedge clk);#1;end endtask
 task arm;begin @(negedge clk);qdone=1;tick();@(negedge clk);qdone=0;end endtask
 task lookup(input expected);begin pv=1;tick();if(!rv || hit!==expected || gen!=pgen)$fatal(1,"lookup expected %0d hit %0d",expected,hit);@(negedge clk);pv=0;tick();end endtask
 integer i;
 initial begin
 tick();@(negedge clk);rst_n=1;
 arm();lookup(1);lookup(0); // single-use
 // Every bit of normalized identity affects hit, including upper region bits.
 for(i=0;i<320;i=i+1)begin arm();pkey=qkey^(320'b1<<i);lookup(0);pkey=qkey;end
 arm();inv=1;lookup(0);inv=0;
 arm();pending=1;lookup(0);pending=0;
 arm();drained=0;lookup(0);drained=1;
 arm();pgen=qgen;lookup(0);pgen=11;
 arm();wrap=1;lookup(0);wrap=0;
 rows=0;arm();lookup(0);rows=1;
 qok=0;arm();lookup(0);qok=1;
 arm();pok=0;lookup(0);pok=1;
 // New mutation after registered match cancels combinational hit immediately.
 arm();pv=1;tick();if(!hit)$fatal;inv=1;#1;if(hit)$fatal(1,"late invalidation");
 @(negedge clk);pv=0;tick();inv=0;
 $display("RETENTION_PASS identity_bits=320 hazards=9 single_use=1 late_invalidate=1");$finish;
 end
endmodule
