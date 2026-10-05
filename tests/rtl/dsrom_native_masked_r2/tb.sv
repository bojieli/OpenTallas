`timescale 1ns/1ps
module tb;
 localparam T=227;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0,rd_v=0; reg [14:0] rd_base_word=0;
 reg [T-1:0] rd_owner=0; wire rd_accept_v,rd_out_v;
 wire [1:0] rd_out_rot; wire [2047:0] rd_out_bank_words; wire [T-1:0] rd_out_owner;
 wire rd_fault,wr_fault,rw_collision_fault;
 reg [3:0] wr_v=0; reg [59:0] wr_word_addr=0; reg [2047:0] wr_word_data=0;
 reg [63:0] wr_lane_mask=0; reg [4*T-1:0] wr_owner=0;
 wire [3:0] wr_accept_v,wr_ack_v; wire [4*T-1:0] wr_ack_owner;
 wire [59:0] wr_ack_word_addr; wire [63:0] wr_ack_lane_mask;
 reg [2047:0] expected_words=0; integer cases=0;
 `DUT #(.MASKED_VISIBLE(1),.DEPTH_GROUPS(16),.AW(15),.TAG_W(T)) dut (.*);
 task tick; begin @(posedge clk); #1; end endtask
 task idle; begin @(negedge clk); wr_v=0;rd_v=0; end endtask
 task clean_tail; begin
  repeat(6) begin tick; if(wr_ack_v!==0 || rd_out_v!==0) $fatal(1,"STALE_OR_UNEXPECTED_RESPONSE"); end
 end endtask
 task write_words(input [14:0] base,input [3:0] valid,input [63:0] mask,input [2047:0] data,input integer ownerid);
 begin
  @(negedge clk);wr_v=valid;wr_lane_mask=mask;wr_word_data=data;
  for(integer b=0;b<4;b=b+1)begin wr_word_addr[b*15+:15]=base+b;wr_owner[b*T+:T]=ownerid+b;end
  #1;if(wr_accept_v!==valid) $fatal(1,"VALID_WRITE_REFUSED");
  tick;if(wr_ack_v!==0) $fatal(1,"EARLY_ACK_E0");idle;
  tick;if(wr_ack_v!==0) $fatal(1,"EARLY_ACK_E1");
  tick;if(wr_ack_v!==0) $fatal(1,"EARLY_ACK_E2");
  tick;if(wr_ack_v!==valid) $fatal(1,"MISSING_ACK_E3");
  for(integer b=0;b<4;b=b+1)if(valid[b])begin
   if(wr_ack_owner[b*T+:T]!==T'(ownerid+b) || wr_ack_word_addr[b*15+:15]!==15'(base+b) || wr_ack_lane_mask[b*16+:16]!==mask[b*16+:16]) $fatal(1,"WRONG_ACK_IDENTITY");
  end
  tick;if(wr_ack_v!==0) $fatal(1,"DUPLICATE_ACK");cases=cases+1;
 end endtask
 task read_words(input [14:0] base,input [2047:0] expected,input integer ownerid);
 begin
  @(negedge clk);rd_v=1;rd_base_word=base;rd_owner=ownerid;
  #1;if(rd_accept_v!==1) $fatal(1,"VALID_READ_REFUSED");tick;idle;
  repeat(3)begin tick;if(rd_out_v!==0) $fatal(1,"EARLY_READ");end
  tick;if(rd_out_v!==1 || rd_out_bank_words!==expected || rd_out_owner!==T'(ownerid) || rd_out_rot!==base[1:0]) $fatal(1,"READ_DATA_TAG_OR_LATENCY");
  tick;if(rd_out_v!==0) $fatal(1,"DUPLICATE_READ");cases=cases+1;
 end endtask
 initial begin
  // Offers are legal except that reset is asserted: they must not be accepted.
  wr_v=1;wr_lane_mask=64'hffff;rd_v=1;
  #1;if(wr_accept_v!==0 || rd_accept_v!==0) $fatal(1,"RESET_ACCEPTANCE_DEFECT");
  repeat(3)begin tick;if(wr_ack_v!==0 || rd_out_v!==0) $fatal(1,"RESET_OUTPUT");end
  cases=cases+1;
  // Cold reset offered writes cannot silently become debt or later responses.
  idle; @(negedge clk);rst_n=1;clean_tail;cases=cases+1;
  for(integer b=0;b<4;b=b+1)for(integer l=0;l<16;l=l+1) expected_words[(b*16+l)*32+:32]=32'h40000000+b*16+l;
  write_words(0,15,64'hffffffffffffffff,expected_words,100);
  read_words(0,expected_words,200);
  // Exercise every lane's 32bit mask expansion, preserving all sibling lanes.
  for(integer l=0;l<16;l=l+1)begin
   wr_word_data=0;wr_word_data[l*32+:32]=32'h3f800000+l;
   expected_words[l*32+:32]=32'h3f800000+l;
   write_words(0,1,64'(1)<<l,wr_word_data,300+l);
   read_words(0,expected_words,400+l);
  end
  // Wrong bank address and zero lane mask both fault without acceptance/ACK.
  @(negedge clk);wr_v=1;wr_word_addr[14:0]=1;wr_lane_mask=64'hffff;
  #1;if(wr_accept_v!==0) $fatal(1,"WRONG_BANK_ACCEPTED");tick;if(wr_fault!==1) $fatal(1,"WRONG_BANK_NOFAULT");idle;clean_tail;cases=cases+1;
  @(negedge clk);wr_v=1;wr_word_addr[14:0]=0;wr_lane_mask=0;
  #1;if(wr_accept_v!==0) $fatal(1,"ZERO_MASK_ACCEPTED");tick;if(wr_fault!==1) $fatal(1,"ZERO_MASK_NOFAULT");idle;clean_tail;cases=cases+1;
  @(negedge clk);rd_v=1;rd_base_word=32767;
  #1;if(rd_accept_v!==0) $fatal(1,"INVALID_READ_ACCEPTED");tick;if(rd_fault!==1) $fatal(1,"INVALID_READ_NOFAULT");idle;clean_tail;cases=cases+1;
  write_words(32764,15,64'hffffffffffffffff,expected_words,600);
  read_words(32764,expected_words,700);
  // Hold a legal offer through reset; first accepted edge is release, not reset.
  @(negedge clk);rst_n=0;wr_v=1;wr_word_addr[14:0]=0;wr_lane_mask=64'hffff;wr_owner[0+:T]=800;wr_word_data=expected_words;rd_v=1;rd_base_word=0;rd_owner=801;
  #1;if(wr_accept_v!==0 || rd_accept_v!==0) $fatal(1,"SECOND_RESET_ACCEPTANCE");
  repeat(3)tick;
  @(negedge clk);rst_n=1;#1;if(wr_accept_v!==1 || rd_accept_v!==1) $fatal(1,"HELD_OFFER_NOT_ACCEPTED_RELEASE");
  tick;idle;tick;tick;tick;
  if(wr_ack_v!==1 || wr_ack_owner[0+:T]!==T'(800)) $fatal(1,"RELEASE_ACK");
  tick;if(rd_out_v!==1 || rd_out_owner!==T'(801) || rd_out_bank_words!==expected_words) $fatal(1,"RELEASE_READ");
  tick;clean_tail;cases=cases+1;
  // Back-to-back accepted writes must retain different identities and masks.
  @(negedge clk);wr_v=1;wr_word_addr[14:0]=0;wr_lane_mask=1;wr_owner[0+:T]=900;wr_word_data=expected_words;
  tick;@(negedge clk);wr_owner[0+:T]=901;wr_lane_mask=2;tick;idle;tick;
  tick;if(wr_ack_v!==1 || wr_ack_owner[0+:T]!==T'(900) || wr_ack_lane_mask[15:0]!==16'h1) $fatal(1,"ORDER_ACK_FIRST");
  tick;if(wr_ack_v!==1 || wr_ack_owner[0+:T]!==T'(901) || wr_ack_lane_mask[15:0]!==16'h2) $fatal(1,"ORDER_ACK_SECOND");
  tick;clean_tail;cases=cases+1;
  $display("PASS RAW_NATIVE_R2_RESET_MASK_VISIBILITY cases=%0d",cases);$finish;
 end
 initial begin #100000; $fatal(1,"TESTBENCH_EVENT_BOUND_EXCEEDED");end
endmodule
