`timescale 1ns/1ps
// ONE retained command/operand/result controller; numerical leaves are stateless.
// power_on_reset_n is cold boot ONLY. warm_reset quarantines accepted debt.
// RF apertures are whole owned, page-aligned pages, pinned until reverse.
module ot_gpu_native_primitive_controller #(
 parameter bit ENABLE=0,
 parameter integer DESCRIPTORS=116,
 parameter DESCRIPTOR_FILE="", PC_TEMPLATE_FILE="",
 parameter [255:0] PROGRAM_SHA=256'hab3fe8d6469d6a1552e2eeaa9efe945c025cc35a567f0d8161e3c2a02fc59354,
 parameter [63:0] EXTERNAL_OPCODE_MASK=0
)(
 input wire clk,power_on_reset_n,warm_reset,
 input wire cmd_valid, output wire cmd_ready,
 input wire [255:0] cmd_program_sha,
 input wire [238:0] cmd_tuple,input wire [54:0] cmd_owner,
 input wire [10:0] cmd_PC,input wire [63:0] cmd_sequence,
 input wire [7:0] cmd_descriptor,input wire [3:0] cmd_template,
 input wire [5:0] cmd_step,input wire [1:0] cmd_substep,
 input wire [2:0] cmd_operands,input wire [7:0] cmd_elements,
 input wire [7:0] cmd_types,input wire [1:0] cmd_dtype,cmd_result_type,
 input wire cmd_canonical_zero,
 input wire [31:0] cmd_counts,input wire [3:0] cmd_scalars,
 input wire [71:0] cmd_source_slots,input wire [183:0] cmd_source_owners,
 input wire [17:0] cmd_result_slots,input wire [45:0] cmd_result_owner,
 input wire [255:0] cmd_shape_sha,
 // Source-compiled movement map: per output {valid,source_select2,index7}.
 input wire [1279:0] cmd_movement_map,
 // These are actual physical authority observations, never caller-made grants.
 input wire authority_valid,input wire [238:0] authority_tuple,
 input wire [54:0] authority_owner,input wire [10:0] authority_PC,
 input wire [255:0] authority_shape_sha,
 input wire [3:0] source_owner_held,input wire result_owner_held,
 input wire [71:0] authority_source_slots,input wire [183:0] authority_source_owners,
 input wire [17:0] authority_result_slots,input wire [45:0] authority_result_owner,
 output wire host_rd_valid,input wire host_rd_ready,
 output wire [8:0] host_a,host_b,
 input wire host_rsp_valid,output wire host_rsp_ready,
 input wire [4095:0] host_rsp_a,host_rsp_b,
 output wire host_wr_valid,input wire host_wr_ready,
 output wire [8:0] host_dst,output reg [4095:0] host_wdata,
 output wire [45:0] host_owner,
 input wire host_ack_valid,output wire host_ack_ready,
 input wire [8:0] host_ack_slot,input wire [45:0] host_ack_owner,
 input wire output_visible,input wire [238:0] visible_tuple,input wire [54:0] visible_owner,
 output wire result_valid,input wire result_ready,
 output wire [10:0] result_PC,output wire [63:0] result_sequence,
 output wire [238:0] result_tuple,output wire [54:0] result_owner,
 output wire [1:0] result_dtype,output wire [10:0] result_bytes,
 output reg [8191:0] result_data,
 output wire reverse_valid,input wire reverse_ready,
 input wire [10:0] reverse_ack_PC,input wire [63:0] reverse_ack_sequence,
 input wire [238:0] reverse_ack_tuple,input wire [54:0] reverse_ack_owner,
 output wire [10:0] reverse_PC,output wire [63:0] reverse_sequence,
 output wire [238:0] reverse_tuple,output wire [54:0] reverse_owner,
 // Other real numerical services share these retained seats, no private buffers.
 output wire external_valid,input wire external_ready,
 output wire [5:0] external_opcode,output wire [1:0] external_dtype,
 output wire external_canonical_zero,output wire external_a_scalar,external_b_scalar,external_c_scalar,
 output wire [7:0] external_types,output wire [3:0] external_mask,
 output wire [255:0] external_a,external_b,external_c,external_d,
 output wire [238:0] external_tuple,output wire [54:0] external_owner,
 output wire [10:0] external_PC,output wire [63:0] external_sequence,
 output wire [5:0] external_beat,
 input wire external_result_valid,output wire external_result_ready,
 input wire [255:0] external_result,input wire [1:0] external_result_type,
 input wire [3:0] external_lane_fault,
 input wire [238:0] external_result_tuple,input wire [54:0] external_result_owner,
 input wire [10:0] external_result_PC,input wire [63:0] external_result_sequence,
 input wire [5:0] external_result_beat,
 output wire busy,output reg fault
);
 import ot_gpu_w6_secded_pkg::*;
 localparam IDLE=0,READ_REQ=1,READ_RSP=2,EXECUTE=3,EXT_WAIT=4,
            WRITE_REQ=5,WRITE_ACK=6,VISIBILITY=7,RESULT=8,REVERSE=9,FP_WAIT=10;
 typedef struct packed {
  logic [1279:0] movement_map;logic [255:0] shape_sha;
  logic [238:0] tuple_id;logic [54:0] owner;logic [10:0] PC;logic [63:0] sequence_id;
  logic [23:0] descriptor;logic canonical_zero;logic [2:0] operands;logic [7:0] elements;
  logic [7:0] types;logic [1:0] dtype,result_type;logic [31:0] counts;logic [3:0] scalars;
  logic [71:0] source_slots;logic [183:0] source_owners;
  logic [17:0] result_slots;logic [45:0] result_rf_owner;
 } command_t;
 command_t offer,saved;
 localparam WORDS=48;
 reg [71:0] command_code[0:WORDS-1];
 reg [71:0] operand_code[0:511];reg [71:0] result_code[0:127];
 reg [23:0] descriptor_rom[0:255];reg [15:0] pc_templates[0:1736];
 reg fault_check;reg [3:0] state,state_check;reg [1:0] operand,operand_check;
 reg page,page_check,write_page,write_page_check;
 reg [5:0] beat,beat_check;
 wire control_clean=(fault_check==~fault)&&(state_check==~state)&&(operand_check==~operand)&&
  (page_check==~page)&&(write_page_check==~write_page)&&(beat_check==~beat);
 reg [3071:0] command_raw;reg command_error,data_error;
 reg [8191:0] retained[0:3];reg [8191:0] normalized_result;
 reg [65:0] dec;integer i,j,k,index,element,width,position;
 reg [1023:0] lane_data;reg [3:0] lane_mask;
 reg [27:0] move_index;reg [7:0] move_select;reg [3:0] move_valid;
 wire [5:0] opcode=saved.descriptor[5:0];
 wire [255:0] bits_result,move_result,conversion_result;
 wire [1:0] bits_type,move_type,conversion_type;wire [3:0] bits_fault,move_fault,conversion_fault;
 wire bits_supported,move_supported,conversion_supported;
 wire [255:0] selected_result=(opcode<=16)?bits_result:(opcode<=25)?conversion_result:move_result;
 wire [1:0] selected_type=(opcode<=16)?bits_type:(opcode<=25)?conversion_type:move_type;
 wire [3:0] selected_fault=(opcode<=16)?bits_fault:(opcode<=25)?conversion_fault:move_fault;
 wire selected_supported=(opcode<=16)?bits_supported:(opcode<=25)?conversion_supported:move_supported;
 wire local_op=(opcode<=16)||(opcode>=21&&opcode<=37);
 wire [23:0] offered_descriptor=descriptor_rom[cmd_descriptor];
 wire [63:0] local_mask=64'h0000003fffffffff;
 wire [63:0] installed_mask=local_mask|(EXTERNAL_OPCODE_MASK&64'h0000003fffffffff);
 wire opcode_present=installed_mask[offered_descriptor[5:0]];
 wire scope_matches=authority_valid&&authority_tuple==saved.tuple_id&&authority_owner==saved.owner&&
  authority_PC==saved.PC&&authority_shape_sha==saved.shape_sha&&
  authority_source_slots==saved.source_slots&&authority_source_owners==saved.source_owners&&
  authority_result_slots==saved.result_slots&&authority_result_owner==saved.result_rf_owner&&
  result_owner_held&&((source_owner_held&((1<<saved.operands)-1))==((1<<saved.operands)-1));
 wire [71:0] source_slots_flat=saved.source_slots;
 wire [17:0] result_slots_flat=saved.result_slots;
 wire [31:0] counts_flat=saved.counts;
 wire [3:0] scalars_flat=saved.scalars;
 wire [7:0] types_flat=saved.types;
 wire [1279:0] movement_flat=saved.movement_map;
 reg offer_legal;
 always @* begin
  offer='0;offer.movement_map=cmd_movement_map;offer.shape_sha=cmd_shape_sha;
  offer.tuple_id=cmd_tuple;offer.owner=cmd_owner;offer.PC=cmd_PC;offer.sequence_id=cmd_sequence;
  offer.canonical_zero=cmd_canonical_zero;offer.descriptor=offered_descriptor;offer.operands=cmd_operands;offer.elements=cmd_elements;
  offer.types=cmd_types;offer.dtype=cmd_dtype;offer.result_type=cmd_result_type;
  offer.counts=cmd_counts;offer.scalars=cmd_scalars;offer.source_slots=cmd_source_slots;
  offer.source_owners=cmd_source_owners;offer.result_slots=cmd_result_slots;offer.result_rf_owner=cmd_result_owner;
  offer_legal=(cmd_PC<1737)&&(cmd_descriptor<DESCRIPTORS)&&offered_descriptor[22]&&
   offered_descriptor[21:18]==cmd_template&&offered_descriptor[17:12]==cmd_step&&
   offered_descriptor[11:10]==cmd_substep&&pc_templates[cmd_PC][cmd_template]&&opcode_present&&
   cmd_program_sha==PROGRAM_SHA&&
   ((offered_descriptor[5:0]<17||offered_descriptor[5:0]>20)||cmd_canonical_zero==offered_descriptor[23])&&cmd_operands<=4&&cmd_elements>0&&cmd_elements<=128&&
   (offered_descriptor[9:8]==3||offered_descriptor[9:8]==cmd_dtype)&&
   authority_valid&&authority_tuple==cmd_tuple&&authority_owner==cmd_owner&&authority_PC==cmd_PC&&
   authority_shape_sha==cmd_shape_sha&&result_owner_held&&
   authority_source_slots==cmd_source_slots&&authority_source_owners==cmd_source_owners&&
   authority_result_slots==cmd_result_slots&&authority_result_owner==cmd_result_owner;
  for(integer a=0;a<4;a=a+1)if(a<cmd_operands)begin
   if(!source_owner_held[a]||cmd_counts[a*8+:8]==0||
      (cmd_scalars[a]?cmd_counts[a*8+:8]!=1:cmd_counts[a*8+:8]!=cmd_elements))offer_legal=0;
  end
 end
 always @* begin
  command_raw=0;command_error=0;data_error=0;dec=0;
  for(i=0;i<WORDS;i=i+1)begin dec=decode64(command_code[i]);command_raw[i*64+:64]=dec[63:0];command_error=command_error|dec[65]|dec[64];end
  saved=command_raw[$bits(command_t)-1:0];
  for(j=0;j<4;j=j+1)begin
   retained[j]=0;
   for(k=0;k<128;k=k+1)begin
    dec=decode64(operand_code[j*128+k]);retained[j][k*64+:64]=dec[63:0];
    // Only loaded elements may be consumed; unused cells have no authority.
    if(j<saved.operands&&k<counts_flat[j*8+:8])data_error=data_error|dec[65]|dec[64];
   end
  end
  normalized_result=0;
  for(i=0;i<128;i=i+1)begin
   dec=decode64(result_code[i]);normalized_result[i*64+:64]=dec[63:0];
   if((state==WRITE_REQ||state==WRITE_ACK||state==VISIBILITY||state==RESULT||state==REVERSE)&&i<saved.elements)data_error=data_error|dec[65]|dec[64];
  end
  lane_mask=0;move_index=0;move_select=0;move_valid=0;
  for(j=0;j<4;j=j+1)begin
   lane_data[j*256+:256]=0;
   for(k=0;k<4;k=k+1)begin
    element=beat*4+k;index=scalars_flat[j]?0:element;
    if(j<saved.operands&&element<saved.elements)lane_data[j*256+k*64+:64]=retained[j][index*64+:64];
   end
  end
  for(k=0;k<4;k=k+1)begin
   element=beat*4+k;
   if(element<saved.elements)begin
    lane_mask[k]=1;move_index[k*7+:7]=movement_flat[element*10+:7];
    move_select[k*2+:2]=movement_flat[element*10+7+:2];move_valid[k]=movement_flat[element*10+9];
    if(opcode==28)begin move_index[k*7+:7]=element;move_valid[k]=1;end
   end
  end
  result_data=0;host_wdata=0;
  width=(saved.result_type==2)?64:(saved.result_type==3)?8:32;
  for(i=0;i<128;i=i+1)if(i<saved.elements)begin
   for(k=0;k<64;k=k+1)if(k<width)begin
    position=i*width+k;result_data[position]=normalized_result[i*64+k];
    if(position/4096==write_page)host_wdata[position%4096]=normalized_result[i*64+k];
   end
  end
 end
 ot_hbm_accel_native_bits #(.ENABLE(ENABLE),.LANES(4)) u_bits(
  .opcode(opcode[4:0]),.dtype(saved.dtype),.a_type(types_flat[1:0]),.b_type(types_flat[3:2]),.c_type(types_flat[5:4]),
  .a_scalar(scalars_flat[0]),.b_scalar(scalars_flat[1]),.c_scalar(scalars_flat[2]),.lane_mask(lane_mask),
  .a_data(lane_data[0+:256]),.b_data(lane_data[256+:256]),.c_data(lane_data[512+:256]),.result(bits_result),.result_type(bits_type),.lane_fault(bits_fault),.supported(bits_supported));
 ot_hbm_native_movement #(.ENABLE(ENABLE)) u_movement(
  .opcode(opcode),.dtype(saved.dtype),.lane_mask(lane_mask),.source_index(move_index),.source_select(move_select),.index_valid(move_valid),
  .a_data(retained[0]),.b_data(retained[1]),.c_data(retained[2]),.literal_data(lane_data[0+:256]),
  .sticky_fault(fault),.lease_required(1'b1),.lease_visible(scope_matches),
  .result(move_result),.result_type(move_type),.lane_fault(move_fault),.supported(move_supported));
 ot_gpu_native_conversion #(.ENABLE(ENABLE),.LANES(4)) u_conversion(
  .opcode(opcode),.dtype(saved.dtype),.a_type(types_flat[1:0]),.b_type(types_flat[3:2]),.c_type(types_flat[5:4]),
  .a_scalar(scalars_flat[0]),.b_scalar(scalars_flat[1]),.c_scalar(scalars_flat[2]),.lane_mask(lane_mask),
  .a_data(lane_data[0+:256]),.b_data(lane_data[256+:256]),.c_data(lane_data[512+:256]),.result(conversion_result),.result_type(conversion_type),.lane_fault(conversion_fault),.supported(conversion_supported));
 wire [3:0] fp_ready,fp_valid,fp_protocol,fp_result_ready;
 wire [7:0] fp_error;wire [127:0] fp_result_bits;
 wire fp_op=(opcode>=17&&opcode<=20);
 wire fp_all_ready=(fp_ready&lane_mask)==lane_mask;
 wire fp_all_valid=(fp_valid&lane_mask)==lane_mask;
 wire fp_launch=operating&&state==EXECUTE&&fp_op&&fp_all_ready&&scope_matches&&!data_error&&saved.result_type==0&&types_flat[1:0]==0&&(opcode==20||types_flat[3:2]==0);
 reg fp_bad;reg [255:0] fp_wide;integer fl;
 always @*begin
  fp_bad=0;fp_wide=0;
  for(fl=0;fl<4;fl=fl+1)if(lane_mask[fl])begin
   fp_bad=fp_bad||fp_protocol[fl]||(fp_valid[fl]&&fp_error[fl*2+:2]!=0);
   fp_wide[fl*64+:64]={32'd0,fp_result_bits[fl*32+:32]};
  end
 end
 wire fp_accept=operating&&state==FP_WAIT&&fp_all_valid&&!fp_bad&&scope_matches&&!data_error;
 assign fp_result_ready={4{fp_accept}}&lane_mask;
 ot_qwen_native_fp32_lanes #(.OPT(ENABLE)) u_fp32(
  .clk(clk),.rst_n(power_on_reset_n),.lane_valid({4{fp_launch}}&lane_mask),.lane_ready(fp_ready),
  .select_add({4{opcode==17}}),.select_mul({4{opcode==18}}),.select_div({4{opcode==19}}),.select_sqrt({4{opcode==20}}),
  .a({lane_data[192+:32],lane_data[128+:32],lane_data[64+:32],lane_data[0+:32]}),
  .b({lane_data[448+:32],lane_data[384+:32],lane_data[320+:32],lane_data[256+:32]}),
  .canonical_zero({4{saved.canonical_zero}}),.result_valid(fp_valid),.result_ready(fp_result_ready),.result_bits(fp_result_bits),.result_error(fp_error),.protocol_error(fp_protocol));
 wire operating=ENABLE&&!warm_reset&&!fault&&control_clean&&!command_error;
 assign busy=ENABLE&&(state!=IDLE);
 assign cmd_ready=ENABLE&&!warm_reset&&!fault&&state==IDLE&&offer_legal;
 assign host_rd_valid=operating&&state==READ_REQ&&scope_matches;
 assign host_a=source_slots_flat[operand*18+page*9+:9];assign host_b=host_a;
 assign host_rsp_ready=operating&&state==READ_RSP&&scope_matches&&(host_rsp_a==host_rsp_b);
 assign host_wr_valid=operating&&state==WRITE_REQ&&scope_matches&&!data_error;
 assign host_dst=result_slots_flat[write_page*9+:9];assign host_owner=saved.result_rf_owner;
 assign host_ack_ready=operating&&state==WRITE_ACK&&scope_matches&&host_ack_slot==host_dst&&host_ack_owner==host_owner;
 assign result_valid=operating&&state==RESULT&&scope_matches&&!data_error;
 assign result_PC=saved.PC;assign result_sequence=saved.sequence_id;assign result_tuple=saved.tuple_id;assign result_owner=saved.owner;
 assign result_dtype=saved.result_type;
 assign result_bytes=saved.elements*((saved.result_type==2)?8:(saved.result_type==3)?1:4);
 wire reverse_match=reverse_ack_PC==saved.PC&&reverse_ack_sequence==saved.sequence_id&&reverse_ack_tuple==saved.tuple_id&&reverse_ack_owner==saved.owner;
 assign reverse_valid=operating&&state==REVERSE&&scope_matches&&!data_error&&(!reverse_ready||reverse_match);
 assign reverse_PC=saved.PC;assign reverse_sequence=saved.sequence_id;assign reverse_tuple=saved.tuple_id;assign reverse_owner=saved.owner;
 assign external_valid=operating&&state==EXECUTE&&!local_op&&scope_matches&&!data_error;
 assign external_canonical_zero=saved.canonical_zero;
 assign external_a_scalar=0;assign external_b_scalar=0;assign external_c_scalar=0;
 assign external_opcode=opcode;assign external_dtype=saved.dtype;assign external_types=saved.types;
 assign external_mask=lane_mask;assign external_a=lane_data[0+:256];assign external_b=lane_data[256+:256];assign external_c=lane_data[512+:256];assign external_d=lane_data[768+:256];
 assign external_tuple=saved.tuple_id;assign external_owner=saved.owner;assign external_PC=saved.PC;assign external_sequence=saved.sequence_id;assign external_beat=beat;
 wire external_identity=external_result_tuple==saved.tuple_id&&external_result_owner==saved.owner&&external_result_PC==saved.PC&&
  external_result_sequence==saved.sequence_id&&external_result_beat==beat;
 assign external_result_ready=operating&&state==EXT_WAIT&&scope_matches&&external_identity&&!data_error;
 initial begin
  if($bits(command_t)>WORDS*64)$fatal(1,"command sizing");
  for(integer r=0;r<256;r=r+1)descriptor_rom[r]=0;
  for(integer r=0;r<1737;r=r+1)pc_templates[r]=0;
  if(DESCRIPTOR_FILE!="")$readmemh(DESCRIPTOR_FILE,descriptor_rom,0,DESCRIPTORS-1);
  if(PC_TEMPLATE_FILE!="")$readmemh(PC_TEMPLATE_FILE,pc_templates);
 end
 task automatic set_state(input [3:0] next_state);begin state<=next_state;state_check<=~next_state;end endtask
 task automatic set_operand(input [1:0] n);begin operand<=n;operand_check<=~n;end endtask
 task automatic set_page(input bit n);begin page<=n;page_check<=~n;end endtask
 task automatic set_write_page(input bit n);begin write_page<=n;write_page_check<=~n;end endtask
 task automatic set_beat(input [5:0] n);begin beat<=n;beat_check<=~n;end endtask
 task automatic capture_beat(input [255:0] data);begin
  for(integer l=0;l<4;l=l+1)if(lane_mask[l])result_code[beat*4+l]<=encode64(data[l*64+:64]);
  if(beat*4+4>=saved.elements)begin set_write_page(0);set_state(WRITE_REQ);end
  else begin set_beat(beat+1'b1);set_state(EXECUTE);end
 end endtask
 integer e,bitwidth,raw_index;
 reg [63:0] captured_word;
 always @(posedge clk or negedge power_on_reset_n)begin
  if(!power_on_reset_n)begin
   state<=IDLE;state_check<=~4'd0;operand<=0;operand_check<=~2'd0;
   page<=0;page_check<=1;write_page<=0;write_page_check<=1;beat<=0;beat_check<=~6'd0;fault<=0;fault_check<=1;
   for(integer n=0;n<WORDS;n=n+1)command_code[n]<=encode64(0);
  end else if(ENABLE)begin
   if(warm_reset&&state!=IDLE)begin fault<=1;fault_check<=0;end
   if(!control_clean||(state!=IDLE&&command_error))begin fault<=1;fault_check<=0;end
   if(state!=IDLE&&!scope_matches)begin fault<=1;fault_check<=0;end
   if(!fault&&!warm_reset&&control_clean&&(state==IDLE||(!command_error&&scope_matches)))case(state)
    IDLE:if(cmd_valid)begin
     if(!offer_legal)begin fault<=1;fault_check<=0;end
     else begin
      for(integer n=0;n<WORDS;n=n+1)command_code[n]<=encode64(({{(WORDS*64-$bits(command_t)){1'b0}},offer})>>(n*64));
      set_operand(0);set_page(0);set_beat(0);
      set_state(cmd_operands==0?EXECUTE:READ_REQ);
     end
    end
    READ_REQ:if(host_rd_valid&&host_rd_ready)set_state(READ_RSP);
    READ_RSP:if(host_rsp_valid)begin
     if(host_rsp_a!=host_rsp_b)begin fault<=1;fault_check<=0;end
     else if(host_rsp_ready)begin
      bitwidth=(types_flat[operand*2+:2]==2)?64:(types_flat[operand*2+:2]==3)?8:32;
      for(e=0;e<128;e=e+1)if(e<counts_flat[operand*8+:8]&&e*bitwidth/4096==page)begin
       raw_index=(e*bitwidth)%4096;captured_word=0;
       for(integer b=0;b<64;b=b+1)if(b<bitwidth)captured_word[b]=host_rsp_a[raw_index+b];
       operand_code[operand*128+e]<=encode64(captured_word);
      end
      if(!page&&types_flat[operand*2+:2]==2&&counts_flat[operand*8+:8]>64)begin set_page(1);set_state(READ_REQ);end
      else if(operand+1<saved.operands)begin set_operand(operand+1'b1);set_page(0);set_state(READ_REQ);end
      else set_state(EXECUTE);
     end
    end
    EXECUTE:if(data_error)begin fault<=1;fault_check<=0;end
     else if(fp_op)begin
      if(saved.result_type!=0||types_flat[1:0]!=0||(opcode!=20&&types_flat[3:2]!=0))begin fault<=1;fault_check<=0;end
      else if(fp_launch)set_state(FP_WAIT);
     end else if(local_op)begin
      if(!selected_supported||(|selected_fault)||selected_type!=saved.result_type)begin fault<=1;fault_check<=0;end
      else capture_beat(selected_result);
     end else if(external_valid&&external_ready)set_state(EXT_WAIT);
    FP_WAIT:if(fp_bad||data_error)begin fault<=1;fault_check<=0;end else if(fp_accept)capture_beat(fp_wide);
    EXT_WAIT:if(external_result_valid)begin
     if(!external_identity||(|external_lane_fault)||external_result_type!=saved.result_type||data_error)begin fault<=1;fault_check<=0;end
     else if(external_result_ready)capture_beat(external_result);
    end
    WRITE_REQ:if(data_error)begin fault<=1;fault_check<=0;end else if(host_wr_valid&&host_wr_ready)set_state(WRITE_ACK);
    WRITE_ACK:if(host_ack_valid)begin
     if(host_ack_slot!=host_dst||host_ack_owner!=host_owner)begin fault<=1;fault_check<=0;end
     else if(host_ack_ready)begin
      if(!write_page&&result_bytes>512)begin set_write_page(1);set_state(WRITE_REQ);end else set_state(VISIBILITY);
     end
    end
    VISIBILITY:if(output_visible)begin
     if(visible_tuple!=saved.tuple_id||visible_owner!=saved.owner)begin fault<=1;fault_check<=0;end else set_state(RESULT);
    end
    RESULT:if(data_error)begin fault<=1;fault_check<=0;end else if(result_valid&&result_ready)set_state(REVERSE);
    REVERSE:if(reverse_ready)begin
     if(reverse_ack_PC!=saved.PC||reverse_ack_sequence!=saved.sequence_id||reverse_ack_tuple!=saved.tuple_id||reverse_ack_owner!=saved.owner)begin fault<=1;fault_check<=0;end
     else set_state(IDLE); // RPC debt only; source/result leases belong to provider.
    end
    default:begin fault<=1;fault_check<=0;end
   endcase
  end
 end
endmodule
