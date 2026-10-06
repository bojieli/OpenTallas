`timescale 1ns/1ps
// New connected mechanism only; selected arithmetic gate remains inherited.
// Canonical production header port-probe is explicit in sources, not numeric RTL.
module tb_hbm_swiglu_vm_connected;
 localparam N=32,D=64,AW=10;
 reg clk=0,por_n=0;always #5 clk=~clk;
 localparam [72:0] FRAME={20'hcdef1,17'h1abcd,4'h9,32'hca123456};
 reg [72:0] live_frame=FRAME,accept_frame=FRAME;
 reg enroll=0,warm=0,caller_accept=0,readback_allow=0,revoke_source=0,expect_fault=0;
 wire retained,issued,stage_fault,start_v,start_r,complete_v,finish_r,warm_ack;
 wire [72:0] held;
 wire [2:0] grants,releases;
 wire grant=grants[1],release_r=releases[1];
 wire release_v=complete_v&&caller_accept&&accept_frame==held;
 wire bridge_idle,bridge_fault,credit_empty;
 wire busy,done,vm_fault,qv;wire [31:0] completion_id;
 wire [7:0] qi;wire [72:0] qframe;
 wire [N*8-1:0] codes;wire [N/32*10-1:0] scales;wire [N*16-1:0] bf16;
 wire [4*N*AW-1:0] rd_addr;wire [4*N-1:0] rd_re;wire [8*N-1:0] rd_src;
 reg [4*N*32-1:0] rd_q;
 wire [N-1:0] vm_we;wire [N*AW-1:0] vm_waddr;wire [N*32-1:0] vm_wdata;
 wire [15:0] reserve_events;
 reg finished=0;reg [1:0] written=0,checked=0;
 reg [777:0] landing[0:1];reg [1:0] read_pending=0;
 reg [31:0] vm[0:511];integer reads=0,packets=0,acks=0;
 wire producer_drained=!busy&&!(|rd_re);
 wire consumer_drained=checked==2'b11;
 // Literal existing protected calendar; no software or tied-high lease grant.
 ot_hbm_integrated_sm0_borrow #(.ENABLE(1)) lease(
  .clk(clk),.por_n(por_n),.native_clients_drained(1'b1),.cdc_drained(1'b1),
  .observe_req(4'd0),.observe_rsp(4'd0),.observe_req_we(4'd0),.observe_rsp_we(4'd0),
  .observe_req_tag(64'd0),.observe_rsp_tag(64'd0),.return_offer(4'd0),.response_authorized(),
  .native_job(FRAME[31:0]),.native_gen(FRAME[35:32]),.native_token(FRAME[52:36]),.native_pos(FRAME[72:53]),
  .native_credit_empty(credit_empty),.lease_v({1'b0,retained,1'b0}),
  .borrower_quiet({1'b1,!busy,1'b1}),
  .lease_job({32'd0,held[31:0],32'd0}),.lease_gen({4'd0,held[35:32],4'd0}),
  .lease_token({17'd0,held[52:36],17'd0}),.lease_pos({20'd0,held[72:53],20'd0}),
  .lease_granted(grants),.release_v({1'b0,release_v,1'b0}),.release_r(releases),
  .release_job({32'd0,accept_frame[31:0],32'd0}),.release_gen({4'd0,accept_frame[35:32],4'd0}),
  .release_token({17'd0,accept_frame[52:36],17'd0}),.release_pos({20'd0,accept_frame[72:53],20'd0}),
  .req_v(4'd0),.req_rdy(),.req_we(4'd0),.req_addr(128'd0),.req_wdata(1024'd0),.req_wstrb(128'd0),.req_tag(64'd0),
  .rsp_v(),.rsp_rdy(4'd0),.rsp_we(),.rsp_tag(),.rsp_data(),
  .m_req_v(),.m_req_rdy(1'b0),.m_req_we(),.m_req_addr(),.m_req_wdata(),.m_req_wstrb(),.m_req_tag(),
  .m_rsp_v(1'b0),.m_rsp_rdy(),.m_rsp_we(1'b0),.m_rsp_tag(16'd0),.m_rsp_data(256'd0),
  .idle(bridge_idle),.fault(bridge_fault));
 ot_hbm_integrated_stage_join #(.ENABLE(1)) seat(
  .clk(clk),.por_n(por_n),.enroll_v(enroll),.enroll_r(),.enroll_frame(FRAME),
  .enroll_pc(32'h80000004),.enroll_op(32'd3),.enroll_source(16'd0),.enroll_expert(9'd65),
  .enroll_matrix(1'b0),.enroll_row(12'd0),.enroll_count(9'd2),
  .owner_valid(1'b1),.owner_frame(live_frame),.source_permit(grant),
  .start_v(start_v),.start_r(start_r),.finish_v(finished),.finish_r(finish_r),
  .producer_drained(producer_drained),.consumer_drained(consumer_drained||!issued),
  .complete_v(complete_v),.complete_r(caller_accept&&accept_frame==held&&release_r),
  .warm_req(warm),.warm_ack(warm_ack),.retained(retained),.issued(issued),
  .ce(),.due(),.fault(stage_fault),.held_frame(held),.held_pc(),.held_op(),
  .held_source(),.held_expert(),.held_matrix(),.held_row(),.held_count());
 // Literal candidate insertion Gibbs must install in selected parent.
 ot_hbm_accel_su_fused_vm #(.ENABLE(1),.KIND(3),.N(N),.D(D),.AW(AW),
   .PUBLISH_QUANT(1),.ROUTED(1),.ADOPTED_SWIGLU_QUANT_ONLY(1)) dut(
  .clk(clk),.rst_n(por_n),.cmd_valid(start_v),.cmd_ready(start_r),
  .source_ready(grant&&!revoke_source),.landing_reserved(retained),.busy(busy),.done(done),.fault(vm_fault),
  .job_id(held[31:0]),.held_frame(held),.q_frame(qframe),
  .xbase(10'd0),.ubase(10'd64),.wbase(10'd128),.ybase(10'd256),.gain_base(10'd0),
  .comb(512'd0),.post_pre(128'd0),.n_f(32'd0),.eps(32'd0),.lim(32'h41234567),
  .cos_t(32'd0),.sin_t(32'd0),.rd_addr(rd_addr),.rd_re(rd_re),.rd_src(rd_src),.rd_q(rd_q),
  .vm_we(vm_we),.vm_waddr(vm_waddr),.vm_wdata(vm_wdata),
  .q_valid(qv),.q_index(qi),.q_codes(codes),.q_exp(scales),.q_bf16(bf16),
  .completion_id(completion_id),.reserve_events(reserve_events));
 // Existing SU VM semantics: real one-cycle read by actual enables/addresses.
 always @(posedge clk) begin
  rd_q<='x;
  for(integer k=0;k<4*N;k=k+1)if(rd_re[k])begin
   if(!grant||rd_src[2*k+:2]!=0||rd_addr[k*AW+:AW]>128)
    $fatal(1,"read without actual VM lease/bounds/source");
   rd_q[32*k+:32]<=vm[rd_addr[k*AW+:AW]];
  end
 end
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin finished<=0;written<=0;checked<=0;read_pending<=0;packets<=0;acks<=0;end
  else begin
   if(bridge_fault||(!expect_fault&&vm_fault)||stage_fault)$fatal(1,"connected owner/VM fault");
   if(|vm_we)$fatal(1,"QDQ silently substituted for original prequant VM write");
   if(done)begin
    if(completion_id!==FRAME[31:0])$fatal(1,"completion job mismatch");finished<=1;
   end
   if(qv)begin
    if(!grant||qframe!==FRAME||qi>1||written[qi])$fatal(1,"quant launch/frame/cursor");
    for(integer k=0;k<N;k=k+1)begin
     if(codes[8*k+:8]!==(((qi*N+k)*13+7)&255) ||
        bf16[16*k+:16]!==(((qi*N+k)*29+16'h5a37)&65535))$fatal(1,"VM source golden mismatch %0d",k);
    end
    if(scales!==10'h205)$fatal(1,"real routing-weight/scaling mismatch");
    landing[qi]<={codes,scales,bf16};written[qi]<=1;read_pending[qi]<=1;packets<=packets+1;
   end
   // Real finite reserved landing writes/readback precede checked ACK/drain.
   // One actual landing read/checked ACK per edge, not parallel invented ports.
   if(readback_allow)for(integer b=1;b>=0;b=b-1)if(read_pending[b]&&(b==0||!read_pending[0]))begin
    for(integer k=0;k<N;k=k+1)
     if(landing[b][522+8*k+:8]!==(((b*N+k)*13+7)&255)||
        landing[b][16*k+:16]!==(((b*N+k)*29+16'h5a37)&65535))$fatal(1,"landing readback mismatch");
    if(landing[b][512+:10]!==10'h205)$fatal(1,"scale readback mismatch");
    checked[b]<=1;read_pending[b]<=0;acks<=acks+1;
   end
  end
 end
 task tick;begin @(posedge clk);#1;end endtask
 task negstep;begin @(negedge clk);#1;end endtask
 initial begin
  for(integer k=0;k<512;k=k+1)vm[k]=32'hffffffff;
  for(integer k=0;k<D;k=k+1)begin
   vm[k]=32'h31000000|((k*13+7)&255);
   vm[64+k]=32'h42000000|((k*29+16'h5a37)&65535);
  end
  vm[128]=32'h53000205;
  tick();negstep();por_n=1;enroll=1;tick();negstep();enroll=0;
  wait(|rd_re);negstep();warm=1;
  wait(finished);repeat(3)tick();
  if(packets!=2||written!=3||complete_v||!grant||!retained||warm_ack)
   $fatal(1,"producer done erased pending landing debt under warm");
  negstep();readback_allow=1;
  wait(complete_v);negstep();readback_allow=0;
  // TOKEN17/POS20 completion negatives retain real lease; not raw frame copies.
  accept_frame=FRAME^(73'd1<<52);caller_accept=1;tick();
  if(!grant||!retained||release_v||warm_ack)$fatal(1,"foreign TOKEN17 completion released");
  negstep();accept_frame=FRAME^(73'd1<<72);tick();
  if(!grant||!retained||release_v||warm_ack)$fatal(1,"foreign POS20 completion released");
  negstep();caller_accept=0;accept_frame=FRAME;repeat(3)tick();
  if(!complete_v||!grant)$fatal(1,"completion not persistent");
  negstep();caller_accept=1;tick();negstep();caller_accept=0;repeat(3)tick();
  if(retained||grant||!bridge_idle||!warm_ack||checked!=3)
   $fatal(1,"joint lease/landing/stage warm drain failed");
  negstep();por_n=0;warm=0;tick();negstep();por_n=1;enroll=1;tick();negstep();enroll=0;
  wait(|rd_re);negstep();expect_fault=1;revoke_source=1;tick();
  if(!vm_fault||!busy||!grant||!retained||complete_v||release_v)
   $fatal(1,"withdrawn accepted source lease silently completed/dropped debt");
  $display("PASS_CONNECTED_VM_SWIGLU N32 D64 full73 actual protected lease, 2 ordered VM-source packets, checked landing, warm debt, TOKEN17/POS20 reject, joint release");
  $finish;
 end
endmodule
