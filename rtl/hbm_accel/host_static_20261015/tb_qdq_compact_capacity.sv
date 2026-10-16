`timescale 1ns/1ps
module tb_qdq_compact_capacity;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,cfg_we=0,start_v=0;reg[9:0]cfg_addr=0,start_base=0;reg[10:0]start_limit=0;reg[255:0]cfg_data=0;
 wire command_v,active,done,fault;wire[47:0]command;wire[31:0]cycle;
 integer seen=0,cy=0,lastcy=-1,base_row=0,expected_count=4096;reg measuring=0,done_seen=0;
 ot_hgi_qdq_record_calendar dut(.*);
 function automatic[255:0]word(input integer row,input integer timestamp);
 reg[255:0]v;begin v=0;v[255:240]=16'hc7a1;v[233:224]=10'(row);v[31:0]=32'(timestamp);v[47:32]=4;v[63:48]=16'(row*16);v[79:64]=16'(row*32);v[85:80]=4;v[93:86]=8'(row);word=v;end endfunction
 function automatic[47:0]expected(input integer n);
 integer row,beat;begin row=base_row+n/4;beat=n%4;expected={beat==3,16'(row*32+beat*4),16'(row*16+beat*4),8'(row),6'd4,1'b1};end endfunction
 always @(negedge clk)begin
 cy=cy+1;
 if(measuring&&done)done_seen=1;
 if(measuring&&fault)$fatal(1,"QDQ_CAPACITY actual calendar fault");
 if(measuring&&command_v)begin
 if(seen>=expected_count||command!==expected(seen))$fatal(1,"QDQ_CAPACITY replay/wrong command n=%0d rowbase=%0d got=%h",seen,base_row,command);
 if(lastcy>=0&&cy!=lastcy+1)$fatal(1,"QDQ_CAPACITY runtime gap");lastcy=cy;seen=seen+1;
 end end
 task execute(input integer b,input integer n);
 begin
 base_row=b;expected_count=n*4;seen=0;lastcy=-1;done_seen=0;
 @(negedge clk);start_base=10'(b);start_limit=11'(b+n);start_v=1;measuring=1;
 @(negedge clk);start_v=0;repeat(n*4+40)@(negedge clk);
 if(!done_seen||seen!=expected_count||active||fault)$fatal(1,"QDQ_CAPACITY completion seen=%0d expected=%0d done=%b",seen,expected_count,done_seen);
 measuring=0;
 end endtask
 initial begin
 repeat(4)@(negedge clk);rst_n=1;
 for(integer row=0;row<1024;row=row+1)begin @(negedge clk);cfg_we=1;cfg_addr=10'(row);cfg_data=word(row,8+row*4);end
 @(negedge clk);cfg_we=0;repeat(4)@(negedge clk);execute(0,1024);
 @(negedge clk);cfg_we=1;cfg_addr=1023;cfg_data=word(1023,8);
 @(negedge clk);cfg_we=0;repeat(4)@(negedge clk);execute(1023,1);
 $display("QDQ_COMPACT_CAPACITY_PASS rows1024 commands4096 gapless1 terminal_base1023_commands4 exhausted_sentinel11");$finish;
 end
 initial begin #100000;$fatal(1,"QDQ_CAPACITY watchdog");end
endmodule
