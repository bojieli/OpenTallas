`timescale 1ns/1ps
module tb;
parameter ENABLE=1;
reg [0:0] clk=0;
reg [0:0] rst_n=0;
reg [0:0] start_v=0;
reg [63:0] native_owner=0;reg [63:0] native_generation=0;
reg [63:0] frame_byte=0;
reg [31:0] parent_ref=0;
reg [31:0] parent_tag=0;
reg [3:0] producer_gen=0;
reg [2:0] caller_client=0;
reg [8:0] rf_slot=0;
reg [0:0] req_r=0;
reg [15:0] accepted_backend16=0;
reg [0:0] rsp_v=0;
reg [91:0] rsp_meta=0;
reg [15:0] rsp_backend16=0;
reg [0:0] rsp_beat=0;
reg [255:0] rsp_data=0;
reg [0:0] stage_ACK_r=0;
reg [0:0] rf_r=0;
reg [0:0] host_common_ACK=0;
reg [0:0] internal_SIMD_ACK=0;
reg [0:0] visible_r=0;
reg [0:0] consumer_done=0;
reg [0:0] reverse_r=0;
reg [0:0] drain_r=0;
reg [54:0] drained_parent=0;
reg [31:0] drained_ref=0;
reg [7:0] drained_epoch=0;
reg [8:0] allcopy_zero=0;
reg [0:0] reset_req=0;
wire [0:0] start_r;
wire [0:0] req_v;
wire [63:0] req_byte;
wire [6:0] req_pc;
wire [45:0] req_owner;
wire [91:0] req_meta;
wire [5:0] req_len;
wire [0:0] req_beat;
wire [0:0] rsp_r;
wire [0:0] stage_ACK_v;
wire [2:0] stage_index;
wire [0:0] rf_v;
wire [4095:0] rf_data;
wire [54:0] stable_parent;
wire [8:0] rf_dst;
wire [0:0] visible_v;
wire [0:0] reverse_v;
wire [91:0] reverse_meta;
wire [15:0] reverse_backend16;
wire [0:0] drain_v;
wire [7:0] reset_epoch;
wire [0:0] idle;
wire [0:0] fault;
wire [63:0] retained_native_owner;wire [63:0] retained_native_generation;
ot_hbm_w5_read_frame #(.ENABLE(ENABLE),.SM(5)) dut(.*);
always #5 clk=~clk;
task tick;begin @(posedge clk);#1;end endtask
reg [91:0] saved;reg [54:0] parent_saved;integer i;integer child_count;integer mode=0;
generate if(ENABLE) begin:seed
 task apply;begin dut.g.child_tag=32'hfffffff0;end endtask
 end else begin:seed
 task apply;begin end endtask
 end endgenerate
initial begin
 if($value$plusargs("mode=%d",mode)) begin end
 tick;rst_n=1;tick;
 if(!ENABLE) begin if(start_r || req_v || rf_v || reverse_v || drain_v) $fatal(1,"disabled output");$display("PASS default-off");$finish;end
 native_owner=64'h800000001234abcd;native_generation=64'h800000003456789a;frame_byte=512;parent_ref=100;parent_tag=32'hfeedbeef;
 if(mode==6) seed.apply;
 producer_gen=6;caller_client=2;rf_slot=43;start_v=1;tick;start_v=0;parent_saved=stable_parent;
 for(i=0;i<16;i=i+1) begin
  if(!req_v || req_len!=1 || req_beat || req_byte!=512+i*32) $fatal(1,"request/span");
  if(req_owner[45:39]!=req_pc || req_meta[45:41]!=5 || req_meta[31:0]!=100) $fatal(1,"metadata");
  saved=req_meta;accepted_backend16=16'ha000+i;req_r=1;tick;req_r=0;
  rsp_v=1;rsp_meta=saved;rsp_backend16=16'ha000+i;rsp_data=i+1;
  if(mode==1 && i==0) rsp_backend16=16'h9000;
  if(mode==2 && i==0) rsp_meta=saved^92'd1;
  tick;rsp_v=0;
  if((mode==1 || mode==2) && i==0) begin
   if(!fault || idle || req_v) $fatal(1,"invalid return released context");
   $display("PASS stale backend generation/wrong owner refused");$finish;
  end
  if(fault) $fatal(1,"legal child fault");
  if(i%2==1) begin
   if(!stage_ACK_v) $fatal(1,"stage ACK missing");
   if(i<15 && req_v) $fatal(1,"one credit bypassed");
   tick; // held ACK, credit must remain unavailable
   if(i<15 && req_v) $fatal(1,"credit returned before store ACK acceptance");
   stage_ACK_r=1;tick;stage_ACK_r=0;
  end
 end
 if(!rf_v || stable_parent!=parent_saved || retained_native_owner!=native_owner || retained_native_generation!=native_generation) $fatal(1,"frame parent");
 for(i=0;i<16;i=i+1) if(rf_data[i*256+:256]!=i+1) $fatal(1,"frame bytes");
 tick;if(!rf_v) $fatal(1,"RF backpressure");rf_r=1;tick;rf_r=0;
 if(visible_v || reverse_v) $fatal(1,"premature visibility");
 if(mode==3) begin internal_SIMD_ACK=1;tick;
  if(!fault || visible_v || reverse_v) $fatal(1,"wrong ACK origin");
  $display("PASS internal SIMD ACK cannot satisfy host");$finish;
 end
 host_common_ACK=1;tick;host_common_ACK=0;visible_r=1;tick;visible_r=0;
 consumer_done=1;tick;consumer_done=0;
 for(i=0;i<16;i=i+1) begin
  if(!reverse_v || reverse_backend16!=16'ha000+i || reverse_meta[31:0]!=100) $fatal(1,"reverse owner");
  reverse_r=1;tick;reverse_r=0;
 end
 if(!drain_v || idle) $fatal(1,"quarantine");
 // Wrong epoch is fail closed; it must not release the parent/backend rows.
 drained_parent=parent_saved;drained_ref=100;drained_epoch=(mode>=4)?0:1;allcopy_zero=9'h1ff;drain_r=1;tick;
 if(mode>=4) begin
  if(fault || !idle || (mode!=6 && !start_r)) $fatal(1,"legal drain did not release");
  if(mode==6) begin
   if(start_r) $fatal(1,"wrapped tag reused same source generation");
   producer_gen=7;#1;if(!start_r) $fatal(1,"drained generation successor refused");
   start_v=1;tick;start_v=0;
   if(!req_v || req_owner[3:0]!=7 || req_owner[35:4]!=0) $fatal(1,"wrap owner");
   $display("PASS drained tag wrap with explicit source generation successor");$finish;
  end
  drain_r=0;
  if(mode==5) begin reset_req=1;tick;reset_req=0;
   if(!drain_v || start_r) $fatal(1,"reset must request drain and stop grants");
   drain_r=1;tick;drain_r=0;
   if(fault || reset_epoch!=1 || !start_r) $fatal(1,"matched reset drain");
  end
  $display("PASS exact drain release/reset all-copy handshake");$finish;
 end
 if(!fault || idle || start_r) $fatal(1,"stale drain released context");
 $display("PASS 16 source translated sectors, 8 staging credits, held RF, exact reverse, stale drain refused");
 $finish;
end
endmodule
