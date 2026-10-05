`timescale 1ns/1ps
// Focused ABI slot/layout and refusal coverage; full program test is separate.
module tb_a3_g2_issue_contract;
 parameter bit RESOLVE=0;
 parameter bit INPUTS=0;
 parameter bit STREAM=0;
 reg [7:0] b_dtype=8'h10,group_size=1;
 wire input_layout_valid;
 wire [31:0] input_a_object,input_b_object,input_a_row_stride,input_a_k_stride,input_b_column_stride,input_b_k_stride;
 wire [63:0] input_a_object_bytes,input_b_object_bytes;
 reg [31:0] bad_input_object=0;
 reg [2:0] bad_input_kind=0;
 wire desc_short;
 wire [63:0] output_object_bytes;
 reg object_bad_type=0,object_readonly=0,object_empty=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,clear=0,issue_valid=0,view_valid=0,array_done=0;
 reg [7:0] issue_family=ot_a3_pkg::A3_MAJOR_TENSOR,array_error_code=0;
 reg [4:0] issue_slot=0,view_irs_slot=0;
 reg [2:0] view_slot=0;
 reg [31:0] view_descriptor_id=0;
 reg [63:0] view_element_offset=0;
 wire issue_ready,complete_valid,complete_fault,desc_req,array_start;
 wire [15:0] complete_trap_class,array_rows,array_cols,array_depth;
 wire [4:0] complete_slot;
 wire [31:0] desc_id,array_out_base;
 reg desc_valid=0,desc_fault=0;
 reg [1535:0] desc_data=0;
 reg [31:0] b_cols=8,b_depth=80,c_rows=1,c_cols=8;
 reg [7:0] c_dtype=8'h10;
 reg c_fault=0,c_scaled=0,c_bad_header=0,cfg_out_fp32=0;
 wire array_out_fp32,output_layout_valid;
 wire [31:0] output_object,output_row_stride,output_col_stride;
 reg [31:0] c_row_stride=32'h80000123,c_col_stride=32'h40000007;
 reg [7:0] a_rank=2,b_rank=2,c_rank=2;
 wire [15:0] output_logical_cols;
 reg [31:0] c_object=32'h12345678;
 integer launches=0,checks=0,cancel_state,bad_case,bad_object;
 ot_a3_g2_array_issue_adapter #(.RESOLVE_OUTPUT_OBJECT(RESOLVE),.RESOLVE_INPUT_OBJECTS(INPUTS),.REQUIRE_BF16_WEIGHT_STREAM(STREAM)) dut(
 .clk(clk),.rst_n(rst_n),.clear(clear),.issue_valid(issue_valid),.issue_ready(issue_ready),
 .issue_family(issue_family),.issue_sub(8'd0),.issue_descriptor_id(32'd0),.issue_slot(issue_slot),
 .view_valid(view_valid),.view_slot(view_slot),.view_irs_slot(view_irs_slot),
 .view_descriptor_id(view_descriptor_id),.view_element_offset(view_element_offset),
 .complete_valid(complete_valid),.complete_fault(complete_fault),.complete_trap_class(complete_trap_class),.complete_slot(complete_slot),
 .desc_req(desc_req),.desc_short(desc_short),.desc_id(desc_id),.desc_valid(desc_valid),.desc_fault(desc_fault || (c_fault && desc_id==12) || (bad_input_kind==6 && desc_id==bad_input_object)),.desc_data(desc_data),
 .cfg_group(group_size),.cfg_block_a(16'd0),.cfg_block_rows_a(16'd0),.cfg_block_b(16'd0),
 .cfg_scale_a_base(32'd0),.cfg_ws_base(32'd0),.cfg_out_fp32(cfg_out_fp32),.array_out_fp32(array_out_fp32),
 .array_start(array_start),.array_rows(array_rows),.array_cols(array_cols),.array_depth(array_depth),.array_out_base(array_out_base),
 .input_layout_valid(input_layout_valid),.input_a_object(input_a_object),.input_b_object(input_b_object),
 .input_a_object_bytes(input_a_object_bytes),.input_b_object_bytes(input_b_object_bytes),
 .input_a_row_stride(input_a_row_stride),.input_a_k_stride(input_a_k_stride),
 .input_b_column_stride(input_b_column_stride),.input_b_k_stride(input_b_k_stride),
 .output_object_bytes(output_object_bytes),
 .output_row_stride(output_row_stride),.output_col_stride(output_col_stride),
 .output_layout_valid(output_layout_valid),.output_object(output_object),.output_logical_cols(output_logical_cols),
 .array_done(array_done),.array_error_code(array_error_code));
 always @(posedge clk)begin
  desc_valid<=desc_req;
  if(desc_req)begin
   desc_data<=0;
   desc_data[31:0]<=(desc_id==12 && c_bad_header)?0:ot_a3_pkg::A3_DESCRIPTOR_MAGIC;
   desc_data[47:32]<=ot_a3_pkg::A3_DESC_TENSOR_VIEW;
   desc_data[55:48]<=ot_a3_pkg::A3_TYPE_MAJOR;
   desc_data[351:320]<=32'd64;
   desc_data[159:128]<=(desc_id==10)?32'd100:(desc_id==11)?32'd101:c_object;
   desc_data[527:520]<=(desc_id==10)?a_rank:(desc_id==11)?b_rank:c_rank;
   desc_data[927:896]<=(desc_id==10)?32'd113:(desc_id==11)?32'h80000003:c_row_stride;
   desc_data[959:928]<=(desc_id==10)?32'd2:(desc_id==11)?32'd7:c_col_stride;
   desc_data[519:512]<=(desc_id==12)?c_dtype:(desc_id==11)?b_dtype:8'h10;
   desc_data[575:544]<=(desc_id==12 && c_scaled)?32'd99:ot_a3_pkg::A3_NO_ID;
   desc_data[735:704]<=(desc_id==10)?32'd1:(desc_id==12)?c_rows:b_cols;
   if(desc_id!=10 && desc_id!=11 && desc_id!=12)begin
    desc_data[47:32]<=object_bad_type?ot_a3_pkg::A3_DESC_TENSOR_VIEW:ot_a3_pkg::A3_DESC_MEMORY_OBJECT;
    desc_data[257]<=!object_readonly;
    desc_data[256]<=1;
    desc_data[703:640]<=object_empty?64'd0:64'h100000123;
   end
   if(desc_id==100 || desc_id==101)begin
    desc_data[47:32]<=ot_a3_pkg::A3_DESC_MEMORY_OBJECT;
    desc_data[703:640]<=(desc_id==100)?64'h200000007:64'h300000011;
    if(desc_id==bad_input_object)begin
     case(bad_input_kind)
      1:desc_data[256]<=0;
      2:desc_data[703:640]<=0;
      3:desc_data[47:32]<=ot_a3_pkg::A3_DESC_TENSOR_VIEW;
      4:desc_data[31:0]<=0;
      5:desc_data[351:320]<=32'd128;
     endcase
    end
   end
   if((desc_id==10 || desc_id==11) && desc_short==INPUTS)$fatal(1,"input descriptor prefix selection");
   desc_data[767:736]<=(desc_id==10)?32'd80:(desc_id==12)?c_cols:b_depth;
  end
  if(array_start)launches<=launches+1;
  if(input_layout_valid)begin
   if(!INPUTS || input_a_object!=100 || input_b_object!=101 ||
      input_a_object_bytes!=64'h200000007 || input_b_object_bytes!=64'h300000011 ||
      input_a_row_stride!=113 || input_a_k_stride!=2 || input_b_column_stride!=32'h80000003 || input_b_k_stride!=7)
    $fatal(1,"input metadata corrupted");
  end
  if(array_start && !clear && INPUTS && !input_layout_valid)$fatal(1,"missing input ownership");
 end
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task view(input [2:0] slot,input [31:0] id,input [63:0] offset);begin
  view_valid=1;view_slot=slot;view_descriptor_id=id;view_element_offset=offset;tick();view_valid=0;
 end endtask
 task issue;begin
  if(!issue_ready)$fatal(1,"adapter not ready");
  issue_valid=1;tick();issue_valid=0;
 end endtask
 task expect_refusal(input [15:0] trap);integer before_launch;begin
  before_launch=launches;issue();
  wait(complete_valid);@(negedge clk);
  if(!complete_fault || complete_trap_class!=trap || complete_slot!=issue_slot || launches!=before_launch)
   $fatal(1,"wrong refusal");
  if(output_layout_valid || input_layout_valid)$fatal(1,"refused layout published");
  checks=checks+1;tick();tick();
 end endtask
 initial begin
  tick();rst_n=1;tick();
  // Actual ABI uses slots 0,1,4; a third input cannot replace the output.
  view(0,10,0);view(1,11,0);view(2,12,999);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);
  // Supply ignored slots as well: slot 2 must not overwrite compact output.
  view(0,10,0);view(1,11,0);view(4,12,123);view(2,13,999);view(5,14,888);issue();
  wait(array_start);@(negedge clk);
  if(array_rows!=1 || array_cols!=8 || array_depth!=80 || array_out_base!=123 || array_out_fp32)$fatal(1,"ABI mapping");
  if(!output_layout_valid || output_object!=c_object || output_logical_cols!=8 || output_row_stride!=c_row_stride || output_col_stride!=c_col_stride)$fatal(1,"output layout missing");
  if(RESOLVE && output_object_bytes!=64'h100000123)$fatal(1,"object capacity truncated");
  c_object=32'h87654321;c_row_stride=13;c_col_stride=3;
  repeat(4)begin tick();if(!output_layout_valid || output_object!=32'h12345678 || output_row_stride!=32'h80000123 || output_col_stride!=32'h40000007)$fatal(1,"layout changed while owned");end
  tick();array_done=1;tick();array_done=0;
  if(output_layout_valid || input_layout_valid)$fatal(1,"completed layout still valid");
  if(!complete_valid || complete_fault)$fatal(1,"success completion");checks=checks+1;tick();tick();
  // No views may carry over when the IRS slot is recycled.
  view(0,10,0);view(1,11,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);
  // A shape prefix alone cannot qualify non-matrix descriptors.
  a_rank=3;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);a_rank=2;
  b_rank=1;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);b_rank=2;
  c_rank=3;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);c_rank=2;
  // Reject old K-major interpretation, mismatched inner extent, and zero N.
  b_cols=80;b_depth=8;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);
  b_cols=8;b_depth=79;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);
  b_cols=0;b_depth=80;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);
  // Malformed descriptor response and mismatched issue ownership also refuse.
  b_cols=8;desc_fault=1;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);desc_fault=0;
  view(0,10,0);view(1,11,0);view(4,12,0);issue_slot=1;expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);
  issue_slot=0;
  // Each required operand must reject offsets whose high bits would alias.
  view(0,10,64'h100000000);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_CAPABILITY);
  view(0,10,0);view(1,11,64'h8000000000000010);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_CAPABILITY);
  view(0,10,0);view(1,11,0);view(4,12,64'hffffffff00000000);expect_refusal(ot_a3_pkg::A3_TRAP_CAPABILITY);
  // Replacing a captured view clears its own overflow; ignored slots do not
  // poison valid operands, and a new IRS set does not inherit the old fault.
  view(0,10,64'h100000000);view(0,10,0);view(1,11,0);view(4,12,0);view(2,13,64'hffffffffffffffff);issue();
  wait(array_start);@(negedge clk);tick();array_done=1;tick();array_done=0;
  if(!complete_valid || complete_fault)$fatal(1,"offset refusal leaked into next issue");checks=checks+1;tick();tick();
  // The output descriptor controls precision even when the host hint disagrees.
  c_dtype=8'h12;cfg_out_fp32=0;
  view(0,10,0);view(1,11,0);view(4,12,0);issue();
  wait(array_start);@(negedge clk);
  if(!array_out_fp32)$fatal(1,"FP32 output descriptor ignored");
  tick();array_done=1;tick();array_done=0;checks=checks+1;tick();tick();
  c_dtype=8'h10;cfg_out_fp32=1;
  view(0,10,0);view(1,11,0);view(4,12,0);issue();
  wait(array_start);@(negedge clk);
  if(array_out_fp32)$fatal(1,"host overrode BF16 descriptor");
  tick();array_done=1;tick();array_done=0;checks=checks+1;tick();tick();
  c_rows=2;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);c_rows=1;
  c_cols=16;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);c_cols=8;
  c_fault=1;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);c_fault=0;
  c_bad_header=1;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);c_bad_header=0;
  c_dtype=8'h20;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_CAPABILITY);c_dtype=8'h10;
  c_scaled=1;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_CAPABILITY);c_scaled=0;
  if(RESOLVE)begin
   object_bad_type=1;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);object_bad_type=0;
   object_readonly=1;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);object_readonly=0;
   object_empty=1;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);object_empty=0;
  end
  if(INPUTS)begin
   for(bad_object=100;bad_object<=101;bad_object=bad_object+1)begin
    bad_input_object=bad_object;
    for(bad_case=1;bad_case<=6;bad_case=bad_case+1)begin
     bad_input_kind=3'(bad_case);view(0,10,0);view(1,11,0);view(4,12,0);
     expect_refusal(ot_a3_pkg::A3_TRAP_DESCRIPTOR);
    end
   end
   bad_input_object=0;bad_input_kind=0;
  end
  if(STREAM)begin
   b_dtype=8'h20;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_CAPABILITY);b_dtype=8'h10;
   group_size=2;view(0,10,0);view(1,11,0);view(4,12,0);expect_refusal(ot_a3_pkg::A3_TRAP_CAPABILITY);group_size=1;
  end
  // Clear wins over views, issue, descriptor response, launch and completion.
  for(cancel_state=1;cancel_state<=(INPUTS?9:(RESOLVE?7:6));cancel_state=cancel_state+1)begin
   if(cancel_state!=7 || RESOLVE)begin
   if(cancel_state==5)b_cols=0;
   view(0,10,0);view(1,11,0);view(4,12,0);issue();
   while(dut.state!=4'(cancel_state))tick();
   clear=1;issue_valid=1;view_valid=1;array_done=1;
   #1;if(issue_ready || output_layout_valid || input_layout_valid)$fatal(1,"clear advertised ownership");
   tick();clear=0;issue_valid=0;view_valid=0;array_done=0;b_cols=8;#1;
   if(!issue_ready || complete_valid || array_start || desc_req || output_layout_valid || dut.view_have!=0)
    $fatal(1,"clear lost priority state=%0d",cancel_state);
   repeat(3)begin tick();if(complete_valid || array_start || output_layout_valid)$fatal(1,"cancelled work escaped");end
   checks=checks+1;
   end
  end
  // A complete new view set must recover after the final cancelled descriptor.
  view(0,10,0);view(1,11,0);view(4,12,0);issue();wait(array_start);@(negedge clk);
  tick();array_done=1;tick();array_done=0;
  if(!complete_valid || complete_fault)$fatal(1,"clear recovery failed");checks=checks+1;
  $display("PASS G2 issue contract checks=%0d",checks);$finish;
 end
 initial begin #100000;$fatal(1,"timeout");end
endmodule
