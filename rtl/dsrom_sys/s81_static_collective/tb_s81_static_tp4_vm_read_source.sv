`timescale 1ns/1ps
module tb_s81_static_tp4_vm_read_source;
 reg clk=0;always #5 clk=~clk;reg rst_n=0,read_slot=0,source_slot=0;
 reg[13:0]read_row=0;reg[2:0]read_group=3,source_group=3,group_id=3;
 reg[4:0]read_return_slot=0,source_return_slot=0;
 reg[31:0]owned_return_slots=32'hffffffff,group_v=0;
 reg[16383:0]group_data=0;
 wire[31:0]rq_v;wire[447:0]rq_row;wire[255:0]rq_tag;wire src_valid,fault;wire[511:0]src_data;
 s81_static_tp4_vm_read_source d(.*);
 integer p;
 initial begin
  repeat(2)@(negedge clk);rst_n=1;
  for(integer s=0;s<32;s=s+1)begin
   read_slot=1;read_row=14'(4096+s);read_return_slot=5'(s);
   source_slot=1;source_return_slot=5'(s);group_v=32'b1<<s;
   group_data=0;group_data[s*512+:512]=512'(s+100);
   #1;p=8*(s%4)+s/4;
   if(rq_v!==(32'b1<<p) || rq_row[p*14+:14]!==read_row || rq_tag[p*8+:8]!=={read_group,read_return_slot})$fatal(1,"request packet permutation");
   if(!src_valid || src_data!==512'(s+100))$fatal(1,"response select");
   @(posedge clk);#1;if(fault)$fatal(1,"valid response fault");@(negedge clk);
  end
  read_slot=0;source_slot=1;group_v=0;
  @(posedge clk);#1;if(!fault)$fatal(1,"missing response escaped");
  @(negedge clk);rst_n=0;read_slot=0;source_slot=0;group_v=0;
  @(negedge clk);rst_n=1;group_v=1;
  @(posedge clk);#1;if(!fault)$fatal(1,"extra response escaped");
  @(negedge clk);rst_n=0;group_v=0;
  @(negedge clk);rst_n=1;read_slot=1;read_row=14'd1;read_return_slot=0;
  #1;if(rq_v!=0)$fatal(1,"invalid request emitted");
  @(posedge clk);#1;if(!fault)$fatal(1,"row-slot mismatch escaped");
  $display("PASS interface-only grouped VM read source32slot permutation, missing/extra/invalidrow faults; no actual SRAM join");$finish;
 end
endmodule
