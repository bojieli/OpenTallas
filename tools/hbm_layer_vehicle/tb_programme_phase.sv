`timescale 1fs/1fs
module tb;
`include "fixture.vh"
reg clk=0;
always #416500 clk=~clk;
reg rst_hub=0,rst_bod=0;
reg [1:0] rst_programme=0;
reg cfg_v=0,desc_v=0,launch_v=0;
reg [11:0] cfg_addr=0;
reg [255:0] cfg_data=0;
reg [0:0] controller_fault=0;
reg [2:0] mutant=0;
wire [1741:0] oc[0:1],nc[0:1];
wire [470:0] oi[0:1],ni[0:1];
wire oce[0:1],nce[0:1],oie[0:1],nie[0:1];
wire [4:0] os[0:1],ns[0:1];
wire [63:0] ow[0:1],nw[0:1],orr[0:1],nr[0:1];
wire [1:0] warm;
phase_pair_NW p0(.clk(clk),.rst_hub(rst_hub),.rst_programme(rst_programme[0]),.rst_bod(rst_bod),.cfg_v(cfg_v),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.launch_v(launch_v),.controller_fault(controller_fault),.mutant(mutant),.old_control(oc[0]),.new_control(nc[0]),.old_control_epoch(oce[0]),.new_control_epoch(nce[0]),.old_io(oi[0]),.new_io(ni[0]),.old_io_epoch(oie[0]),.new_io_epoch(nie[0]),.old_status(os[0]),.new_status(ns[0]),.old_writes(ow[0]),.new_writes(nw[0]),.old_reads(orr[0]),.new_reads(nr[0]),.warm(warm[0]));
phase_pair_NE p1(.clk(clk),.rst_hub(rst_hub),.rst_programme(rst_programme[1]),.rst_bod(rst_bod),.cfg_v(cfg_v),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.launch_v(launch_v),.controller_fault(controller_fault),.mutant(mutant),.old_control(oc[1]),.new_control(nc[1]),.old_control_epoch(oce[1]),.new_control_epoch(nce[1]),.old_io(oi[1]),.new_io(ni[1]),.old_io_epoch(oie[1]),.new_io_epoch(nie[1]),.old_status(os[1]),.new_status(ns[1]),.old_writes(ow[1]),.new_writes(nw[1]),.old_reads(orr[1]),.new_reads(nr[1]),.warm(warm[1]));
reg [267:0] frames[0:NF-1];
reg [1741:0] expected_ctl[0:3];
reg [470:0] expected_io[0:1];
reg [1741:0] ch[0:1][0:2];
reg [470:0] ih[0:1][0:2];
reg [4:0] sh[0:1][0:4];
integer co[0:1],cn[0:1],ioo[0:1],ion[0:1];
integer cyc=0,compare_count=0;
reg compare_enable=0,score_enable=0,epoch_check_enable=0;
time previous_clock=0;
integer mutarg=0;

always @(posedge clk)begin
 if(previous_clock!=0 && $time-previous_clock!=833000)$fatal(1,"CLOCK_PERIOD");
 previous_clock=$time;
 cyc=cyc+1;
 #1;
 for(integer r=0;r<2;r=r+1)begin
  for(integer h=2;h>0;h=h-1)begin ch[r][h]=ch[r][h-1];ih[r][h]=ih[r][h-1];end
  ch[r][0]=oc[r];ih[r][0]=oi[r];
  for(integer h=4;h>0;h=h-1)sh[r][h]=sh[r][h-1];
  sh[r][0]=os[r];
  if(epoch_check_enable)begin
   if(nce[r]!==oce[r] || nie[r]!==oie[r])$fatal(1,"EPOCH_PHASE r=%0d c=%0d old=%b%b new=%b%b",r,cyc,oce[r],oie[r],nce[r],nie[r]);
  end
  if(compare_enable && rst_hub && rst_bod && (&rst_programme) && (&warm))begin
   if(nce[r] && nc[r]!==ch[r][2])$fatal(1,"CONTROL_PHASE r=%0d c=%0d",r,cyc);
   if(nie[r] && ni[r]!==ih[r][2])$fatal(1,"IO_PHASE r=%0d c=%0d",r,cyc);
   if(ns[r]!==sh[r][4])$fatal(1,"STATUS_PHASE r=%0d c=%0d old4=%h new=%h",r,cyc,sh[r][4],ns[r]);
   compare_count=compare_count+1;
  end
  if(score_enable && rst_hub && rst_bod && (&rst_programme))begin
   if(oce[r] && (|oc[r]))begin
    if(oc[r]!==expected_ctl[co[r]%4])$fatal(1,"OLD_NATIVE_CONTROL r=%0d c=%0d row=%0d",r,cyc,co[r]);
    co[r]=co[r]+1;
   end
   if(nce[r] && (|nc[r]))begin
    if(nc[r]!==expected_ctl[cn[r]%4])$fatal(1,"NEW_NATIVE_CONTROL r=%0d c=%0d row=%0d",r,cyc,cn[r]);
    cn[r]=cn[r]+1;
   end
   if(oie[r] && (|oi[r]))begin
    if(oi[r]!==expected_io[ioo[r]%2])$fatal(1,"OLD_NATIVE_IO r=%0d c=%0d row=%0d",r,cyc,ioo[r]);
    ioo[r]=ioo[r]+1;
   end
   if(nie[r] && (|ni[r]))begin
    if(ni[r]!==expected_io[ion[r]%2])$fatal(1,"NEW_NATIVE_IO r=%0d c=%0d row=%0d",r,cyc,ion[r]);
    ion[r]=ion[r]+1;
   end
  end
 end
