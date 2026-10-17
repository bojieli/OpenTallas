`timescale 1ns/1ps
// Component boundary: declared controller credits/data and independent physical
// WDONE events. This is not an onchip controller substitute for native proof.
module tb_host_boot_debt;
 parameter integer MUT=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,go=0;wire[287:0]es;reg[260:0]er=0;
 reg cv=0,cwe=0;wire bd,bo,fault,quiet;wire[3:0]cause;
 wire[260:0]ner;wire ncv,ncw,bcv,bcw;
 qkd_hbm_boot_static_completion_debt #(.MUT(MUT))dut(.ck(ck),.ck_test(ck),.rst_n(rst_n),.boot_go(go),.normal_es(288'b0),.normal_er(ner),.ctrl_es(es),.ctrl_er(er),.completion_v(cv),.completion_we(cwe),.normal_completion_v(ncv),.normal_completion_we(ncw),.boot_completion_v(bcv),.boot_completion_we(bcw),.boot_done(bd),.boot_ok(bo),.boot_cause(cause),.fault(fault),.boot_quiet(quiet));
 integer cyc=0,issued=0,retired=0;integer credit_due[0:3],read_due[0:3],done_due[0:3];
 reg writes[0:3];reg[255:0]read_data[0:3],memory_word;integer observed_late=0;
 always @(posedge ck)if(rst_n)begin
  cyc=cyc+1;
  if(es[0])begin
   if(issued>=4||es[285:276]!={5'd3,5'd2}||es[275:257]!=0)$fatal(1,"BOOT_ADDRESS");
   writes[issued]=es[286];credit_due[issued]=cyc+3;done_due[issued]=cyc+(issued==3?100:20);
   read_due[issued]=es[286]?-1:cyc+8;
   if(es[286])memory_word=es[256:1];else read_data[issued]=memory_word;
   issued=issued+1;
  end
  if(cv)retired=retired+1;
  #0.001;
  if(quiet&&(issued!=4||retired!=4))$fatal(1,"BOOT_FALSE_QUIET issued%0d retired%0d",issued,retired);
  if(bd&&retired!=4)$fatal(1,"BOOT_DONE_BEFORE_WDONE");
  if(issued==4&&retired<4)observed_late=observed_late+1;
 end
 always @(negedge ck)begin
  er=0;cv=0;cwe=0;
  if(rst_n)for(integer j=0;j<issued;j++)begin
   if(cyc==credit_due[j])er[259]=1;
   if(cyc==read_due[j])begin er[0]=1;er[256:1]=read_data[j];end
   if(cyc==done_due[j])begin cv=1;cwe=writes[j];end
  end
 end
 initial begin
  for(integer i=0;i<4;i++)begin credit_due[i]=-1;read_due[i]=-1;done_due[i]=-1;end
  repeat(3)@(negedge ck);rst_n=1;repeat(8)@(negedge ck);if(quiet)$fatal(1,"UNBOOTED_QUIET");
  go=1;@(negedge ck);go=0;repeat(220)@(negedge ck);
  if(!quiet||!bd||!bo||fault||issued!=4||retired!=4||observed_late<30)$fatal(1,"FINAL_BOOT_DEBT q%0d bd%0d bo%0d f%0d issued%0d done%0d",quiet,bd,bo,fault,issued,retired);
  $display("PASS actualboot two realreadbacks fourphysicalWDONE delayedlastWDONE quietheld%0dedges",observed_late);$finish;
 end
 initial begin #50000;$fatal(1,"TIMEOUT");end
endmodule
