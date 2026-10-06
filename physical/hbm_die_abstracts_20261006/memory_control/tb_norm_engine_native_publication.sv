`timescale 1ps/1fs
// Actual production KIND0 N64/D5120 engine with peer0 CP and32SRAM root.
// Retained outputs are expected readback ONLY, never DUT output stimuli.
// Gibbs16e5cb9f8 owns adapter/parent RTL; this file is bench-only.
module tb_norm_engine_native_publication;
 reg clk=0,por_n=0;always #416.666667 clk=~clk;
 reg warm_req=0,enroll_v=0,allocation_valid=0,publication_r=0;
 reg [72:0] allocation_frame;wire [72:0] vm_held_frame;
 reg [72:0] frame,publication_owner;reg [2:0] fn;reg [31:0] local_tag;
 wire warm_ack,enroll_r,lease_v,quiet,release_v,req_v,rsp_r,publication_v,retained,fault,ce,due;
 wire [72:0] held_frame;wire [336:0] req;
 wire rsp_v;wire [272:0] rsp;wire grant,req_r,release_r;
 wire [2:0] grants,releases;wire [3:0] req_ready,response_valid;
 wire [63:0] response_tag;wire [3:0] response_we;wire [1023:0] response_data;
 wire m_req_v,m_req_we,m_rsp_r;wire [31:0] m_req_addr,m_req_strb;
 wire [255:0] m_req_data;wire [15:0] m_req_tag;
 wire m_rsp_v,m_rsp_we;wire [15:0] m_rsp_tag;wire [255:0] m_rsp_data;
 wire m_req_r;wire bridge_fault,bridge_idle,credit_empty;
 assign grant=grants[1];assign release_r=releases[1];assign req_r=req_ready[2];
 assign rsp_v=response_valid[2];assign rsp={response_tag[32+:16],response_we[2],response_data[512+:256]};
 // Actual parent peer0 is SU/norm route: lease index1 -> request index2
 // inside this SAME canonical shared owner; gather wrapper exports grants[2:1].
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
 .clk_sm(clk),.por_n(por_n),.warm_req(warm_req&&publication_checked),
 .bind_v(bind_v),.bind_r(bind_r),.bind_frame(frame),.bind_rank(7'd41),.bind_base(32'd3584),.bind_span(32'd12800),
 .retire_v(retire_v&&!retained),.retire_r(retire_r),.retire_frame(frame),.held_frame(vm_held_frame),.retained(vm_retained),.warm_ack(vm_warm_ack),.fault(vm_fault),
 .activation_wr_v(1'b0),.activation_wr_frame(73'd0),.activation_wr_bank(1'b0),.activation_wr_addr(7'd0),.activation_wr_data(2063'd0),.activation_wr_owner(192'd0),.activation_ACK_r(1'b0),
 .activation_rd_v(1'b0),.activation_rd_frame(73'd0),.activation_rd_bank(1'b0),.activation_rd_addr(7'd0),.activation_rd_owner(192'd0),
 .tap_r(4'd0),.tap_ACK_v(4'd0),.tap_ACK_owner(768'd0),.tap_ACK_frame(292'd0),.activation_release_r(1'b0),
 .su_pub_v(apub_v),.su_pub_r(root_pub_r),.su_pub_frame(held_frame),.su_pub_addr(apub_addr),.su_pub_data(apub_data),.su_ACK_v(root_ACK_v),.su_ACK_r(aACK_r&&(ack_gate||root_ACK_addr!=16352)),.publication_ACK_frame(root_ACK_frame),.publication_ACK_addr(root_ACK_addr),
 .index_read_v(checking?check_read_v:aread_v),.index_read_r(ir_r),.index_read_frame(frame),.index_read_rank(7'd41),.index_read_addr(checking?check_addr:aread_addr),.index_read_words(6'd32),.index_read_tag(checking?check_tag:aread_tag),
 .index_rsp_v(ir_rsp_v),.index_rsp_r(checking?check_rsp_r:arsp_r),.index_rsp_data(ir_data),.index_rsp_tag(ir_rsp_tag),.index_rsp_frame(ir_frame),.index_rsp_rank(ir_rank),
 .sfu_source_owned(allocation_valid),.sfu_enroll_v(1'b0),.sfu_enroll_r(nv_enroll_r),.sfu_enroll_frame(frame),.sfu_base_word(32'd64),.sfu_tag(local_tag),
 .sfu_rx_v(1'b0),.sfu_rx_r(nv_tx_r),.sfu_rx_data(nv_tx_d),.sfu_rx_frame(nv_tx_owner),.sfu_rx_index(nv_tx_index),.sfu_rx_last(nv_tx_last),
 .sfu_publication_done(nv_done),.sfu_complete_v(nv_complete_v),.sfu_complete_r(1'b0),.sfu_complete_frame(nv_complete_frame),.sfu_complete_tag(nv_complete_tag),.sfu_retained(),.sfu_drained());

 reg checking=0;
 reg ack_gate=0,fault_last_ack=0;wire q_valid;wire [7:0] q_index;wire [511:0] q_codes;wire [19:0] q_exp;wire [1023:0] q_bf16;wire [72:0] q_frame;
 reg check_read_v=0,check_rsp_r=0;reg [31:0] check_addr;reg [7:0] check_tag;
 wire root_pub_r,root_ACK_v;wire [72:0] root_ACK_frame;wire [31:0] root_ACK_addr;
 wire aread_v,arsp_r,apub_v,aACK_r;wire [31:0] aread_addr,apub_addr;wire [7:0] aread_tag;wire [6:0] aread_rank;
 wire [1023:0] apub_data;wire child_enable,read_permit,drained,publication_checked,adapter_fault;
 wire [6143:0] rd_addr;wire [255:0] rd_re;wire [511:0] rd_src;wire [8191:0] rd_q;wire [63:0] wr_we;wire [1535:0] wr_addr;wire [2047:0] wr_data;wire [15:0] reserve_events;
 // Positive storage is3200 real256-bit sectors for4D x plusD gain words.
 ot_gpu_hbm_partition #(.ENABLE(1),.NS(1),.TW(16),.NPC(2),.MEM_WORDS(3200),.CLK_PS(833),.USE_W2(0)) cp_memory(
  .clk(clk),.rst_n(por_n),.req_v(m_req_v),.req_rdy(m_req_r),.req_we(m_req_we),
  .req_addr(m_req_addr),.req_wdata(m_req_data),.req_wstrb(m_req_strb),.req_tag(m_req_tag),
  .rsp_v(m_rsp_v),.rsp_rdy(m_rsp_r),.rsp_we(m_rsp_we),.rsp_tag(m_rsp_tag),.rsp_data(m_rsp_data),.fault(cp_fault));
 wire cp_fault;
 // ONE selected production stage, including its protected descriptor and ICG.
 // CP input lease is backed by the initialized image; landing is the accepted
 // protected root lease. The stage itself checks enrollment identity.
 ot_hbm_integrated_norm_stage #(.ENABLE(1),.NATIVE_VM(1),.KIND(0),.N(64),.D(5120),.RD(0),.AW(24),
 .PUBLISH_QUANT(1),.ROUTED(1),.RW(9),.BW(9),.BCAST(7),.RET(8)) u_norm_c12(
 .clk(clk),.por_n(por_n),.warm_req(warm_req),.warm_ack(warm_ack),
 .native_clock_enable(child_enable),.native_read_permit(read_permit),
 .enroll_v(enroll_v),.enroll_r(enroll_r),.enroll_frame(frame),.enroll_pc(32'd1),.enroll_op(32'd1),
 .enroll_source(16'd0),.enroll_expert(9'd41),.enroll_matrix(1'b0),.enroll_row(12'd0),.enroll_count(9'd80),
 .owner_valid(allocation_valid&&!cp_fault&&!bridge_fault&&!adapter_fault&&!vm_fault),.owner_frame(frame),
 .allocation_valid(vm_retained&&!vm_fault&&allocation_valid&&allocation_frame==vm_held_frame),
 .allocation_frame(vm_held_frame),.landing_reserved(vm_retained&&!adapter_fault&&!vm_fault),.landing_frame(vm_held_frame),
 .provider_drained(drained),.publication_checked(publication_checked),.publication_frame(held_frame),
 .grant(grant),.lease_v(lease_v),.quiet(quiet),.release_v(release_v),.release_r(release_r),
 .publication_v(publication_v),.publication_r(publication_r),.publication_owner(publication_owner),
 .xbase(24'd0),.ubase(24'd0),.wbase(24'd0),.ybase(24'd3584),.gain_base(24'd20480),
 .comb(512'd0),.post_pre({cfg[3],cfg[2],cfg[1],cfg[0]}),.n_f(cfg[4]),.eps(cfg[5]),.lim(32'd0),
 .cos_t(32'd0),.sin_t(32'd0),.rd_addr(rd_addr),.rd_re(rd_re),.rd_src(rd_src),.rd_q(rd_q),
 .vm_we(wr_we),.vm_waddr(wr_addr),.vm_wdata(wr_data),
 .q_valid(q_valid),.q_index(q_index),.q_codes(q_codes),.q_exp(q_exp),.q_bf16(q_bf16),.q_frame(q_frame),
 .reserve_events(reserve_events),.held_frame(held_frame),.retained(retained),.fault(fault),.ce(ce),.due(due));
 ot_hbm_norm_native_vm_adapter #(.ENABLE(1),.N(64),.D(5120),.AW(24),.PUBLISH_QUANT(1),.INPUT_CP(1)) adapter(
 .clk(clk),.por_n(por_n),.enroll(enroll_v&&enroll_r),.bind_accept(bind_v&&bind_r),.retained(retained),.owner_valid(frame==held_frame&&vm_retained&&!vm_fault&&allocation_valid&&allocation_frame==held_frame),.frame(held_frame),.rank(7'd41),
 .rd_addr(rd_addr),.rd_re(rd_re),.rd_q(rd_q),.wr_we(wr_we),.wr_addr(wr_addr),.wr_data(wr_data),
 .q_valid(q_valid),.q_index(q_index),.q_codes(q_codes),.q_exp(q_exp),.q_bf16(q_bf16),.q_frame(q_frame),.quant_base(32'd8704),
 .cp_req_v(req_v),.cp_req_r(req_r),.cp_req(req),.cp_rsp_v(rsp_v),.cp_rsp_r(rsp_r),.cp_rsp(rsp),
 .child_enable(child_enable),.read_permit(read_permit),.drained(drained),.publication_checked(publication_checked),.fault(adapter_fault),
 .read_v(aread_v),.read_r(ir_r&&!checking),.read_addr(aread_addr),.read_tag(aread_tag),.read_rank(aread_rank),
 .rsp_v(ir_rsp_v&&!checking),.rsp_r(arsp_r),.rsp_data(ir_data),.rsp_frame(ir_frame),.rsp_tag(ir_rsp_tag),.rsp_rank(ir_rank),
 .pub_v(apub_v),.pub_r(root_pub_r),.pub_addr(apub_addr),.pub_data(apub_data),.ACK_v(root_ACK_v&&(ack_gate||root_ACK_addr!=16352)),.ACK_r(aACK_r),.ACK_frame(root_ACK_frame^((fault_last_ack&&root_ACK_addr==16352)?(73'd1<<52):73'd0)),.ACK_addr(root_ACK_addr));
 // Expected result arrays are used ONLY for same-bank readback comparisons.
 reg [31:0] xgold[0:20479],wgold[0:5119],ey[0:5119],cfg[0:5];
 reg [255:0] eqc[0:159];reg [15:0] eqe[0:159];reg [511:0] eqy[0:159];
 integer bind_count=0,enroll_count=0,retire_count=0,read_offers=0,read_returns=0;
 integer cp_requests=0,cp_returns=0,result_ACKs=0,quant_captures=0;
 integer cycles=0,stalled=0,previous_state=-1,phase=0;
 integer engine_child_edges=0;
 always @(posedge u_norm_c12.g_on.child_clk)if(por_n)engine_child_edges<=engine_child_edges+1;
 reg [1023:0] received;reg [72:0] received_frame;reg [7:0] received_tag;reg [6:0] received_rank;
 // Single-outstanding CP worst service: refresh+request/response+row timings,
 // plus finite512row SRAM geometry,256lane scan and protected72bit control.
 // Include the selected source pipeline drain: BCAST, HC mix, lane/tree
 // reduction, seven vector levels, scalar/divide/rsqrt, BW,80-vector scale
 // sweep, quant, RET and registered fault. This is not a wall/build deadline.
 localparam integer ENGINE_DRAIN_BOUND=7+(5+3*6+1)+(5+7*6+3*6)+7*6+9+8+6+(1+3*(3*5+6))+9+80+2*(5+1)+1+18+8+2;
 localparam integer STALL_BOUND=ENGINE_DRAIN_BOUND+(350000+10000+10000+19375+12500+16250+28125+1024+832)/833+512+4*256+2*72;
 always @(posedge clk)begin
  if(!por_n)begin
   bind_count<=0;enroll_count<=0;retire_count<=0;read_offers<=0;read_returns<=0;
   cp_requests<=0;cp_returns<=0;result_ACKs<=0;quant_captures<=0;
   stalled<=0;previous_state<=-1;
  end else begin
   cycles<=cycles+1;
   if(vm_fault||cp_fault||bridge_fault)$fatal(1,"REAL_BACKEND_FAULT phase=%0d vm=%b cp=%b bridge=%b",phase,vm_fault,cp_fault,bridge_fault);
   if((fault||adapter_fault)&&!(fault_last_ack&&result_ACKs==400))
    $fatal(1,"UNEXPECTED_SOURCE_FAULT phase=%0d state=%0d idx=%0d ACK=%0d",phase,adapter.g_on.state,adapter.g_on.idx,result_ACKs);
   if(bind_v&&bind_r)bind_count<=bind_count+1;
   if(enroll_v&&enroll_r)enroll_count<=enroll_count+1;
   if(retire_v&&retire_r&&!retained)retire_count<=retire_count+1;
   if(checking&&check_read_v&&ir_r)read_offers<=read_offers+1;
   if(checking&&ir_rsp_v&&check_rsp_r)begin
    read_returns<=read_returns+1;received<=ir_data;received_frame<=ir_frame;received_tag<=ir_rsp_tag;received_rank<=ir_rank;
   end
   if(m_req_v&&m_req_r)begin
    if(m_req_we||m_req_addr[4:0]!=0||m_req_addr>=102400)$fatal(1,"CP_NONZERO_SECTOR_SHAPE addr=%0d we=%b",m_req_addr,m_req_we);
    cp_requests<=cp_requests+1;
   end
   if(m_rsp_v&&m_rsp_r)cp_returns<=cp_returns+1;
   if(adapter.g_on.quant_capture)begin
    if(q_frame!==held_frame||q_index!=quant_captures)$fatal(1,"REAL_ENGINE_QUANT_IDENTITY");
    quant_captures<=quant_captures+1;
   end
   if(root_ACK_v&&aACK_r&&(ack_gate||root_ACK_addr!=16352))begin
    if(root_ACK_frame!==held_frame)$fatal(1,"REAL_ACK_FULL73");
    if(root_ACK_addr<3584||root_ACK_addr>16352||root_ACK_addr[4:0]!=0)$fatal(1,"REAL_ACK_OUTPUT_BOUNDARY");
    result_ACKs<=result_ACKs+1;
   end
   if(adapter.g_on.state!=previous_state||bind_v&&bind_r||enroll_v&&enroll_r||
      m_req_v&&m_req_r||m_rsp_v&&m_rsp_r||apub_v&&root_pub_r||
      root_ACK_v&&aACK_r&&(ack_gate||root_ACK_addr!=16352)||
      checking&&(check_read_v&&ir_r||ir_rsp_v&&check_rsp_r)||retire_v&&retire_r)
    stalled<=0;
   else stalled<=stalled+1;
   previous_state<=adapter.g_on.state;
   if(stalled>STALL_BOUND)$fatal(1,"NO_MECHANISM_PROGRESS phase=%0d state=%0d idx=%0d CP=%0d/%0d ACK=%0d rootR=%b rootV=%b child=%b permit=%b owned=%b retained=%b",phase,adapter.g_on.state,adapter.g_on.idx,cp_requests,cp_returns,result_ACKs,ir_r,ir_rsp_v,child_enable,read_permit,grant,retained);
  end
 end
 task tick;begin @(posedge clk);#1;end endtask
 task negstep;begin @(negedge clk);#1;end endtask
 function automatic [1023:0] golden_row(input integer row);
  integer k,v,r;reg [1023:0] value;
  begin
   value=0;
   if(row<160)for(k=0;k<32;k=k+1)value[k*32+:32]=ey[row*32+k];
   else begin v=(row-160)/3;r=(row-160)%3;
    case(r)
     0:value[511:0]={eqc[2*v+1],eqc[2*v]};
     1:value[19:0]={eqe[2*v+1][9:0],eqe[2*v][9:0]};
     2:value={eqy[2*v+1],eqy[2*v]};
    endcase
   end
   golden_row=value;
  end
 endfunction
 integer j,k,before_count,checked_words=0;string dir;
 reg [1023:0] gold_row;reg [255:0] sector;
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"RETAINED_GOLD_DIR_REQUIRED");
  fault_last_ack=$test$plusargs("FAULT_LAST_ACK");
  $readmemh({dir,"/x.mem"},xgold);$readmemh({dir,"/w.mem"},wgold);
  $readmemh({dir,"/ey.mem"},ey);$readmemh({dir,"/eqc.mem"},eqc);
  $readmemh({dir,"/eqe.mem"},eqe);$readmemh({dir,"/eqy.mem"},eqy);$readmemh({dir,"/cfg.mem"},cfg);
  // Retained scales are signed16; the literal adapter carries signed10.
  // Preserve the two's-complement bits, and reject a noncanonical narrowing.
  for(j=0;j<160;j=j+1)
   if(eqe[j] !== {{6{eqe[j][9]}},eqe[j][9:0]})
    $fatal(1,"RETAINED_SCALE_SIGN_EXTENSION block=%0d scale16=%h scale10=%h",j,eqe[j],eqe[j][9:0]);
  frame={20'hfffff,17'h10001,4'h9,32'h9234abcd};publication_owner=frame;
  allocation_frame=frame;phase=1;repeat(3)tick();negstep();
  // Initialize the actual existing behavioural HBM backing, after its own
  // time-zero initializer. CP responses still come from its real scheduler.
  for(j=0;j<3200;j=j+1)begin
   for(k=0;k<8;k=k+1)sector[k*32+:32]=j*8+k<20480?xgold[j*8+k]:wgold[j*8+k-20480];
   cp_memory.g_on.u_model.mem[j]=sector;
  end
  allocation_valid=1;por_n=1;tick();negstep();bind_v=1;
  before_count=bind_count;while(bind_count==before_count)tick();negstep();bind_v=0;
  if(!vm_retained||vm_fault)$fatal(1,"ACTUAL_OUTPUT_BIND_REQUIRED");
  enroll_v=1;before_count=enroll_count;while(enroll_count==before_count)tick();negstep();enroll_v=0;
  // Actual stage autonomously loads gain/operands and generates every output.
  // No procedural assignment to rd/vm/q signals and no retained-output replay.
  phase=4;while(!(root_ACK_v&&root_ACK_addr==16352))tick();
  if(!grant||held_frame!==frame||vm_held_frame!==frame||q_frame!==frame||reserve_events!=160)
   $fatal(1,"ACTUAL_ENGINE_FULL73_ALLOCATION");
  repeat(7)begin tick();if(publication_checked||publication_v||!retained||!vm_retained||child_enable)$fatal(1,"LASTWORD_UNCHECKED_VISIBILITY");end
  negstep();ack_gate=1;
  if(fault_last_ack)begin
   phase=10;while(!adapter_fault)tick();negstep();warm_req=1;repeat(7)tick();
   if(!fault||!retained||!vm_retained||publication_checked||publication_v||warm_ack||vm_warm_ack||
      adapter.g_on.checked!=5120||adapter.g_on.q[91:60]!=239||result_ACKs!=400||
      quant_captures!=80||cp_requests!=25600||cp_returns!=25600||engine_child_edges==0)
    $fatal(1,"ENGINE_LASTROW_FOREIGN_FULL73_NOT_REFUSED");
   $display("NORM_ENGINE_NATIVE_NEGATIVE_PASS actual_engine N64 D5120 CP25600 ACK400 finalROW16352 finalWORD16383 wrongTOKENbit52 quant_checked239 FP32_checked5120 owner_retained warm_refused child_edges=%0d",engine_child_edges);$finish;
  end
  phase=7;while(!publication_v)tick();
  if(cp_requests!=25600||cp_returns!=25600||engine_child_edges==0||result_ACKs!=400||quant_captures!=80||!publication_checked||adapter.g_on.checked!=5120||adapter.g_on.q[91:60]!=240)$fatal(1,"PRODUCTION_400_CHECKED_ACK_DEBT");
  // One all-payload golden comparison reads the exact native SRAMs just written.
  negstep();checking=1;
  for(j=0;j<400;j=j+1)begin
   negstep();check_addr=3584+j*32;check_tag=j;check_read_v=1;check_rsp_r=0;
   before_count=read_offers;while(read_offers==before_count)tick();negstep();check_read_v=0;
   while(!ir_rsp_v)tick();
   repeat(3)begin tick();if(!ir_rsp_v||ir_frame!==held_frame||ir_rsp_tag!==check_tag||ir_rank!=41)$fatal(1,"HELD_REAL_SRAM_REPLY_IDENTITY");end
   before_count=read_returns;negstep();check_rsp_r=1;while(read_returns==before_count)tick();negstep();check_rsp_r=0;
   gold_row=golden_row(j);
   if(received_frame!==held_frame||received_tag!==check_tag||received_rank!=41)$fatal(1,"SAMEBANK_FULL73_RETURN");
   for(k=0;k<32;k=k+1)begin
    if(received[k*32+:32]!==gold_row[k*32+:32])$fatal(1,"PRODUCTION_GOLD_MISMATCH WORD=%0d expected=%h actual=%h",3584+j*32+k,gold_row[k*32+:32],received[k*32+:32]);
    checked_words=checked_words+1;
   end
  end
  if(check_addr+31!=16383||checked_words!=12800)$fatal(1,"FULL_LASTWORD_GEOMETRY");
  phase=8;negstep();checking=0;warm_req=1;repeat(7)tick();
  if(!retained||!vm_retained||warm_ack||vm_warm_ack||!publication_v)$fatal(1,"WARM_CHECKED_CALLER_DEBT");
  negstep();publication_r=1;while(retained)tick();negstep();publication_r=0;
  if(grant)$fatal(1,"REAL_PEER0_REVERSE_ACK_REQUIRED");
  phase=9;retire_v=1;before_count=retire_count;while(retire_count==before_count)tick();negstep();retire_v=0;
  repeat(7)tick();if(!warm_ack||!vm_warm_ack||vm_retained)$fatal(1,"CHECKED_WARM_ROOT_RETIRE");
  $display("NORM_ENGINE_NATIVE_PUBLICATION_PASS N64 D5120 KIND0 CP25600 sectors3200 ACK400 FP32ACK160 QUANTACK240 words12800 finalWORD16383 codegroups160 scalegroups160 QDQgroups160 full73 held7edges warm_jointretire actual_engine_outputs child_edges=%0d",engine_child_edges);$finish;
 end
endmodule
