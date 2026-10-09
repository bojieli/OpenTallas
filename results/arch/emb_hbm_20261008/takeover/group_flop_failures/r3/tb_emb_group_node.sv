`timescale 1ps/1fs
module tb_emb_group_node;
 parameter integer PCBASE=0,MODE=0;
 reg clk=0,rst_n=0;always #416.666667 clk=~clk;
 reg [349:0] cmd_i=0;wire [349:0] cmd_o,off_cmd_o;
 reg [259:0] ret[0:7];wire [287:0] cmd[0:7],off_cmd[0:7];
 reg [265:0] upstream_i=0;wire upstream_credit,off_up_credit;
 wire [265:0] reply_o,off_reply;reg downstream_credit=0;wire fault,off_fault;
 reg [349:0] expected_trunk=0;
 reg [264:0] expected[0:8][0:31];integer accepted_at[0:8][0:31];
 integer wr[0:8],rd[0:8],pc_credit[0:7],wait_service[0:8];
 integer cyc=0,total=0,up_credit=8,pending_ack=0,consume=0,max_count=0,max_outstanding=0,max_wait=0,credit_stalls=0,min_latency=100000,max_latency=0;
 integer i,j,k,src,elapsed,uptag;
 ot_qfd_emb_group_node #(.ENABLE(1),.PCBASE(PCBASE)) dut(.clk(clk),.rst_n(rst_n),.cmd_i(cmd_i),.cmd_o(cmd_o),.upstream_i(upstream_i),.upstream_credit(upstream_credit),.reply_o(reply_o),.downstream_credit(downstream_credit),.fault(fault),.cmd0(cmd[0]),.ret0(ret[0]),.cmd1(cmd[1]),.ret1(ret[1]),.cmd2(cmd[2]),.ret2(ret[2]),.cmd3(cmd[3]),.ret3(ret[3]),.cmd4(cmd[4]),.ret4(ret[4]),.cmd5(cmd[5]),.ret5(ret[5]),.cmd6(cmd[6]),.ret6(ret[6]),.cmd7(cmd[7]),.ret7(ret[7]));
 ot_qfd_emb_group_node #(.PCBASE(PCBASE)) disabled(.clk(clk),.rst_n(rst_n),.cmd_i(cmd_i),.cmd_o(off_cmd_o),.upstream_i(upstream_i),.upstream_credit(off_up_credit),.reply_o(off_reply),.downstream_credit(downstream_credit),.fault(off_fault),.cmd0(off_cmd[0]),.ret0(ret[0]),.cmd1(off_cmd[1]),.ret1(ret[1]),.cmd2(off_cmd[2]),.ret2(ret[2]),.cmd3(off_cmd[3]),.ret3(ret[3]),.cmd4(off_cmd[4]),.ret4(ret[4]),.cmd5(off_cmd[5]),.ret5(ret[5]),.cmd6(off_cmd[6]),.ret6(ret[6]),.cmd7(off_cmd[7]),.ret7(ret[7]));
 function automatic [259:0] event_packet(input integer lane,input integer ordinal,input bit credit);
  reg [255:0] payload;begin payload={8{32'(32'h9e3779b9*lane+32'h7f4a7c15*ordinal+32'h89abcdef)}};
   event_packet={credit,!credit,1'(ordinal==5),1'(ordinal==4),payload};end
 endfunction
 always @(posedge clk) begin
  cyc=cyc+1;
  if(rst_n)begin
   if({off_cmd_o,off_reply,off_up_credit,off_fault}!==0)$fatal(1,"FAIL default-off group");
   if(!fault)begin
    if(cmd_o!==expected_trunk)$fatal(1,"FAIL registered shared350 command");
    for(k=0;k<8;k=k+1)begin
     if(cmd[k]!=={expected_trunk[318+PCBASE+k],expected_trunk[286+PCBASE+k],expected_trunk[285:0]})$fatal(1,"FAIL local command lane=%0d",k);
     if(off_cmd[k]!==0)$fatal(1,"FAIL default-off local command");
     if(cmd[k][287])begin
      if(pc_credit[k]==0)$fatal(1,"FAIL producer spent unreturned command credit");
      pc_credit[k]=pc_credit[k]-1;
     end
     if(ret[k][259]||ret[k][258])begin expected[k][wr[k]]={5'(PCBASE+k),ret[k]};accepted_at[k][wr[k]]=cyc;wr[k]=wr[k]+1;end
    end
    if(upstream_i[265])begin
     if(up_credit==0 && MODE!=2)$fatal(1,"FAIL producer spent unreturned transit credit");
     up_credit=up_credit-1;expected[8][wr[8]]=upstream_i[264:0];accepted_at[8][wr[8]]=cyc;wr[8]=wr[8]+1;
    end
    if(reply_o[265])begin
     src=(reply_o[264:260]>=PCBASE && reply_o[264:260]<PCBASE+8) ? reply_o[264:260]-PCBASE : 8;
     if(rd[src]>=wr[src] || reply_o[264:0]!==expected[src][rd[src]])$fatal(1,"FAIL tagged packet/data/order src=%0d ordinal=%0d",src,rd[src]);
     elapsed=cyc-accepted_at[src][rd[src]];if(elapsed<min_latency)min_latency=elapsed;if(elapsed>max_latency)max_latency=elapsed;
     if(upstream_credit!==(src==8))$fatal(1,"FAIL upstream credit before/without actual retirement");
     if(src<8 && reply_o[259])begin pc_credit[src]=pc_credit[src]+1;if(pc_credit[src]>4)$fatal(1,"FAIL duplicate command credit");end
     rd[src]=rd[src]+1;total=total+1;pending_ack=pending_ack+1;
    end else if(upstream_credit)$fatal(1,"FAIL fabricated upstream credit");
    if(upstream_credit)begin up_credit=up_credit+1;if(up_credit>8)$fatal(1,"FAIL duplicate transit credit");end
    for(k=0;k<9;k=k+1)begin
     if(dut.enabled.used[k]>max_count)max_count=dut.enabled.used[k];
     if(dut.enabled.pop && dut.enabled.used[k]!=0)begin
      wait_service[k]=wait_service[k]+1;if(wait_service[k]>max_wait)max_wait=wait_service[k];
      if(dut.enabled.selected==k)wait_service[k]=0;
      else if(wait_service[k]>9)$fatal(1,"FAIL fair9source RR bound");
     end
    end
    for(k=0;k<8;k=k+1)if(dut.enabled.outstanding[k]>max_outstanding)max_outstanding=dut.enabled.outstanding[k];
    if(dut.enabled.have && dut.enabled.credits==0)credit_stalls=credit_stalls+1;
   end else if(MODE!=2 && MODE!=3 && MODE!=4)$fatal(1,"FAIL unexpected node fault");
   expected_trunk<=cmd_i;
  end
 end
 always @(negedge clk)begin #1;downstream_credit=0;if(consume && pending_ack>0)begin downstream_credit=1;pending_ack=pending_ack-1;end end
 task step;begin @(negedge clk);#2;end endtask
 initial begin
  uptag=PCBASE==24 ? 0 : 31;
  for(i=0;i<9;i=i+1)begin wr[i]=0;rd[i]=0;wait_service[i]=0;end
  for(i=0;i<8;i=i+1)begin ret[i]=0;pc_credit[i]=4;end
  repeat(5)step();rst_n=1;repeat(3)step();
  if(MODE==3)begin
   ret[0]=event_packet(0,0,1);step();ret[0]=0;repeat(2)step();
   if(!fault || reply_o[265] || upstream_credit)$fatal(1,"FAIL duplicate raw credit guard");
   $display("PASS group duplicate-credit guard fault withholds release");$finish;
  end
  // Spend exactly eight real downstream slots, withholding their ACKs.
  for(j=0;j<8;j=j+1)begin upstream_i={1'b1,5'(uptag),event_packet(8,j,0)};step();end
  upstream_i=0;wait(total==8);step();
  if(dut.enabled.credits!=0 || pending_ack!=8 || up_credit!=8)$fatal(1,"FAIL initial prepaid-credit accounting");
  for(j=0;j<4;j=j+1)begin cmd_i={32'(32'hff<<PCBASE),32'(32'hff<<PCBASE),{1'b1,5'(j*7),5'(j*13),19'(j*743),{8{32'(32'h9e3779b9*j ^ 32'hab5fe724)}}}};step();end
  cmd_i=0;repeat(3)step();
  if(max_outstanding!=4)$fatal(1,"FAIL did not reach actual4command window");
  if(MODE==4)begin
   cmd_i={32'(32'hff<<PCBASE),32'b0,286'b0};step();cmd_i=0;repeat(3)step();
   if(!fault||reply_o[265]||upstream_credit)$fatal(1,"FAIL fifth-command guard");
   $display("PASS group fifth-command guard actualwindow4");$finish;
  end
  // Four credit pulses + four responses/PC stress all eight physical slots.
  // This synthetic stress is stronger than the serialized two-response fetch.
  for(j=0;j<8;j=j+1)begin
   for(i=0;i<8;i=i+1)ret[i]=event_packet(i,j,j<4);
   upstream_i={1'b1,5'(uptag),event_packet(8,8+j,0)};step();
  end
  for(i=0;i<8;i=i+1)ret[i]=0;upstream_i=0;step();
  for(i=0;i<9;i=i+1)if(dut.enabled.used[i]!=8)$fatal(1,"FAIL FIFO depth/reservation source=%0d used=%0d",i,dut.enabled.used[i]);
  if(up_credit!=0)$fatal(1,"FAIL transit capacity is not8prepaid slots");
  if(MODE==2)begin
   // Deliberate bad producer bypasses its zero-credit check only in this fault case.
   upstream_i={1'b1,5'(uptag),event_packet(8,16,0)};
   @(posedge clk);#2;upstream_i=0;repeat(2)step();
   if(!fault||reply_o[265]||upstream_credit||dut.enabled.used[8]!=8)$fatal(1,"FAIL ninth-entry overflow guard");
   $display("PASS group ninth-entry overflow guard no invented slot/credit");$finish;
  end
  if(MODE==1)dut.enabled.mem[0][0]=~dut.enabled.mem[0][0];
  consume=1;
  wait(total==80);wait(pending_ack==0);repeat(2)step();consume=0;downstream_credit=0;
  if(fault||max_count!=8||max_outstanding!=4||up_credit!=8||dut.enabled.credits!=8||pending_ack!=0)$fatal(1,"FAIL final finite-flow accounting fault=%0d maxFIFO=%0d maxcmd=%0d upcr=%0d downcr=%0d pending=%0d",fault,max_count,max_outstanding,up_credit,dut.enabled.credits,pending_ack);
  for(i=0;i<8;i=i+1)if(pc_credit[i]!=4||rd[i]!=8||dut.enabled.used[i]!=0)$fatal(1,"FAIL final PC accounting lane=%0d",i);
  if(rd[8]!=16||max_wait>9||min_latency!=2)$fatal(1,"FAIL service/latency bound");
  rst_n=0;cmd_i=0;upstream_i=0;step();
  if({cmd_o,reply_o,upstream_credit,fault}!==0)$fatal(1,"FAIL reset flush");
  $display("PASS group PCBASE=%0d packets80 local64 upstream16 full265bits HBMflagsCEUEpreserved defaultoff resetflush maxFIFO8 maxcommands4 maxRRwait=%0d creditstallcycles=%0d ingress_to_sink_min=%0d max=%0d core833.333334ps",PCBASE,max_wait,credit_stalls,min_latency,max_latency);$finish;
 end
 initial begin repeat(4096)@(posedge clk);$fatal(1,"FAIL finite80packet gate completion, expected bound4096edges");end
endmodule
