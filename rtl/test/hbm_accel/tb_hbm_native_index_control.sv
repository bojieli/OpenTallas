`timescale 1ps/1fs
module tb_hbm_native_index_control;
 reg clk=0;always #416.667 clk=~clk;
 reg por_n=0,owner_valid=0,owner_fault=0,allocation_granted=0;
 reg [72:0] owner_frame=0,allocation_frame=0,command_frame=0,keep_frame=0;
 reg producer_published=0,producer_drained=0,selector_idle=1;
 reg command_v=0,command_cand=0,command_keep=0,keep_v=0;
 reg [6:0] command_rank=0;reg [13:0] command_ndie=0;reg [9:0] command_k=0;
 reg [1:0] keep_quarter=0;reg [341:0] keep_bitmap=0;
 wire command_r,keep_r,source_start_v;reg source_start_r=0;
 wire [89:0] fs;wire [344:0] kin;wire [72:0] held_frame;wire [6:0] held_rank;
 reg source_done=0;reg [1:0] index_event=0;reg returns_drained=0,source_idle=0;
 wire retained,done,fault;
 ot_hbm_native_index_control #(.ENABLE(1)) dut(.*);
 integer fr,q,j,frames=0,masks=0,starts=0,retirements=0;
 reg [89:0] expected_fs;reg [341:0] expected_mask[0:3];
 always @(posedge clk)begin
  if(por_n)begin
   if(fs[0])begin
    if(fs!==expected_fs)$fatal(1,"dynamic frame metadata mismatch");
    if(!producer_published||!producer_drained)$fatal(1,"premature unpublished frame");
    frames=frames+1;
   end
   if(kin[0])begin
    if(kin[344:3]!==expected_mask[kin[2:1]])$fatal(1,"keep bitmap mismatch");
    masks=masks+1;
   end
   if(source_start_v&&source_start_r)starts=starts+1;
   if(done)begin
    if(!returns_drained||!source_idle||!selector_idle)$fatal(1,"premature retirement");
    retirements=retirements+1;
   end
  end
 end
 task tick;begin @(negedge clk);end endtask
 task reset;begin por_n=0;command_v=0;keep_v=0;source_done=0;index_event=0;
  repeat(3)tick();por_n=1;repeat(2)tick();end endtask
 initial begin
  reset();owner_valid=1;allocation_granted=1;
  for(fr=0;fr<24;fr=fr+1)begin
   owner_frame={20'(500+fr),17'(99+fr),4'(fr),32'(32'hbad100+fr)};
   allocation_frame=owner_frame;command_frame=owner_frame;keep_frame=owner_frame;
   command_rank=(fr==23)?95:7'(fr);command_ndie=14'(400+fr);
   command_k=512;command_cand=fr[1];command_keep=fr[0];
   expected_fs={command_keep,command_cand,command_k,command_ndie,command_rank,
                owner_frame[72:53],owner_frame[35:32],owner_frame[31:0],1'b1};
   producer_published=0;producer_drained=0;source_start_r=0;
   returns_drained=0;source_idle=0;selector_idle=1;
   if(!command_r)$fatal(1,"command not admitted");
   command_v=1;tick();command_v=0;
   repeat(4)begin if(fs[0])$fatal(1,"missing publication wait");tick();end
   producer_published=1;producer_drained=1;
   if(command_keep)begin
    for(q=0;q<4;q=q+1)begin
     for(j=0;j<342;j=j+1)expected_mask[q][j]=((j+q+fr)%3)==0;
     keep_quarter=q;keep_bitmap=expected_mask[q];keep_v=1;
     while(!keep_r)tick();tick();keep_v=0;
    end
   end
   while(!source_start_v)tick();
   repeat(3)begin if(!source_start_v||held_frame!==owner_frame)$fatal(1,"start changed under stall");tick();end
   source_start_r=1;tick();source_start_r=0;selector_idle=0;
   source_done=1;tick();source_done=0;
   index_event=1;tick();index_event=0;
   repeat(4)begin if(done||!retained)$fatal(1,"lost consumer debt");tick();end
   returns_drained=1;source_idle=1;selector_idle=1;
   while(!done)tick();tick();tick();
   if(fault||retained)$fatal(1,"legal frame failed");
  end
  if(frames!=24||masks!=48||starts!=24||retirements!=24)$fatal(1,"missing frame/mask/start/receipt");
  command_rank=96;command_v=1;tick();command_v=0;tick();
  if(!fault||fs[0]||source_start_v)$fatal(1,"bad rank not failclosed");
  $display("PASS_NATIVE_INDEX_CONTROL frames=%0d masks=%0d starts=%0d receipts=%0d",frames,masks,starts,retirements);
  $finish;
 end
 // Minimum control latency is below100edges/frame; generous mechanism
 // watchdog only detects missing handshakes, not a build/process time cap.
 initial begin repeat(6000)@(posedge clk);$fatal(1,"control handshake deadlock");end
endmodule
