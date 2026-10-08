`timescale 1ps/1fs
module tb_epoch_join;
 reg clk_chain=0,clk_stream=0;always #555.555555556 clk_chain=~clk_chain;always #416.666666667 clk_stream=~clk_stream;
 reg cold_abort=1,in_valid=0,done_ready=0,endpoint_event_valid=0,den_valid=0;
 reg [1083:0] in_packet=0;reg [2:0] endpoint_event_kind=0;
 reg [31:0] endpoint_epoch=0,den_epoch=0;reg [15:0] endpoint_tag=0,den_tag=0;
 wire in_ready,done_valid,endpoint_event_ready,core_valid,core_pv,active_out,fault;
 wire [63:0] done_packet;wire [8191:0] core_data;wire [15:0] core_tag;wire [6:0] core_addr,phase_row;wire [2:0] phase_kind;
 ot_dsrom_softmax_epoch_join dut(.*);
 integer drained=0;
 always @(posedge clk_stream)if(endpoint_event_valid&&endpoint_event_ready&&endpoint_event_kind==7)drained=drained+1;
 always @(posedge clk_chain)if(done_valid&&drained!=32)$fatal(1,"EARLY_VISIBLE_COMPLETION");
 integer checked=0,score_seen=0,pv_seen=0,stream_edge=0,last_core=0;reg [31:0] expected_epoch=0;reg[15:0] expected_tag=0;
 always @(negedge clk_stream)stream_edge=stream_edge+1;
 function automatic[63:0] value(input integer ep,addr,lane);
  value=64'h9e3779b97f4a7c15*(64'(addr*128+lane+ep*8192)+1);
 endfunction
 always @(posedge clk_stream)if(core_valid)begin
  if(core_tag!=expected_tag)$fatal(1,"CORE_TAG");
  if(core_addr!=(core_pv?40+pv_seen:score_seen))$fatal(1,"CORE_ORDER");
  if((core_pv?pv_seen:score_seen)>0&&stream_edge-last_core!=1)$fatal(1,"CORE_STALLED");
  for(integer l=0;l<128;l=l+1)if(core_data[l*64+:64]!==value(expected_epoch,core_addr,l))$fatal(1,"CORE_PAYLOAD addr%0d lane%0d",core_addr,l);
  if(core_pv)pv_seen=pv_seen+1;else score_seen=score_seen+1;
  checked=checked+1;last_core=stream_edge;
 end
 task automatic cold;
  @(negedge clk_chain);cold_abort=1;in_valid=0;endpoint_event_valid=0;den_valid=0;done_ready=0;
  repeat(4)@(negedge clk_chain);cold_abort=0;
  repeat(5)@(negedge clk_chain);
  if(fault||active_out||done_valid)$fatal(1,"RESET_ABORT");
  score_seen=0;pv_seen=0;
 endtask
 task automatic send(input [1083:0] packet);
  @(negedge clk_chain);in_packet=packet;in_valid=1;
  while(!in_ready)@(negedge clk_chain);
  @(posedge clk_chain);@(negedge clk_chain);in_valid=0;
 endtask
 task automatic beginrow(input short_t,input [31:0] ep,input[15:0] tag_t);
  expected_epoch=ep;expected_tag=tag_t;drained=0;score_seen=0;pv_seen=0;
  send({2'd0,ep,tag_t,7'd0,3'd0,1023'd0,short_t});
  wait(active_out);if(fault)$fatal(1,"BEGIN");
 endtask
 task automatic vector(input integer addr);
  reg [1023:0] payload;
  for(integer b=0;b<8;b=b+1)begin
   for(integer l=0;l<16;l=l+1)payload[l*64+:64]=value(expected_epoch,addr,b*16+l);
   send({2'd1,expected_epoch,expected_tag,7'(addr),3'(b),payload});
  end
 endtask
 task automatic receipt(input[2:0] kind);
  @(negedge clk_stream);while(!endpoint_event_ready||phase_kind!=kind)@(negedge clk_stream);
  endpoint_event_valid=1;endpoint_event_kind=kind;endpoint_epoch=expected_epoch;endpoint_tag=expected_tag;
  @(posedge clk_stream);@(negedge clk_stream);endpoint_event_valid=0;
  if(fault)$fatal(1,"ENDPOINT_RECEIPT kind%0d",kind);
 endtask
 task automatic row(input short_t,input[31:0] ep,input[15:0] tag_t);
  integer ns;reg[63:0] held;
  ns=short_t?8:40;beginrow(short_t,ep,tag_t);
  for(integer a=0;a<ns;a=a+1)vector(a);
  wait(score_seen==ns);
  // Actual E producer dependency: no probability receipt or P.V supply until all scores replayed.
  for(integer a=0;a<ns;a=a+1)receipt(2);
  @(negedge clk_stream);den_valid=1;den_epoch=ep;den_tag=tag_t;
  @(negedge clk_stream);den_valid=0;
  for(integer a=0;a<ns;a=a+1)receipt(3);
  for(integer a=40;a<72;a=a+1)vector(a);
  wait(pv_seen==32);
  for(integer a=0;a<32;a=a+1)receipt(6);
  for(integer a=0;a<31;a=a+1)receipt(7);
  // Final BF16 destination-visible receipt is withheld. Producer emptiness is insufficient.
  repeat(64)begin @(negedge clk_chain);if(done_valid||!active_out||fault)$fatal(1,"EARLY_COMPLETION");end
  receipt(7);wait(done_valid);held=done_packet;
  if(held!={ep,tag_t,16'd0})$fatal(1,"COMPLETION_IDENTITY");
  repeat(16)begin @(negedge clk_chain);if(!done_valid||done_packet!==held||fault)$fatal(1,"COMPLETION_STALL");end
  done_ready=1;@(posedge clk_chain);@(negedge clk_chain);done_ready=0;
  repeat(4)@(negedge clk_chain);
  $display("EPOCH_ROW_PASS epoch%0d score%0d PV32 checked%0d",ep,ns,checked);
 endtask
 initial begin
  cold();
`ifndef SOFTMAX_EPOCH_IGNORE_EPOCH
 row(0,1,16'h1201);row(1,2,16'h1202);
  // Abort while accepted score payload remains queued or in assembly.
  beginrow(0,3,16'h1203);vector(0);cold();row(1,4,16'h1204);
  // Cold assertion during an active no-ready replay must suppress visible output immediately.
  beginrow(1,5,16'h1205);for(integer a=0;a<8;a=a+1)vector(a);
  wait(core_valid);#100;cold_abort=1;#1;
  if(core_valid||in_ready||done_valid||endpoint_event_ready)$fatal(1,"COLD_PERMISSION_ESCAPED");
  cold();
`endif
  // A late prior-epoch beat must fault before reaching SRAM/replay.
  beginrow(1,6,16'h1206);send({2'd1,32'd3,16'h1206,7'd0,3'd0,1024'd0});
  repeat(12)@(negedge clk_stream);if(!fault||core_valid||done_valid)$fatal(1,"STALE_EPOCH_ESCAPED");
  cold();send({2'd3,32'd7,16'h1207,7'd0,3'd0,1024'd0});
  repeat(12)@(negedge clk_stream);if(!fault||active_out||done_valid)$fatal(1,"ILLEGAL_OPCODE_ESCAPED");
  $display("PASS_EPOCH_JOIN full1084_CDC actual36SRAM scorePV_II1 phase_E_to_PV completion_visibility stall epoch_reject cold_abort vectors%0d",checked);$finish;
 end
endmodule
