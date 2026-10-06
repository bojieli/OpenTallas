`timescale 1ps/1fs
module tb_native_quarter_publication;
 wire checker_gate_done; tb_w2_bank_check_pipeline checker_gate(clk_sm,checker_gate_done);
 integer edge_count=0; always @(posedge clk_sm) edge_count<=edge_count+1;
 always @(posedge clk_sm) if(q_ack_v && ack_gate) $display("CALENDAR_QUARTER_ACK edge=%0d",edge_count);
 always @(posedge clk_sm) if(activation_release && activation_release_r) $display("CALENDAR_PARENT_RELEASE edge=%0d",edge_count);
 always @(posedge clk_sm) if(warm_ack) $display("CALENDAR_WARM_ACK edge=%0d",edge_count);
 reg  clk_sm=0;
 reg  por_n=0;
 reg  warm_req=0;
 reg  bind_v=0;
 wire  bind_r;
 reg [72:0] bind_frame=0;
 reg [6:0] bind_rank=0;
 reg [31:0] bind_base=0;
 reg [31:0] bind_span=0;
 reg  retire_v=0;
 wire  retire_r;
 reg [72:0] retire_frame=0;
 wire [72:0] held_frame;
 wire  retained;
 wire  warm_ack;
 wire  fault;
 reg  activation_wr_v=0;
 wire  activation_wr_r;
 reg [72:0] activation_wr_frame=0;
 reg  activation_wr_bank=0;
 reg [6:0] activation_wr_addr=0;
 reg [2062:0] activation_wr_data=0;
 reg [191:0] activation_wr_owner=0;
 wire  activation_ACK_v;
 reg  activation_ACK_r=0;
 wire [72:0] activation_ACK_frame;
 wire [191:0] activation_ACK_owner;
 reg  activation_rd_v=0;
 wire  activation_rd_r;
 reg [72:0] activation_rd_frame=0;
 reg  activation_rd_bank=0;
 reg [6:0] activation_rd_addr=0;
 reg [191:0] activation_rd_owner=0;
 wire [3:0] tap_v;
 wire [3:0] tap_r; reg [2:0] other_r=0; wire q_r; assign tap_r={other_r,q_r};
 wire [4*2063-1:0] tap_data;
 wire [4*192-1:0] tap_owner;
 wire [4*73-1:0] tap_frame;
 wire [3:0] tap_source_clk;
 wire [3:0] tap_ACK_v; reg [2:0] other_ack=0; wire q_ack_v; reg ack_gate=0; assign tap_ACK_v={other_ack,q_ack_v&&ack_gate};
 wire [3:0] tap_ACK_r;
 wire [4*192-1:0] tap_ACK_owner; reg [3*192-1:0] other_owner=0; wire [191:0] q_owner; assign tap_ACK_owner={other_owner,q_owner};
 wire [4*73-1:0] tap_ACK_frame; reg [3*73-1:0] other_frame=0; wire [72:0] q_frame; assign tap_ACK_frame={other_frame,q_frame};
 wire  activation_release;
 reg  activation_release_r=0;
 wire [72:0] activation_release_frame;
 wire [191:0] activation_release_owner;
 reg  su_pub_v=0;
 wire  su_pub_r;
 reg [72:0] su_pub_frame=0;
 reg [31:0] su_pub_addr=0;
 reg [1023:0] su_pub_data=0;
 wire  su_ACK_v;
 reg  su_ACK_r=0;
 reg  result_pub_v=0;
 wire  result_pub_r;
 reg [72:0] result_pub_frame=0;
 reg [31:0] result_pub_addr=0;
 reg [1023:0] result_pub_data=0;
 wire  result_ACK_v;
 reg  result_ACK_r=0;
 wire [31:0] publication_ACK_addr;
 wire [72:0] publication_ACK_frame;
 reg  index_read_v=0;
 wire  index_read_r;
 reg [72:0] index_read_frame=0;
 reg [6:0] index_read_rank=0;
 reg [31:0] index_read_addr=0;
 reg [5:0] index_read_words=0;
 reg [7:0] index_read_tag=0;
 wire  index_rsp_v;
 reg  index_rsp_r=0;
 wire [1023:0] index_rsp_data;
 wire [7:0] index_rsp_tag;
 wire [72:0] index_rsp_frame;
 wire [6:0] index_rsp_rank;
 always #416.666 clk_sm=~clk_sm;
 ot_hbm_vm_publication_parent #(.ENABLE(1)) dut(
 .clk_sm(clk_sm),
 .por_n(por_n),
 .warm_req(warm_req),
 .bind_v(bind_v),
 .bind_r(bind_r),
 .bind_frame(bind_frame),
 .bind_rank(bind_rank),
 .bind_base(bind_base),
 .bind_span(bind_span),
 .retire_v(retire_v),
 .retire_r(retire_r),
 .retire_frame(retire_frame),
 .held_frame(held_frame),
 .retained(retained),
 .warm_ack(warm_ack),
 .fault(fault),
 .activation_wr_v(activation_wr_v),
 .activation_wr_r(activation_wr_r),
 .activation_wr_frame(activation_wr_frame),
 .activation_wr_bank(activation_wr_bank),
 .activation_wr_addr(activation_wr_addr),
 .activation_wr_data(activation_wr_data),
 .activation_wr_owner(activation_wr_owner),
 .activation_ACK_v(activation_ACK_v),
 .activation_ACK_r(activation_ACK_r),
 .activation_ACK_frame(activation_ACK_frame),
 .activation_ACK_owner(activation_ACK_owner),
 .activation_rd_v(activation_rd_v),
 .activation_rd_r(activation_rd_r),
 .activation_rd_frame(activation_rd_frame),
 .activation_rd_bank(activation_rd_bank),
 .activation_rd_addr(activation_rd_addr),
 .activation_rd_owner(activation_rd_owner),
 .tap_v(tap_v),
 .tap_r(tap_r),
 .tap_data(tap_data),
 .tap_owner(tap_owner),
 .tap_frame(tap_frame),
 .tap_source_clk(tap_source_clk),
 .tap_ACK_v(tap_ACK_v),
 .tap_ACK_r(tap_ACK_r),
 .tap_ACK_owner(tap_ACK_owner),
 .tap_ACK_frame(tap_ACK_frame),
 .activation_release(activation_release),
 .activation_release_r(activation_release_r),
 .activation_release_frame(activation_release_frame),
 .activation_release_owner(activation_release_owner),
 .su_pub_v(su_pub_v),
 .su_pub_r(su_pub_r),
 .su_pub_frame(su_pub_frame),
 .su_pub_addr(su_pub_addr),
 .su_pub_data(su_pub_data),
 .su_ACK_v(su_ACK_v),
 .su_ACK_r(su_ACK_r),
 .result_pub_v(result_pub_v),
 .result_pub_r(result_pub_r),
 .result_pub_frame(result_pub_frame),
 .result_pub_addr(result_pub_addr),
 .result_pub_data(result_pub_data),
 .result_ACK_v(result_ACK_v),
 .result_ACK_r(result_ACK_r),
 .publication_ACK_addr(publication_ACK_addr),
 .publication_ACK_frame(publication_ACK_frame),
 .index_read_v(index_read_v),
 .index_read_r(index_read_r),
 .index_read_frame(index_read_frame),
 .index_read_rank(index_read_rank),
 .index_read_addr(index_read_addr),
 .index_read_words(index_read_words),
 .index_read_tag(index_read_tag),
 .index_rsp_v(index_rsp_v),
 .index_rsp_r(index_rsp_r),
 .index_rsp_data(index_rsp_data),
 .index_rsp_tag(index_rsp_tag),
 .index_rsp_frame(index_rsp_frame),
 .index_rsp_rank(index_rsp_rank));
 localparam [72:0] F={20'habcde,17'h1ffff,4'hb,32'hfeed1234};
 // Explicit TEST identity only; production Gibbs issuer is still absent.
 localparam [191:0] O={64'hb0123456789abcde,64'h0011223344556677,64'h8899aabbccddeeff};
 localparam [2062:0] X={2063{1'b1}} ^ (2063'(64'h812345679abcdef0));
 wire [7:0] sm_v;reg [7:0] sm_r=0,sm_ack=0;
 wire [8*2063-1:0] sm_data;wire [8*192-1:0] sm_owner;wire [8*73-1:0] sm_frame;
 reg [8*192-1:0] ack_owner=0;reg [8*73-1:0] ack_frame=0;
 wire chain_empty,chain_warm,chain_fault,chain_pause;wire [3:0] forwarded;
 ot_hbm_native_quarter_chain #(.ENABLE(1)) chain(
  .clk_sm(clk_sm),.por_n(por_n),.warm_req(warm_req),
  .tap_v(tap_v[0]),.tap_r(q_r),.tap_data(tap_data[0+:2063]),.tap_owner(tap_owner[0+:192]),.tap_frame(tap_frame[0+:73]),
  .tap_ACK_v(q_ack_v),.tap_ACK_r(tap_ACK_r[0]&&ack_gate),.tap_ACK_owner(q_owner),.tap_ACK_frame(q_frame),
  .sm_v(sm_v),.sm_r(sm_r),.sm_data(sm_data),.sm_owner(sm_owner),.sm_frame(sm_frame),
  .sm_ACK_v(sm_ack),.sm_ACK_owner(ack_owner),.sm_ACK_frame(ack_frame),
  .fclk_o(forwarded),.drained(chain_empty),.warm_drained(chain_warm),.paused(chain_pause),.fault(chain_fault));
 reg [7:0] accepted=0;integer sends=0,quarter_acks=0,checks=0;reg negative=0;
 always @(posedge clk_sm)begin
  if(!por_n)begin accepted<=0;sends=0;quarter_acks=0;end
  else begin
   if((fault||chain_fault)&&!negative)$fatal(1,"unexpected parent/chain fault");
   for(integer i=0;i<8;i++)if(sm_v[i]&&sm_r[i])begin
    if(accepted[i]||sm_data[i*2063+:2063]!==X||sm_owner[i*192+:192]!==O||sm_frame[i*73+:73]!==F)
      $fatal(1,"duplicate or mismatched actual SM tap i=%0d",i);
    accepted[i]<=1;sends++;
   end
   if(tap_ACK_v[0]&&tap_ACK_r[0])quarter_acks++;
  end
 end
 task cold;
  begin por_n=0;warm_req=0;sm_ack=0;other_ack=0;ack_gate=0;sm_r=0;other_r=0;
   repeat(3)@(negedge clk_sm);por_n=1;repeat(2)@(negedge clk_sm);end
 endtask
 task launch;
  begin
   bind_v=1;bind_frame=F;bind_rank=65;bind_base=64;bind_span=8224;
   do @(posedge clk_sm);while(!bind_r);@(negedge clk_sm);bind_v=0;
   activation_wr_frame=F;activation_wr_bank=1;activation_wr_addr=127;activation_wr_data=X;activation_wr_owner=O;activation_wr_v=1;
   do @(posedge clk_sm);while(!activation_wr_r);@(negedge clk_sm);activation_wr_v=0;
   wait(activation_ACK_v);if(activation_ACK_frame!==F||activation_ACK_owner!==O)$fatal(1,"provider write receipt");
   activation_ACK_r=1;@(posedge clk_sm);@(negedge clk_sm);activation_ACK_r=0;
   activation_rd_frame=F;activation_rd_bank=1;activation_rd_addr=127;activation_rd_owner=O;activation_rd_v=1;
   do @(posedge clk_sm);while(!activation_rd_r);@(negedge clk_sm);activation_rd_v=0;
   // Actual parent accepts before warm; owed publication must continue.
   warm_req=1;sm_r=8'hff;other_r=3'b111;
   wait(accepted==8'hff);@(negedge clk_sm);sm_r=0;other_r=0;
   if(sends!=8||q_ack_v||activation_release||warm_ack||chain_warm)$fatal(1,"acceptance fabricated terminal ACK");checks++;
   for(integer i=0;i<8;i++)begin ack_owner[i*192+:192]=O;ack_frame[i*73+:73]=F;end
   for(integer i=0;i<3;i++)begin other_owner[i*192+:192]=O;other_frame[i*73+:73]=F;end
  end
 endtask
 initial begin
  wait(checker_gate_done); cold;launch;
  // Actual visibility receipt per SM, terminal columns first. No delay ACK.
  for(integer i=7;i>=0;i--)begin
   if(i==0)chain.stage[0].u_station.held.u_receipt.u_state.code[0][0]=~chain.stage[0].u_station.held.u_receipt.u_state.code[0][0];
   sm_ack=8'b1<<i;@(posedge clk_sm);@(negedge clk_sm);sm_ack=0;
   repeat(3)@(negedge clk_sm);
   if(i>0&&(q_ack_v||activation_release))$fatal(1,"partial receipts retired root");
   checks++;
  end
  repeat(12)@(negedge clk_sm);
  if(!q_ack_v)$fatal(1,"empty receipt CE lost unbackpressurable release after final ACK and completed repair");
  // CE in held full-frame reverse seat while parent backpressures ACK.
  chain.stage[0].u_station.held.u_receipt.u_state.code[0][0]=~chain.stage[0].u_station.held.u_receipt.u_state.code[0][0];
  @(negedge clk_sm);wait(q_ack_v);
  repeat(4)begin @(negedge clk_sm);
   if(!q_ack_v||q_frame!==F||q_owner!==O||chain_empty||chain_warm||activation_release||warm_ack)
    $fatal(1,"held full73 receipt lost across repair/warm/backpressure");checks++;
  end
  ack_gate=1;other_ack=3'b111;
  do @(posedge clk_sm);while(tap_ACK_r!==4'hf);@(negedge clk_sm);other_ack=0;ack_gate=0;
  wait(activation_release);repeat(3)begin @(negedge clk_sm);
   if(activation_release_frame!==F||activation_release_owner!==O||warm_ack||quarter_acks!=1)
    $fatal(1,"parent release identity/conservation");checks++;
  end
  activation_release_r=1;@(posedge clk_sm);@(negedge clk_sm);activation_release_r=0;
  retire_frame=F;retire_v=1;
  do @(posedge clk_sm);while(!retire_r);@(negedge clk_sm);retire_v=0;
  wait(warm_ack);if(!chain_warm||!chain_empty)$fatal(1,"chain debt did not drain");checks++;
  // Real full-frame negative: token16 is bit52. No truncation to native63.
  negative=1;cold;launch;
  ack_frame[0+:73]=F^(73'd1<<52);sm_ack=1;
  @(posedge clk_sm);@(negedge clk_sm);sm_ack=0;
  repeat(6)@(negedge clk_sm);
  if(!chain_fault||q_ack_v||q_r||chain_warm||chain_empty||activation_release||warm_ack||!retained)
    $fatal(1,"wrong full73 receipt fabricated retirement");checks++;
  $display("PASS_NATIVE_QUARTER_PUBLICATION seed=1062026 fanouts=3/3/3/2 sm=8 full73=1 owner192=1 checks=%0d heldACK_CE=1 emptyACK_CE=1 warm_debt=1 token16_negative=1 provider_macros=32 extra_macros=0",checks);
  $finish;
 end
endmodule
