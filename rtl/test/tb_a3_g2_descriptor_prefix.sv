`timescale 1ns/1ps
module tb_a3_g2_descriptor_prefix;
 parameter integer WORDS=3;
 parameter bit SHORT=0;
 localparam SHORT_WORDS=WORDS>1?WORDS-1:1;
 localparam EXPECT_WORDS=SHORT?SHORT_WORDS:WORDS;
 reg aux_short=SHORT;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,req=0,aux_req=0,host_we=0;
 reg [31:0] id=0,aux_id=0;
 reg [10:0] host_row=0;
 reg host_lane=0;
 reg [127:0] host_wdata=0;
 wire valid,fault,aux_valid,aux_fault,host_accept;
 wire [1535:0] data,aux_data;
 wire [31:0] reads,faults,dropped;
 integer cycles=0,checks=0,seq_latency,aux_latency,started,ram_reads=0;
 always @(posedge clk)begin
  cycles<=cycles+1;
  if(dut.ram_ce && !dut.ram_we0 && !dut.ram_we1)ram_reads<=ram_reads+1;
 end
 ot_a3_g2_descriptor_store #(.AUXILIARY_WORDS(WORDS),.AUXILIARY_SHORT_WORDS(SHORT_WORDS)) dut(
 .clk(clk),.rst_n(rst_n),.desc_req(req),.desc_id(id),.desc_valid(valid),.desc_fault(fault),.desc_data(data),
 .aux_req(aux_req),.aux_short(aux_short),.aux_id(aux_id),.aux_valid(aux_valid),.aux_fault(aux_fault),.aux_data(aux_data),
 .host_we(host_we),.host_row(host_row),.host_lane(host_lane),.host_wdata(host_wdata),.host_accept(host_accept),
 .read_count(reads),.fault_count(faults),.dropped_requests(dropped));
 function automatic [127:0] pattern(input integer record_id,input integer halfword);
  pattern={32'(record_id),32'(halfword),32'hcafe1234,32'(record_id*97+halfword)};
 endfunction
 function automatic [1535:0] record_pattern(input integer record_id,input integer count);
  reg [1535:0] result;integer n;
  begin
   result=0;
   for(n=0;n<count*2;n=n+1)result[n*128+:128]=pattern(record_id,n);
   record_pattern=result;
  end
 endfunction
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task load(input integer record_id);integer n;begin
  for(n=0;n<12;n=n+1)begin
   host_we=1;host_row=11'(record_id*6+n/2);host_lane=1'(n%2);host_wdata=pattern(record_id,n);
   #1;if(!host_accept)$fatal(1,"loader refused");tick();
  end
  host_we=0;tick();
 end endtask
 task read_one(input bit aux,input integer record_id,input bit bad);integer before_reads;begin
  before_reads=ram_reads;
  aux_short=SHORT;id=32'(record_id);aux_id=32'(record_id);req=!aux;aux_req=aux;started=cycles;tick();req=0;aux_req=0;aux_short=!SHORT;
  if(aux)begin
   wait(aux_valid);@(negedge clk);aux_latency=cycles-started;
   if(aux_fault!=bad || aux_data!=(bad?1536'd0:record_pattern(record_id,EXPECT_WORDS)))$fatal(1,"aux prefix mismatch");
  end else begin
   wait(valid);@(negedge clk);seq_latency=cycles-started;
   if(fault!=bad || data!=(bad?1536'd0:record_pattern(record_id,6)))$fatal(1,"full record mismatch");
  end
  if(ram_reads-before_reads!=(bad?0:aux?EXPECT_WORDS:6))$fatal(1,"wrong number of SRAM reads");
  checks=checks+1;tick();tick();
 end endtask
 initial begin
  tick();rst_n=1;tick();load(0);load(1);load(340);
  read_one(0,0,0);read_one(1,1,0);
  if(seq_latency-aux_latency!=6-EXPECT_WORDS)$fatal(1,"prefix latency did not remove unused beats");
  // Simultaneous requests retain sequencer priority and preserve both identities.
  aux_short=SHORT;id=0;aux_id=340;req=1;aux_req=1;tick();req=0;aux_req=0;aux_short=!SHORT;
  wait(valid);@(negedge clk);
  if(aux_valid || fault || data!=record_pattern(0,6))$fatal(1,"priority/full response");
  wait(aux_valid);@(negedge clk);
  if(aux_fault || aux_data!=record_pattern(340,EXPECT_WORDS))$fatal(1,"queued prefix response");
  checks=checks+2;tick();tick();
  read_one(1,341,1);read_one(0,32'hffffffff,1);
  // A full read after a short one must replace every word, not publish stale tail.
  read_one(0,340,0);read_one(1,0,0);
  if(reads!=6 || faults!=2 || dropped!=0)$fatal(1,"accounting reads=%0d faults=%0d dropped=%0d",reads,faults,dropped);
  // Reset revokes an in-flight short read and leaves the next full read intact.
  aux_req=1;aux_id=1;tick();aux_req=0;tick();rst_n=0;tick();rst_n=1;
  repeat(12)begin tick();if(valid || aux_valid)$fatal(1,"cancelled response escaped");end
  read_one(0,1,0);
  $display("PASS descriptor prefix words=%0d checks=%0d saved_cycles=%0d",WORDS,checks,6-EXPECT_WORDS);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
