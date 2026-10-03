`timescale 1ns/1ps
// Unit tests of the new publisher/caller lease state, not a production gate.
module tb;
reg  clk;
reg  por_n;
reg  rst_n;
reg  publish_valid;
wire  publish_ready;
reg [4095:0] publish_data;
reg [45:0] publish_owner46;
reg [63:0] publish_native_tag;
reg [63:0] publish_native_generation;
reg  source_lease_reserved;
reg  workspace_reserved;
reg  issuer_namespace_reserved;
reg  admission_stop;
wire  c_req_valid;
reg  c_req_ready;
wire [45:0] c_owner46;
wire [63:0] c_native_tag;
wire [63:0] c_native_generation;
reg  c_wr_valid;
wire  c_wr_ready;
reg [8:0] c_wr_slot;
reg [4095:0] c_wr_data;
reg [45:0] c_wr_owner;
wire  c_ack_valid;
reg  c_ack_ready;
wire [45:0] c_ack_owner;
wire [8:0] c_ack_slot;
wire  c_ack_fault;
wire  rf_wr_valid;
reg  rf_wr_ready;
wire [8:0] rf_wr_slot;
wire [4095:0] rf_wr_data;
wire [45:0] rf_wr_owner;
reg  rf_ack_valid;
wire  rf_ack_ready;
reg [45:0] rf_ack_owner;
reg [8:0] rf_ack_slot;
reg  rf_ack_fault;
reg  c_done_valid;
reg  c_done_ready;
reg  c_fault;
reg  source_release_valid;
reg [54:0] source_release_identity;
wire  source_release_ready;
wire  source_lease_live;
wire  workspace_lease_live;
wire  source_published;
wire  fault;
ot_gpu_pc40_native_ingress #(.ENABLE(1))dut(
.clk(clk),
.por_n(por_n),
.rst_n(rst_n),
.publish_valid(publish_valid),
.publish_ready(publish_ready),
.publish_data(publish_data),
.publish_owner46(publish_owner46),
.publish_native_tag(publish_native_tag),
.publish_native_generation(publish_native_generation),
.source_lease_reserved(source_lease_reserved),
.workspace_reserved(workspace_reserved),
.issuer_namespace_reserved(issuer_namespace_reserved),
.admission_stop(admission_stop),
.c_req_valid(c_req_valid),
.c_req_ready(c_req_ready),
.c_owner46(c_owner46),
.c_native_tag(c_native_tag),
.c_native_generation(c_native_generation),
.c_wr_valid(c_wr_valid),
.c_wr_ready(c_wr_ready),
.c_wr_slot(c_wr_slot),
.c_wr_data(c_wr_data),
.c_wr_owner(c_wr_owner),
.c_ack_valid(c_ack_valid),
.c_ack_ready(c_ack_ready),
.c_ack_owner(c_ack_owner),
.c_ack_slot(c_ack_slot),
.c_ack_fault(c_ack_fault),
.rf_wr_valid(rf_wr_valid),
.rf_wr_ready(rf_wr_ready),
.rf_wr_slot(rf_wr_slot),
.rf_wr_data(rf_wr_data),
.rf_wr_owner(rf_wr_owner),
.rf_ack_valid(rf_ack_valid),
.rf_ack_ready(rf_ack_ready),
.rf_ack_owner(rf_ack_owner),
.rf_ack_slot(rf_ack_slot),
.rf_ack_fault(rf_ack_fault),
.c_done_valid(c_done_valid),
.c_done_ready(c_done_ready),
.c_fault(c_fault),
.source_release_valid(source_release_valid),
.source_release_identity(source_release_identity),
.source_release_ready(source_release_ready),
.source_lease_live(source_lease_live),
.workspace_lease_live(workspace_lease_live),
.source_published(source_published),
.fault(fault));
always #5 clk=~clk;

 task tick;begin @(posedge clk);#1;end endtask
 task cold;begin por_n=0;rst_n=1;publish_valid=0;rf_ack_valid=0;rf_ack_fault=0;
  source_release_valid=0;c_fault=0;c_wr_valid=0;c_done_valid=0;tick();por_n=1;tick();end endtask
 task offer;begin
  source_lease_reserved=1;workspace_reserved=1;issuer_namespace_reserved=1;
  publish_data={128{32'h12345678}};publish_owner46=46'h8000001237;
  publish_native_tag=64'h10000000009;publish_native_generation=64'h40000000003;
  publish_valid=1;#1;if(!publish_ready)$fatal(1,"publication not ready");tick();publish_valid=0;
  if(!rf_wr_valid||rf_wr_slot!=38||rf_wr_owner!=publish_owner46||rf_wr_data!=publish_data)$fatal(1,"actual ingress write fields");
  publish_data='0;publish_owner46=0;publish_native_tag=0;publish_native_generation=0;#1;
  if(rf_wr_data!={128{32'h12345678}})$fatal(1,"payload not retained");
  rf_wr_ready=1;tick();rf_wr_ready=0;
 end endtask
 initial begin
clk=0;por_n=0;rst_n=0;publish_valid=0;publish_data=0;publish_owner46=0;publish_native_tag=0;publish_native_generation=0;source_lease_reserved=0;workspace_reserved=0;issuer_namespace_reserved=0;admission_stop=0;c_req_ready=0;c_wr_valid=0;c_wr_slot=0;c_wr_data=0;c_wr_owner=0;c_ack_ready=0;rf_wr_ready=0;rf_ack_valid=0;rf_ack_owner=0;rf_ack_slot=0;rf_ack_fault=0;c_done_valid=0;c_done_ready=0;c_fault=0;source_release_valid=0;source_release_identity=0;
  cold();
  publish_valid=1;#1;if(publish_ready)$fatal(1,"missing lease admitted");publish_valid=0;
  offer();rf_ack_valid=1;rf_ack_owner=46'h8000001237;rf_ack_slot=38;#1;
  if(rf_ack_ready)$fatal(1,"ACK bypassed positive check");tick();
  if(!rf_ack_ready)$fatal(1,"matching held ACK did not become ready");tick();rf_ack_valid=0;#1;
  if(!c_req_valid||c_owner46!=46'h8000001237||c_native_tag!=64'h10000000009||c_native_generation!=64'h40000000003)$fatal(1,"private native identity changed");
  c_req_ready=1;rf_wr_ready=1;tick();c_req_ready=0;
  c_wr_valid=1;c_wr_owner=c_owner46;c_wr_slot=17;c_wr_data={128{32'habcdef01}};#1;
  if(!rf_wr_valid||rf_wr_slot!=17||rf_wr_owner!=c_owner46)$fatal(1,"callee write not routed");
  tick();c_wr_valid=0;c_done_valid=1;c_done_ready=1;tick();c_done_valid=0;
  if(!source_lease_live||workspace_lease_live||publish_ready)$fatal(1,"source prematurely released at selected completion");
  source_release_identity={46'h8000001237,9'd38};source_release_valid=1;#1;
  if(!source_release_ready)$fatal(1,"actual caller release refused");tick();source_release_valid=0;
  if(source_lease_live)$fatal(1,"matching release retained lease");
  $display("UNIT_PASS ingress_retained_payload_and_source_lifetime");
  cold();offer();rf_ack_valid=1;rf_ack_owner=46'h8000001236;rf_ack_slot=38;#1;
  if(!fault||rf_ack_ready||c_req_valid)$fatal(1,"wrong owner released publisher");tick();rf_ack_valid=0;
  if(!fault||!source_lease_live)$fatal(1,"wrong owner debt not held");
  $display("UNIT_PASS wrong_owner_held");
  cold();offer();rf_ack_valid=1;rf_ack_owner=46'h8000001237;rf_ack_slot=19;#1;
  if(!fault||rf_ack_ready||c_req_valid)$fatal(1,"wrong slot released publisher");
  $display("UNIT_PASS wrong_slot_held");
  cold();offer();rst_n=0;tick();rst_n=1;tick();
  if(!fault||!source_lease_live||publish_ready)$fatal(1,"reset dropped accepted debt");
  $display("UNIT_PASS reset_debt_held");$finish;
 end
endmodule
