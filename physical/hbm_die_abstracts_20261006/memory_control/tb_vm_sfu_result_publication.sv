`timescale 1ps/1fs
// New result-publication mechanism component gate; real VM parent/SRAM,
// arbitrary-bit framed producer fixture, no SFU numerical/clock qualification.
module tb_vm_sfu_result_publication;
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
 wire  result_pub_v;
 wire  result_pub_r;
 wire [72:0] result_pub_frame;
 wire [31:0] result_pub_addr;
 wire [1023:0] result_pub_data;
 wire  result_ACK_v;
 wire  result_ACK_r;
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
 reg enroll_v=0;wire enroll_r;reg [72:0] enroll_frame;
 reg [31:0] enroll_base_word,enroll_tag;
 reg rx_v=0;wire rx_r;reg [1023:0] rx_data;
 reg [72:0] rx_frame;reg [3:0] rx_index;reg rx_last;
 wire publication_done,complete_v,publisher_retained,publisher_drained,publisher_fault,publisher_warm;
 reg complete_r=0,inject_ACK=0;wire [72:0] complete_frame;wire [31:0] complete_tag;
 wire [72:0] checked_ACK_frame=publication_ACK_frame^(inject_ACK?(73'd1<<52):73'd0);
 ot_hbm_vm_sfu_result_publication #(.ENABLE(1)) u_publisher(
 .clk_sm(clk_sm),.por_n(por_n),.warm_req(warm_req),.warm_ack(publisher_warm),
 .enroll_v(enroll_v),.enroll_r(enroll_r),.enroll_frame(enroll_frame),.enroll_base_word(enroll_base_word),.enroll_tag(enroll_tag),
 .owner_valid(retained&&!fault),.owner_frame(held_frame),
 .rx_v(rx_v),.rx_r(rx_r),.rx_data(rx_data),.rx_frame(rx_frame),.rx_index(rx_index),.rx_last(rx_last),
 .result_pub_v(result_pub_v),.result_pub_r(result_pub_r),.result_pub_data(result_pub_data),.result_pub_frame(result_pub_frame),.result_pub_addr(result_pub_addr),
 .result_ACK_v(result_ACK_v),.result_ACK_r(result_ACK_r),.result_ACK_frame(checked_ACK_frame),.result_ACK_addr(publication_ACK_addr),
 .publication_done(publication_done),.complete_v(complete_v),.complete_r(complete_r),.complete_frame(complete_frame),.complete_tag(complete_tag),
 .retained(publisher_retained),.drained(publisher_drained),.fault(publisher_fault));
 integer publications=0,ACKs=0,checks=0;
 reg [2047:0] payload;reg [1023:0] held_payload;
 always @(posedge clk_sm)if(por_n)begin
  if(result_pub_v&&result_pub_r)begin
   if(result_pub_frame!==bind_frame||result_pub_addr!==bind_base+32'(32*publications))$fatal(1,"native publication address/frame mismatch");
   if(result_pub_data!==payload[1024*publications+:1024])$fatal(1,"native publication payload mismatch");
   publications<=publications+1;
  end
  if(result_ACK_v&&result_ACK_r)ACKs<=ACKs+1;
  if(publication_done&&(publications!=2||ACKs!=2))$fatal(1,"completion before both actual SRAM receipts");
 end
 task tick;begin @(posedge clk_sm);#1;@(negedge clk_sm);end endtask
 task beat(input integer index,input [1023:0] bits);begin
  rx_index=4'(index);rx_last=index==2;rx_data=bits;rx_frame=bind_frame;rx_v=1;#1;
  if(!rx_r)$fatal(1,"matched framed result refused");
  tick();rx_v=0;
 end endtask
 task read_row(input integer offset);begin
  index_read_frame=bind_frame;index_read_rank=bind_rank;index_read_addr=bind_base+32'(offset);index_read_words=32;index_read_tag=8'(offset+3);index_read_v=1;
  wait(index_read_r);@(negedge clk_sm);tick();index_read_v=0;
  wait(index_rsp_v);@(negedge clk_sm);
  if(index_rsp_frame!==bind_frame||index_rsp_rank!==bind_rank||index_rsp_tag!==index_read_tag||index_rsp_data!==payload[32*offset+:1024])$fatal(1,"actual SRAM readback differs64 FP32 results");
  for(integer lane=0;lane<32;lane++)begin
   if(index_rsp_data[32*lane+:32]!==payload[32*(offset+lane)+:32])$fatal(1,"FP32 bitpattern changed");checks++;
  end
  held_payload=index_rsp_data;repeat(3)begin tick();if(!index_rsp_v||index_rsp_data!==held_payload)$fatal(1,"held native read response changed");end
  index_rsp_r=1;tick();index_rsp_r=0;
 end endtask
 initial begin
  bind_frame={20'hfffff,17'h10001,4'hd,32'h2468ace0};bind_rank=95;bind_base=32'h2000;bind_span=64;
  enroll_frame=bind_frame;enroll_base_word=bind_base;enroll_tag=32'hfacedead;
  for(integer lane=0;lane<64;lane++)payload[32*lane+:32]=32'h3f012345^32'(lane*32'h1050801);
  por_n=0;repeat(2)tick();por_n=1;repeat(3)tick();
  bind_v=1;#1;if(!bind_r)$fatal(1,"real bounded VM allocation refused");tick();bind_v=0;
  enroll_v=1;#1;if(!enroll_r)$fatal(1,"real held VM frame enrollment refused");tick();enroll_v=0;
  beat(0,payload[1023:0]);beat(1,payload[2047:1024]);
  repeat(4)begin tick();if(result_pub_v||publications||ACKs||complete_v)$fatal(1,"unvalidated SFU tail published payload");end
  if($test$plusargs("TAIL_ERROR"))begin
   beat(2,{991'b0,enroll_tag,1'b1});tick();
   if(!publisher_fault||!publisher_retained||result_pub_v||complete_v||publications||ACKs)$fatal(1,"real error tail published speculative rows");
   $display("PASS_SFU_RESULT_ERROR_REFUSED no_native_write no_ACK retained_full73");$finish;
  end
  beat(2,{991'b0,enroll_tag,1'b0});
  if($test$plusargs("ACK_TOKEN"))begin
   wait(result_ACK_v);@(negedge clk_sm);inject_ACK=1;#1;
   if(result_ACK_r)$fatal(1,"wrong full73 ACK accepted");tick();
   if(!publisher_fault||!publisher_retained||complete_v||ACKs!=0||!retained)$fatal(1,"wrong ACK dropped result/lease debt");
   $display("PASS_SFU_RESULT_ACK_TOKEN_REFUSED real_SRAM_ACK_high_TOKEN17_quarantined");$finish;
  end
  wait(complete_v);@(negedge clk_sm);
  if(fault||publisher_fault||complete_frame!==bind_frame||complete_tag!==enroll_tag||publications!=2||ACKs!=2)$fatal(1,"publication completed without actual matched SRAM ACKs");
  repeat(4)begin tick();if(!complete_v||!publisher_retained)$fatal(1,"held publication completion lost");end
  complete_r=1;tick();complete_r=0;
  read_row(0);read_row(32);
  if(checks!=64||!publisher_drained)$fatal(1,"finite 64FP32 check/drain failed");
  $display("PASS_NATIVE_SFU_RESULT_PUBLICATION 3framedbeats 2real_SRAM_publications 2readback_ACKs 64FP32checks full73 heldcompletion no_pretail_publish");$finish;
 end
endmodule
