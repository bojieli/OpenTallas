`timescale 1ns/1ps
// credit-ready (2026-10-08): reset bench for ot_ha2_truecredit_receiver_p #(.CREDIT(1)) (derived from
// tb_ha2_truecredit_reset). A CRD-deep consumer buffer replaces the same-cycle ready and returns one credit pulse per
// pop after CRET cycles; reset (common to all) flushes the consumer and the credit line. MUTANT 1 = return pipe not
// reset, MUTANT 2 = stale sender credit replay (as the original); MUTANT 3 = the credit-return line is NOT reset
// (stale credits after reset -> receiver credit overflow fault).
module tb_ha2_truecredit_cr_reset #(
 parameter integer FWD=7, RET=7, MUTANT=0, ROWS=192, TAGW=16, CRD=8, CRET=5
);
 localparam integer W=544,INJ=2;
 reg initial_reset_done=0,replay=0;integer epoch=0;
 wire pipe_rst_n=(MUTANT==1 && initial_reset_done)?1'b1:rst_n;
 wire[INJ-1:0] hubquiet,fwdquiet,retquiet;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[INJ-1:0] issue_v=0,receiver_ready=0;
 integer cnt[0:INJ-1],wr[0:INJ-1],rd[0:INJ-1];reg[W-1:0] buffer[0:INJ-1][0:63];reg[63:0] line[0:INJ-1];
 reg[INJ*W-1:0] source_data=0;
 wire[INJ-1:0] issue_ready,hub_v,txv,rxv,rv,backv,output_v;
 wire[INJ*W-1:0] hub_data,txdata,rxdata,output_data;
 wire[INJ*TAGW-1:0] txtag,rxtag,rtag,backtag;
 wire txquiet,rxquiet,txfault,rxfault;
 integer issued[0:INJ-1],received[0:INJ-1];
 integer cycle=0,stalls=0,first_issue=-1,last_receive=-1;
 function automatic[W-1:0] row(input integer lane,n);
  for(integer j=0;j<W/32;j=j+1)row[j*32+:32]=32'h7f023456^(epoch<<28)^(lane<<24)^(n<<8)^j;
 endfunction
 for(genvar i=0;i<INJ;i=i+1)begin:g_lane
  ot_ha2_delay_quiet #(.W(W),.D(35)) u_hub
   (.clk(clk),.rst_n(rst_n),.v_in(issue_v[i]),.d_in(source_data[i*W+:W]),
    .v_out(hub_v[i]),.d_out(hub_data[i*W+:W]),.quiet(hubquiet[i]));
  wire[W+TAGW-1:0] frame;
  if(FWD==0)begin
   assign fwdquiet[i]=!txv[i];assign rxv[i]=txv[i];assign frame={txtag[i*TAGW+:TAGW],txdata[i*W+:W]};
  end else begin
   ot_ha2_delay_quiet #(.W(W+TAGW),.D(FWD)) u_forward
    (.clk(clk),.rst_n(rst_n),.v_in(txv[i]),.d_in({txtag[i*TAGW+:TAGW],txdata[i*W+:W]}),
     .v_out(rxv[i]),.d_out(frame),.quiet(fwdquiet[i]));
  end
  assign rxdata[i*W+:W]=frame[W-1:0];
  assign rxtag[i*TAGW+:TAGW]=frame[W+:TAGW] ^ TAGW'(0);
  if(RET==0)begin assign retquiet[i]=!rv[i];assign backv[i]=rv[i];assign backtag[i*TAGW+:TAGW]=rtag[i*TAGW+:TAGW];end
  else begin
   ot_ha2_delay_quiet #(.W(TAGW),.D(RET)) u_return
    (.clk(clk),.rst_n(pipe_rst_n),.v_in(rv[i]),.d_in(rtag[i*TAGW+:TAGW]),
     .v_out(backv[i]),.d_out(backtag[i*TAGW+:TAGW]),.quiet(retquiet[i]));
  end
 end
 ot_ha2_truecredit_sender #(.W(W),.INJ(INJ),.TAGW(TAGW),.MUTANT(0)) tx
  (.clk(clk),.rst_n(rst_n),.issue_v(issue_v),.arrival_v(hub_v),.arrival_data(hub_data),
   .return_v(replay ? 2'b01 : backv),.return_tag(replay ? {INJ*TAGW{1'b0}} : backtag),.issue_ready(issue_ready),
   .send_v(txv),.send_data(txdata),.send_tag(txtag),.quiet(txquiet),.fault(txfault));
 ot_ha2_truecredit_receiver_p #(.W(W),.INJ(INJ),.TAGW(TAGW),.MUTANT(0),.CREDIT(1),.CRD(CRD)) rx
  (.clk(clk),.rst_n(rst_n),.arrival_v(rxv),.arrival_data(rxdata),.arrival_tag(rxtag),
   .receiver_ready(receiver_ready),.send_v(output_v),.send_data(output_data),
   .return_v(rv),.return_tag(rtag),.quiet(rxquiet),.fault(rxfault));
 initial begin
  if(FWD==0||RET==0)$fatal(1,"RESET_TEST_REQUIRES_INFLIGHT_LINKS");
  for(integer i=0;i<INJ;i=i+1)begin cnt[i]=0;wr[i]=0;rd[i]=0;line[i]=0;end
  repeat(4)@(negedge clk);rst_n=1;initial_reset_done=1;
  for(epoch=0;epoch<2;epoch=epoch+1)begin
   for(integer i=0;i<INJ;i=i+1)begin issued[i]=0;received[i]=0;end
   begin:run_phase
    for(cycle=0;cycle<ROWS*20+2000+4*(FWD+RET);cycle=cycle+1)begin
     @(negedge clk);
     replay=(MUTANT==2 && epoch==1 && cycle==0);
     for(integer i=0;i<INJ;i=i+1)begin
      reg pop;
      pop=cnt[i]>0 && ((i==0)?(cycle>=220 && cycle%2==0):(cycle>=500 && cycle%7<3));
      if(pop)begin
       if(buffer[i][rd[i]]!==row(i,received[i]))$fatal(1,"RESET_STALE_DATA epoch=%0d row=%0d lane=%0d",epoch,received[i],i);
       rd[i]=(rd[i]+1)%CRD;cnt[i]=cnt[i]-1;received[i]=received[i]+1;
      end
      line[i]={line[i][62:0],pop};
      receiver_ready[i]=line[i][CRET];
      issue_v[i]=issue_ready[i]&&issued[i]<ROWS;
      source_data[i*W+:W]=row(i,issued[i]);
     end
     @(posedge clk);
     for(integer i=0;i<INJ;i=i+1)if(issue_v[i])issued[i]=issued[i]+1;
     #1;
     if(txfault||rxfault)$fatal(1,"RESET_PROTOCOL_FAULT epoch=%0d tx=%0d rx=%0d",epoch,txfault,rxfault);
     for(integer i=0;i<INJ;i=i+1)if(output_v[i])begin
      if(cnt[i]>=CRD)$fatal(1,"TRUECREDIT_CONSUMER_OVF epoch=%0d lane=%0d",epoch,i);
      buffer[i][wr[i]]=output_data[i*W+:W];wr[i]=(wr[i]+1)%CRD;cnt[i]=cnt[i]+1;
     end
     // Reset only after proving all three flight classes and receiver work.
     if(epoch==0 && received[0]>4 && !( &hubquiet) && !( &fwdquiet) && !( &retquiet))begin
      $display("RESET_INTERRUPTION fwd=%0d ret=%0d issued=%0d/%0d received=%0d/%0d hubquiet=%b fwdquiet=%b retquiet=%b",FWD,RET,issued[0],issued[1],received[0],received[1],hubquiet,fwdquiet,retquiet);
      disable run_phase;
     end
     if(epoch==1 && received[0]==ROWS&&received[1]==ROWS&&txquiet&&rxquiet&&line[0]==0&&line[1]==0&&(&hubquiet)&&(&fwdquiet)&&(&retquiet))begin
      if(tx.g_lane[0].reserved!=0 || tx.g_lane[1].reserved!=0 || tx.g_lane[0].sent!=0 || tx.g_lane[1].sent!=0)
       $fatal(1,"RESET_ACCOUNTING_DRAIN");
      $display("PASS_TRUECREDIT_CR_RESET crd=%0d cret=%0d fwd=%0d ret=%0d fresh_rows=%0d injectors=2 cycles=%0d",CRD,CRET,FWD,RET,ROWS,cycle);$finish;
     end
    end
    $fatal(1,"RESET_TEST_TIMEOUT epoch=%0d received=%0d/%0d",epoch,received[0],received[1]);
   end
   @(negedge clk);rst_n=0;issue_v=0;receiver_ready=0;replay=0;
   if(MUTANT==3 && line[0]==0 && line[1]==0)$fatal(1,"RESET_MUTANT_VACUOUS no credit in flight at reset");
   for(integer i=0;i<INJ;i=i+1)begin cnt[i]=0;wr[i]=0;rd[i]=0;if(MUTANT!=3)line[i]=0;end
   #1;
   if(!( &retquiet))$fatal(1,"RESET_STALE_RETURN_PIPE");
   if(!txquiet||!rxquiet||!( &hubquiet)||!( &fwdquiet)||(|txv)||(|rxv)||(|rv)||(|backv)||(|output_v))
    $fatal(1,"RESET_NOT_QUIET");
   if(tx.g_lane[0].reserved!=0 || tx.g_lane[1].reserved!=0 || tx.g_lane[0].sent!=0 || tx.g_lane[1].sent!=0)
    $fatal(1,"RESET_ACCOUNTING_CLEAR");
   repeat(4)@(negedge clk);rst_n=1;
  end
 end
endmodule
