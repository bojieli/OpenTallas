`timescale 1ps/1fs
`default_nettype none
module tb_hbm_svc_wb_pipeline_cdc;
 reg stream_clk=0,hbm_clk=0;initial forever begin #416.666 stream_clk=1;#416.667 stream_clk=0;end
 initial begin #173;forever #512 hbm_clk=~hbm_clk;end
 reg stream_rst_n=0,hbm_rst_n=0,reserve_v=0,reserve_bank=0;
 reg [15:0] reserve_epoch=0;reg [31:0] reserve_base=0;reg [11:0] reserve_total=0;
 wire reserve_ready;reg fill_start=0,fill_start_bank=0;reg [15:0] fill_start_epoch=0;reg [2311:0] wd=0;
 wire fill_done,done_v,done_bank,fault;wire [15:0] done_epoch;wire [11:0] done_sectors;wire [1:0] bank_owned;
 wire [31:0] k_v,k_we,k_wr_done;reg [31:0] k_rdy=0;wire [959:0] k_addr;
 wire [127:0] k_len;wire [543:0] k_tag;wire [8191:0] k_wdata;wire [1023:0] k_wstrb;
 wire [3:0] stream_fifo_clk={4{stream_clk}};
 ot_hbm_svc_wb_cutthrough_cdc dut(.*);
 localparam [31:0] BASE0=32'h00015342,BASE1=32'h00028597;
 reg [31:0] pending=0,stalled=0;integer queued[0:31];reg [31:0] queue_sector[0:31][0:63];integer qrd[0:31],qwr[0:31];integer simultaneous=0,max_queued=0;integer early_reads=0;integer reads=0,copy_overlap=0,max_parallel=0,parallel_now;integer delay_count[0:31];reg [959:0] stalled_addr;reg [8191:0] stalled_data;
 reg [2687:0] seen=0;integer cycle=0,accepted=0,acked=0,acked0=0,acked1=0,blocks_done=0,input_cycles=0,expected0=640,pressure_cycles=0;
 reg [31:0] pending_sector[0:31];integer p,idx;reg [29:0] sec;
 real first_accept[0:1],last_accept[0:1],last_ack[0:1];reg [1:0] first_seen=0;integer hbm_edges=0,stream_edges=0;
 always @(posedge stream_clk)if(dut.srst)begin
  parallel_now=0;for(integer j=0;j<32;j=j+1)begin
   if(dut.mem_read[j])begin reads=reads+1;if(dut.filling)early_reads=early_reads+1;parallel_now=parallel_now+1;end
   if(dut.mem_read[j]&&dut.fifo_we[j])copy_overlap=copy_overlap+1;
  end
  if(parallel_now>max_parallel)max_parallel=parallel_now;
  stream_edges=stream_edges+1;if(|dut.fifo_full)pressure_cycles=pressure_cycles+1;end
 always @(posedge hbm_clk)if(dut.hrst)hbm_edges=hbm_edges+1;
 function automatic [4:0] hash_pc(input [29:0] s);begin hash_pc=s[6:2]^s[11:7]^s[16:12];end endfunction
 function automatic [255:0] data_for(input [31:0] sector);integer j;begin for(j=0;j<8;j=j+1)data_for[32*j+:32]=32'hacf00127^(sector*32'h10021)^(j*32'h1234567);end endfunction
 genvar q;generate for(q=0;q<32;q=q+1)begin:g_done
  assign k_wr_done[q]=(queued[q]!=0)&&delay_count[q]==0;
 end endgenerate
 always @*begin for(integer j=0;j<32;j=j+1)k_rdy[j]=$test$plusargs("fast")?1:((cycle+j*3)%11)>=3;end
 always @(posedge hbm_clk)begin
  if(!dut.hrst)begin pending<=0;stalled<=0;cycle<=0;accepted=0;acked=0;acked0=0;acked1=0;seen=0;for(p=0;p<32;p=p+1)begin delay_count[p]<=0;pending_sector[p]<=0;queued[p]=0;qrd[p]=0;qwr[p]=0;end end
  else begin
   cycle<=cycle+1;
   for(p=0;p<32;p=p+1)begin
    if(stalled[p]&&(!k_v[p]||k_addr[p*30+:30]!==stalled_addr[p*30+:30]||k_wdata[p*256+:256]!==stalled_data[p*256+:256]))$fatal(1,"PHY request not held under backpressure pc=%0d",p);
    stalled[p]<=k_v[p]&&!k_rdy[p];stalled_addr[p*30+:30]<=k_addr[p*30+:30];stalled_data[p*256+:256]<=k_wdata[p*256+:256];
    if(queued[p]!=0&&delay_count[p]>0)delay_count[p]<=delay_count[p]-1;
    if(k_wr_done[p])begin
     pending_sector[p]=queue_sector[p][qrd[p]];qrd[p]=(qrd[p]+1)%64;queued[p]=queued[p]-1;delay_count[p]<=$test$plusargs("fast")?0:$test$plusargs("depth")?200:4+(pending_sector[p]%9);acked=acked+1;
     if(pending_sector[p]>=BASE0&&pending_sector[p]<BASE0+640)begin acked0=acked0+1;last_ack[0]=$realtime;end
     else begin acked1=acked1+1;last_ack[1]=$realtime;end
    end
    if(k_v[p]&&k_rdy[p])begin
     sec=k_addr[p*30+:30];
     if(queued[p]>=64)$fatal(1,"outstanding limit exceeded");if(k_wr_done[p])simultaneous=simultaneous+1;
     if(hash_pc(sec)!==p)$fatal(1,"XOR PC mismatch sector=%h actualpc=%0d expectedpc=%0d",sec,p,hash_pc(sec));
     if(sec>=BASE0&&sec<BASE0+640)begin if(!first_seen[0])begin first_accept[0]=$realtime;first_seen[0]=1;end last_accept[0]=$realtime;idx=sec-BASE0;if(k_tag[p*17+:17]!==17'h01111)$fatal(1,"bank0 epoch");end
     else if(sec>=BASE1&&sec<BASE1+2048)begin if(acked0!=640)$fatal(1,"descriptor admitted before prior all-ACK"); if(!first_seen[1])begin first_accept[1]=$realtime;first_seen[1]=1;end last_accept[1]=$realtime;idx=640+sec-BASE1;if(k_tag[p*17+:17]!==17'h12222)$fatal(1,"bank1 epoch");end
     else $fatal(1,"native full sector address lost %h",sec);
     if(seen[idx]||k_wdata[p*256+:256]!==data_for(sec)||!k_we[p]||k_len[p*4+:4]!==1||k_wstrb[p*32+:32]!==32'hffffffff)$fatal(1,"actual sector payload/duplicate/PHY ABI mismatch sector=%h",sec);
     seen[idx]=1;accepted=accepted+1;queue_sector[p][qwr[p]]=sec;qwr[p]=(qwr[p]+1)%64;if(queued[p]==0&&!k_wr_done[p])delay_count[p]<=$test$plusargs("fast")?0:$test$plusargs("depth")?200:4+(sec%9);queued[p]=queued[p]+1;if(queued[p]>max_queued)max_queued=queued[p];
    end
    pending[p]<=(queued[p]!=0);
   end
  end
 end
 task tick;begin @(posedge stream_clk);#1;if(fault)$fatal(1,"unexpected boundary fault");end endtask
 always @(posedge stream_clk)if(dut.srst)begin
  if(done_v)begin
   if(done_bank==0)begin if(acked0!=expected0||done_sectors!==expected0||done_epoch!==16'h1111)$fatal(1,"bank0 ACK before actual write completions");end
   else begin if(acked1!=2048||done_sectors!==12'd2048||done_epoch!==16'h2222)$fatal(1,"bank1 ACK before actual write completions");end
   $display("WB_TIMING bank=%0d first_accept_ps=%0.3f last_accept_ps=%0.3f last_real_ack_ps=%0.3f returned_ack_ps=%0.3f",done_bank,first_accept[done_bank],last_accept[done_bank],last_ack[done_bank],$realtime);
   blocks_done=blocks_done+1;
  end
 end
 task fill_block(input bit b,input [31:0] base,input integer count,input [15:0] ep);
  integer n,j;real fill_begin;begin
   reserve_bank=b;reserve_base=base;reserve_total=count;reserve_epoch=ep;#1;
   if(!reserve_ready)$fatal(1,"free bank not ready");reserve_v=1;tick;reserve_v=0;
   if(!bank_owned[b])$fatal(1,"reservation ownership missing");
   fill_start=1;fill_start_bank=b;fill_start_epoch=ep;tick;fill_start=0;fill_begin=$realtime;
   for(n=0;n<count;n=n+8)begin
    wd=0;for(j=0;j<8;j=j+1)if(n+j<count)wd[289*j+:289]={1'b1,(base+n+j),data_for(base+n+j)};
    tick;input_cycles=input_cycles+1;
    if(fill_done!==(n+8>=count))$fatal(1,"fixed fill duration mismatch");
    if(!bank_owned[b])$fatal(1,"SRAM bank freed during fixed fill");
   end
   wd=0;$display("WB_FILL bank=%0d sectors=%0d fixed_edges=%0d begin_ps=%0.3f end_ps=%0.3f elapsed_ps=%0.3f",b,count,(count+7)/8,fill_begin,$realtime,$realtime-fill_begin);tick;
  end
 endtask
 task fault_reset;begin
  stream_rst_n=0;hbm_rst_n=0;reserve_v=0;fill_start=0;wd=0;
  repeat(4)begin @(posedge stream_clk);#1;end
  stream_rst_n=1;hbm_rst_n=1;repeat(4)tick;
 end endtask
 task fault_expected(input integer id);begin
  @(posedge stream_clk);#1;if(!fault)$fatal(1,"fault missing id=%0d",id);
  reserve_v=0;fill_start=0;wd=0;
  @(posedge stream_clk);#1;if(!fault)$fatal(1,"fault not sticky id=%0d",id);
 end endtask
 task reserve_small;begin
  reserve_bank=0;reserve_base=BASE0;reserve_epoch=16'h1111;reserve_total=8;reserve_v=1;tick;reserve_v=0;
 end endtask
 genvar reset_lane;generate for(reset_lane=0;reset_lane<32;reset_lane=reset_lane+1)begin:g_reset_check
  always @(negedge dut.srst or negedge dut.hrst)begin
   #1;if(!dut.srst&&!dut.hrst&&(dut.g_root[reset_lane/8].g_lane[reset_lane%8].u_fifo.wbin||dut.g_root[reset_lane/8].g_lane[reset_lane%8].u_fifo.rbin))$fatal(1,"payload FIFO pointers not reset lane=%0d",reset_lane);
  end
 end endgenerate
 task reset_pointer_check;begin
  if(dut.srst||dut.hrst||dut.root_rst_n||bank_owned||k_v||reserve_ready||dut.u_meta.wbin||dut.u_meta.rbin||dut.u_ack.wbin||dut.u_ack.rbin)
   $fatal(1,"independent reset did not clear both domains");
 end endtask
 task independent_reset(input bit which);integer wait_cycles;begin
  fault_reset;reserve_small;
  fill_start=1;fill_start_bank=0;fill_start_epoch=16'h1111;tick;fill_start=0;
  for(wait_cycles=0;wait_cycles<8;wait_cycles=wait_cycles+1)wd[wait_cycles*289+:289]={1'b1,(BASE0+wait_cycles),data_for(BASE0+wait_cycles)};
  tick;wd=0;wait_cycles=0;
  while(!(|pending))begin tick;wait_cycles=wait_cycles+1;if(wait_cycles>1000)$fatal(1,"reset proof never reached live PHY request");end
  if(which)hbm_rst_n=0;else stream_rst_n=0;
  #1;reset_pointer_check;
  repeat(3)begin @(posedge stream_clk);#1;reset_pointer_check;end
  // Deassert at an arbitrary time, then prove each synchronizer needs its
  // own two positive edges. Other-domain clock edges cannot release it.
  #137;if(which)hbm_rst_n=1;else stream_rst_n=1;
  #1;if(dut.srst||dut.hrst)$fatal(1,"asynchronous reset release");
  fork
   begin @(posedge stream_clk);#1;if(dut.root_rst_n)$fatal(1,"FIFO roots released before second edge");if(dut.srst)$fatal(1,"stream released before second edge");@(posedge stream_clk);#1;if(!dut.srst||dut.root_rst_n!==4'hf)$fatal(1,"stream/FIFO roots did not release on second edge");end
   begin @(posedge hbm_clk);#1;if(dut.hrst)$fatal(1,"HBM released before second edge");@(posedge hbm_clk);#1;if(!dut.hrst)$fatal(1,"HBM did not release on second edge");end
  join
  tick;if(bank_owned||k_v||fault)$fatal(1,"stale work survived reset");
 end endtask
 integer guard;
 initial begin
  if($test$plusargs("resets"))begin
   independent_reset(0);independent_reset(1);
   $display("WB_PIPELINE_CDC_RESETS PASS independent_assertions=2 domain_local_release_edges=2 live_requests_flushed=2");$finish;
  end
  if($test$plusargs("tail"))begin
   expected0=13;repeat(4)tick;stream_rst_n=1;hbm_rst_n=1;repeat(4)tick;
   fill_block(0,BASE0,13,16'h1111);guard=0;
   while(blocks_done<1)begin tick;guard=guard+1;if(guard>10000)$fatal(1,"tail timeout");end
   tick;if(bank_owned||accepted!=13||acked!=13||seen[12:0]!==13'h1fff)$fatal(1,"tail exact coverage");
   $display("WB_PIPELINE_CDC_TAIL PASS sectors=13 fixed_edges=2 real_acks=13");$finish;
  end
  if($test$plusargs("faults"))begin
   fault_reset;reserve_bank=0;reserve_base=BASE0;reserve_epoch=16'h1111;reserve_total=0;reserve_v=1;fault_expected(1);
   fault_reset;reserve_total=2049;reserve_v=1;fault_expected(2);
   fault_reset;reserve_small;reserve_v=1;fault_expected(3);
   fault_reset;reserve_small;fill_start=1;fill_start_bank=0;fill_start_epoch=16'h1112;fault_expected(4);
   fault_reset;reserve_small;fill_start=1;fill_start_bank=0;fill_start_epoch=16'h1111;tick;fill_start=0;
   wd=0;fault_expected(5);
   fault_reset;reserve_small;fill_start=1;fill_start_bank=0;fill_start_epoch=16'h1111;tick;fill_start=0;
   for(guard=0;guard<8;guard=guard+1)wd[289*guard+:289]={1'b1,(BASE0+guard+32'd1),data_for(BASE0+guard)};
   fault_expected(6);
   fault_reset;wd[288]=1;fault_expected(7);
   $display("WB_PIPELINE_CDC_FAULTS PASS cases=7");$finish;
  end
  repeat(4)tick;stream_rst_n=1;hbm_rst_n=1;repeat(4)tick;
  fill_block(0,BASE0,640,16'h1111);
  // A second bank fills on a fixed 256-edge calendar while bank0 PHY waits.
  fill_block(1,BASE1,2048,16'h2222);
  guard=0;while(blocks_done<2)begin tick;guard=guard+1;if(guard>50000)$fatal(1,"block completion timeout");end
  tick;if(bank_owned||accepted!=2688||acked!=2688||seen!=={2688{1'b1}})$fatal(1,"full block coverage/ownership mismatch");
  $display("WB_PIPELINE_CDC PASS production640_fixedcycles=80 max2048_fixedcycles=256 sectors=%0d real_acks=%0d input_cycles=%0d blocks=%0d stream_period_ps=833.333 hbm_period_ps=1024 hbm_phase_ps=173",accepted,acked,input_cycles,blocks_done);
  $display("WB_PIPELINE_OUTSTANDING max=%0d simultaneous_done_accept=%0d",max_queued,simultaneous);if((!$test$plusargs("fast")&&max_queued<2)||(!$test$plusargs("depth")&&simultaneous==0))$fatal(1,"pipeline not exercised");
  if($test$plusargs("depth")&&max_queued!=64)$fatal(1,"64 outstanding not reached");
  $display("WB_COPY reads=%0d max_parallel=%0d overlapped_read_enqueue=%0d",reads,max_parallel,copy_overlap);if(reads!=2688||max_parallel!=32||copy_overlap==0)$fatal(1,"wide II1 copy not exercised");
  if(early_reads==0)$fatal(1,"cut-through never read during fixed ingress");$display("WB_CUTTHROUGH PASS early_SRAM_reads=%0d",early_reads);
  $display("WB_CLOCK_EDGES stream=%0d hbm=%0d finish_ps=%0.3f fifo_full_stream_edges=%0d",stream_edges,hbm_edges,$realtime,pressure_cycles);$finish;
 end
 initial begin #100000000;$fatal(1,"timeout");end
endmodule
`default_nettype wire
