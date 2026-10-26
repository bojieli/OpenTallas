`timescale 1ns/1ps
module tb_qslots_partitioned_v1;
 parameter integer NPT=3,MUT_SELECT=0,MUT_PIN_LATENCY=0;
 localparam integer NS=NPT+7,ND=NPT+13,PWT=545,SELW=4,NSL=18;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;
 reg [NS-1:0] src_v=0,capture_slot=0;
 reg [NS*PWT-1:0] src_d=0;
 reg [ND-1:0] sink_slot=0;
 reg [ND*SELW-1:0] sink_select=0;
 wire [ND-1:0] ref_v,dut_v;
 wire [ND*PWT-1:0] ref_d,dut_d;
 wire ref_fault,dut_fault;
 wire [3:0] ref_kind,dut_kind;
 ot_hgi_coll_qslots #(.NPT(NPT)) reference(
  .clk_capture(clk),.clk_output(clk),.rst_n(rst_n),.src_v(src_v),.src_d(src_d),.capture_slot(capture_slot),
  .sink_slot(sink_slot),.sink_select(sink_select),.dst_v(ref_v),.dst_d(ref_d),.fault(ref_fault),.fault_kind(ref_kind));
 ot_hgi_coll_qslots_partitioned_v1 #(.NPT(NPT),.MUT_SELECT(MUT_SELECT),.MUT_PIN_LATENCY(MUT_PIN_LATENCY)) dut(
  .clk_capture({NS{clk}}),.clk_output({NSL{clk}}),.rst_n(rst_n),.src_v(src_v),.src_d(src_d),.capture_slot(capture_slot),
  .sink_slot(sink_slot),.sink_select(sink_select),.dst_v(dut_v),.dst_d(dut_d),.fault(dut_fault),.fault_kind(dut_kind));
 reg [31:0] rng=32'hb1a53c79;
 function automatic [31:0] next_rng(input reg [31:0] x);next_rng=(x<<13)^x;next_rng=(next_rng>>17)^next_rng;next_rng=(next_rng<<5)^next_rng;endfunction
 integer checked=0;
 task automatic compare;
  if(dut_v!==ref_v || ((|ref_v) && dut_d!==ref_d) || dut_fault!==ref_fault || dut_kind!==ref_kind)
   $fatal(1,"QSLOTS_PARTITION mismatch NPT=%0d cycle=%0d payload=%0d valid=%0d fault=%0d kind=%h/%h",NPT,checked,dut_d!==ref_d,dut_v!==ref_v,dut_fault!==ref_fault,dut_kind,ref_kind);
  checked=checked+1;
 endtask
 initial begin
  repeat(4)begin @(negedge clk);@(posedge clk);#1;end
  @(negedge clk);rst_n=1;
  for(integer c=0;c<192;c=c+1)begin
   @(negedge clk);
   for(integer bitpos=0;bitpos<NS*PWT;bitpos=bitpos+1)begin rng=next_rng(rng);src_d[bitpos]=rng[9];end
   // Initial full reservations exercise every source/destination without faults.
   src_v='1;capture_slot='1;sink_slot='1;
   if(c<2 || (c>=48 && c<54) || (c>=96 && c<102) || (c>=144 && c<150))sink_slot=0;
   for(integer d=0;d<ND;d=d+1)sink_select[d*SELW+:SELW]=SELW'((d+c)%NS);
   // Fault phases exercise all three independent sticky fault classes; reset
   // between phases avoids an earlier fault hiding a later comparison.
   if(c==48 || c==96 || c==144)rst_n=0;
   if(c==52 || c==100 || c==148)rst_n=1;
   if(c>=60 && c<80)capture_slot[0]=0;
   if(c>=60 && c<96)for(integer d=0;d<ND;d=d+1)sink_select[d*SELW+:SELW]=SELW'(1+(d+c)%(NS-1));
   if(c>=108 && c<128)begin src_v[0]=0;capture_slot[0]=0;end
   if(c>=156 && c<176)sink_select[0+:SELW]=SELW'(NS);
   @(posedge clk);#1;compare();
   if(c==40 && ref_kind!==0)$fatal(1,"nominal reserved timeline fault=%h",ref_kind);
   if(c==84 && ref_kind!==1)$fatal(1,"capture fault control did not isolate fault=%h",ref_kind);
   if(c==140 && ref_kind!==4)$fatal(1,"availability fault control did not isolate fault=%h",ref_kind);
   if(c==180 && ref_kind!==2)$fatal(1,"selector fault control did not isolate fault=%h",ref_kind);
  end
  $display("QSLOTS_PARTITION PASS NPT=%0d checked=%0d NS=%0d ND=%0d bits=%0d slices=%0d cycles_added=0",NPT,checked,NS,ND,PWT,NSL);$finish;
 end
endmodule
