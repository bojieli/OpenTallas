`timescale 1ns/1ps
// Default-off source-selected PC40/tile0 controller. Connect L/R ports to
// existing exclusive ot_gpu_rf_service endpoint (rank0, SM0). No HBM ticket,
// fake physical-PC, arithmetic callback, WR acceptance-as-visibility or ACK timer.
// Issuer supplies immutable owner46 and native64 identities under admission-stop
// and all-copy allocation contract; this module does not fabricate that allocator.
module ot_gpu_c0_connected_bridge #(parameter bit ENABLE=0) (
 input wire clk,por_n,rst_n,
 input wire req_valid, output wire req_ready,
 input wire [45:0] req_owner46,
 input wire [63:0] req_native_tag,req_native_generation,
 input wire issuer_binding_valid,
 output wire local_rd_valid,input wire local_rd_ready,
 output wire [8:0] local_rd_a,local_rd_b,
 input wire local_rsp_valid,output wire local_rsp_ready,
 input wire [4095:0] local_rsp_a,local_rsp_b,
 output wire local_wr_valid,input wire local_wr_ready,
 output wire [8:0] local_wr_addr,output wire [4095:0] local_wr_data,
 input wire local_ack_valid,output wire local_ack_ready,
 output wire remote_wr_valid,input wire remote_wr_ready,
 output wire [8:0] remote_wr_addr,output wire [4095:0] remote_wr_data,
 input wire remote_ack_valid,output wire remote_ack_ready,
 output wire visible_valid,input wire visible_ready,output wire [54:0] visible_identity,
 input wire [1:0] consumer_valid,output wire [1:0] consumer_ready,input wire [109:0] consumer_identity,
 input wire [1:0] child_reverse_valid,output wire [1:0] child_reverse_ready,input wire [109:0] child_reverse_identity,
 input wire [1:0] parent_reverse_valid,output wire [1:0] parent_reverse_ready,input wire [109:0] parent_reverse_identity,
 input wire [1:0] reverse_CDC_valid,output wire [1:0] reverse_CDC_ready,input wire [109:0] reverse_CDC_identity,
 output wire [1:0] drain_req_valid,input wire [1:0] drain_req_ready,
 output wire [109:0] drain_req_identity,output wire [1:0] drain_req_has_owner,drain_req_reset_scope,
 input wire [1:0] drain_rsp_valid,output wire [1:0] drain_rsp_ready,
 input wire [109:0] drain_rsp_identity,input wire [1:0] drain_rsp_has_owner,drain_rsp_reset_scope,
 input wire [17:0] alldrain_live,
 output wire done_valid,input wire done_ready,output wire [63:0] done_native_tag,done_native_generation,
 input wire rearm_valid,admission_stop,issuer_allcopy_fenced,
 output wire rearm_ready,exclusive_lease,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if (ENABLE) begin: enabled
 localparam [4:0] IDLE=0,HOME_RD=1,HOME_RSP=2,A_WR=3,A_ACK=4,B_WR=5,B_ACK=6,
 WORK_RD=7,WORK_RSP=8,ALU=9,OUT_WR=10,OUT_ACK=11,OUT_RD=12,OUT_RSP=13,
 LOCAL_WR=14,LOCAL_ACK=15,REMOTE_WR=16,REMOTE_ACK=17,FENCE=18,CONST_WR=19,CONST_ACK=20,FMAX_RD=21,FMAX_RSP=22,FMAX_WRITE=23,FMAX_ACK=24,FMAX_CAPTURE=25;
 // Sole control storage: SECDED256->288. No unprotected state shadow.
 reg [287:0] control;
 reg [71:0] data_a[0:63],data_b[0:63];
 wire [65:0] cd[0:3];wire [255:0] raw;wire [3:0] ctrl_bad;
 genvar k;
 for(k=0;k<4;k=k+1) begin: control_word
  assign cd[k]=decode64(control[k*72+:72]);
  assign raw[k*64+:64]=cd[k][63:0];assign ctrl_bad[k]=cd[k][65];
 end
 wire [4095:0] a,b;wire [127:0] data_bad;
 for(k=0;k<64;k=k+1) begin: data_word
  wire [65:0] da=decode64(data_a[k]),db=decode64(data_b[k]);
  assign a[k*64+:64]=da[63:0];assign b[k*64+:64]=db[63:0];
  assign data_bad[k]=da[65];assign data_bad[k+64]=db[65];
 end
 wire [4:0] phase=raw[4:0];wire [54:0] identity=raw[59:5];
 wire [1:0] fq,quarantine,fr,vis,retire,ack_ready;
 wire [109:0] vi,ri;
 wire row_bad=(|ctrl_bad)||(|data_bad)||(|raw[255:196])||phase>FMAX_CAPTURE;
 wire busy=phase!=IDLE;
 wire unexpected=busy && ((local_ack_valid && !(phase==A_ACK||phase==B_ACK||phase==OUT_ACK||phase==CONST_ACK||phase==FMAX_ACK)) ||
                         (remote_ack_valid && phase!=REMOTE_ACK) ||
                         (local_rsp_valid && !(phase==HOME_RSP||phase==WORK_RSP||phase==FMAX_RSP)));
 wire live=por_n && rst_n && !row_bad && !raw[188] && !(|fq) && !unexpected;
 assign fault=row_bad||raw[188]||(|fq)||unexpected;
 assign exclusive_lease=busy;
 assign req_ready=live && phase==IDLE && (&fr) && issuer_binding_valid && req_owner46[38:36]==0 &&
                  !local_ack_valid && !remote_ack_valid && !local_rsp_valid && !admission_stop;
 wire accept=req_valid && req_ready;
 assign rearm_ready=por_n && rst_n && admission_stop && issuer_allcopy_fenced && (&fr) &&
                   !local_ack_valid && !remote_ack_valid && !local_rsp_valid && !row_bad;
 assign local_rd_valid=live && (phase==HOME_RD||phase==WORK_RD||phase==FMAX_RD);
 assign local_rd_a=phase==HOME_RD?9'd38:phase==WORK_RD?9'd17:9'd17;
 assign local_rd_b=phase==HOME_RD?9'd38:phase==WORK_RD?9'd18:9'd18;
 assign local_rsp_ready=live && (phase==HOME_RSP||phase==WORK_RSP||phase==FMAX_RSP);
 assign local_wr_valid=live && (phase==A_WR||phase==B_WR||phase==OUT_WR||phase==CONST_WR||phase==FMAX_WRITE);
 assign local_wr_addr=phase==A_WR?9'd17:phase==B_WR?9'd18:phase==OUT_WR?9'd17:phase==CONST_WR?9'd18:9'd19;
 assign local_wr_data=phase==B_WR?b:phase==CONST_WR?{128{32'hc2ae0000}}:a;
 assign local_ack_ready=live && (phase==A_ACK||phase==B_ACK||phase==OUT_ACK||phase==CONST_ACK||
                               (phase==FMAX_ACK && ack_ready[0]));
 assign remote_wr_valid=0;
 assign remote_wr_addr=0;assign remote_wr_data=0;
 assign remote_ack_ready=0;
 wire launch=live && phase==WORK_RSP && local_rsp_valid;
 wire fmax_launch=live && phase==FMAX_RSP && local_rsp_valid;
 wire [4095:0] result;wire [127:0] leaf_fault,leaf_valid,input_nonfinite;
 for(k=0;k<128;k=k+1) begin: lane
  assign input_nonfinite[k]=(local_rsp_a[k*32+23+:8]==8'hff);
  ot_gpu_c0_fmax_leaf u_max(.clk(clk),.por_n(por_n),.valid_in(fmax_launch),
   .a(local_rsp_a[k*32+:32]),.b(local_rsp_b[k*32+:32]),
   .y(result[k*32+:32]),.valid_out(leaf_valid[k]),.fault(leaf_fault[k]));
 end
 // NEG's explicit BITCAST_U/XOR/BITCAST_F producer sequence is lane-local;
 // three positive control edges; output write waits the ordered sequence.
 wire neg_done=phase==ALU && raw[191];
 reg [255:0] next_raw;
 always @* begin
  next_raw=raw;
  next_raw[195:189]={4'b0,raw[190:189],launch};
  if (accept) begin next_raw='0;next_raw[4:0]=HOME_RD;next_raw[59:5]={req_owner46,9'd19};
   next_raw[123:60]=req_native_tag;next_raw[187:124]=req_native_generation;end
  else if (rearm_valid && rearm_ready) next_raw='0;
  else if (live) case(phase)
   HOME_RD:if(local_rd_ready)next_raw[4:0]=HOME_RSP;
   HOME_RSP:if(local_rsp_valid)next_raw[4:0]=A_WR;
   A_WR:if(local_wr_ready)next_raw[4:0]=A_ACK;
   A_ACK:if(local_ack_valid)next_raw[4:0]=B_WR;
   B_WR:if(local_wr_ready)next_raw[4:0]=B_ACK;
   B_ACK:if(local_ack_valid)next_raw[4:0]=WORK_RD;
   WORK_RD:if(local_rd_ready)next_raw[4:0]=WORK_RSP;
   WORK_RSP:if(local_rsp_valid)begin if(|input_nonfinite)next_raw[188]=1;else next_raw[4:0]=ALU;end
   ALU:if(neg_done)next_raw[4:0]=OUT_WR;
   OUT_WR:if(local_wr_ready)next_raw[4:0]=OUT_ACK;
   OUT_ACK:if(local_ack_valid)next_raw[4:0]=CONST_WR;
   CONST_WR:if(local_wr_ready)next_raw[4:0]=CONST_ACK;
   CONST_ACK:if(local_ack_valid)next_raw[4:0]=FMAX_RD;
   FMAX_RD:if(local_rd_ready)next_raw[4:0]=FMAX_RSP;
   FMAX_RSP:if(local_rsp_valid)next_raw[4:0]=FMAX_CAPTURE;
   FMAX_CAPTURE:begin if(|leaf_fault)next_raw[188]=1;else if(&leaf_valid)next_raw[4:0]=FMAX_WRITE;end
   FMAX_WRITE:if(local_wr_ready)next_raw[4:0]=FMAX_ACK;
   FMAX_ACK:if(local_ack_valid && local_ack_ready)next_raw[4:0]=FENCE;
   FENCE:if(done_valid && done_ready)next_raw='0;
   default:begin end
  endcase
  if (unexpected || (|fq))next_raw[188]=1;
  if (!rst_n && busy)next_raw[188]=1;
 end
 integer i;
 always @(posedge clk or negedge por_n) begin
  if(!por_n)begin control<=0;for(i=0;i<64;i=i+1)begin data_a[i]<=0;data_b[i]<=0;end end
  else if(!row_bad)begin
   for(i=0;i<4;i=i+1)control[i*72+:72]<=encode64(next_raw[i*64+:64]);
   if(live && phase==HOME_RSP && local_rsp_valid)for(i=0;i<64;i=i+1)begin
    data_a[i]<=encode64(local_rsp_a[i*64+:64]);data_b[i]<=encode64({2{32'h80000000}});end
   if(live && launch && !(|input_nonfinite))for(i=0;i<64;i=i+1)data_a[i]<=encode64(local_rsp_a[i*64+:64]^local_rsp_b[i*64+:64]);
   if(live && phase==FMAX_CAPTURE && (&leaf_valid) && !(|leaf_fault))for(i=0;i<64;i=i+1)data_a[i]<=encode64(result[i*64+:64]);
  end
 end
 assign visible_valid=live && phase==FENCE && (&vis);
 assign visible_identity=identity;
 assign done_valid=live && phase==FENCE && (&retire);
 assign done_native_tag=raw[123:60];assign done_native_generation=raw[187:124];
 for(k=0;k<2;k=k+1)begin:fence
  if(k==0)begin:actual
  ot_gpu_rf_visibility_fence_w6 #(.ENABLE(1)) u_w6(
   .clk(clk),.por_n(por_n),.rst_n(rst_n),.req_valid(accept),.req_identity({req_owner46,9'd19}),
   .req_internal_SIMD(1'b0),.req_ready(fr[k]),
   .host_ack_valid(live && phase==FMAX_ACK && local_ack_valid),
   .host_ack_identity(identity),.host_ack_ready(ack_ready[k]),
   .simd_ack_retire_valid(1'b0),.simd_ack_retire_identity(55'd0),.simd_ack_retire_ready(),
   .visible_valid(vis[k]),.visible_identity(vi[k*55+:55]),.visible_ready(visible_valid && visible_ready),
   .consumer_valid(consumer_valid[k]),.consumer_identity(consumer_identity[k*55+:55]),.consumer_ready(consumer_ready[k]),
   .child_reverse_valid(child_reverse_valid[k]),.child_reverse_identity(child_reverse_identity[k*55+:55]),.child_reverse_ready(child_reverse_ready[k]),
   .parent_reverse_valid(parent_reverse_valid[k]),.parent_reverse_identity(parent_reverse_identity[k*55+:55]),.parent_reverse_ready(parent_reverse_ready[k]),
   .reverse_CDC_valid(reverse_CDC_valid[k]),.reverse_CDC_identity(reverse_CDC_identity[k*55+:55]),.reverse_CDC_ready(reverse_CDC_ready[k]),
   .drain_req_valid(drain_req_valid[k]),.drain_req_identity(drain_req_identity[k*55+:55]),
   .drain_req_has_owner(drain_req_has_owner[k]),.drain_req_reset_scope(drain_req_reset_scope[k]),.drain_req_ready(drain_req_ready[k]),
   .drain_rsp_valid(drain_rsp_valid[k]),.drain_rsp_identity(drain_rsp_identity[k*55+:55]),
   .drain_rsp_has_owner(drain_rsp_has_owner[k]),.drain_rsp_reset_scope(drain_rsp_reset_scope[k]),
   .alldrain_live(alldrain_live[k*9+:9]),.drain_rsp_ready(drain_rsp_ready[k]),
   .retire_valid(retire[k]),.retire_identity(ri[k*55+:55]),.retire_ready(done_valid && done_ready),.fault(fq[k]),.quarantine(quarantine[k]));
  end else begin:absent_remote
   assign fr[k]=1;assign vis[k]=1;assign retire[k]=1;assign fq[k]=0;assign quarantine[k]=0;assign ack_ready[k]=0;
   assign vi[k*55+:55]=0;assign ri[k*55+:55]=0;
   assign consumer_ready[k]=0;assign child_reverse_ready[k]=0;assign parent_reverse_ready[k]=0;assign reverse_CDC_ready[k]=0;
   assign drain_req_valid[k]=0;assign drain_req_identity[k*55+:55]=0;assign drain_req_has_owner[k]=0;
   assign drain_req_reset_scope[k]=0;assign drain_rsp_ready[k]=0;
  end
 end
 end else begin:disabled
 assign req_ready=0;assign local_rd_valid=0;assign local_rd_a=0;assign local_rd_b=0;
 assign local_rsp_ready=0;assign local_wr_valid=0;assign local_wr_addr=0;assign local_wr_data=0;assign local_ack_ready=0;
 assign remote_wr_valid=0;assign remote_wr_addr=0;assign remote_wr_data=0;assign remote_ack_ready=0;
 assign visible_valid=0;assign visible_identity=0;assign consumer_ready=0;assign child_reverse_ready=0;
 assign parent_reverse_ready=0;assign reverse_CDC_ready=0;assign drain_req_valid=0;assign drain_req_identity=0;
 assign drain_req_has_owner=0;assign drain_req_reset_scope=0;assign drain_rsp_ready=0;
 assign done_valid=0;assign done_native_tag=0;assign done_native_generation=0;
 assign rearm_ready=0;assign exclusive_lease=0;assign fault=0;
 end endgenerate
endmodule
