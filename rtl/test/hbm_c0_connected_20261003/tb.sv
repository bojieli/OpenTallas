`timescale 1ns/1ps
// Functional fixture: actual RF/W6/FMAX RTL, behavioral SRAM ONLY.
// Fixture ownership/certificates are not production issuer/drain receipts.
module tb;
 reg  clk;
 reg  por_n;
 reg  rst_n;
 reg  req_valid;
 wire  req_ready;
 reg [45:0] req_owner46;
 reg [63:0] req_native_tag;
 reg [63:0] req_native_generation;
 reg  issuer_binding_valid;
 wire  local_rd_valid;
 wire  local_rd_ready;
 wire [8:0] local_rd_a;
 wire [8:0] local_rd_b;
 wire  local_rsp_valid;
 wire  local_rsp_ready;
 wire [4095:0] local_rsp_a;
 wire [4095:0] local_rsp_b;
 wire  local_wr_valid;
 wire  local_wr_ready;
 wire [8:0] local_wr_addr;
 wire [4095:0] local_wr_data;
 wire  local_ack_valid;
 wire  local_ack_ready;
 wire  remote_wr_valid;
 wire  remote_wr_ready;
 wire [8:0] remote_wr_addr;
 wire [4095:0] remote_wr_data;
 wire  remote_ack_valid;
 wire  remote_ack_ready;
 wire  visible_valid;
 reg  visible_ready;
 wire [54:0] visible_identity;
 reg [1:0] consumer_valid;
 wire [1:0] consumer_ready;
 reg [109:0] consumer_identity;
 reg [1:0] child_reverse_valid;
 wire [1:0] child_reverse_ready;
 reg [109:0] child_reverse_identity;
 reg [1:0] parent_reverse_valid;
 wire [1:0] parent_reverse_ready;
 reg [109:0] parent_reverse_identity;
 reg [1:0] reverse_CDC_valid;
 wire [1:0] reverse_CDC_ready;
 reg [109:0] reverse_CDC_identity;
 wire [1:0] drain_req_valid;
 reg [1:0] drain_req_ready;
 wire [109:0] drain_req_identity;
 wire [1:0] drain_req_has_owner;
 wire [1:0] drain_req_reset_scope;
 reg [1:0] drain_rsp_valid;
 wire [1:0] drain_rsp_ready;
 reg [109:0] drain_rsp_identity;
 reg [1:0] drain_rsp_has_owner;
 reg [1:0] drain_rsp_reset_scope;
 reg [17:0] alldrain_live;
 wire  done_valid;
 reg  done_ready;
 wire [63:0] done_native_tag;
 wire [63:0] done_native_generation;
 reg  rearm_valid;
 reg  admission_stop;
 reg  issuer_allcopy_fenced;
 wire  rearm_ready;
 wire  exclusive_lease;
 wire  fault;
 ot_gpu_c0_connected_bridge #(.ENABLE(1)) dut(
 .clk(clk),
 .por_n(por_n),
 .rst_n(rst_n),
 .req_valid(req_valid),
 .req_ready(req_ready),
 .req_owner46(req_owner46),
 .req_native_tag(req_native_tag),
 .req_native_generation(req_native_generation),
 .issuer_binding_valid(issuer_binding_valid),
 .local_rd_valid(local_rd_valid),
 .local_rd_ready(local_rd_ready),
 .local_rd_a(local_rd_a),
 .local_rd_b(local_rd_b),
 .local_rsp_valid(local_rsp_valid),
 .local_rsp_ready(local_rsp_ready),
 .local_rsp_a(local_rsp_a),
 .local_rsp_b(local_rsp_b),
 .local_wr_valid(local_wr_valid),
 .local_wr_ready(local_wr_ready),
 .local_wr_addr(local_wr_addr),
 .local_wr_data(local_wr_data),
 .local_ack_valid(local_ack_valid),
 .local_ack_ready(local_ack_ready),
 .remote_wr_valid(remote_wr_valid),
 .remote_wr_ready(remote_wr_ready),
 .remote_wr_addr(remote_wr_addr),
 .remote_wr_data(remote_wr_data),
 .remote_ack_valid(remote_ack_valid),
 .remote_ack_ready(remote_ack_ready),
 .visible_valid(visible_valid),
 .visible_ready(visible_ready),
 .visible_identity(visible_identity),
 .consumer_valid(consumer_valid),
 .consumer_ready(consumer_ready),
 .consumer_identity(consumer_identity),
 .child_reverse_valid(child_reverse_valid),
 .child_reverse_ready(child_reverse_ready),
 .child_reverse_identity(child_reverse_identity),
 .parent_reverse_valid(parent_reverse_valid),
 .parent_reverse_ready(parent_reverse_ready),
 .parent_reverse_identity(parent_reverse_identity),
 .reverse_CDC_valid(reverse_CDC_valid),
 .reverse_CDC_ready(reverse_CDC_ready),
 .reverse_CDC_identity(reverse_CDC_identity),
 .drain_req_valid(drain_req_valid),
 .drain_req_ready(drain_req_ready),
 .drain_req_identity(drain_req_identity),
 .drain_req_has_owner(drain_req_has_owner),
 .drain_req_reset_scope(drain_req_reset_scope),
 .drain_rsp_valid(drain_rsp_valid),
 .drain_rsp_ready(drain_rsp_ready),
 .drain_rsp_identity(drain_rsp_identity),
 .drain_rsp_has_owner(drain_rsp_has_owner),
 .drain_rsp_reset_scope(drain_rsp_reset_scope),
 .alldrain_live(alldrain_live),
 .done_valid(done_valid),
 .done_ready(done_ready),
 .done_native_tag(done_native_tag),
 .done_native_generation(done_native_generation),
 .rearm_valid(rearm_valid),
 .admission_stop(admission_stop),
 .issuer_allcopy_fenced(issuer_allcopy_fenced),
 .rearm_ready(rearm_ready),
 .exclusive_lease(exclusive_lease),
 .fault(fault));
 reg seed_valid;reg [8:0] seed_addr;reg [4095:0] seed_data;
 wire seed_ready,seed_ack,local_provider_wr_ready,local_provider_ack;
 assign local_wr_ready=local_provider_wr_ready && !seed_valid;
 assign local_ack_valid=local_provider_ack && !seed_mode;
 reg seed_mode;
 ot_gpu_rf_service rf0(.clk(clk),.rst_n(rst_n),.rd_valid(local_rd_valid),.rd_ready(local_rd_ready),
 .rd_a(local_rd_a),.rd_b(local_rd_b),.rsp_valid(local_rsp_valid),.rsp_ready(local_rsp_ready),.rsp_a(local_rsp_a),.rsp_b(local_rsp_b),
 .wr_valid(seed_valid || local_wr_valid),.wr_ready(local_provider_wr_ready),.wr_addr(seed_valid?seed_addr:local_wr_addr),
 .wr_data(seed_valid?seed_data:local_wr_data),.ack_valid(local_provider_ack),.ack_ready(seed_mode?1'b1:local_ack_ready));
 ot_gpu_rf_service rf1(.clk(clk),.rst_n(rst_n),.rd_valid(1'b0),.rd_ready(),.rd_a(9'd0),.rd_b(9'd0),
 .rsp_valid(),.rsp_ready(1'b0),.rsp_a(),.rsp_b(),.wr_valid(remote_wr_valid),.wr_ready(remote_wr_ready),
 .wr_addr(remote_wr_addr),.wr_data(remote_wr_data),.ack_valid(remote_ack_valid),.ack_ready(remote_ack_ready));
 always #0.416667 clk=~clk;
 integer j; integer writes,reads,remote_writes;
 always @(posedge clk)begin
  if(local_wr_valid && local_wr_ready)begin
   writes<=writes+1;
   if(local_wr_addr==19)
    for(j=0;j<128;j=j+1) if(local_wr_data[j*32+:32]!==32'hc2ae0000)$fatal(1,"native FMAX result");
  end
  if(local_rd_valid && local_rd_ready)reads<=reads+1;
  if(remote_wr_valid && remote_wr_ready)begin
   remote_writes<=remote_writes+1;
   if(remote_wr_addr!==36)$fatal(1,"wrong remote home");
   for(j=0;j<128;j=j+1)if(remote_wr_data[j*32+:32]!==32'hc2ae0000)$fatal(1,"remote FMAX result");
  end
 end
 // Held positive-latency allcopy responder, local protocol fixture scope only.
 always @(posedge clk)begin
  if(!por_n)begin drain_rsp_valid<=0;drain_rsp_identity<=0;drain_rsp_has_owner<=0;drain_rsp_reset_scope<=0;end
  else for(integer c=0;c<2;c=c+1)begin
   if(drain_rsp_valid[c] && drain_rsp_ready[c])drain_rsp_valid[c]<=0;
   else if(drain_req_valid[c] && drain_req_ready[c])begin
    drain_rsp_valid[c]<=1;drain_rsp_identity[c*55+:55]<=drain_req_identity[c*55+:55];
    drain_rsp_has_owner[c]<=drain_req_has_owner[c];drain_rsp_reset_scope[c]<=drain_req_reset_scope[c];
   end
  end
 end
 always @* drain_req_ready=~drain_rsp_valid;
 task seed(input [8:0] addr,input [31:0] value);
 begin
  @(negedge clk);seed_mode=1;seed_addr=addr;seed_data={128{value}};seed_valid=1;
  wait(local_provider_wr_ready);@(posedge clk);@(negedge clk);seed_valid=0;
  wait(local_provider_ack);@(posedge clk);@(negedge clk);seed_mode=0;
 end endtask
 initial begin
  clk=0;
  por_n=0;
  rst_n=0;
  req_valid=0;
  req_owner46=0;
  req_native_tag=0;
  req_native_generation=0;
  issuer_binding_valid=0;
  visible_ready=0;
  consumer_valid=0;
  consumer_identity=0;
  child_reverse_valid=0;
  child_reverse_identity=0;
  parent_reverse_valid=0;
  parent_reverse_identity=0;
  reverse_CDC_valid=0;
  reverse_CDC_identity=0;
  alldrain_live=0;
  done_ready=0;
  rearm_valid=0;
  admission_stop=0;
  issuer_allcopy_fenced=0;
  seed_valid=0;seed_mode=0;seed_addr=0;seed_data=0;writes=0;reads=0;remote_writes=0;
  alldrain_live=18'h3ffff;issuer_binding_valid=1;
  repeat(2)@(negedge clk);por_n=1;rst_n=1;
  seed(38,32'h42c80000);
  // Literal independent test namespace, not a derived physical HBM PC.
  req_owner46={7'd1,3'd0,32'd13,4'd2};req_native_tag=64'h100000001;req_native_generation=64'h100000012;
  wait(req_ready);@(negedge clk);req_valid=1;@(posedge clk);@(negedge clk);req_valid=0;
  wait(visible_valid);
  repeat(4)begin @(negedge clk);if(!visible_valid || req_ready)$fatal(1,"lost held publication");end
  if(writes!=5 || reads!=3 || remote_writes!=0)$fatal(1,"provider service counts");
  consumer_identity={2{visible_identity}};child_reverse_identity={2{visible_identity}};
  parent_reverse_identity={2{visible_identity}};reverse_CDC_identity={2{visible_identity}};
  visible_ready=1;@(posedge clk);@(negedge clk);visible_ready=0;
  wait(consumer_ready[0]);@(negedge clk);consumer_valid=1;@(posedge clk);@(negedge clk);consumer_valid=0;
  wait(child_reverse_ready[0]);@(negedge clk);child_reverse_valid=1;@(posedge clk);@(negedge clk);child_reverse_valid=0;
  wait(parent_reverse_ready[0]);@(negedge clk);parent_reverse_valid=1;@(posedge clk);@(negedge clk);parent_reverse_valid=0;
  wait(reverse_CDC_ready[0]);@(negedge clk);reverse_CDC_valid=1;@(posedge clk);@(negedge clk);reverse_CDC_valid=0;
  wait(done_valid);
  repeat(3)begin @(negedge clk);if(!done_valid || req_ready)$fatal(1,"lost held retirement");end
  if(done_native_tag!==64'h100000001 || done_native_generation!==64'h100000012 || fault)$fatal(1,"native identity lost");
  done_ready=1;@(posedge clk);@(negedge clk);done_ready=0;
  wait(req_ready);seed(38,32'h7fc12345);
  req_owner46={7'd1,3'd0,32'd14,4'd2};req_native_tag=64'h100000002;
  wait(req_ready);@(negedge clk);req_valid=1;@(posedge clk);@(negedge clk);req_valid=0;
  wait(fault);repeat(3)@(negedge clk);
  if(writes!=7 || remote_writes!=0 || visible_valid || req_ready || !exclusive_lease)$fatal(1,"exception published/lost debt");
  $display("PASS actual RF/FMAX/W6 controller normal/held/identity/NaN fault fixture; production caller NOT qualified");$finish;
 end
endmodule
// Behavioral test macro: real provider drives both independent mirror instances.
module ot_sram_1r1w_128x256_m1_r2c2(input wire clk,r_ce_in,input wire[6:0]r_addr_in,output reg[255:0]rd_out,
 input wire w_ce_in,input wire[6:0]w_addr_in,input wire[255:0]wd_in,w_mask_in,
 input wire[1:0]rr_en,input wire[11:0]rr_addr,input wire[1:0]cr_en,input wire[15:0]cr_sel);
 reg [255:0] mem[0:127];
 always @(posedge clk)begin if(r_ce_in)rd_out<=mem[r_addr_in];if(w_ce_in)mem[w_addr_in]<=wd_in;end
endmodule
