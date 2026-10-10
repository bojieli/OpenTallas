`timescale 1ns/1ps
// credit-ready (2026-10-08): mechanism bench for ot_ha2_truecredit_receiver_p #(.CREDIT(1)).
// Same sender, hub flight, forward/return links and source rows as tb_ha2_truecredit; the same-cycle ready is
// replaced by a consumer with a CRD-deep buffer that pops on the old ready pattern and returns one credit pulse per
// pop after CRET cycles. Checks: data order/value at the consumer, consumer buffer never overflows, the credit limit
// binds (coverage), sender stalls (coverage), all credits and tags home at the end.
// MUTANT 1-4 as tb_ha2_truecredit (sender reservations, retire id, forward id, read ring) passed to the DUTs;
// MUTANT 5 = receiver starts one credit above CRD (over-issue); MUTANT 6 = the consumer returns one spurious credit.
module tb_ha2_truecredit_cr #(
 parameter integer FWD=7, RET=7, MUTANT=0, ROWS=192, TAGW=16, REG=0, CRD=8, CRET=3
);
 localparam integer W=544,INJ=2;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[INJ-1:0] issue_v=0,credit=0;
 reg[INJ*W-1:0] source_data=0;
 wire[INJ-1:0] issue_ready,hub_v,txv,rxv,rv,backv,output_v;
 wire[INJ*W-1:0] hub_data,txdata,rxdata,output_data;
 wire[INJ*TAGW-1:0] txtag,rxtag,rtag,backtag;
 wire txquiet,rxquiet,txfault,rxfault;
 integer issued[0:INJ-1],received[0:INJ-1],cnt[0:INJ-1],wr[0:INJ-1],rd[0:INJ-1];
 reg[W-1:0] buffer[0:INJ-1][0:63];
 reg[63:0] line[0:INJ-1];
 integer cycle=0,stalls=0,cr_stalls=0,first_issue=-1,last_receive=-1,spurious=0;
 function automatic[W-1:0] row(input integer lane,n);
  for(integer j=0;j<W/32;j=j+1)row[j*32+:32]=32'h7f023456^(lane<<24)^(n<<8)^j;
 endfunction
 for(genvar i=0;i<INJ;i=i+1)begin:g_lane
  ot_ha2_delay_quiet #(.W(W),.D(35)) u_hub
   (.clk(clk),.rst_n(rst_n),.v_in(issue_v[i]),.d_in(source_data[i*W+:W]),
    .v_out(hub_v[i]),.d_out(hub_data[i*W+:W]),.quiet());
  wire[W+TAGW-1:0] frame;
  if(FWD==0)begin
   assign rxv[i]=txv[i];assign frame={txtag[i*TAGW+:TAGW],txdata[i*W+:W]};
  end else begin
   ot_ha2_delay_quiet #(.W(W+TAGW),.D(FWD)) u_forward
    (.clk(clk),.rst_n(rst_n),.v_in(txv[i]),.d_in({txtag[i*TAGW+:TAGW],txdata[i*W+:W]}),
     .v_out(rxv[i]),.d_out(frame),.quiet());
  end
  assign rxdata[i*W+:W]=frame[W-1:0];
  assign rxtag[i*TAGW+:TAGW]=frame[W+:TAGW] ^ ((MUTANT==3)?TAGW'(1):TAGW'(0));
  if(RET==0)begin assign backv[i]=rv[i];assign backtag[i*TAGW+:TAGW]=rtag[i*TAGW+:TAGW];end
  else begin
   ot_ha2_delay_quiet #(.W(TAGW),.D(RET)) u_return
    (.clk(clk),.rst_n(rst_n),.v_in(rv[i]),.d_in(rtag[i*TAGW+:TAGW]),
     .v_out(backv[i]),.d_out(backtag[i*TAGW+:TAGW]),.quiet());
  end
 end
 ot_ha2_truecredit_sender #(.W(W),.INJ(INJ),.TAGW(TAGW),.MUTANT((MUTANT<=4)?MUTANT:0),.REG(REG)) tx
  (.clk(clk),.rst_n(rst_n),.issue_v(issue_v),.arrival_v(hub_v),.arrival_data(hub_data),
   .return_v(backv),.return_tag(backtag),.issue_ready(issue_ready),
   .send_v(txv),.send_data(txdata),.send_tag(txtag),.quiet(txquiet),.fault(txfault));
 ot_ha2_truecredit_receiver_p #(.W(W),.INJ(INJ),.TAGW(TAGW),.MUTANT((MUTANT==6)?0:MUTANT),.CREDIT(1),.CRD(CRD)) rx
  (.clk(clk),.rst_n(rst_n),.arrival_v(rxv),.arrival_data(rxdata),.arrival_tag(rxtag),
   .receiver_ready(credit),.send_v(output_v),.send_data(output_data),
   .return_v(rv),.return_tag(rtag),.quiet(rxquiet),.fault(rxfault));
 initial begin
  if(CRD>64||CRET>62)$fatal(1,"TRUECREDIT_CR_BENCH_RANGE");
  for(integer i=0;i<INJ;i=i+1)begin issued[i]=0;received[i]=0;cnt[i]=0;wr[i]=0;rd[i]=0;line[i]=0;end
  repeat(4)@(negedge clk);rst_n=1;
  for(cycle=0;cycle<ROWS*20+1000+4*(FWD+RET+CRET);cycle=cycle+1)begin
   @(negedge clk);
   for(integer i=0;i<INJ;i=i+1)begin
    reg pop;
    pop=cnt[i]>0 && ((i==0)?(cycle>=220 && cycle%2==0):(cycle>=500 && cycle%7<3));
    if(pop)begin
     if(buffer[i][rd[i]]!==row(i,received[i]))$fatal(1,"TRUECREDIT_DATA row=%0d lane=%0d",received[i],i);
     rd[i]=(rd[i]+1)%CRD;cnt[i]=cnt[i]-1;received[i]=received[i]+1;last_receive=cycle;
    end
    if(MUTANT==6 && i==0 && cycle==301 && !pop)begin pop=1;spurious=1;end
    line[i]={line[i][62:0],pop};
    credit[i]=line[i][CRET];
    issue_v[i]=issue_ready[i]&&issued[i]<ROWS;
    source_data[i*W+:W]=row(i,issued[i]);
    if(!issue_ready[i]&&issued[i]<ROWS)stalls=stalls+1;
   end
   if(!rx.g_lane[0].empty && !rx.g_lane[0].cr_ok)cr_stalls=cr_stalls+1;
   @(posedge clk);
   for(integer i=0;i<INJ;i=i+1)if(issue_v[i])begin
    issued[i]=issued[i]+1;if(first_issue<0)first_issue=cycle;
   end
   #1;
   if(txfault||rxfault)$fatal(1,"TRUECREDIT_FAULT tx=%0d rx=%0d cycle=%0d",txfault,rxfault,cycle);
   for(integer i=0;i<INJ;i=i+1)if(output_v[i])begin
    if(cnt[i]>=CRD)$fatal(1,"TRUECREDIT_CONSUMER_OVF lane=%0d cycle=%0d",i,cycle);
    buffer[i][wr[i]]=output_data[i*W+:W];wr[i]=(wr[i]+1)%CRD;cnt[i]=cnt[i]+1;
   end
   if(received[0]==ROWS&&received[1]==ROWS&&txquiet&&rxquiet&&line[0]==0&&line[1]==0)begin
    if(stalls==0)$fatal(1,"TRUECREDIT_NO_STALL_COVERAGE");
    if(cr_stalls==0)$fatal(1,"TRUECREDIT_NO_CREDIT_STALL_COVERAGE");
    $display("PASS_TRUECREDIT_CR rows=%0d injectors=2 width=544 fwd=%0d ret=%0d crd=%0d cret=%0d stalls=%0d credit_stalls=%0d elapsed=%0d credit_drain=%0d",ROWS,FWD,RET,CRD,CRET,stalls,cr_stalls,last_receive-first_issue+1,cycle-last_receive);$finish;
   end
  end
  $fatal(1,"TRUECREDIT_TIMEOUT received=%0d/%0d",received[0],received[1]);
 end
endmodule
