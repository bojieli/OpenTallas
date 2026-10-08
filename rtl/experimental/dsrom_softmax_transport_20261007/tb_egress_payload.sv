`timescale 1ps/1fs
module tb_egress_payload;
 import ot_gpu_w6_secded_pkg::*;
 reg clk_stream=0,clk_chain=0;always #416.666666667 clk_stream=~clk_stream;always #555.555555556 clk_chain=~clk_chain;
 reg cold_abort=1,begin_valid=0,begin_short=0,e_valid=0,b_valid=0,destination_allow_commit=0,done_ready=0;
 reg [31:0] begin_epoch=0,producer_epoch=0;reg [15:0] begin_tag=0,producer_tag=0;
 reg [8191:0] e_data=0;reg[4095:0] b_data=0;
 wire begin_ready,e_visible,done_valid,capture_commit,destination_commit,receipt_valid,fault;
 wire [6:0] capture_addr;wire [55:0] destination_identity,receipt_identity;
 ot_dsrom_softmax_egress_payload dut(.*);
 integer checked=0,receipts=0,e_receipts=0,b_receipts=0,captures=0,full_stalls=0;
 reg [127:0] committed=0;
 integer stream_edge=0,last_capture_edge=0,e_first_edge=0,b_first_edge=0,e_elapsed=0,b_elapsed=0;
 always @(negedge clk_stream)stream_edge=stream_edge+1;
 wire [9215:0] visible_code;
 genvar bank;generate for(bank=0;bank<36;bank=bank+1)begin:g_inspect
  assign visible_code[bank*256+:256]=dut.destination_bank.g_bank[bank].mem.arr[receipt_identity[6:0]][255:0];
 end endgenerate
 function automatic [63:0] value(input integer ep,row,lane);
  value=64'h9e3779b97f4a7c15*(64'(ep*8192+row*128+lane)+1);
 endfunction
 always @(posedge clk_chain)if(destination_commit)begin
  if(!destination_allow_commit)$fatal(1,"COMMIT_WITHHELD");
  if(destination_identity[54:23]!=producer_epoch||destination_identity[22:7]!=producer_tag)$fatal(1,"DEST_IDENTITY");
  committed[destination_identity[6:0]]=1;
 end
 always @(posedge clk_stream)begin
  if(dut.srst&&!dut.failed&&(dut.ack_bad||dut.bad_capture||fault))$display("FIRST_FAULT t%0t ackbad%b ackv%b ack%h exp%h capbad%b integ%b fault%b",$time,dut.ack_bad,dut.ack_v,dut.ack,{dut.b_phase,dut.epoch,dut.tag,((dut.b_phase?7'd112:7'd72)+{1'b0,dut.received})},dut.bad_capture,dut.integrity,fault);
  if(dut.sv&&!dut.fifo_ready)full_stalls=full_stalls+1;
  if(capture_commit)begin
   if(capture_addr>72&&capture_addr<112&&stream_edge-last_capture_edge!=1)$fatal(1,"E_CAPTURE_NOT_II1");
   if(capture_addr>112&&stream_edge-last_capture_edge!=2)$fatal(1,"BF_PACK_NOT_II2");
   last_capture_edge=stream_edge;captures=captures+1;
  end
  if(receipt_valid)begin
   if(!committed[receipt_identity[6:0]])$fatal(1,"RECEIPT_BEFORE_DESTINATION_WRITE row%0d",receipt_identity[6:0]);
   if(receipt_identity[54:23]!=producer_epoch||receipt_identity[22:7]!=producer_tag)$fatal(1,"RECEIPT_IDENTITY");
   for(integer l=0;l<128;l=l+1)begin:chk
    reg [65:0] decoded;reg [63:0] expect_data;integer row;
    row=receipt_identity[6:0];decoded=decode64(visible_code[l*72+:72]);
    if(row<112)expect_data=value(producer_epoch,row,l);
    else expect_data=value(producer_epoch,200+(row-112)*2+l/64,l%64);
    if(decoded[65]||decoded[63:0]!==expect_data)$fatal(1,"DESTINATION_PAYLOAD row%0d lane%0d got%h expected%h",row,l,decoded[63:0],expect_data);
   end
   checked=checked+1;receipts=receipts+1;
   if(receipt_identity[55])b_receipts=b_receipts+1;else e_receipts=e_receipts+1;
  end
  if(e_visible&&e_receipts!=(begin_short?8:40))$fatal(1,"EARLY_E_VISIBILITY");
  if(done_valid&&(b_receipts!=16))$fatal(1,"EARLY_COMPLETION");
 end
 task automatic cold;
  @(negedge clk_stream);cold_abort=1;begin_valid=0;e_valid=0;b_valid=0;done_ready=0;destination_allow_commit=0;
  repeat(5)@(negedge clk_chain);cold_abort=0;repeat(8)@(negedge clk_stream);
  if(fault||done_valid||e_visible)$fatal(1,"RESET_ABORT");
  committed=0;receipts=0;e_receipts=0;b_receipts=0;captures=0;
 endtask
 task automatic start(input integer ep,input bit short_t);
  wait(begin_ready);@(negedge clk_stream);
  destination_allow_commit=0;begin_epoch=ep;producer_epoch=ep;begin_tag=16'hc0de;producer_tag=16'hc0de;begin_short=short_t;begin_valid=1;
  committed=0;receipts=0;e_receipts=0;b_receipts=0;captures=0;
  @(negedge clk_stream);begin_valid=0;
 endtask
 task automatic capture_e;
  e_first_edge=stream_edge;
  for(integer r=0;r<(begin_short?8:40);r=r+1)begin
   e_valid=1;for(integer l=0;l<128;l=l+1)e_data[l*64+:64]=value(producer_epoch,72+r,l);
   @(negedge clk_stream);if(fault)$fatal(1,"E_CAPTURE_FAULT state%0d",dut.state);
  end
  e_valid=0;
 endtask
 task automatic capture_b;
  b_first_edge=stream_edge;
  for(integer r=0;r<32;r=r+1)begin
   b_valid=1;for(integer l=0;l<64;l=l+1)b_data[l*64+:64]=value(producer_epoch,200+r,l);
   @(negedge clk_stream);if(fault)$fatal(1,"BF_CAPTURE_FAULT");
  end
  b_valid=0;
 endtask
 task automatic campaign(input integer ep,input bit short_t);
  start(ep,short_t);capture_e();
  // Single physical data-cell error before this row is read must be corrected.
  dut.source_bank.g_bank[17].mem.arr[74][35]=~dut.source_bank.g_bank[17].mem.arr[74][35];
  wait(dut.mwv);repeat(250)@(negedge clk_chain);
  if(e_visible||done_valid||receipts!=0)$fatal(1,"SOURCE_SEND_IS_NOT_VISIBILITY");
  destination_allow_commit=1;while(!e_visible&&!fault)@(negedge clk_stream);if(fault)$fatal(1,"E_DRAIN_FAULT integrity%b sf%b df%b qf%b af%b destfailed%b bad_dest%b ackbad%b state%0d sent%0d rec%0d did%h qid%h",dut.integrity,dut.sfault,dut.dfault,dut.qfault,dut.afault,dut.d_failed,dut.bad_dest,dut.ack_bad,dut.state,dut.sent,dut.received,dut.dest_id,dut.q_identity);
  e_elapsed=stream_edge-e_first_edge;@(negedge clk_stream);capture_b();while(!done_valid&&!fault)@(negedge clk_stream);if(fault)$fatal(1,"BF_DRAIN_FAULT");
  b_elapsed=stream_edge-b_first_edge;
  if(captures!=(short_t?24:56)||receipts!=(short_t?24:56))$fatal(1,"COUNTS captures%0d receipts%0d",captures,receipts);
  repeat(16)@(negedge clk_stream);if(!done_valid)$fatal(1,"DONE_BACKPRESSURE");
  done_ready=1;@(negedge clk_stream);done_ready=0;
  $display("CAMPAIGN PASS epoch%0d E%0d BF32 packed%0d E_with250chain_write_stall_stream_edges=%0d BF_no_extra_stall_stream_edges=%0d",ep,short_t?8:40,receipts,e_elapsed,b_elapsed);
 endtask
 initial begin
  cold();campaign(1,0);campaign(2,1);
  if(full_stalls==0)$fatal(1,"NO_FIFO_BACKPRESSURE");
  // Reject an early BF16 result before E is destination-visible.
  start(3,1);b_valid=1;@(negedge clk_stream);b_valid=0;
  if(!fault)$fatal(1,"EARLY_BF_NOT_REJECTED");
  cold();start(6,1);producer_epoch=7;e_valid=1;@(negedge clk_stream);e_valid=0;
  if(!fault)$fatal(1,"STALE_PRODUCER_EPOCH_ESCAPED");
  cold();start(7,1);dut.sent[0]=~dut.sent[0];@(negedge clk_stream);if(!fault)$fatal(1,"CONTROL_COMPLEMENT_ESCAPED");
  cold();start(4,1);capture_e();
  // Two physical cells of one codeword: no output receipt may escape.
  dut.source_bank.g_bank[35].mem.arr[72][186]=~dut.source_bank.g_bank[35].mem.arr[72][186];
  dut.source_bank.g_bank[35].mem.arr[72][187]=~dut.source_bank.g_bank[35].mem.arr[72][187];
  destination_allow_commit=1;while(!fault)@(negedge clk_stream);if(receipts!=0)$fatal(1,"UE_ESCAPED");
  cold();start(5,1);capture_e();wait(dut.mwv);cold();
  repeat(30)@(negedge clk_chain);if(receipt_valid||done_valid)$fatal(1,"STALE_RESET_RECEIPT");
  $display("PASS egress actual destination SRAM rows=%0d bytes=%0d fullstall_edges=%0d II1_E_and_BF capture; SECDED single correction/double abort; coordinated queued abort",checked,checked*1024,full_stalls);
  $finish;
 end
 // Bounded by the finite deterministic protocol inventory, not host wall time.
 initial begin repeat(25000)@(posedge clk_stream);$fatal(1,"PROTOCOL_NO_PROGRESS state%0d fault%b sent%0d received%0d",dut.state,fault,dut.sent,dut.received);end
endmodule