end

task wait_warm;
 integer done;
 begin
  done=0;
  begin: ww
   for(integer k=0;k<40;k=k+1)begin
    @(negedge clk);
    if((&warm)===1'b1)begin done=1;disable ww;end
   end
  end
  if(!done)$fatal(1,"NATIVE_RESET_WARM_TIMEOUT");
  $display("WARM c=%0d delivered_r10=%b native_warm=%b",cyc,rst_programme,warm);
 end
endtask

task drive_cfg(input [11:0] a,input [255:0] d);
 begin @(negedge clk);cfg_v=1;cfg_addr=a;cfg_data=d;desc_v=0;launch_v=0;end
endtask

task install;
 begin
  for(integer k=0;k<NF;k=k+1)drive_cfg(frames[k][267:256],frames[k][255:0]);
  drive_cfg(12'h800,PRM);
  $display("LAST_CFG_SENT c=%0d oldw=%0d,%0d neww=%0d,%0d",cyc,ow[0],ow[1],nw[0],nw[1]);
 end
endtask

task activate;
 begin
  @(negedge clk);cfg_v=0;desc_v=1;
  $display("DESCRIPTOR_SENT c=%0d oldready=%b,%b newready=%b,%b",cyc,os[0][1],os[1][1],ns[0][1],ns[1][1]);
  @(negedge clk);desc_v=0;
  repeat(3)@(negedge clk);
  launch_v=1;
  $display("LAUNCH_SENT c=%0d oldw=%0d,%0d neww=%0d,%0d",cyc,ow[0],ow[1],nw[0],nw[1]);
  @(negedge clk);launch_v=0;
  // Four control/two IO rows, fixed source pipeline and TAIL4 fit within64 edges;
  //128 is a functional observation horizon, not a wall-clock build deadline.
  repeat(128)@(negedge clk);
 end
endtask

task check_runs(input integer n);
 begin
  for(integer r=0;r<2;r=r+1)begin
   if(co[r]!=4*n || cn[r]!=4*n || ioo[r]!=2*n || ion[r]!=2*n)$fatal(1,"NATIVE_ROW_COUNTS r=%0d runs=%0d ctl=%0d/%0d io=%0d/%0d",r,n,co[r],cn[r],ioo[r],ion[r]);
   if(os[r][0] || ns[r][0])$fatal(1,"NATIVE_ACTIVE_STUCK r=%0d",r);
   if(os[r][2] || ns[r][2] || os[r][4] || ns[r][4])$fatal(1,"NATIVE_FAULT r=%0d old=%h new=%h",r,os[r],ns[r]);
  end
 end
endtask

task pulse_abort_reset;
 begin
  @(negedge clk);cfg_v=0;desc_v=0;launch_v=0;compare_enable=0;score_enable=0;
  #100000;rst_hub=0;
  #1;
  if(p0.new_bod.prog_old_hub_rst_n!==1'b0 || p1.new_bod.prog_old_hub_rst_n!==1'b0)$fatal(1,"ASYNC_RESET_ASSERTION hub delivery changed at nonclock time");
  #10000;rst_programme=0;
  #1;
  if(p0.new_bod.prog_old_r10_rst_n!==1'b0 || p1.new_bod.prog_old_r10_rst_n!==1'b0)$fatal(1,"ASYNC_RESET_ASSERTION real regional r10 delivery changed");
  repeat(2)@(negedge clk);rst_bod=0;
  repeat(66)@(negedge clk);
  if(os[0][1] || os[1][1] || ns[0][1] || ns[1][1])$fatal(1,"RESET_STALE_READY");
  rst_hub=1;
  repeat(2)@(negedge clk);rst_bod=1;
  repeat(2)@(negedge clk);rst_programme[0]=1;
  @(negedge clk);rst_programme[1]=1;
  wait_warm();compare_enable=1;
 end
endtask

reg [63:0] warm_ow[0:1],warm_nw[0:1],prefix_ow[0:1],prefix_nw[0:1];
initial begin
 $readmemh("frames.mem",frames);$readmemh("ctl.mem",expected_ctl);$readmemh("io.mem",expected_io);
 if($value$plusargs("MUT=%d",mutarg))mutant=mutarg[2:0];
 for(integer r=0;r<2;r=r+1)begin co[r]=0;cn[r]=0;ioo[r]=0;ion[r]=0;end
 repeat(66)@(negedge clk);
 rst_hub=1;
 repeat(2)@(negedge clk);rst_bod=1;
 repeat(2)@(negedge clk);rst_programme[0]=1;
 @(negedge clk);rst_programme[1]=1;
 wait_warm();compare_enable=1;score_enable=1;epoch_check_enable=1;
 install();activate();check_runs(1);
 for(integer r=0;r<2;r=r+1)begin warm_ow[r]=ow[r];warm_nw[r]=nw[r];end
 drive_cfg(12'h800,PRM);activate();check_runs(2);
 for(integer r=0;r<2;r=r+1)begin
  if(ow[r]!=warm_ow[r] || nw[r]!=warm_nw[r])$fatal(1,"WARM_RELAUNCH_REWROTE_SRAM r=%0d",r);
  prefix_ow[r]=ow[r];prefix_nw[r]=nw[r];
 end
 $display("WARM_RELAUNCH_RETAINED_SRAM c=%0d writes=%0d/%0d,%0d/%0d",cyc,ow[0],nw[0],ow[1],nw[1]);
 // Start a real prefix overwrite and reset before its newest CFG packets can
 // traverse the actual input/collar/native write pipeline.
 for(integer k=0;k<8;k=k+1)drive_cfg(frames[k][267:256],frames[k][255:0]^(k==0?256'd0:256'h20000));
 @(negedge clk);cfg_v=0;
 $display("INFLIGHT_CFG_ABORT c=%0d sent=7words oldcommits=%0d,%0d newcommits=%0d,%0d",cyc,ow[0]-prefix_ow[0],ow[1]-prefix_ow[1],nw[0]-prefix_nw[0],nw[1]-prefix_nw[1]);
 if(nw[0]-prefix_nw[0]>=7 || nw[1]-prefix_nw[1]>=7)$fatal(1,"FIXTURE_DID_NOT_HAVE_INFLIGHT_CFG");
 pulse_abort_reset();
 // Retained SRAM may contain a partially committed overwrite. Reset clears
 // collar metadata; it is not a commit ACK or permission to reuse that image.
 if(os[0][1] || os[1][1] || ns[0][1] || ns[1][1])$fatal(1,"ABORT_RETAINED_IMAGE_WAS_ASSUMED_READY");
 activate();
 if(co[0]!=8 || co[1]!=8 || cn[0]!=8 || cn[1]!=8 || ioo[0]!=4 || ioo[1]!=4 || ion[0]!=4 || ion[1]!=4)$fatal(1,"ABORTED_IMAGE_RELAUNCHED");
 if(!os[0][2] || !os[1][2] || !ns[0][2] || !ns[1][2])$fatal(1,"NATIVE_PROTOCOL_DID_NOT_REJECT_POSTRESET_LAUNCH");
 $display("ABORT_REQUIRES_REINSTALL c=%0d oldstatus=%h,%h newstatus=%h,%h",cyc,os[0],os[1],ns[0],ns[1]);
 pulse_abort_reset();score_enable=1;
 install();activate();check_runs(3);
 $display("PASS_NATIVE_PROGRAMME_PHASE clock_fs=833000 checks=%0d ctl=%0d/%0d,%0d/%0d io=%0d/%0d,%0d/%0d writes=%0d/%0d,%0d/%0d reads=%0d/%0d,%0d/%0d cycles=%0d",compare_count,co[0],cn[0],co[1],cn[1],ioo[0],ion[0],ioo[1],ion[1],ow[0],nw[0],ow[1],nw[1],orr[0],nr[0],orr[1],nr[1],cyc);
 $finish;
end
endmodule
