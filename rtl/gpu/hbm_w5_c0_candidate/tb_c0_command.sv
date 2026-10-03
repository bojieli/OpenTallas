`timescale 1ns/1ps
module tb;parameter ENABLE=1;
reg [0:0] clk=0;
reg [0:0] por_n=0;
reg [0:0] rst_n=0;
reg context_admitted=1;reg [1023:0] context_reservation=0;reg [0:0] start_v=0;
wire [0:0] start_r;
reg [63:0] native_owner=0;
reg [63:0] native_generation=0;
reg [54:0] command_parent=0;
reg [3:0] frame_count=0;
reg [255:0] frame_refs=0;
reg [71:0] frame_slots=0;
wire [0:0] allocation_v;
reg [0:0] allocation_r=0;
reg [31:0] allocation_tag=0;
reg [3:0] allocation_gen=0;
reg [38:0] allocation_byte=0;
wire [6:0] allocation_index;
wire [31:0] allocation_frame_ref;
wire [8:0] allocation_RFslot;
wire [0:0] req_v;
reg [0:0] req_r=0;
wire [38:0] req_byte;
wire [30:0] req_phy_sector31;wire [4:0] req_phy_len5;wire [3:0] req_phy_beat4;wire [6:0] req_PC;
wire [45:0] req_owner;
wire [91:0] req_meta;
reg [15:0] accepted_backend16=0;
reg [0:0] rsp_v=0;
wire [0:0] rsp_r;
reg [91:0] rsp_meta=0;
reg [15:0] rsp_backend16=0;
reg [255:0] rsp_data=0;
wire [0:0] stage_ACK_v;
reg [0:0] stage_ACK_r=0;
wire [5:0] stage_fragment;
wire [0:0] rf_v;
reg [0:0] rf_r=0;
wire [4095:0] rf_data;
wire [8:0] rf_slot;
wire [54:0] stable_parent;
reg [0:0] host_common_ACK=0;reg [45:0] host_ack_owner=0;reg [8:0] host_ack_slot=0;reg host_ack_identity_fault=0;wire host_ack_ready;wire [45:0] rf_owner;
reg [0:0] internal_SIMD_ACK=0;
wire [0:0] visible_v;
reg [0:0] visible_r=0;
reg [0:0] consumer_v=0;
reg [54:0] consumer_identity=0;
wire [0:0] consumer_r;
wire [0:0] reverse_v;
reg [0:0] reverse_r=0;
wire [91:0] reverse_meta;
wire [15:0] reverse_backend16;
reg [0:0] parent_reverse_v=0;
reg [54:0] parent_reverse_identity=0;
wire [0:0] parent_reverse_r;
reg [0:0] reverse_CDC_v=0;
reg [54:0] reverse_CDC_identity=0;
wire [0:0] reverse_CDC_r;
wire [0:0] drain_req_v;
wire [54:0] drain_req_identity;
wire [0:0] drain_req_has_owner;
wire [0:0] drain_req_reset_scope;
reg [0:0] drain_req_r=0;
reg [0:0] drain_rsp_v=0;
reg [54:0] drain_rsp_identity=0;
reg [0:0] drain_rsp_has_owner=0;
reg [0:0] drain_rsp_reset_scope=0;
reg [8:0] allcopy_live_zero=0;
wire [0:0] drain_rsp_r;
wire [0:0] retire_v;
reg [0:0] retire_r=0;
reg [0:0] recovery_v=0;
reg [63:0] recovery_native_owner=0;
reg [63:0] recovery_native_generation=0;
reg [54:0] recovery_parent=0;
wire [0:0] recovery_r;
wire [63:0] retained_native_owner;
wire [63:0] retained_native_generation;
wire [7:0] retained_children;
wire [0:0] fault;
wire [0:0] quarantine;
ot_hbm_w5_c0_command #(.ENABLE(ENABLE),.SM(5)) dut(.*);
always #5 clk=~clk;
integer ticks=0;task tick;begin @(posedge clk);#1;ticks=ticks+1;if(fault && mode==0)$fatal(1,"control fault W5=%0d",dut.state);end endtask
integer mode=0;integer i,j;reg [91:0] children[0:127];
task finish_drain;
begin
 while(!drain_req_v) tick;
 drain_rsp_identity=drain_req_identity;drain_rsp_has_owner=drain_req_has_owner;drain_rsp_reset_scope=drain_req_reset_scope;
 drain_req_r=1;tick;drain_req_r=0;tick;
 drain_rsp_v=1;allcopy_live_zero=9'h1ff;#1;
 while(!drain_rsp_r) tick;
 tick;drain_rsp_v=0;
end endtask
initial begin
 if($value$plusargs("mode=%d",mode))begin end
 tick;por_n=1;rst_n=1;tick;
 if(!ENABLE)begin if(start_r || allocation_v || req_v || req_meta!=0 || rf_v || reverse_v || drain_req_v || retire_v)$fatal(1,"disabled outputs");$display("PASS disabled C0/W2/W6 component");$finish;end
 finish_drain;tick;tick;
 native_owner=64'h8000000012345678;native_generation=64'h8000000098765432;
 command_parent={7'd0,3'd0,32'hfeedbeef,4'd6,9'd20};frame_count=8;
 for(i=0;i<8;i=i+1) begin frame_refs[i*32+:32]=100+i;frame_slots[i*9+:9]=20+i;end
 if(mode==4)frame_slots[17:9]=frame_slots[8:0];
 for(i=0;i<8;i=i+1)for(j=0;j<4;j=j+1)context_reservation[(j*32+i)*8+:8]=4;
 if(mode==6)begin context_reservation[7:0]=0;context_reservation[15:8]=8;end
 if(mode==7)context_admitted=0;
 start_v=1;#1;
 if(mode==7)begin tick;if(start_r || allocation_v || req_v || retained_children!=0 || fault)$fatal(1,"missing G0 grant accepted");$display("PASS unbound G0 grant refuses admission");$finish;end
 while(!start_r)tick;tick;start_v=0;
 if(mode==4)begin if(!fault || allocation_v || rf_v)$fatal(1,"live RF slot alias accepted");$display("PASS premature RF slot reuse refused");$finish;end
 for(i=0;i<128;i=i+1)begin
  if(!allocation_v || allocation_index!=i || allocation_frame_ref!=100+i/16 || allocation_RFslot!=20+i/16) $fatal(1,"source allocation index");
  allocation_byte=i*32;allocation_tag=32'habcde000+i;allocation_gen=6;if(mode==8 && i==0)allocation_byte=39'd81000000000;
  allocation_r=1;tick;allocation_r=0;
  if((mode==6 || mode==8) && i==0)begin tick;
   if(!fault || req_v || retained_children!=0 || retained_native_owner!=native_owner)$fatal(1,"unreserved PC/physical extent accepted");
   $display("PASS unreserved PC/physical extent refused before backend issue");$finish;
  end
  if(!req_v || req_owner[38:36]!=0 || req_owner[35:4]!=32'habcde000+i) $fatal(1,"source tag32 not preserved");
  if(req_meta[45:41]!=5 || req_meta[40:32]!=20+i/16 || req_meta[31:0]!=100+i/16) $fatal(1,"actual frame descriptor");
  children[i]=req_meta;req_r=1;accepted_backend16=16'ha000+i;tick;req_r=0;
  if(mode==3 && i==31)begin rst_n=0;tick;tick;end
  rsp_meta=children[i];rsp_backend16=16'ha000+i;rsp_data=i+1;
  if(mode==1 && i==0)rsp_backend16=16'h9000;
  if(mode==2 && i==0)rsp_meta=children[i]^92'd1;
  rsp_v=1;tick;rsp_v=0;
  if((mode==1 || mode==2)&&i==0)begin
   if(!fault || retained_children!=1 || req_v || allocation_v) $fatal(1,"wrong return freed owner");
   $display("PASS wrong full16/metadata retained");$finish;
  end
  if(mode==3 && i==31)begin
   if(retained_children!=32 || retained_native_owner!=native_owner || retained_native_generation!=native_generation || allocation_v || req_v) $fatal(1,"runtime reset cleared owner");
   rst_n=1;tick;tick;
   if(!quarantine || allocation_v || retained_children!=32) $fatal(1,"reset resumed without source abort/drain");
   $display("PASS runtime reset retains32children and native64, no invented allcopy credit");$finish;
  end
  if(i%2==1)begin
   if(!stage_ACK_v || allocation_v || stage_fragment!=i/2) $fatal(1,"sourcecredit1");
   tick;if(allocation_v)$fatal(1,"early fragment credit");
   stage_ACK_r=1;tick;stage_ACK_r=0;
  end
  if(i%16==15)begin
   if(!rf_v || rf_slot!=20+i/16 || stable_parent!=command_parent || visible_v) $fatal(1,"frame RF/aggregate fence");
   for(j=0;j<16;j=j+1)if(rf_data[j*256+:256]!=(i/16)*16+j+1)$fatal(1,"assembled byte payload");
   rf_r=1;tick;rf_r=0;tick;host_ack_owner=rf_owner;host_ack_slot=rf_slot;
   if(mode==5 && i==31)host_ack_slot=20;
   host_common_ACK=1;tick;
   if(mode==5 && i==31)begin
    if(!fault || retained_children!=32 || allocation_v)$fatal(1,"stale RF ACK retired frame");
    $display("PASS source W4 ACK owner/slot stale receipt refused");$finish;
   end
   host_common_ACK=0;
   if(retained_children!=i+1) $fatal(1,"assembler reuse retired sector metadata");
  end
 end
 if(retained_children!=128)$fatal(1,"MAX64 command retention");
 while(!visible_v)tick;
 visible_r=1;tick;visible_r=0;consumer_identity=command_parent;consumer_v=1;#1;
 while(!consumer_r)tick;tick;consumer_v=0;
 for(i=0;i<128;i=i+1)begin
  if(!reverse_v || reverse_meta!=children[i] || reverse_backend16!=16'ha000+i || retained_children!=128)$fatal(1,"retained reverse128");
  if(i%3==0)tick;
  reverse_r=1;tick;reverse_r=0;
 end
 tick;tick;tick;
 parent_reverse_identity=command_parent;parent_reverse_v=1;#1;
 while(!parent_reverse_r)tick;tick;parent_reverse_v=0;tick;
 reverse_CDC_identity=command_parent;reverse_CDC_v=1;#1;
 while(!reverse_CDC_r)tick;tick;reverse_CDC_v=0;
 finish_drain;
 while(!retire_v)tick;
 if(retained_children!=128 || fault)$fatal(1,"premature final release");
 retire_r=1;tick;retire_r=0;
 if(retained_children!=0 || fault)$fatal(1,"actual W6 retirement");
 $display("PASS sourcecredit1,64fragmentACK,8RFframes,128retainedchildren and actual W6 command lifecycle");$finish;
end
endmodule
