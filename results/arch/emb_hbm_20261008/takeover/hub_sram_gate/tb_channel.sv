`timescale 1ns/1ps
module tb_channel;
 reg wclk=0;always #0.416666667 wclk=~wclk;
 reg rclk=0;initial begin #0.1;forever #0.416666667 rclk=~rclk;end
 reg rn=0,iv=0;reg [522:0] id=0;
 wire [2:0] cr,wf,ov,rf;wire [522:0] od[0:2];reg [2:0] ocr=0;
 ot_qwen_die_cdc_ch #(.W(523),.IBUF(128),.OCRED(8),.AD(8)) baseline(
 .wclk(wclk),.wrst_n(rn),.i_v(iv),.i_d(id),.i_cr(cr[0]),.w_fault(wf[0]),
 .rclk(rclk),.rrst_n(rn),.o_v(ov[0]),.o_d(od[0]),.o_cr(ocr[0]),.r_fault(rf[0]));
 genvar g;
 generate for(g=1;g<3;g=g+1)begin:version
 ot_qwen_die_cdc_ch_sram #(.SRAM(g-1),.W(523),.IBUF(128),.OCRED(8),.AD(8)) dut(
 .wclk(wclk),.wrst_n(rn),.i_v(iv),.i_d(id),.i_cr(cr[g]),.w_fault(wf[g]),
 .rclk(rclk),.rrst_n(rn),.o_v(ov[g]),.o_d(od[g]),.o_cr(ocr[g]),.r_fault(rf[g]));
 end endgenerate
 function automatic [522:0] pattern(input integer n);
 integer k;begin for(k=0;k<523;k=k+1)pattern[k]=((n*29+k*3+k/5)>>(k%17))&1;
 pattern[31:0]=n;pattern[522:512]=11'(n^11'h733);end endfunction
 integer returned[0:2],received[0:2],debt[0:2],first_cycle[0:2];
 integer i,wcycle=0,rcycle=0;reg allow=0;
 always @(posedge wclk)if(rn)begin
 wcycle=wcycle+1;
 for(i=0;i<3;i=i+1)if(cr[i])returned[i]=returned[i]+1;
 if(cr[0]!==cr[1] || wf[0]!==wf[1])$fatal(1,"default-disabled ingress cycle mismatch");
 if(|wf)$fatal(1,"unexpected write fault");
 end
 integer j;
 always @(posedge rclk)if(rn)begin
 rcycle=rcycle+1;
 if(ov[0]!==ov[1] || rf[0]!==rf[1] || (ov[0] && od[0]!==od[1]))$fatal(1,"default-disabled output cycle mismatch");
 if(|rf)$fatal(1,"unexpected read fault");
 for(j=0;j<3;j=j+1)begin
  if(ov[j])begin
   if(od[j]!==pattern(received[j]))$fatal(1,"channel golden mismatch version%0d word%0d",j,received[j]);
   if(received[j]==0)first_cycle[j]=rcycle;
   received[j]=received[j]+1;debt[j]=debt[j]+1;
  end
 end
 end
 integer k,n,minimum,deadline;
 always @(negedge rclk)begin
  for(k=0;k<3;k=k+1)begin ocr[k]=0;if(allow && debt[k]>0 && rcycle%13!=0)begin ocr[k]=1;debt[k]=debt[k]-1;end end
 end
 initial begin
  for(n=0;n<3;n=n+1)begin returned[n]=0;received[n]=0;debt[n]=0;first_cycle[n]=0;end
  repeat(5)@(negedge wclk);rn=1;repeat(20)@(negedge wclk);
  iv=1;id=pattern(0);@(negedge wclk);iv=0;
  repeat(25)@(negedge wclk);
  if(received[0]!=1 || received[1]!=1 || received[2]!=1 || first_cycle[2]-first_cycle[0]!=3)
   $fatal(1,"first ingress latency expected+3edges baseline%0d enabled%0d",first_cycle[0],first_cycle[2]);
  // Fill exactly128 further outstanding reservations with returned credits withheld downstream.
  for(n=1;n<129;n=n+1)begin iv=1;id=pattern(n);@(negedge wclk);end
  iv=0;repeat(30)@(negedge wclk);allow=1;
  n=129;deadline=wcycle+6000;
  while((n<512 || received[2]<512) && wcycle<deadline)begin
   minimum=returned[0];if(returned[1]<minimum)minimum=returned[1];if(returned[2]<minimum)minimum=returned[2];
   iv=0;if(n<512 && n-minimum<128)begin iv=1;id=pattern(n);n=n+1;end
   @(negedge wclk);
  end
  iv=0;repeat(30)@(negedge wclk);
  for(n=0;n<3;n=n+1)if(received[n]!=512 || returned[n]!=512)$fatal(1,"count mismatch version%0d recv%0d credits%0d",n,received[n],returned[n]);
  $display("PASS channel523 full128 AD8 OD8 original/default cycleexact enabled512 golden actualclocks833.333ps phase100ps added_first3edges cycles%0d",wcycle);
  $finish;
 end
endmodule
