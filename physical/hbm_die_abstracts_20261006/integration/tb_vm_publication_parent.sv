`timescale 1ps/1fs
module tb_vm_publication_parent;
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
 reg [3:0] tap_r=0;
 wire [4*2063-1:0] tap_data;
 wire [4*192-1:0] tap_owner;
 wire [4*73-1:0] tap_frame;
 wire [3:0] tap_source_clk;
 reg [3:0] tap_ACK_v=0;
 wire [3:0] tap_ACK_r;
 reg [4*192-1:0] tap_ACK_owner=0;
 reg [4*73-1:0] tap_ACK_frame=0;
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
 localparam [191:0] OWNER=192'hb0123456789abcdef00112233445566778899aabbccddeeff;
 localparam [2062:0] X={2063{1'b1}} ^ (2063'(64'h812345679abcdef0));
 localparam [1023:0] S={32{32'h3f812345}},R={32{32'hbf012345}};
 integer comparisons=0,root_sends=0,root_acks=0,pub_acks=0;
 task cold;
  begin por_n=0;repeat(3)@(negedge clk_sm);por_n=1;repeat(2)@(negedge clk_sm);end
 endtask
 task bind_context;
  begin bind_frame=F;bind_rank=65;bind_base=64;bind_span=8224;bind_v=1;
   do @(posedge clk_sm);while(!bind_r);@(negedge clk_sm);bind_v=0;
   if(held_frame!==F||!retained||fault)$fatal(1,"full73 frame bind failed");comparisons++;
  end
 endtask
 task read_word(input [31:0] address,input [1023:0] expected,input [7:0] tag);
  begin index_read_frame=F;index_read_rank=65;index_read_addr=address;index_read_words=32;index_read_tag=tag;index_read_v=1;
   do @(posedge clk_sm);while(!index_read_r);@(negedge clk_sm);index_read_v=0;
   wait(index_rsp_v);repeat(3)begin @(negedge clk_sm);
    if(!index_rsp_v||index_rsp_data!==expected||index_rsp_frame!==F||index_rsp_tag!==tag||index_rsp_rank!=65)$fatal(1,"actual SRAM held frame/response mismatch");comparisons++;
   end
   index_rsp_r=1;@(posedge clk_sm);@(negedge clk_sm);index_rsp_r=0;
  end
 endtask
 always @(posedge clk_sm)if(por_n)begin
  if(fault&&!(negative))$fatal(1,"unexpected parent fault");
  for(integer k=0;k<4;k++)begin
   if(tap_v[k]&&tap_r[k])begin
    if(tap_data[k*2063+:2063]!==X||tap_owner[k*192+:192]!==OWNER||tap_frame[k*73+:73]!==F)$fatal(1,"native multicast content/frame");
    root_sends++;
   end
   if(tap_ACK_v[k]&&tap_ACK_r[k])root_acks++;
  end
  if(su_ACK_v&&su_ACK_r)pub_acks++;
  if(result_ACK_v&&result_ACK_r)pub_acks++;
 end
 reg negative=0;
 initial begin
  cold;bind_context;
  activation_wr_frame=F;activation_wr_bank=1;activation_wr_addr=127;activation_wr_data=X;activation_wr_owner=OWNER;activation_wr_v=1;
  do @(posedge clk_sm);while(!activation_wr_r);@(negedge clk_sm);activation_wr_v=0;
  wait(activation_ACK_v);repeat(3)begin @(negedge clk_sm);
   if(!activation_ACK_v||activation_ACK_frame!==F||activation_ACK_owner!==OWNER)$fatal(1,"checked activation publication lost");comparisons++;
  end
  activation_ACK_r=1;@(posedge clk_sm);@(negedge clk_sm);activation_ACK_r=0;
  // Both real publishers compete for the one existing provider write port.
  su_pub_v=1;su_pub_frame=F;su_pub_addr=64;su_pub_data=S;
  result_pub_v=1;result_pub_frame=F;result_pub_addr=96;result_pub_data=R;
  do begin @(posedge clk_sm);if(result_pub_r)$fatal(1,"SU priority changed");end while(!su_pub_r);
  @(negedge clk_sm);su_pub_v=0;
  wait(su_ACK_v);repeat(3)begin @(negedge clk_sm);
   if(!su_ACK_v||result_ACK_v||publication_ACK_addr!=64||publication_ACK_frame!==F)$fatal(1,"publisher seat/ACK incorrect");comparisons++;
  end
  su_ACK_r=1;@(posedge clk_sm);@(negedge clk_sm);su_ACK_r=0;
  do @(posedge clk_sm);while(!result_pub_r);@(negedge clk_sm);result_pub_v=0;
  wait(result_ACK_v);if(publication_ACK_addr!=96||publication_ACK_frame!==F)$fatal(1,"result publication wrong source");comparisons++;
  result_ACK_r=1;@(posedge clk_sm);@(negedge clk_sm);result_ACK_r=0;
  read_word(64,S,8'hff);read_word(96,R,8'h81);
  activation_rd_frame=F;activation_rd_bank=1;activation_rd_addr=127;activation_rd_owner=OWNER;activation_rd_v=1;
  do @(posedge clk_sm);while(!activation_rd_r);@(negedge clk_sm);activation_rd_v=0;
  wait(|tap_v);repeat(3)@(negedge clk_sm);tap_r=4'hf;
  @(posedge clk_sm);@(negedge clk_sm);tap_r=0;
  if(root_sends!=4)$fatal(1,"not all four real branches sent");
  warm_req=1;
  // Parent CE must not discard an already owed reverse receipt.
  dut.on.descriptor.code[0][0]=~dut.on.descriptor.code[0][0];
  for(integer k=0;k<4;k++)begin tap_ACK_owner[k*192+:192]=OWNER;tap_ACK_frame[k*73+:73]=F;end
  tap_ACK_v=4'hf;
  do @(posedge clk_sm);while(tap_ACK_r!==4'hf);@(negedge clk_sm);tap_ACK_v=0;
  wait(dut.on.root_release);@(negedge clk_sm);
  // Empty completion-seat CE coincident with the unbackpressurable child pulse.
  dut.on.release_code[0][0]=~dut.on.release_code[0][0];
  wait(activation_release);
  retire_v=1;retire_frame=F;
  repeat(3)begin @(negedge clk_sm);
   if(warm_ack||retire_r||!activation_release||activation_release_frame!==F||activation_release_owner!==OWNER)$fatal(1,"release pulse/debt lost during repair or warm");comparisons++;
  end
  activation_release_r=1;@(posedge clk_sm);@(negedge clk_sm);activation_release_r=0;
  do @(posedge clk_sm);while(!retire_r);@(negedge clk_sm);retire_v=0;
  wait(warm_ack);if(root_acks!=4||pub_acks!=2||fault)$fatal(1,"actual retirement conservation");
  warm_req=0;repeat(2)@(negedge clk_sm);
  // Same child owner, new context: old SRAM bytes must not gain fresh validity.
  bind_context;negative=1;activation_rd_v=1;
  @(posedge clk_sm);@(negedge clk_sm);
  if(!fault||activation_rd_r||(|tap_v)||!retained)$fatal(1,"old context activation republished");comparisons++;
  activation_rd_v=0;cold;bind_context;
  su_pub_frame=F ^ (73'd1<<52);su_pub_v=1;
  @(posedge clk_sm);@(negedge clk_sm);
  if(!fault||su_pub_r||su_ACK_v||!retained)$fatal(1,"token16 truncated in native63 provider join");comparisons++;
  su_pub_v=0;cold;bind_context;
  index_read_frame=F ^ (73'd1<<72);index_read_v=1;
  @(posedge clk_sm);@(negedge clk_sm);
  if(!fault||index_read_r||index_rsp_v||!retained)$fatal(1,"position19 truncated");comparisons++;
  index_read_v=0;cold;bind_context;
  dut.on.descriptor.code[0][0]=~dut.on.descriptor.code[0][0];
  dut.on.descriptor.code[0][1]=~dut.on.descriptor.code[0][1];
  @(negedge clk_sm);
  if(!fault||bind_r||su_pub_r||index_read_r||!retained)$fatal(1,"descriptor UE fabricated permissions");comparisons++;
  $display("PASS_VM_PUBLICATION_PARENT comparisons=%0d sends=%0d reverseACK=%0d pubACK=%0d full73=1 CEarrival=1 warmdebt=1 staleactivation_refused=1 token16_refused=1 position19_refused=1 DUE_refused=1",comparisons,root_sends,root_acks,pub_acks);
  $finish;
 end
endmodule
