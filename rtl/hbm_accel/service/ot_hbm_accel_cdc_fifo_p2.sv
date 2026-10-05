`timescale 1ps/1fs
// Protected coded-word crossing. Pointer rail mismatch refuses transfer; local
// mutable mismatch is sticky. No ECC is removed from the coded payload words.
module ot_hbm_accel_cdc_fifo_p2 #(parameter W=360,AW=5)(
 input wire wclk,wrst_n,we,input wire[W-1:0] wdata,output wire full,
 output wire[2:0] rd_freed,output wire w_fault,
 input wire rclk,rrst_n,re,output wire[W-1:0] rdata,output wire empty,output wire r_fault);
 localparam D=1<<AW;
 (* keep = 1 *) reg[W-1:0] mem[0:D-1];
 (* keep = 1 *) reg[AW:0] wb,wg,rb,rg,wb_n,wg_n,rb_n,rg_n;
 (* async_reg="true" *) (* keep = 1 *) reg[AW:0] rw1,rw2,rn1,rn2,ww1,ww2,wn1,wn2;
 (* keep = 1 *) reg[AW:0] freed,freed_n;
 (* keep = 1 *) reg wf,rf,wf_n,rf_n;
 wire wbad=(wf!=~wf_n)||(wb!=~wb_n)||(wg!=~wg_n)||(freed!=~freed_n);
 wire rbad=(rf!=~rf_n)||(rb!=~rb_n)||(rg!=~rg_n);
 wire rok=rw2==~rn2,wok=ww2==~wn2;
 assign full=wf||wbad||!rok||(wg=={~rw2[AW:AW-1],rw2[AW-2:0]});
 assign empty=rf||rbad||!wok||(rg==ww2);
 wire[AW:0] bw=wb+(we&&!full),br=rb+(re&&!empty);
 wire[AW:0] gw=bw^(bw>>1),gr=br^(br>>1);
 function automatic[AW:0] graybin(input[AW:0] g);
  for(integer i=AW;i>=0;i=i-1)graybin[i]=(i==AW)?g[i]:graybin[i+1]^g[i];
 endfunction
 wire[AW:0] released=graybin(rw2);
 assign rd_freed=rok&&!wbad&&!wf?3'(released-freed):0;
 assign rdata=mem[rb[AW-1:0]];
 assign w_fault=wf||wbad;assign r_fault=rf||rbad;
 always @(posedge wclk or negedge wrst_n)
  if(!wrst_n)begin wb<=0;wg<=0;wb_n<='1;wg_n<='1;rw1<=0;rw2<=0;rn1<='1;rn2<='1;freed<=0;freed_n<='1;begin wf<=0;wf_n<=~(0);end end
  else begin
   if(we&&!full)mem[wb[AW-1:0]]<=wdata;
   wb<=bw;wg<=gw;wb_n<=~bw;wg_n<=~gw;
   rw1<=rg;rw2<=rw1;rn1<=rg_n;rn2<=rn1;
   if(rok)begin freed<=released;freed_n<=~released;end
   if(wbad)begin wf<=1;wf_n<=~(1);end 
  end
 always @(posedge rclk or negedge rrst_n)
  if(!rrst_n)begin rb<=0;rg<=0;rb_n<='1;rg_n<='1;ww1<=0;ww2<=0;wn1<='1;wn2<='1;begin rf<=0;rf_n<=~(0);end end
  else begin rb<=br;rg<=gr;rb_n<=~br;rg_n<=~gr;ww1<=wg;ww2<=ww1;wn1<=wg_n;wn2<=wn1;if(rbad)begin rf<=1;rf_n<=~(1);end end
endmodule
