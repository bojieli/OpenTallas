`timescale 1ns/1ps
// Raw immutable macro port calibration only; no calendar storage RTL.
module tb_qwen_witness_native32;
 reg ck=0;always #5 ck=~ck;
 reg rce=0,wce=0;reg[4:0]ra=0,wa=0;reg[63:0]wd=0,wm=~64'd0;
 wire[63:0]q;reg[63:0]capture;reg[63:0]image[0:31];reg[63:0]old,newword,previous;string path;
 integer checks=0;
 ot_sram_1r1w_32x64_m1 dut(.clk(ck),.r_ce_in(rce),.r_addr_in(ra),.rd_out(q),.w_ce_in(wce),.w_addr_in(wa),.wd_in(wd),.w_mask_in(wm));
 always@(posedge ck)capture<=q;
 initial begin
  if(!$value$plusargs("IMAGE=%s",path))$fatal(1,"IMAGE");$readmemh(path,image);
  // Explicitly install all32 rows; silicon powerup values are not assumed.
  for(integer i=0;i<32;i++)begin @(negedge ck);wce=1;wa=i;wd=image[i];end
  @(negedge ck);wce=0;
  for(integer i=0;i<32;i++)begin
   @(negedge ck);rce=1;ra=i;previous=q;
   @(posedge ck);#1;
   if(q!==image[i])$fatal(1,"read output publication row%0d",i);
   if(capture!==previous)$fatal(1,"external capture did not add one edge");checks++;
  end
  @(negedge ck);rce=0;previous=q;repeat(2)begin @(posedge ck);#1;if(q!==previous)$fatal(1,"CE0 hold");checks++;end
  @(negedge ck);rce=1;ra=0;wce=1;wa=0;old=image[0];newword=old^64'hf0e1d2c3b4a59687;wd=newword;
  @(posedge ck);#1;if(q!==old)$fatal(1,"same-address must return old word");checks++;
  @(negedge ck);wce=0;@(posedge ck);#1;if(q!==newword||capture!==old)$fatal(1,"write/read/capture age");checks++;
  @(negedge ck);wce=1;wm=64'h00000000ffffffff;wd=64'h0123456789abcdef;old=newword;
  @(posedge ck);#1;if(q!==old)$fatal(1,"masked same-address old word");checks++;
  @(negedge ck);wce=0;@(posedge ck);#1;
  if(q!==((old&64'hffffffff00000000)|64'h0000000089abcdef))$fatal(1,"masked write");checks++;
  $display("WITNESS_NATIVE32_PASS checks=%0d read_sample_to_output_publication=0 output_to_external_capture=1 same_address=read_before_write initialized_rows=32",checks);$finish;
 end
endmodule
