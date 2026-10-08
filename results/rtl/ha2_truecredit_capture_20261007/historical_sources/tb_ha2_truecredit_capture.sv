`timescale 1ns/1ps
module tb_ha2_truecredit_capture #(
 parameter integer FWD=7, RET=7, MUTANT=0, ROWS=192, TAGW=16
);
 localparam integer W=544,INJ=2;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0;reg[INJ-1:0] issue_v=0,receiver_ready=0;
 reg[INJ*W-1:0] source_data=0;
 wire[INJ-1:0] issue_ready,hub_v,txv,rxv,rv,backv,output_v;
 wire[INJ*W-1:0] hub_data,txdata,rxdata,output_data;
 wire[INJ*TAGW-1:0] txtag,rxtag,rtag,backtag;
 wire txquiet,rxquiet,txfault,rxfault;
 integer issued[0:INJ-1],received[0:INJ-1];
 wire[INJ-1:0] split_pre_v,split_v,ref_ready,ref_v;
 wire[INJ*W-1:0] split_pre_data,split_data,ref_data;
 wire[INJ*TAGW-1:0] ref_tag;
 wire ref_quiet,ref_fault;
 reg[INJ*W-1:0] poisoned;
 reg[INJ*W-1:0] previous_ref=0,previous_new=0;
 integer ref_toggles=0,new_toggles=0,invalid_cycles=0;
 integer cycle=0,stalls=0,first_issue=-1,last_receive=-1;
 function automatic[W-1:0] row(input integer lane,n);
  for(integer j=0;j<W/32;j=j+1)row[j*32+:32]=32'h7f023456^(lane<<24)^(n<<8)^j;
 endfunction
 for(genvar i=0;i<INJ;i=i+1)begin:g_lane
  ot_ha2_delay_quiet #(.W(W),.D(35)) u_hub
   (.clk(clk),.rst_n(rst_n),.v_in(issue_v[i]),.d_in(source_data[i*W+:W]),
    .v_out(hub_v[i]),.d_out(hub_data[i*W+:W]),.quiet());
  ot_ha2_delay_quiet #(.W(W),.D(34)) u_split_ring
   (.clk(clk),.rst_n(rst_n),.v_in(issue_v[i]),.d_in(source_data[i*W+:W]),
    .v_out(split_pre_v[i]),.d_out(split_pre_data[i*W+:W]),.quiet());
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
 ot_ha2_hub_launch_single #(.W(W),.INJ(INJ)) launch
  (.clk(clk),.rst_n(rst_n),.v_in(split_pre_v),.d_in(split_pre_data),
   .v_out(split_v),.d_out(split_data),.quiet());
 always @* for(integer i=0;i<INJ;i=i+1)
  poisoned[i*W+:W]=split_v[i]?split_data[i*W+:W]:{W{cycle[0]}};
 ot_ha2_truecredit_sender #(.W(W),.INJ(INJ),.TAGW(TAGW)) reference_tx
  (.clk(clk),.rst_n(rst_n),.issue_v(issue_v),.arrival_v(hub_v),.arrival_data(hub_data),
   .return_v(backv),.return_tag(backtag),.issue_ready(ref_ready),
   .send_v(ref_v),.send_data(ref_data),.send_tag(ref_tag),.quiet(ref_quiet),.fault(ref_fault));
 ot_ha2_truecredit_sender_capture #(.W(W),.INJ(INJ),.TAGW(TAGW),.CAPTURE_ALWAYS(1)) tx
  (.clk(clk),.rst_n(rst_n),.issue_v(issue_v),.arrival_v(split_v),.arrival_data(poisoned),
   .return_v(backv),.return_tag(backtag),.issue_ready(issue_ready),
   .send_v(txv),.send_data(txdata),.send_tag(txtag),.quiet(txquiet),.fault(txfault));
 ot_ha2_truecredit_receiver #(.W(W),.INJ(INJ),.TAGW(TAGW),.MUTANT(MUTANT)) rx
  (.clk(clk),.rst_n(rst_n),.arrival_v(rxv),.arrival_data(rxdata),.arrival_tag(rxtag),
   .receiver_ready(receiver_ready),.send_v(output_v),.send_data(output_data),
   .return_v(rv),.return_tag(rtag),.quiet(rxquiet),.fault(rxfault));
 initial begin
  for(integer i=0;i<INJ;i=i+1)begin issued[i]=0;received[i]=0;end
  repeat(4)@(negedge clk);rst_n=1;
  for(cycle=0;cycle<ROWS*20+1000+4*(FWD+RET);cycle=cycle+1)begin
   @(negedge clk);
   receiver_ready[0]=cycle>=220 && cycle%2==0;
   receiver_ready[1]=cycle>=500 && cycle%7<3;
   for(integer i=0;i<INJ;i=i+1)begin
    issue_v[i]=issue_ready[i]&&issued[i]<ROWS && (cycle%11!=i);
    source_data[i*W+:W]=row(i,issued[i]);
    if(!issue_ready[i]&&issued[i]<ROWS)stalls=stalls+1;
   end
   @(posedge clk);
   for(integer i=0;i<INJ;i=i+1)if(issue_v[i])begin
    issued[i]=issued[i]+1;if(first_issue<0)first_issue=cycle;
   end
   if(split_v!==hub_v)$fatal(1,"SPLIT_VALID_TIMING");
   for(integer i=0;i<INJ;i=i+1)if(hub_v[i] && split_data[i*W+:W]!==hub_data[i*W+:W])$fatal(1,"SPLIT_PAYLOAD");
   #1;
   if({ref_ready,ref_v,ref_tag,ref_quiet,ref_fault}!=={issue_ready,txv,txtag,txquiet,txfault})$fatal(1,"CAPTURE_CONTROL_TIMING");
   for(integer i=0;i<INJ;i=i+1)begin
    if(txv[i] && ref_data[i*W+:W]!==txdata[i*W+:W])$fatal(1,"CAPTURE_VALID_DATA");
    if(!txv[i])invalid_cycles=invalid_cycles+1;
   end
   if(!$isunknown(ref_data) && !$isunknown(previous_ref))ref_toggles=ref_toggles+$countones(ref_data^previous_ref);
   if(!$isunknown(txdata) && !$isunknown(previous_new))new_toggles=new_toggles+$countones(txdata^previous_new);
   previous_ref=ref_data;previous_new=txdata;
   if(txfault||rxfault)$fatal(1,"TRUECREDIT_FAULT tx=%0d rx=%0d cycle=%0d",txfault,rxfault,cycle);
   for(integer i=0;i<INJ;i=i+1)if(output_v[i])begin
    if(!receiver_ready[i])$fatal(1,"TRUECREDIT_NO_READY");
    if(output_data[i*W+:W]!==row(i,received[i]))$fatal(1,"TRUECREDIT_DATA row=%0d lane=%0d",received[i],i);
    received[i]=received[i]+1;last_receive=cycle;
   end
   if(received[0]==ROWS&&received[1]==ROWS&&txquiet&&rxquiet)begin
    if(stalls==0)$fatal(1,"TRUECREDIT_NO_STALL_COVERAGE");
    $display("PASS_TRUECREDIT rows=%0d injectors=2 width=544 fwd=%0d ret=%0d stalls=%0d elapsed=%0d credit_drain=%0d",ROWS,FWD,RET,stalls,last_receive-first_issue+1,cycle-last_receive);$display("CAPTURE_ACTIVITY baseline_toggles=%0d candidate_toggles=%0d invalid_lane_cycles=%0d",ref_toggles,new_toggles,invalid_cycles);$finish;
   end
  end
  $fatal(1,"TRUECREDIT_TIMEOUT received=%0d/%0d",received[0],received[1]);
 end
endmodule
