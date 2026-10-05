`timescale 1ns/1ps
module tb;
reg clk=0;
reg power_on_reset_n=0;
reg warm_reset=0;
reg cmd_valid=0;
wire cmd_ready;
reg [255:0] cmd_program_sha=0;
reg [238:0] cmd_tuple=0;
reg [54:0] cmd_owner=0;
reg [10:0] cmd_PC=0;
reg [63:0] cmd_sequence=0;
reg [7:0] cmd_descriptor=0;
reg [3:0] cmd_template=0;
reg [5:0] cmd_step=0;
reg [1:0] cmd_substep=0;
reg [2:0] cmd_operands=0;
reg [7:0] cmd_elements=0;
reg [7:0] cmd_types=0;
reg [1:0] cmd_dtype=0;
reg [1:0] cmd_result_type=0;
reg cmd_canonical_zero=0;
reg [31:0] cmd_counts=0;
reg [3:0] cmd_scalars=0;
reg [71:0] cmd_source_slots=0;
reg [183:0] cmd_source_owners=0;
reg [17:0] cmd_result_slots=0;
reg [45:0] cmd_result_owner=0;
reg [255:0] cmd_shape_sha=0;
reg [1279:0] cmd_movement_map=0;
reg authority_valid=0;
reg [238:0] authority_tuple=0;
reg [54:0] authority_owner=0;
reg [10:0] authority_PC=0;
reg [255:0] authority_shape_sha=0;
reg [3:0] source_owner_held=0;
reg result_owner_held=0;
reg [71:0] authority_source_slots=0;
reg [183:0] authority_source_owners=0;
reg [17:0] authority_result_slots=0;
reg [45:0] authority_result_owner=0;
wire host_rd_valid;
reg host_rd_ready=0;
wire [8:0] host_a;
wire [8:0] host_b;
reg host_rsp_valid=0;
wire host_rsp_ready;
reg [4095:0] host_rsp_a=0;
reg [4095:0] host_rsp_b=0;
wire host_wr_valid;
reg host_wr_ready=0;
wire [8:0] host_dst;
wire [4095:0] host_wdata;
wire [45:0] host_owner;
reg host_ack_valid=0;
wire host_ack_ready;
reg [8:0] host_ack_slot=0;
reg [45:0] host_ack_owner=0;
reg output_visible=0;
reg [238:0] visible_tuple=0;
reg [54:0] visible_owner=0;
wire result_valid;
reg result_ready=0;
wire [10:0] result_PC;
wire [63:0] result_sequence;
wire [238:0] result_tuple;
wire [54:0] result_owner;
wire [1:0] result_dtype;
wire [10:0] result_bytes;
wire [8191:0] result_data;
wire reverse_valid;
reg reverse_ready=0;
reg [10:0] reverse_ack_PC=0;
reg [63:0] reverse_ack_sequence=0;
reg [238:0] reverse_ack_tuple=0;
reg [54:0] reverse_ack_owner=0;
wire [10:0] reverse_PC;
wire [63:0] reverse_sequence;
wire [238:0] reverse_tuple;
wire [54:0] reverse_owner;
wire external_valid;
reg external_ready=0;
wire [5:0] external_opcode;
wire [1:0] external_dtype;
wire external_canonical_zero;
wire external_a_scalar;
wire external_b_scalar;
wire external_c_scalar;
wire [7:0] external_types;
wire [3:0] external_mask;
wire [255:0] external_a;
wire [255:0] external_b;
wire [255:0] external_c;
wire [255:0] external_d;
wire [238:0] external_tuple;
wire [54:0] external_owner;
wire [10:0] external_PC;
wire [63:0] external_sequence;
wire [5:0] external_beat;
reg external_result_valid=0;
wire external_result_ready;
reg [255:0] external_result=0;
reg [1:0] external_result_type=0;
reg [3:0] external_lane_fault=0;
reg [238:0] external_result_tuple=0;
reg [54:0] external_result_owner=0;
reg [10:0] external_result_PC=0;
reg [63:0] external_result_sequence=0;
reg [5:0] external_result_beat=0;
wire busy;
wire fault;
always #5 clk=~clk;
integer cycles=0;always @(posedge clk) cycles<=cycles+1;
ot_gpu_native_primitive_controller #(.ENABLE(1),.DESCRIPTOR_FILE("/home/ubuntu/native-primitive-controller-20261003/results/uarch/qwen_native_primitive_control_20261003/descriptor.mem"),.PC_TEMPLATE_FILE("/home/ubuntu/native-primitive-controller-20261003/results/uarch/qwen_native_primitive_control_20261003/pc_templates.mem")) dut(.clk(clk),.power_on_reset_n(power_on_reset_n),.warm_reset(warm_reset),.cmd_valid(cmd_valid),.cmd_ready(cmd_ready),.cmd_program_sha(cmd_program_sha),.cmd_tuple(cmd_tuple),.cmd_owner(cmd_owner),.cmd_PC(cmd_PC),.cmd_sequence(cmd_sequence),.cmd_descriptor(cmd_descriptor),.cmd_template(cmd_template),.cmd_step(cmd_step),.cmd_substep(cmd_substep),.cmd_operands(cmd_operands),.cmd_elements(cmd_elements),.cmd_types(cmd_types),.cmd_dtype(cmd_dtype),.cmd_result_type(cmd_result_type),.cmd_canonical_zero(cmd_canonical_zero),.cmd_counts(cmd_counts),.cmd_scalars(cmd_scalars),.cmd_source_slots(cmd_source_slots),.cmd_source_owners(cmd_source_owners),.cmd_result_slots(cmd_result_slots),.cmd_result_owner(cmd_result_owner),.cmd_shape_sha(cmd_shape_sha),.cmd_movement_map(cmd_movement_map),.authority_valid(authority_valid),.authority_tuple(authority_tuple),.authority_owner(authority_owner),.authority_PC(authority_PC),.authority_shape_sha(authority_shape_sha),.source_owner_held(source_owner_held),.result_owner_held(result_owner_held),.authority_source_slots(authority_source_slots),.authority_source_owners(authority_source_owners),.authority_result_slots(authority_result_slots),.authority_result_owner(authority_result_owner),.host_rd_valid(host_rd_valid),.host_rd_ready(host_rd_ready),.host_a(host_a),.host_b(host_b),.host_rsp_valid(host_rsp_valid),.host_rsp_ready(host_rsp_ready),.host_rsp_a(host_rsp_a),.host_rsp_b(host_rsp_b),.host_wr_valid(host_wr_valid),.host_wr_ready(host_wr_ready),.host_dst(host_dst),.host_wdata(host_wdata),.host_owner(host_owner),.host_ack_valid(host_ack_valid),.host_ack_ready(host_ack_ready),.host_ack_slot(host_ack_slot),.host_ack_owner(host_ack_owner),.output_visible(output_visible),.visible_tuple(visible_tuple),.visible_owner(visible_owner),.result_valid(result_valid),.result_ready(result_ready),.result_PC(result_PC),.result_sequence(result_sequence),.result_tuple(result_tuple),.result_owner(result_owner),.result_dtype(result_dtype),.result_bytes(result_bytes),.result_data(result_data),.reverse_valid(reverse_valid),.reverse_ready(reverse_ready),.reverse_ack_PC(reverse_ack_PC),.reverse_ack_sequence(reverse_ack_sequence),.reverse_ack_tuple(reverse_ack_tuple),.reverse_ack_owner(reverse_ack_owner),.reverse_PC(reverse_PC),.reverse_sequence(reverse_sequence),.reverse_tuple(reverse_tuple),.reverse_owner(reverse_owner),.external_valid(external_valid),.external_ready(external_ready),.external_opcode(external_opcode),.external_dtype(external_dtype),.external_canonical_zero(external_canonical_zero),.external_a_scalar(external_a_scalar),.external_b_scalar(external_b_scalar),.external_c_scalar(external_c_scalar),.external_types(external_types),.external_mask(external_mask),.external_a(external_a),.external_b(external_b),.external_c(external_c),.external_d(external_d),.external_tuple(external_tuple),.external_owner(external_owner),.external_PC(external_PC),.external_sequence(external_sequence),.external_beat(external_beat),.external_result_valid(external_result_valid),.external_result_ready(external_result_ready),.external_result(external_result),.external_result_type(external_result_type),.external_lane_fault(external_lane_fault),.external_result_tuple(external_result_tuple),.external_result_owner(external_result_owner),.external_result_PC(external_result_PC),.external_result_sequence(external_result_sequence),.external_result_beat(external_result_beat),.busy(busy),.fault(fault));

 reg [4095:0] RF[0:15];reg rd_debt=0,wr_debt=0,bad_ack=0;
 integer writes=0,reads=0;reg [8191:0] expected;
 always @(posedge clk)begin
  if(!power_on_reset_n)begin rd_debt<=0;wr_debt<=0;host_rsp_valid<=0;host_ack_valid<=0;end
  else begin
   if(host_rd_valid&&host_rd_ready)begin
    if(rd_debt)$fatal(1,"duplicate RF read");
    rd_debt<=1;host_rsp_a<=RF[host_a];host_rsp_b<=RF[host_b];host_rsp_valid<=1;reads<=reads+1;
   end
   if(host_rsp_valid&&host_rsp_ready)begin host_rsp_valid<=0;rd_debt<=0;end
   if(host_wr_valid&&host_wr_ready)begin
    if(wr_debt)$fatal(1,"duplicate RF write");
    RF[host_dst]<=host_wdata;host_ack_slot<=host_dst;host_ack_owner<=host_owner^(bad_ack?46'd1:46'd0);
    host_ack_valid<=1;wr_debt<=1;writes<=writes+1;
   end
   if(host_ack_valid&&host_ack_ready)begin host_ack_valid<=0;wr_debt<=0;end
  end
 end
 task edge;begin @(posedge clk);#1;end endtask
 task boot;begin
  @(negedge clk);power_on_reset_n=0;cmd_valid=0;result_ready=0;reverse_ready=0;output_visible=0;warm_reset=0;host_wr_ready=0;
  edge();@(negedge clk);power_on_reset_n=1;edge();
 end endtask
 task setup_copy;begin
  cmd_program_sha=256'hab3fe8d6469d6a1552e2eeaa9efe945c025cc35a567f0d8161e3c2a02fc59354;
  cmd_tuple=239'h123abc;cmd_owner=55'h1234;cmd_PC=0;cmd_sequence=64'hfed0123456789abc;
  cmd_descriptor=29;cmd_template=4;cmd_step=11;cmd_substep=0;cmd_operands=1;cmd_elements=128;
  cmd_types=8'h02;cmd_dtype=2;cmd_result_type=2;cmd_counts=32'h80;cmd_scalars=0;
  cmd_source_slots={54'd0,9'd2,9'd1};cmd_source_owners=184'hbc;cmd_result_slots={9'd4,9'd3};cmd_result_owner=46'hcd;
  cmd_shape_sha=256'hca;cmd_canonical_zero=0;
  authority_valid=1;authority_tuple=cmd_tuple;authority_owner=cmd_owner;authority_PC=cmd_PC;authority_shape_sha=cmd_shape_sha;
  authority_source_slots=cmd_source_slots;authority_source_owners=cmd_source_owners;authority_result_slots=cmd_result_slots;authority_result_owner=cmd_result_owner;
  source_owner_held=1;result_owner_held=1;visible_tuple=cmd_tuple;visible_owner=cmd_owner;host_rd_ready=1;
  reverse_ack_PC=cmd_PC;reverse_ack_sequence=cmd_sequence;reverse_ack_tuple=cmd_tuple;reverse_ack_owner=cmd_owner;
 end endtask
 task submit;begin
  @(negedge clk);cmd_valid=1;
  if(!cmd_ready)begin #1;if(!cmd_ready)$fatal(1,"legal command not ready");end
  edge();@(negedge clk);cmd_valid=0;
 end endtask
 initial begin
  expected=0;
  for(integer e=0;e<128;e=e+1)expected[e*64+:64]=64'hf000000000000000|e;
  RF[1]=expected[4095:0];RF[2]=expected[8191:4096];RF[3]=0;RF[4]=0;
  boot();setup_copy();submit();
  // Live request mutation cannot change accepted scope/data/retirement identity.
  cmd_PC=40;cmd_sequence=7;cmd_tuple=0;cmd_owner=0;
  wait(host_wr_valid);#1;
  repeat(4)begin edge();if(result_valid||host_dst!=3||host_owner!=46'hcd||host_wdata!=expected[4095:0])$fatal(1,"write backpressure or retag");end
  @(negedge clk);host_wr_ready=1;
  wait(writes==2);wait(!host_ack_valid);repeat(4)begin edge();if(result_valid)$fatal(1,"early visibility");end
  if({RF[4],RF[3]}!==expected)$fatal(1,"owned RF publication mismatch");
  @(negedge clk);output_visible=1;wait(result_valid);#1;
  repeat(8)begin edge();if(!result_valid||result_data!==expected||result_PC!=0||result_sequence!=64'hfed0123456789abc||result_bytes!=1024||fault)$fatal(1,"held result mismatch");end
  @(negedge clk);result_ready=1;edge();@(negedge clk);result_ready=0;
  repeat(5)begin edge();if(!reverse_valid||!busy||cmd_ready||reverse_tuple!=239'h123abc)$fatal(1,"reverse debt lost");end
  @(negedge clk);reverse_ready=1;edge();@(negedge clk);reverse_ready=0;edge();if(busy||fault)$fatal(1,"matched reverse failed");
  $display("PASS full128 I64 two-page RF read/write, hold, visibility, tuple/tag capture, separate reverse");
  boot();setup_copy();bad_ack=1;submit();host_wr_ready=1;wait(fault);edge();if(!busy||result_valid||host_ack_ready)$fatal(1,"wrong ACK escaped quarantine");
  $display("PASS stale owner ACK quarantines accepted debt");
  boot();setup_copy();bad_ack=0;submit();@(negedge clk);dut.command_code[0][0]=~dut.command_code[0][0];edge();edge();if(!fault||!busy||result_valid)$fatal(1,"command protection failed");
  $display("PASS protected command fault holds debt");
  boot();setup_copy();submit();@(negedge clk);warm_reset=1;edge();edge();if(!fault||!busy||host_rd_valid||result_valid)$fatal(1,"warm reset discarded debt");
  $display("PASS warm-reset quarantine retains debt");
  boot();setup_copy();cmd_descriptor=0;cmd_template=0;cmd_step=0;cmd_dtype=0;cmd_result_type=0;cmd_canonical_zero=0;
  @(negedge clk);cmd_valid=1;edge();if(!fault||busy)$fatal(1,"source attr mismatch accepted");
  $display("PASS source canonical_zero mismatch refused before launch");
  $display("PASS controller directed protocol terminal cycles=%0d reads=%0d writes=%0d",cycles,reads,writes);$finish;
 end
 endmodule

