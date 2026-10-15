`timescale 1ns/1ps
module tb_s81_embed_full_table #(parameter integer MUTANT=0);
 reg clk=0,rst_n=0,start=0;
 reg [16:0] token=0;
 reg [13:0] vm_base=17;
 reg [511:0] header=512'h1234;
 wire busy,done,fault,vm_v,hop_v,hop_last;
 wire [13:0] vm_row;
 wire [511:0] vm_d,hop_d;
 ot_s81_embed_full_table #(.MUTANT(MUTANT)) dut(
  .clk(clk),.rst_n(rst_n),.rom_clocks({96{clk}}),.start(start),.token(token),.vm_base(vm_base),.header(header),
  .busy(busy),.done(done),.fault(fault),.vm_v(vm_v),.vm_row(vm_row),.vm_d(vm_d),.hop_v(hop_v),.hop_last(hop_last),.hop_d(hop_d));
 reg [511:0] expected [0:8319];
 reg [16:0] tokens [0:12];
 string expected_file,tokens_file,out_dir;
 integer test_id,age,rows,hops,outfile;
 task tick;begin #5;clk=1;#1;clk=0;#4;end endtask
 initial begin
  if(!$value$plusargs("EXPECTED=%s",expected_file)) $fatal(1,"missing oracle");
  if(!$value$plusargs("TOKENS=%s",tokens_file)) $fatal(1,"missing token boundary stimuli");
  if(!$value$plusargs("OUT=%s",out_dir)) $fatal(1,"missing actual RTL output directory");
  $readmemh(expected_file,expected);$readmemh(tokens_file,tokens);
  tick;tick;rst_n=1;tick;
  for(test_id=0;test_id<13;test_id=test_id+1) begin
   token=tokens[test_id];start=1;tick;start=0;rows=0;hops=0;age=0;
   outfile=$fopen($sformatf("%s/hin_token%0d.mem",out_dir,token),"w");
   while(!done && age<1500) begin
    tick;age=age+1;
    if(fault) $fatal(1,"static schedule/command fault token%0d age%0d",token,age);
    if(hop_v) begin
     if(hops==0 && hop_d!=header) $fatal(1,"header mismatch");
     if(hops==0 && age!=337) $fatal(1,"header timing%0d",age);
     $fdisplay(outfile,"%0128h",hop_d);hops=hops+1;
    end
    if(vm_v) begin
     if(rows>=640 || vm_row!=vm_base+rows || vm_d!==expected[640*test_id+rows]) $fatal(1,"native result mismatch token%0d row%0d age%0d",token,rows,age);
     if(!hop_v || hop_d!=vm_d || hop_last!=(rows==639)) $fatal(1,"native VM/hop seam mismatch");
     rows=rows+1;
    end
   end
   $fclose(outfile);
   if(rows!=640 || hops!=641 || age!=1377 || !done || busy) $fatal(1,"full row completion token%0d rows%0d hops%0d age%0d",token,rows,hops,age);
   $display("FULL_EMBED token%0d rows640 hops641 cycles%0d PASS",token,age);
   tick;tick;
  end
  $display("S81_FULL_EMBED PASS actual5052residentROMs allvocab boundary identities");$finish;
 end
endmodule
