`timescale 1ps/1fs
// Changed provider join, real SFU64, existing Carson golden vectors unchanged.
module tb_hbm_integrated_sfu_provider_join;
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
 ot_hbm_integrated_sfu_provider_join #(.ENABLE(1)) dut(
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
 begin negstep();por_n=0;warm_req=0;enroll_v=0;publication_r=0;corrupt_readback=0;
 repeat(3)tick();negstep();por_n=1;tick();end endtask
 task start(input integer case_i,input integer pos);
 begin
  negstep();frame={20'(pos),17'h10001,4'h9,32'hca001234};publication_owner=frame;
  fn=requests[case_i][2050:2048];local_tag=requests[case_i][2082:2051];#1;
  for(j=0;j<8;j=j+1)memory[j]=requests[case_i][j*256+:256];
  if(!enroll_r)$fatal(1,"NO_REAL_ENROLL");enroll_v=1;tick();negstep();enroll_v=0;
 end endtask
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR_REQUIRED");
  $readmemh({dir,"/sfu_req.mem"},requests);$readmemh({dir,"/sfu_exp.mem"},expected);
  reset();
  for(k=0;k<10;k=k+1)begin
   start(k,k%2?8191:1048575);
   w=0;while(!publication_v)begin
    tick();w=w+1;if(fault||bridge_fault||w>4000)$fatal(1,"JOIN_FAILURE case=%0d phase=%0d fault=%0d",k,dut.g_on.phase,fault);
    // Warm during an already admitted provider operation must drain that op.
    if(k==3&&reads==49)begin negstep();warm_req=1;end
   end
   for(j=0;j<8;j=j+1)if(memory[8+j]!==expected[k][j*256+:256])
    $fatal(1,"FIRST_NUMERICAL_MISMATCH case=%0d sector=%0d got=%h expected=%h",k,j,memory[8+j],expected[k][j*256+:256]);
   if(reads!=16*(k+1)||writes!=8*(k+1)||held_frame!==frame)$fatal(1,"PUBLICATION_DEBT_COUNT");
   repeat(5)tick();if(!publication_v||!retained)$fatal(1,"HELD_PUBLICATION_LOST");
   negstep();publication_r=1;tick();negstep();publication_r=0;tick();
   if(retained||grant||acks!=k+1)$fatal(1,"REVERSE_ACK_RETIRE");
   if(warm_req)begin if(!warm_ack)$fatal(1,"WARM_DRAIN");negstep();warm_req=0;tick();end
   checked=checked+64;
  end
  // True source readback corruption must retain owner and suppress publication.
  reset();start(0,1048575);negstep();corrupt_readback=1;w=0;
  while(!fault)begin tick();w=w+1;if(w>4000)$fatal(1,"NO_READBACK_REFUSAL");end
  if(publication_v||req_v||release_v||!retained)$fatal(1,"FALSE_PUBLICATION_ON_READBACK_MISMATCH");
  // Full TOKEN17 is part of publication authority, not just local_tag32.
  reset();start(1,8191);w=0;
  while(!publication_v)begin tick();w=w+1;if(fault||w>4000)$fatal(1,"TOKEN_NEGATIVE_SETUP");end
  negstep();publication_owner=frame^(73'b1<<52);publication_r=1;tick();negstep();publication_r=0;
  if(!fault||!retained||release_v||!grant)$fatal(1,"TOKEN17_WRONG_PUBLICATION_ACCEPTED");
  // Real mutable landing-seat two-bit UE: no issue/release/publication permission.
  reset();start(2,1048575);tick();negstep();dut.g_on.io_state.code[0]^=72'd3;
  #1;if(!due||!fault||req_v||publication_v||release_v||!retained)$fatal(1,"IO_SRAM_UE_PERMISSION");
  $display("SFU_PROVIDER_JOIN_PASS lanes=%0d DS1M_pos=1048575 QWEN8K_pos=8191 warm_and_readback_negative=PASS",checked);$finish;
 end
endmodule
