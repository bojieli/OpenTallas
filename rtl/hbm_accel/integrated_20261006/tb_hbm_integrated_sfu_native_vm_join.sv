`timescale 1ps/1fs
// Changed provider join, real SFU64, existing Carson golden vectors unchanged.
module tb_hbm_integrated_sfu_native_vm_join;
 reg clk=0,por_n=0;always #416.666667 clk=~clk;
 reg warm_req=0,enroll_v=0,allocation_valid=1,publication_r=0;
 reg [72:0] frame,publication_owner;reg [2:0] fn;reg [31:0] local_tag;
 wire warm_ack,enroll_r,lease_v,quiet,release_v,req_v,rsp_r,publication_v,retained,fault,ce,due;
 wire [72:0] held_frame;wire [336:0] req;
 wire rsp_v;wire [272:0] rsp;wire grant,req_r,release_r;
 wire [2:0] grants,releases;wire [3:0] req_ready,response_valid;
 wire [63:0] response_tag;wire [3:0] response_we;wire [1023:0] response_data;
 wire m_req_v,m_req_we,m_rsp_r;wire [31:0] m_req_addr,m_req_strb;
 wire [255:0] m_req_data;wire [15:0] m_req_tag;
 reg m_rsp_v=0,m_rsp_we=0;reg [15:0] m_rsp_tag;reg [255:0] m_rsp_data;
 wire m_req_r=!m_rsp_v;wire bridge_fault,bridge_idle,credit_empty;
 assign grant=grants[1];assign release_r=releases[1];assign req_r=req_ready[2];
 assign rsp_v=response_valid[2];assign rsp={response_tag[32+:16],response_we[2],response_data[512+:256]};
 // Actual existing protected grant/calendar/reverse ACK and CAP1 sector path.
 ot_hbm_integrated_sm0_borrow #(.ENABLE(1)) bridge(
  .clk(clk),.por_n(por_n),.native_clients_drained(1'b1),.cdc_drained(!m_rsp_v),
  .observe_req(4'd0),.observe_rsp(4'd0),.observe_req_we(4'd0),.observe_rsp_we(4'd0),
  .observe_req_tag(64'd0),.observe_rsp_tag(64'd0),.return_offer(4'd0),.response_authorized(),
  .native_job(frame[31:0]),.native_gen(frame[35:32]),.native_token(frame[52:36]),.native_pos(frame[72:53]),
  .native_credit_empty(credit_empty),.lease_v({1'b0,lease_v,1'b0}),.borrower_quiet({1'b1,quiet,1'b1}),
  .lease_job({32'd0,frame[31:0],32'd0}),.lease_gen({4'd0,frame[35:32],4'd0}),
  .lease_token({17'd0,frame[52:36],17'd0}),.lease_pos({20'd0,frame[72:53],20'd0}),.lease_granted(grants),
  .release_v({1'b0,release_v,1'b0}),.release_r(releases),
  .release_job({32'd0,publication_owner[31:0],32'd0}),.release_gen({4'd0,publication_owner[35:32],4'd0}),
  .release_token({17'd0,publication_owner[52:36],17'd0}),.release_pos({20'd0,publication_owner[72:53],20'd0}),
  .req_v({1'b0,req_v,2'b00}),.req_rdy(req_ready),.req_we({1'b0,req[336],2'b00}),
  .req_addr({32'd0,req[335:304],64'd0}),.req_wdata({256'd0,req[303:48],512'd0}),
  .req_wstrb({32'd0,req[47:16],64'd0}),.req_tag({16'd0,req[15:0],32'd0}),
  .rsp_v(response_valid),.rsp_rdy({1'b0,rsp_r,2'b00}),.rsp_we(response_we),.rsp_tag(response_tag),.rsp_data(response_data),
  .m_req_v(m_req_v),.m_req_rdy(m_req_r),.m_req_we(m_req_we),.m_req_addr(m_req_addr),
  .m_req_wdata(m_req_data),.m_req_wstrb(m_req_strb),.m_req_tag(m_req_tag),
  .m_rsp_v(m_rsp_v),.m_rsp_rdy(m_rsp_r),.m_rsp_we(m_rsp_we),.m_rsp_tag(m_rsp_tag),.m_rsp_data(m_rsp_data),
  .idle(bridge_idle),.fault(bridge_fault));
 wire nv_enroll_v,nv_enroll_r,nv_tx_v,nv_tx_r,nv_tx_last,nv_done,nv_complete_v,nv_complete_r,nv_drained;
 wire [1023:0] nv_tx_d;wire [72:0] nv_tx_owner,nv_complete_frame;wire [3:0] nv_tx_index;wire [31:0] nv_complete_tag;
 reg bind_v=0,retire_v=0,ir_v=0,ir_rsp_r=0;reg [31:0] ir_addr;reg [7:0] ir_tag;
 wire bind_r,retire_r,vm_fault,vm_retained,vm_warm_ack,ir_r,ir_rsp_v;
 wire [1023:0] ir_data;wire [72:0] ir_frame;wire [7:0] ir_rsp_tag;wire [6:0] ir_rank;
 // One actual existing 32-SRAM VM root, no output payload fixture.
 ot_hbm_die_vm_sfu_publication_root #(.ENABLE(1)) vm(
 .clk_sm(clk),.por_n(por_n),.warm_req(warm_req&&nv_drained),
 .bind_v(bind_v),.bind_r(bind_r),.bind_frame(frame),.bind_rank(7'd41),.bind_base(32'd64),.bind_span(32'd64),
 .retire_v(retire_v&&!retained),.retire_r(retire_r),.retire_frame(frame),.held_frame(),.retained(vm_retained),.warm_ack(vm_warm_ack),.fault(vm_fault),
 .activation_wr_v(1'b0),.activation_wr_frame(73'd0),.activation_wr_bank(1'b0),.activation_wr_addr(7'd0),.activation_wr_data(2063'd0),.activation_wr_owner(192'd0),.activation_ACK_r(1'b0),
 .activation_rd_v(1'b0),.activation_rd_frame(73'd0),.activation_rd_bank(1'b0),.activation_rd_addr(7'd0),.activation_rd_owner(192'd0),
 .tap_r(4'd0),.tap_ACK_v(4'd0),.tap_ACK_owner(768'd0),.tap_ACK_frame(292'd0),.activation_release_r(1'b0),
 .su_pub_v(1'b0),.su_pub_frame(73'd0),.su_pub_addr(32'd0),.su_pub_data(1024'd0),.su_ACK_r(1'b0),
 .index_read_v(ir_v),.index_read_r(ir_r),.index_read_frame(frame),.index_read_rank(7'd41),.index_read_addr(ir_addr),.index_read_words(6'd32),.index_read_tag(ir_tag),
 .index_rsp_v(ir_rsp_v),.index_rsp_r(ir_rsp_r),.index_rsp_data(ir_data),.index_rsp_tag(ir_rsp_tag),.index_rsp_frame(ir_frame),.index_rsp_rank(ir_rank),
 .sfu_source_owned(allocation_valid),.sfu_enroll_v(nv_enroll_v),.sfu_enroll_r(nv_enroll_r),.sfu_enroll_frame(frame),.sfu_base_word(32'd64),.sfu_tag(local_tag),
 .sfu_rx_v(nv_tx_v),.sfu_rx_r(nv_tx_r),.sfu_rx_data(nv_tx_d),.sfu_rx_frame(nv_tx_owner),.sfu_rx_index(nv_tx_index),.sfu_rx_last(nv_tx_last),
 .sfu_publication_done(nv_done),.sfu_complete_v(nv_complete_v),.sfu_complete_r(nv_complete_r),.sfu_complete_frame(nv_complete_frame),.sfu_complete_tag(nv_complete_tag),.sfu_retained(),.sfu_drained());
 ot_hbm_integrated_sfu_provider_join #(.ENABLE(1),.NATIVE_VM_PUBLICATION(1)) dut(
  .clk(clk),.por_n(por_n),.warm_req(warm_req),.warm_ack(warm_ack),
  .enroll_v(enroll_v),.enroll_r(enroll_r),.enroll_frame(frame),
  .enroll_pc(32'h12345678),.enroll_op(32'd1),.enroll_source(16'd0),
  .enroll_expert(9'd41),.enroll_matrix(1'b0),.enroll_row(12'd0),.enroll_count(9'd64),
  .allocation_valid(allocation_valid),.allocation_frame(frame),
  .source_addr(32'd0),.dest_addr(32'd256),.source_base(32'd0),.source_limit(32'd256),
  .dest_base(32'd256),.dest_limit(32'd512),.fn(fn),.local_tag(local_tag),
  .owner_valid(1'b1),.owner_frame(frame),.grant(grant),.lease_v(lease_v),.quiet(quiet),
  .release_v(release_v),.release_r(release_r),.req_v(req_v),.req_r(req_r),.req(req),
  .rsp_v(rsp_v),.rsp_r(rsp_r),.rsp(rsp),.publication_v(publication_v),.publication_r(publication_r),
  .native_enroll_v(nv_enroll_v),.native_enroll_r(nv_enroll_r),
  .native_tx_v(nv_tx_v),.native_tx_r(nv_tx_r),.native_tx_d(nv_tx_d),.native_tx_owner(nv_tx_owner),.native_tx_index(nv_tx_index),.native_tx_last(nv_tx_last),
  .native_publication_done(nv_done),.native_complete_v(nv_complete_v),.native_fault(vm_fault),.native_complete_frame(nv_complete_frame),.native_complete_tag(nv_complete_tag),
  .native_complete_r(nv_complete_r),.native_producer_drained(nv_drained),
  .publication_owner(publication_owner),.held_frame(held_frame),.retained(retained),.fault(fault),.ce(ce),.due(due));
 reg [255:0] memory[0:15];reg [2082:0] requests[0:9];reg [2080:0] expected[0:9];
 integer reads=0,writes=0,acks=0,checked=0,cycles=0,k,j,w;string dir;
 reg corrupt_readback=0;
 // Finite one-outstanding actual sector store, no synthetic publication ACK.
 // NBA response is sampled only on following clock, same as real provider.
 always @(posedge clk)begin
  cycles<=cycles+1;
  if(!por_n)begin m_rsp_v<=0;reads<=0;writes<=0;acks<=0;end
  else begin
   if(release_v&&release_r)begin acks<=acks+1;end
   if(m_rsp_v&&m_rsp_r)m_rsp_v<=0;
   if(m_req_v&&m_req_r)begin
    if(m_req_addr[4:0]!=0)$fatal(1,"UNALIGNED_PROVIDER");
    if(m_req_addr>=512)$fatal(1,"OUT_OF_ALLOCATION_PROVIDER");
    m_rsp_v<=1;m_rsp_tag<=m_req_tag;m_rsp_we<=m_req_we;
    if(m_req_we)begin
     if(m_req_strb!=32'hffffffff)$fatal(1,"INCOMPLETE_WRITE");
     memory[m_req_addr>>5]<=m_req_data;m_rsp_data<=0;writes<=writes+1;
    end else begin
     m_rsp_data<=memory[m_req_addr>>5]^((corrupt_readback&&m_req_addr>=256)?256'd1:256'd0);
     reads<=reads+1;
    end
   end
  end
 end
 task tick;begin @(posedge clk);#1;end endtask
 task negstep;begin @(negedge clk);#1;end endtask
 task reset;
 begin negstep();por_n=0;warm_req=0;enroll_v=0;publication_r=0;corrupt_readback=0;bind_v=0;retire_v=0;ir_v=0;ir_rsp_r=0;
 repeat(3)tick();negstep();por_n=1;tick();end endtask
 task start(input integer case_i,input integer pos);
 begin
  negstep();frame={20'(pos),17'h10001,4'h9,32'hca001234};publication_owner=frame;
  fn=requests[case_i][2050:2048];local_tag=requests[case_i][2082:2051];#1;
  for(j=0;j<8;j=j+1)memory[j]=requests[case_i][j*256+:256];
  bind_v=1;#1;
  // Fresh POR, no outstanding traffic: the actual drained root must offer bind.
  if(!bind_r)$fatal(1,"BIND_NOT_READY cycles=%0d fault=%b retained=%b",cycles,vm_fault,vm_retained);
  tick();negstep();bind_v=0;#1;
  if(!enroll_r)$fatal(1,"NO_REAL_ENROLL");enroll_v=1;tick();negstep();enroll_v=0;
 end endtask
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR_REQUIRED");
  $readmemh({dir,"/sfu_req.mem"},requests);$readmemh({dir,"/sfu_exp.mem"},expected);
  // One seed, one actual64-lane operation; Carson owns the eight-opcode gate.
  reset();start(0,1048575);w=0;
  while(!publication_v)begin tick();w=w+1;if(fault||vm_fault||bridge_fault||w>4000)$fatal(1,"NATIVE_JOIN_FAILURE");end
  $display("SFU_NATIVE_CHECKED_PUBLICATION cycles=%0d reads=%0d writes=%0d full73=%h",cycles,reads,writes,held_frame);
  if(reads!=8||writes!=0||!nv_done||held_frame!==frame)$fatal(1,"PREMATURE_OR_CP_PUBLICATION");
  for(j=0;j<2;j=j+1)begin
   negstep();ir_addr=64+j*32;ir_tag=8'(j);ir_v=1;
   #1; // Settle address/tag/valid BEFORE the acceptance edge.
   if(!ir_r)$fatal(1,"READ_NOT_READY block=%0d cycles=%0d response_v=%b fault=%b",j,cycles,ir_rsp_v,vm_fault);
   tick();negstep();ir_v=0;
   // Accepted IDLE->READ, then READ->CAPTURE->CHECK->RESP: three edges.
   repeat(3)tick();
   if(!ir_rsp_v)$fatal(1,"READ_RESPONSE_MISSING block=%0d cycles=%0d response_v=%b fault=%b",j,cycles,ir_rsp_v,vm_fault);
   negstep();
   if(ir_frame!==frame||ir_rsp_tag!==8'(j)||ir_rank!==41||ir_data!==expected[0][j*1024+:1024])
    $fatal(1,"FIRST_NATIVE_SRAM_NUMERICAL_MISMATCH block=%0d",j);
   $display("SFU_NATIVE_SRAM_READBACK block=%0d cycles=%0d addr=%0d full73=%h",j,cycles,ir_addr,ir_frame);
   ir_rsp_r=1;tick();negstep();ir_rsp_r=0;
  end
  negstep();warm_req=1;repeat(5)tick();
  if(!publication_v||!retained||warm_ack||vm_warm_ack)$fatal(1,"HELD_COMPLETION_WARM_DEBT");
  negstep();publication_r=1;tick();negstep();publication_r=0;tick();
  if(retained||grant||acks!=1||nv_complete_v)$fatal(1,"NONJOINT_RETIRE");
  negstep();retire_v=1;#1;
  // Both response ACKs and joint stage/publisher completion have drained.
  if(!retire_r)$fatal(1,"ROOT_RETIRE_NOT_READY cycles=%0d readReady=%b response_v=%b stageRetained=%b VMfault=%b",cycles,ir_r,ir_rsp_v,retained,vm_fault);
  tick();negstep();retire_v=0;repeat(4)tick();
  if(!warm_ack||!vm_warm_ack||vm_retained)$fatal(1,"ROOT_WARM_DRAIN");
  // Caller high TOKEN17 refusal retains stage AND publisher completion.
  reset();start(0,8191);w=0;
  while(!publication_v)begin tick();w=w+1;if(fault||w>4000)$fatal(1,"TOKEN_NEGATIVE_SETUP");end
  negstep();publication_owner=frame^(73'b1<<52);publication_r=1;tick();negstep();publication_r=0;
  if(!fault||!retained||!nv_complete_v||release_v||!grant)$fatal(1,"TOKEN17_WRONG_JOINT_ACCEPT");
  $display("SFU_NATIVE_VM_JOIN_PASS 64FP32 actual32SRAM checked2ACK CP8READ zeroCPwrite full73 warm jointretire");$finish;
 end
endmodule
