`timescale 1ps/1fs
// Changed provider join, real SFU64, existing Carson golden vectors unchanged.
module tb_hbm_integrated_norm_native_vm_join;
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
 .clk_sm(clk),.por_n(por_n),.warm_req(warm_req&&publication_checked),
 .bind_v(bind_v),.bind_r(bind_r),.bind_frame(frame),.bind_rank(7'd41),.bind_base(32'd0),.bind_span(32'd192),
 .retire_v(retire_v&&!retained),.retire_r(retire_r),.retire_frame(frame),.held_frame(),.retained(vm_retained),.warm_ack(vm_warm_ack),.fault(vm_fault),
 .activation_wr_v(1'b0),.activation_wr_frame(73'd0),.activation_wr_bank(1'b0),.activation_wr_addr(7'd0),.activation_wr_data(2063'd0),.activation_wr_owner(192'd0),.activation_ACK_r(1'b0),
 .activation_rd_v(1'b0),.activation_rd_frame(73'd0),.activation_rd_bank(1'b0),.activation_rd_addr(7'd0),.activation_rd_owner(192'd0),
 .tap_r(4'd0),.tap_ACK_v(4'd0),.tap_ACK_owner(768'd0),.tap_ACK_frame(292'd0),.activation_release_r(1'b0),
 .su_pub_v(loading?load_v:apub_v),.su_pub_r(root_pub_r),.su_pub_frame(frame),.su_pub_addr(loading?load_addr:apub_addr),.su_pub_data(loading?load_data:apub_data),.su_ACK_v(root_ACK_v),.su_ACK_r(loading?load_ACK_r:aACK_r),.publication_ACK_frame(root_ACK_frame),.publication_ACK_addr(root_ACK_addr),
 .index_read_v(checking?check_read_v:aread_v),.index_read_r(ir_r),.index_read_frame(frame),.index_read_rank(7'd41),.index_read_addr(checking?check_addr:aread_addr),.index_read_words(6'd32),.index_read_tag(checking?check_tag:aread_tag),
 .index_rsp_v(ir_rsp_v),.index_rsp_r(checking?check_rsp_r:arsp_r),.index_rsp_data(ir_data),.index_rsp_tag(ir_rsp_tag),.index_rsp_frame(ir_frame),.index_rsp_rank(ir_rank),
 .sfu_source_owned(allocation_valid),.sfu_enroll_v(1'b0),.sfu_enroll_r(nv_enroll_r),.sfu_enroll_frame(frame),.sfu_base_word(32'd64),.sfu_tag(local_tag),
 .sfu_rx_v(1'b0),.sfu_rx_r(nv_tx_r),.sfu_rx_data(nv_tx_d),.sfu_rx_frame(nv_tx_owner),.sfu_rx_index(nv_tx_index),.sfu_rx_last(nv_tx_last),
 .sfu_publication_done(nv_done),.sfu_complete_v(nv_complete_v),.sfu_complete_r(1'b0),.sfu_complete_frame(nv_complete_frame),.sfu_complete_tag(nv_complete_tag),.sfu_retained(),.sfu_drained());

 reg loading=1,load_v=0,load_ACK_r=0,checking=0,foreign_response=0;
 reg [31:0] load_addr;reg [1023:0] load_data;
 reg check_start=0;
 wire check_read_v,check_rsp_r,check_passed;wire [31:0] check_addr;wire [7:0] check_tag;
 wire root_pub_r,root_ACK_v;wire [72:0] root_ACK_frame;wire [31:0] root_ACK_addr;
 wire aread_v,arsp_r,apub_v,aACK_r;wire [31:0] aread_addr,apub_addr;wire [7:0] aread_tag;wire [6:0] aread_rank;
 wire [1023:0] apub_data;wire child_enable,read_permit,drained,publication_checked,adapter_fault;
 wire [1023:0] rd_addr;wire [127:0] rd_re;wire [4095:0] rd_q;wire [31:0] wr_we;wire [255:0] wr_addr;wire [1023:0] wr_data;
 assign req_v=0;assign req=0;
 ot_hbm_integrated_norm_stage #(.ENABLE(1),.NATIVE_VM(1),.KIND(1),.N(32),.D(64),.AW(8),.PUBLISH_QUANT(0)) dut(
 .clk(clk),.por_n(por_n),.warm_req(warm_req),.warm_ack(warm_ack),.native_clock_enable(child_enable),.native_read_permit(read_permit),
 .enroll_v(enroll_v),.enroll_r(enroll_r),.enroll_frame(frame),.enroll_pc(32'd1),.enroll_op(32'd1),.enroll_source(16'd0),.enroll_expert(9'd41),.enroll_matrix(1'b0),.enroll_row(12'd0),.enroll_count(9'd2),
 .owner_valid(!adapter_fault),.owner_frame(frame),.allocation_valid(vm_retained&&!vm_fault),.allocation_frame(frame),.landing_reserved(vm_retained&&!adapter_fault),.landing_frame(frame),
 .provider_drained(drained),.publication_checked(publication_checked),.publication_frame(frame),.grant(grant),.lease_v(lease_v),.quiet(quiet),.release_v(release_v),.release_r(release_r),
 .publication_v(publication_v),.publication_r(publication_r),.publication_owner(publication_owner),
 .xbase(8'd0),.gain_base(8'd64),.ybase(8'd128),.ubase(8'd0),.wbase(8'd0),.comb(512'd0),.post_pre(128'd0),.n_f(32'h42800000),.eps(32'h3a83126f),.lim(32'h41200000),.cos_t(32'd0),.sin_t(32'd0),
 .rd_addr(rd_addr),.rd_re(rd_re),.rd_src(),.rd_q(rd_q),.vm_we(wr_we),.vm_waddr(wr_addr),.vm_wdata(wr_data),.q_valid(),.q_index(),.q_codes(),.q_exp(),.q_bf16(),.reserve_events(),.held_frame(held_frame),.retained(retained),.fault(fault),.ce(ce),.due(due));
 ot_hbm_norm_native_vm_adapter #(.ENABLE(1),.N(32),.D(64),.AW(8)) adapter(
 .clk(clk),.por_n(por_n),.enroll(enroll_v&&enroll_r),.bind_accept(bind_v&&bind_r),.retained(retained),.owner_valid(frame==held_frame&&vm_retained&&!vm_fault),.frame(held_frame),.rank(7'd41),
 .rd_addr(rd_addr),.rd_re(rd_re),.rd_q(rd_q),.wr_we(wr_we),.wr_addr(wr_addr),.wr_data(wr_data),
 .child_enable(child_enable),.read_permit(read_permit),.drained(drained),.publication_checked(publication_checked),.fault(adapter_fault),
 .read_v(aread_v),.read_r(ir_r&&!checking),.read_addr(aread_addr),.read_tag(aread_tag),.read_rank(aread_rank),
 .rsp_v(ir_rsp_v&&!checking),.rsp_r(arsp_r),.rsp_data(ir_data),.rsp_frame(ir_frame^(foreign_response?(73'd1<<52):73'd0)),.rsp_tag(ir_rsp_tag),.rsp_rank(ir_rank),
 .pub_v(apub_v),.pub_r(root_pub_r&&!loading),.pub_addr(apub_addr),.pub_data(apub_data),.ACK_v(root_ACK_v&&!loading),.ACK_r(aACK_r),.ACK_frame(root_ACK_frame),.ACK_addr(root_ACK_addr));
 ot_hbm_norm_samebank_readback_checker #(.D(64),.GOLDEN_FILE("ey.mem")) u_readback(
  .clk(clk),.por_n(por_n),.start(check_start),.publication_checked(publication_checked),.lease_retained(retained&&vm_retained),
  .held_frame(held_frame),.rank(7'd41),.output_base_word(32'd128),
  .native_ACK_v(root_ACK_v&&!loading),.native_ACK_r(aACK_r),.native_ACK_frame(root_ACK_frame),.native_ACK_addr(root_ACK_addr),
  .read_v(check_read_v),.read_r(ir_r&&checking),.read_addr(check_addr),.read_words(),.read_tag(check_tag),.read_frame(),.read_rank(),
  .rsp_v(ir_rsp_v&&checking),.rsp_r(check_rsp_r),.rsp_data(ir_data),.rsp_tag(ir_rsp_tag),.rsp_frame(ir_frame),.rsp_rank(ir_rank),.passed(check_passed));
 reg [31:0] inputs[0:63],gain[0:63],expected[0:63];string dir;integer j,k;
 task tick;begin @(posedge clk);#1;end endtask
 task negstep;begin @(negedge clk);#1;end endtask
 task setup;
 begin
  negstep();por_n=0;enroll_v=0;publication_r=0;warm_req=0;bind_v=0;retire_v=0;ir_v=0;ir_rsp_r=0;loading=1;checking=0;check_start=0;foreign_response=0;load_v=0;load_ACK_r=0;
  frame={20'hfffff,17'h10001,4'h9,32'h9234abcd};publication_owner=frame;
  repeat(3)tick();negstep();por_n=1;tick();
  negstep();bind_v=1;while(!bind_r)tick();tick();negstep();bind_v=0;
  for(j=0;j<4;j=j+1)begin
   load_addr=j*32;for(k=0;k<32;k=k+1)load_data[k*32+:32]=j<2?inputs[j*32+k]:gain[(j-2)*32+k];
   load_v=1;while(!root_pub_r)tick();tick();negstep();load_v=0;
   while(!root_ACK_v)tick();negstep();
   if(root_ACK_frame!==frame||root_ACK_addr!==load_addr)$fatal(1,"PRELOAD_CHECKED_ACK");
   load_ACK_r=1;tick();negstep();load_ACK_r=0;
  end
  loading=0;if(!enroll_r)$fatal(1,"NORM_REAL_ENROLL_NOT_READY");enroll_v=1;tick();negstep();enroll_v=0;
 end endtask
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"NORM_GOLD_DIR_REQUIRED");
  $readmemh({dir,"/x.mem"},inputs);$readmemh({dir,"/w.mem"},gain);$readmemh({dir,"/ey.mem"},expected);
  setup();while(!publication_v)begin tick();if(fault||adapter_fault||vm_fault||bridge_fault)$fatal(1,"NORM_JOIN_FAULT state=%0d",adapter.g_on.state);end
  if(!publication_checked||held_frame!==frame)$fatal(1,"UNCHECKED_NORM_PUB");
  negstep();checking=1;check_start=1;tick();negstep();check_start=0;
  while(!check_passed)tick();
  checking=0;warm_req=1;repeat(4)tick();if(!retained||warm_ack||vm_warm_ack||!publication_v)$fatal(1,"NORM_WARM_DEBT");
  negstep();publication_r=1;tick();negstep();publication_r=0;tick();if(retained||grant)$fatal(1,"NORM_JOINT_RELEASE");
  negstep();retire_v=1;while(!retire_r)tick();tick();negstep();retire_v=0;repeat(4)tick();if(!warm_ack||!vm_warm_ack||vm_retained)$fatal(1,"NORM_ROOT_RETIRE");
  setup();foreign_response=1;while(!adapter_fault)tick();repeat(3)tick();if(!fault||!retained||publication_v||!vm_retained)$fatal(1,"NORM_FOREIGN_RESPONSE_DEBT");
  $display("NORM_NATIVE_VM_JOIN_PASS 64FP32 real32SRAM checkedpublication full73 highTOKEN17refusal warmjointretire");$finish;
 end
endmodule
