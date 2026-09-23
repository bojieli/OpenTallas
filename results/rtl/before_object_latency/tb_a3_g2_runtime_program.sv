`timescale 1ns/1ps
// Host-load a real ABI program and compare outputs with the functional Device.
module tb_a3_g2_runtime_program;
 parameter bit WEIGHT_ROW_REUSE=1;
 parameter bit PASS_FIRST=0;
 parameter integer PASS_COLUMNS=3;
 parameter bit OBJECT_WRITES=0;
 parameter bit INPUT_LAYOUT=0;
 parameter bit WEIGHT_OBJECT_READS=0;
 parameter bit WEIGHT_LINE_REUSE=1;
 parameter bit WEIGHT_WORD_HANDOFF=1;
 wire input_layout_valid;
 wire [31:0] input_a_object,input_b_object,input_a_row_stride,input_a_k_stride,input_b_column_stride,input_b_k_stride;
 wire [63:0] input_a_object_bytes,input_b_object_bytes;
 parameter integer WRITE_OUTSTANDING=4;
 parameter integer AUXILIARY_DEPTH=3;
 parameter bit REGISTER_AUXILIARY_REQUESTS=0;
 parameter integer WEIGHT_RESPONSE_GAP=1;
 parameter bit ACTIVATION_MISS_ALIGNED=0;
 `include "program_config.svh"
 localparam LOCAL_OUTPUTS=ROWS*COLS/8, WEIGHT_WORDS=DEPTH*LOCAL_OUTPUTS;
 reg [127:0] program_image[0:PROGRAM_WORDS-1],descriptor_image[0:DESCRIPTOR_WORDS-1],weight_image[0:WEIGHT_WORDS-1];
 reg [31:0] expected[0:ROWS*COLS-1];
 reg [63:0] activation_image[0:DEPTH*ROWS-1],adata=0;
 reg [7:0] activation_bytes[0:2*DEPTH*ROWS-1];
 reg host_we=0;reg [2:0] host_sel=0;reg [31:0] host_row=0;reg [5:0] host_lane=0;reg [127:0] host_wdata=0;
 wire host_ready,host_write_refused,done,complete,trapped;
 wire [15:0] trap_class;wire [31:0] count_issued,count_retired;
 reg [31:0] wbase=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,kick=0,runtime_abort=0,runtime_transport_ack=0,runtime_writes_drained=0;
 wire runtime_transport_cancel,array_busy,array_done;
 wire [31:0] runtime_generation;
 wire [7:0] array_error_code;
 wire output_layout_valid,output_fp32;
 wire [63:0] output_object_bytes;
 wire [31:0] output_object,output_element_base,output_row_stride,output_col_stride;
 wire [15:0] output_rows,output_logical_cols,output_padded_cols;
 wire [7:0] part_we;wire [255:0] part_data,part_addr;
 wire weight_request_valid,weight_response_ready,auxiliary_request_valid,auxiliary_response_ready;
 wire [63:0] weight_request_tag;
 wire [31:0] weight_request_address,auxiliary_request_generation,auxiliary_request_w,auxiliary_request_a;
 wire [9:0] weight_request_words;
 reg wactive=0,auxvalid=0;
 reg [63:0] wtag=0;reg [9:0] wi=0,wn=0;
 reg [31:0] agen=0,aw=0;
 integer outputs=0,fills=0,cycles=0,phase=0;
 reg [ROWS*COLS-1:0] seen=0;
 reg [ROWS*COLS-1:0] expected_seen=0;
 reg release_output=0;
 wire part_valid;
 wire part_ready=!STRESS_OUTPUT || (release_output && cycles%7<3);
 reg held=0;reg [775:0] held_payload;
 wire [255:0] part_acc;
 integer output_stalls=0,reservation_stalls=0;
 reg tail_hold=0;
 wire writer_drained,writer_error,part_accepted;
 wire sink_enable=part_ready && !tail_hold;
 wire sink_ready=part_accepted;
 wire object_write_valid,object_write_ready,object_response_ready;
 wire [31:0] object_write_generation,object_write_object;
 wire [7:0] object_write_mask;
 wire [511:0] object_write_offset;
 wire [255:0] object_write_data;
 wire object_write_fp32;
 reg [31:0] ack_due[0:7],ack_generation[0:7];
 reg ack_fault[0:7];
 reg [2:0] ack_head=0,ack_tail=0;
 integer late_write_faults=0;
 reg [63:0] configured_object_bytes=0;
 integer writes_before_bad_binding;
 reg [3:0] ack_count=0;
 wire object_ack=ack_count!=0 && cycles>=ack_due[ack_head] &&
  (!ack_fault[ack_head] || dut.runtime_operands.lifetime.state==2);
 wire [31:0] object_ack_generation=ack_generation[ack_head];
 wire object_request_fire=object_write_valid && object_write_ready;
 wire object_ack_fire=object_ack && object_response_ready;
 integer object_writes=0,object_acks=0;
 reg [7:0] output_memory[0:OUTPUT_BYTES-1];
 reg [ROWS*LOGICAL_COLS-1:0] object_seen=0;
 function automatic integer object_index(input [63:0] offset);
  integer e,r,c;
  begin
   e=integer'(offset/2)-OUTPUT_BASE;r=e/OUTPUT_ROW_STRIDE;c=(e%OUTPUT_ROW_STRIDE)/OUTPUT_COL_STRIDE;
   if(offset%2 || e<0 || r>=ROWS || c>=LOGICAL_COLS || e%OUTPUT_ROW_STRIDE%OUTPUT_COL_STRIDE!=0)object_index=-1;
   else object_index=r*LOGICAL_COLS+c;
  end
 endfunction
 assign object_write_ready=ack_count<8 && cycles%5!=0;
 // Behavioral object memory accepts complete checked beats and delays commit ack.
 // Golden comparison is independent of the writer's incremental address cursor.
 always @(posedge clk)begin
  if(!rst_n)begin ack_head<=0;ack_tail<=0;ack_count<=0;object_writes<=0;object_acks<=0;end
  else begin
   if(kick)begin
    object_seen<=0;
    for(integer byte_index=0;byte_index<OUTPUT_BYTES;byte_index=byte_index+1)output_memory[byte_index]<=8'ha5;
   end
   if(INPUT_LAYOUT && input_layout_valid)begin
    if(input_a_object!=ACTIVATION_OBJECT || input_b_object!=WEIGHT_OBJECT ||
       input_a_object_bytes!=64'(2*DEPTH*ROWS) || input_b_object_bytes!=64'(WEIGHT_OBJECT_BYTES) ||
       input_a_row_stride!=DEPTH || input_a_k_stride!=1 || input_b_column_stride!=WEIGHT_COLUMN_STRIDE || input_b_k_stride!=WEIGHT_K_STRIDE)
     $fatal(1,"descriptor input layout mismatch");
   end
   if(dut.arr_start)configured_object_bytes<=0; // captured bounds must survive host mutation
   if(object_write_valid && object_write_ready)begin
    if(object_write_object!=OUTPUT_OBJECT || object_write_generation!=runtime_generation || object_write_fp32)
     $fatal(1,"object write identity");
    ack_fault[ack_tail]<=0;
    for(integer i=0;i<8;i=i+1)if(object_write_mask[i])begin
     if(object_write_offset[64*i+:64]>=OUTPUT_BYTES || object_index(object_write_offset[64*i+:64])<0)
      $fatal(1,"object write bounds/alignment");
     if(object_seen[object_index(object_write_offset[64*i+:64])])$fatal(1,"duplicate object write");
     object_seen[object_index(object_write_offset[64*i+:64])]<=1;
     if(phase==6 && object_index(object_write_offset[64*i+:64])==ROWS*LOGICAL_COLS-1)ack_fault[ack_tail]<=1;
     output_memory[object_write_offset[64*i+:64]]<=object_write_data[32*i+:8];
     output_memory[object_write_offset[64*i+:64]+1]<=object_write_data[32*i+8+:8];
     if(object_write_data[32*i+:32]!=expected[(object_index(object_write_offset[64*i+:64])/LOGICAL_COLS)*COLS+object_index(object_write_offset[64*i+:64])%LOGICAL_COLS])
      $fatal(1,"object write value/address");
    end
    object_writes<=object_writes+1;ack_generation[ack_tail]<=object_write_generation;ack_due[ack_tail]<=cycles+12;ack_tail<=ack_tail+1'b1;
   end
   case({object_request_fire,object_ack_fire})
    2'b10:ack_count<=ack_count+1'b1;
    2'b01:ack_count<=ack_count-1'b1;
    default:begin end
   endcase
   if(object_ack_fire && ack_fault[ack_head])begin
    if(dut.runtime_operands.lifetime.state!=2 || dut.core_busy || array_done)
     $fatal(1,"write fault not exercised after arithmetic completion");
    late_write_faults<=late_write_faults+1;
   end
   if(object_ack_fire)begin ack_head<=ack_head+1'b1;object_acks<=object_acks+1;end
   if(array_done && OBJECT_WRITES && (!writer_drained || object_ack || ack_count!=0 || object_writes!=object_acks))
    $fatal(1,"completion bypassed actual write acknowledgements");
  end
 end
 wire mem_request_ready,mem_response_valid,mem_error;
 wire [31:0] mem_generation,mem_w;
 wire [63:0] mem_a;
 wire [2:0] mem_missing;
 wire [31:0] mem_base,mem_window_generation,mem_fill_generation;
 wire [8:0] mem_extent,mem_fill_index;
 wire [1:0] mem_plane,mem_fill_plane;
 wire mem_window_valid,mem_fill_valid,mem_window_ready,mem_fill_ready;
 wire [63:0] mem_fill_data;
 wire manager_active,manager_error,manager_ready,fetch_valid,fetch_response_ready;
 wire mapper_ready,mapper_command_ready,mapper_error,byte_valid;
 wire [31:0] byte_object;
 wire [63:0] byte_tag,byte_offset;
 wire [11:0] byte_count;
 wire [8:0] byte_words;
 wire [1:0] byte_shift;
 reg mapper_started=0;
 wire byte_ready=!fetch_active && cycles%5!=0;
 wire [31:0] response_byte_address=saved_fetch_address+{22'd0,fetch_index,1'b0};
 wire [63:0] transport_data={48'd0,activation_bytes[response_byte_address+1],activation_bytes[response_byte_address]};
 always @(posedge clk)begin
  if(!rst_n || runtime_transport_cancel)mapper_started<=0;
  else if(SRAM_AUX && auxiliary_request_valid && mapper_command_ready)mapper_started<=1;
 end
 ot_a3_operand_byte_mapper byte_mapper(
  .clk(clk),.rst_n(rst_n),.clear(runtime_transport_cancel),
  .command_valid(SRAM_AUX && auxiliary_request_valid && !mapper_started),.command_ready(mapper_command_ready),
  .command_generation(auxiliary_request_generation),.command_objects({64'd0,INPUT_LAYOUT?input_a_object:ACTIVATION_OBJECT}),
  .command_word_bases(96'd0),.command_byte_bases(192'd0),
  .command_object_bytes({128'd0,INPUT_LAYOUT?input_a_object_bytes:64'(2*DEPTH*ROWS)}),.command_word_shifts(6'd1),
  .request_valid(fetch_valid),.request_ready(mapper_ready),.request_tag(fetch_tag),
  .request_plane(fetch_plane),.request_address(fetch_address),.request_words(fetch_words),
  .burst_valid(byte_valid),.burst_ready(byte_ready),.burst_tag(byte_tag),.burst_object(byte_object),
  .burst_offset(byte_offset),.burst_bytes(byte_count),.burst_words(byte_words),.burst_shift(byte_shift),
  .protocol_error(mapper_error));
 wire [63:0] fetch_tag;
 wire [1:0] fetch_plane;
 wire [31:0] fetch_address;
 wire [8:0] fetch_words;
 reg fetch_active=0;
 reg [63:0] saved_fetch_tag=0;
 reg [31:0] saved_fetch_address=0;
 reg [8:0] saved_fetch_words=0,fetch_index=0;
 integer mem_fills=0,mem_windows=0,mem_requests=0;
 integer first_mem_fills=0,first_mem_requests=0,first_weight_fills=0;
 // RTL owns window planning/fill publication. The fixture supplies only the
 // external burst transport and admitted plane bounds in service-word units.
 ot_a3_auxiliary_window_scheduler #(.ACTIVATION_MISS_ALIGNED(ACTIVATION_MISS_ALIGNED)) auxiliary_manager(
  .clk(clk),.rst_n(rst_n),.clear(runtime_transport_cancel),
  .command_valid(SRAM_AUX && auxiliary_request_valid && !manager_active),.command_ready(manager_ready),
  .command_generation(auxiliary_request_generation),.command_bases(96'd0),
  .command_words({32'd0,32'd0,32'(DEPTH*ROWS)}),
  .request_valid(SRAM_AUX && auxiliary_request_valid),.request_generation(auxiliary_request_generation),
  .request_addresses({32'd0,32'd0,auxiliary_request_a}),.missing_planes(mem_missing),
  .window_valid(mem_window_valid),.window_ready(mem_window_ready),.window_plane(mem_plane),
  .window_generation(mem_window_generation),.window_base(mem_base),.window_words(mem_extent),
  .fill_valid(mem_fill_valid),.fill_ready(mem_fill_ready),.fill_plane(mem_fill_plane),
  .fill_generation(mem_fill_generation),.fill_index(mem_fill_index),.fill_data(mem_fill_data),
  .fetch_valid(fetch_valid),.fetch_ready(mapper_ready),.fetch_tag(fetch_tag),
  .fetch_plane(fetch_plane),.fetch_address(fetch_address),.fetch_words(fetch_words),
  .response_valid(fetch_active && cycles%3!=0),.response_ready(fetch_response_ready),
  .response_tag(saved_fetch_tag),.response_index(fetch_index),
  .response_data(transport_data),
  .active(manager_active),.protocol_error(manager_error));
 ot_a3_runtime_auxiliary_windows auxiliary_memory(
  .clk(clk),.rst_n(rst_n),.clear(runtime_transport_cancel),
  .window_valid(mem_window_valid),.window_ready(mem_window_ready),
  .window_plane(mem_plane),.window_generation(mem_window_generation),.window_base(mem_base),.window_words(mem_extent),
  .fill_valid(mem_fill_valid),.fill_ready(mem_fill_ready),.fill_plane(mem_fill_plane),
  .fill_generation(mem_fill_generation),.fill_index(mem_fill_index),.fill_data(mem_fill_data),
  .request_valid(SRAM_AUX && auxiliary_request_valid),.request_ready(mem_request_ready),
  .request_generation(auxiliary_request_generation),.request_a(auxiliary_request_a),
  .request_s(32'd0),.request_ws(32'd0),.request_w(auxiliary_request_w),
  .request_scale_a(1'b0),.request_scale_b(1'b0),.missing_planes(mem_missing),
  .response_valid(mem_response_valid),.response_ready(auxiliary_response_ready),
  .response_generation(mem_generation),.response_w(mem_w),.response_a_data(mem_a),
  .response_s_data(),.response_ws_data(),.protocol_error(mem_error));
 always @(posedge clk)begin
  if(!rst_n || runtime_transport_cancel)fetch_active<=0;
  else if(SRAM_AUX)begin
   if((mem_error || manager_error || mapper_error) && phase!=5)$fatal(1,"unexpected auxiliary service error");
   if(auxiliary_request_valid && mem_request_ready)mem_requests<=mem_requests+1;
   if(mem_window_valid && mem_window_ready)mem_windows<=mem_windows+1;
   if(mem_fill_valid && mem_fill_ready)mem_fills<=mem_fills+1;
   if(byte_valid && byte_ready)begin
    if(byte_object!=ACTIVATION_OBJECT || byte_shift!=1 || byte_offset+64'(byte_count)>2*DEPTH*ROWS || byte_count!={2'd0,byte_words,1'b0})$fatal(1,"unbounded object byte burst");
    fetch_active<=1;saved_fetch_tag<=byte_tag ^ ((phase==5)?64'd1:64'd0);saved_fetch_address<=byte_offset[31:0];
    saved_fetch_words<=byte_words;fetch_index<=0;
   end
   if(fetch_active && cycles%3!=0 && fetch_response_ready)begin
    if(fetch_index==saved_fetch_words-1)fetch_active<=0;else fetch_index<=fetch_index+1'b1;
   end
  end
 end
 // Actual byte-addressed weight object backing the cluster's internal gather.
 wire wobj_valid,wobj_response_ready;
 wire [63:0] wobj_tag,wobj_offset;
 wire [31:0] wobj_object;
 wire [4:0] wobj_bytes;
 reg wobj_pending=0;
 reg [63:0] wobj_saved_tag=0,wobj_saved_offset=0;
 integer wobj_delay=0,wobj_reads=0,wobj_total_bytes=0;
 integer first_wobj_reads=0,first_wobj_bytes=0;
 reg [7:0] weight_bytes[0:WEIGHT_OBJECT_BYTES-1];
 reg [127:0] wobj_data;
 wire wobj_ready=!wobj_pending && !runtime_transport_cancel && cycles%5!=0;
 wire wobj_response_valid=wobj_pending && wobj_delay==0 && !runtime_transport_cancel;
 always @*begin
  wobj_data=0;
  for(integer b=0;b<16;b=b+1)
   if(wobj_saved_offset+64'(b)<64'(WEIGHT_OBJECT_BYTES))
    wobj_data[8*b+:8]=weight_bytes[wobj_saved_offset+64'(b)];
 end
 always @(posedge clk)begin
  if(!rst_n || (runtime_transport_cancel && runtime_transport_ack))wobj_pending<=0;
  else begin
   if(wobj_valid && wobj_ready)begin
    if(wobj_object!=WEIGHT_OBJECT || wobj_offset[3:0]!=0 || wobj_bytes==0 ||
       wobj_offset+64'(wobj_bytes)>64'(WEIGHT_OBJECT_BYTES))$fatal(1,"weight object read bounds");
    wobj_pending<=1;wobj_saved_offset<=wobj_offset;wobj_delay<=3;
    wobj_saved_tag<=wobj_tag ^ ((phase==3)?64'h100000000:64'd0);
    wobj_reads<=wobj_reads+1;wobj_total_bytes<=wobj_total_bytes+integer'(wobj_bytes);
   end
   if(wobj_pending && wobj_delay>0)wobj_delay<=wobj_delay-1;
   if(wobj_response_valid && wobj_response_ready)wobj_pending<=0;
  end
 end
 generate if(WEIGHT_OBJECT_READS)begin : check_read_ownership
  always @(posedge clk)if(rst_n && runtime_transport_cancel && !runtime_transport_ack && wobj_pending &&
      !dut.runtime_operands.descriptor_weight_transport.transport.gather.active)
   $fatal(1,"weight read ownership cleared before cancellation acknowledgement");
 end endgenerate
 ot_a3_g2_cluster #(.RUNTIME_OPERANDS(1),.RUNTIME_PASS_FIRST(PASS_FIRST),.PASS_COLUMNS(PASS_COLUMNS),.RESOLVE_INPUT_OBJECTS(INPUT_LAYOUT),.RUNTIME_WEIGHT_OBJECT_READS(WEIGHT_OBJECT_READS),.RUNTIME_WEIGHT_LINE_REUSE(WEIGHT_LINE_REUSE),.RUNTIME_WEIGHT_WORD_HANDOFF(WEIGHT_WORD_HANDOFF),.RUNTIME_OBJECT_WRITES(OBJECT_WRITES),.WRITE_OUTSTANDING(WRITE_OUTSTANDING),.RUNTIME_WEIGHT_ROW_REUSE(WEIGHT_ROW_REUSE),
 .RUNTIME_AUXILIARY_DEPTH(AUXILIARY_DEPTH),.RUNTIME_REGISTER_AUXILIARY_REQUESTS(REGISTER_AUXILIARY_REQUESTS)) dut(
 .input_layout_valid(input_layout_valid),.input_a_object(input_a_object),.input_b_object(input_b_object),
 .input_a_object_bytes(input_a_object_bytes),.input_b_object_bytes(input_b_object_bytes),
 .input_a_row_stride(input_a_row_stride),.input_a_k_stride(input_a_k_stride),
 .input_b_column_stride(input_b_column_stride),.input_b_k_stride(input_b_k_stride),
 .weight_object_read_valid(wobj_valid),.weight_object_read_ready(wobj_ready),
 .weight_object_read_tag(wobj_tag),.weight_object_read_object(wobj_object),
 .weight_object_read_offset(wobj_offset),.weight_object_read_bytes(wobj_bytes),
 .weight_object_response_valid(wobj_response_valid),.weight_object_response_ready(wobj_response_ready),
 .weight_object_response_tag(wobj_saved_tag),.weight_object_response_data(wobj_data),.weight_object_response_error(1'b0),
 .cfg_output_object(phase==7?OUTPUT_OBJECT^32'd1:OUTPUT_OBJECT),.cfg_output_object_bytes(configured_object_bytes),
 .object_write_valid(object_write_valid),.object_write_ready(object_write_ready),
 .object_write_generation(object_write_generation),.object_write_object(object_write_object),
 .object_write_mask(object_write_mask),.object_write_offset(object_write_offset),.object_write_data(object_write_data),
 .object_write_fp32(object_write_fp32),.object_response_valid(object_ack),.object_response_ready(object_response_ready),
 .object_response_generation(object_ack_generation),.object_response_error(ack_fault[ack_head]),
 .object_writer_drained(writer_drained),.object_writer_error(writer_error),.part_accepted(part_accepted),
 .clk(clk),.rst_n(rst_n),.part_ready(sink_enable),.part_valid(part_valid),.start(kick),.host_we(host_we),.host_sel(host_sel),.host_row(host_row),.host_lane(host_lane),.host_wdata(host_wdata),
 .host_ready(host_ready),.host_write_refused(host_write_refused),
 .cfg_program_base(32'd0),.cfg_instruction_count(INSTRUCTION_COUNT),.cfg_entry_pc(32'd0),
 .cfg_max_retired_work(MAX_WORK),.cfg_state_count(32'd0),
 .cfg_array_group(8'd1),.cfg_array_block_a(16'd0),.cfg_array_block_rows_a(16'd0),.cfg_array_block_b(16'd0),
 .cfg_array_scale_a_base(32'd0),.cfg_array_ws_base(32'd0),.cfg_array_out_fp32(1'b0),
 .done(done),.complete(complete),.trapped(trapped),.trap_class(trap_class),.count_issued(count_issued),.count_retired(count_retired),
 .runtime_service_fault((SRAM_AUX && (mem_error || manager_error || mapper_error))),.runtime_abort(runtime_abort),.runtime_transport_ack(runtime_transport_ack),.runtime_writes_drained(runtime_writes_drained),
 .runtime_transport_cancel(runtime_transport_cancel),.runtime_generation(runtime_generation),
 .weight_request_valid(weight_request_valid),.weight_request_ready(!wactive),.weight_request_tag(weight_request_tag),
 .weight_request_address(weight_request_address),.weight_request_words(weight_request_words),
 .weight_response_valid(wactive && cycles%WEIGHT_RESPONSE_GAP==0),.weight_response_ready(weight_response_ready),
 .weight_response_tag(wtag),.weight_response_index(wi),.weight_response_data(weight_image[wbase+wi]),
 .auxiliary_request_valid(auxiliary_request_valid),.auxiliary_request_ready(SRAM_AUX?mem_request_ready:!auxvalid),
 .auxiliary_request_generation(auxiliary_request_generation),.auxiliary_request_w(auxiliary_request_w),.auxiliary_request_a(auxiliary_request_a),
 .auxiliary_response_valid(SRAM_AUX?mem_response_valid:auxvalid),.auxiliary_response_ready(auxiliary_response_ready),
 .auxiliary_response_generation(SRAM_AUX?mem_generation:agen),.auxiliary_response_w(SRAM_AUX?mem_w:aw),
 .auxiliary_response_a_data(SRAM_AUX?mem_a:adata),.auxiliary_response_s_data(32'b0),.auxiliary_response_ws_data(64'b0),
 .output_row_stride(output_row_stride),.output_col_stride(output_col_stride),
 .output_object_bytes(output_object_bytes),
 .output_layout_valid(output_layout_valid),.output_object(output_object),.output_element_base(output_element_base),
 .output_rows(output_rows),.output_logical_cols(output_logical_cols),.output_padded_cols(output_padded_cols),.output_fp32(output_fp32),
 .array_busy(array_busy),.array_done(array_done),.array_error_code(array_error_code),.part_we(part_we),.part_data(part_data),.part_addr(part_addr),.part_acc(part_acc));
 always @(posedge clk)begin
  if(!rst_n)begin wactive<=0;auxvalid<=0;end
  else begin
   cycles<=cycles+1;
   if(!WEIGHT_OBJECT_READS && weight_request_valid && !wactive)begin wactive<=1;wtag<=weight_request_tag ^ ((phase==3) ? 64'd1 : 64'd0);wi<=0;wn<=weight_request_words;wbase<=weight_request_address;
    if(weight_request_address+weight_request_words>WEIGHT_WORDS)$fatal(1,"weight address out of bounds");end
   if(WEIGHT_OBJECT_READS && dut.runtime_operands.weight_response_valid_i && dut.runtime_operands.weight_response_ready_i)fills<=fills+1;
   if(wactive && cycles%WEIGHT_RESPONSE_GAP==0 && weight_response_ready)begin fills<=fills+1;if(wi==wn-1)wactive<=0;else wi<=wi+1'b1;end
   if(!SRAM_AUX && auxiliary_request_valid && !auxvalid)begin auxvalid<=1;agen<=auxiliary_request_generation;aw<=auxiliary_request_w;adata<=activation_image[auxiliary_request_a];
    if(auxiliary_request_a>=DEPTH*ROWS || auxiliary_request_w>=WEIGHT_WORDS)$fatal(1,"auxiliary address out of bounds");end
   if(auxvalid && auxiliary_response_ready)auxvalid<=0;
   if(runtime_transport_cancel)begin wactive<=0;auxvalid<=0;end
   if(OBJECT_WRITES && part_valid && output_object_bytes!=OUTPUT_BYTES)$fatal(1,"descriptor object capacity");
   if(part_valid && (!output_layout_valid || output_object!=OUTPUT_OBJECT || output_element_base!=OUTPUT_BASE ||
      output_row_stride!=OUTPUT_ROW_STRIDE || output_col_stride!=OUTPUT_COL_STRIDE ||
      output_rows!=ROWS || output_logical_cols!=LOGICAL_COLS || output_padded_cols!=COLS || output_fp32))
    $fatal(1,"output descriptor layout not owned through drain");
   if(held && (!part_valid || {part_we,part_addr,part_data,part_acc}!=held_payload))$fatal(1,"stalled output changed");
   held<=part_valid && !sink_ready;held_payload<={part_we,part_addr,part_data,part_acc};
   if(part_valid && !sink_ready)output_stalls<=output_stalls+1;
   if(dut.operand_request && dut.operand_last && !dut.runtime_operands.output_credit)reservation_stalls<=reservation_stalls+1;
   if(kick)seen<=0;
   else if(part_valid && sink_ready)begin
    outputs<=outputs+$countones(part_we);
    for(integer i=0;i<8;i=i+1)if(part_we[i])begin
     if(((part_addr[32*i+:32]-OUTPUT_BASE)%(COLS/8))*8+i>=LOGICAL_COLS)$fatal(1,"padded lane escaped output mask");
     if(part_addr[32*i+:32]<OUTPUT_BASE || part_addr[32*i+:32]-OUTPUT_BASE>=LOCAL_OUTPUTS)$fatal(1,"wrong output address");
     if(seen[8*(part_addr[32*i+:32]-OUTPUT_BASE)+i])$fatal(1,"duplicate output");
     seen[8*(part_addr[32*i+:32]-OUTPUT_BASE)+i]<=1;
     if((phase!=1 && phase!=4 && phase!=6) || part_data[32*i+:32]!=expected[8*(part_addr[32*i+:32]-OUTPUT_BASE)+i])$fatal(1,"wrong result or write after abort");
    end
   end
   if(host_write_refused)$fatal(1,"host write refused");
   if(trapped && phase==1 && !kick)$fatal(1,"unexpected sequencer trap class=%0d issued=%0d adapter_state=%0d depth=%0d dims=%0d,%0d",trap_class,count_issued,dut.issue_adapter.state,dut.arr_depth,dut.issue_adapter.d_dim0,dut.issue_adapter.d_dim1);
   if(array_done && (!runtime_transport_ack || !runtime_writes_drained || part_valid))$fatal(1,"early completion");
  end
 end
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 integer launch_cycle=0;
 task launch;begin launch_cycle=cycles;configured_object_bytes=64'd1;kick=1;tick();kick=0;end endtask
 task drain(input [7:0] err);begin
  wait(runtime_transport_cancel);@(negedge clk);
  repeat(4)begin tick();if(array_done || !array_busy)$fatal(1,"lost operation during drain");end
  runtime_transport_ack=1;tick();repeat(3)tick();if(array_done)$fatal(1,"write ack bypassed");
  runtime_writes_drained=1;
  if(tail_hold)begin
   repeat(12)begin tick();if(array_done)$fatal(1,"queued outputs bypassed drain barrier");end
   tail_hold=0;
  end
  wait(array_done);@(negedge clk);
  if(array_error_code!=err)$fatal(1,"wrong completion error");
  if(OBJECT_WRITES && err==0)begin
   for(integer b=0;b<OUTPUT_BYTES;b=b+1)
    if(object_index(64'(b & ~1))<0 && output_memory[b]!=8'ha5)$fatal(1,"write corrupted output gap");
   if(object_seen!={ROWS*LOGICAL_COLS{1'b1}})$fatal(1,"missing committed object outputs");
   for(integer r=0;r<ROWS;r=r+1)for(integer c=0;c<LOGICAL_COLS;c=c+1)
    if({16'b0,output_memory[2*(OUTPUT_BASE+r*OUTPUT_ROW_STRIDE+c*OUTPUT_COL_STRIDE)+1],output_memory[2*(OUTPUT_BASE+r*OUTPUT_ROW_STRIDE+c*OUTPUT_COL_STRIDE)]}!=expected[r*COLS+c])
     $fatal(1,"committed object memory differs from golden");
  end
  wait(done);@(negedge clk);
  if(err==0 && (!complete || trapped || count_issued!=1 || count_retired!=2))
   $fatal(1,"program did not retire successfully issued=%0d retired=%0d",count_issued,count_retired);
  if(err!=0 && (!trapped || trap_class!=ot_a3_pkg::A3_TRAP_ENGINE))$fatal(1,"abort did not reach sequencer");
  $display("program phase=%0d complete=%0d trap=%0d cycles=%0d",phase,complete,trap_class,cycles);
  $display("phase latency phase=%0d elapsed_cycles=%0d",phase,cycles-launch_cycle);
  tick();runtime_transport_ack=0;runtime_writes_drained=0;tick();
 end endtask
 initial begin
  for(integer r=0;r<ROWS;r=r+1)
   for(integer c=0;c<LOGICAL_COLS;c=c+1)expected_seen[r*COLS+c]=1;
  $readmemh("program.hex",program_image);$readmemh("descriptor.hex",descriptor_image);
  $readmemh("weight_bytes.hex",weight_bytes);$readmemh("activation_bytes.hex",activation_bytes);$readmemh("activation.hex",activation_image);$readmemh("weight.hex",weight_image);$readmemh("expected.hex",expected);
  tick();rst_n=1;tick();
  host_we=1;host_sel=0;
  for(integer j=0;j<PROGRAM_WORDS;j=j+1)begin host_row=j;host_wdata=program_image[j];tick();end
  host_sel=1;
  for(integer j=0;j<DESCRIPTOR_WORDS;j=j+1)begin host_row=j/2;host_lane=j%2;host_wdata=descriptor_image[j];tick();end
  host_we=0;tick();tick();phase=1;launch();
  if(STRESS_OUTPUT)begin
   wait(dut.operand_request && dut.operand_last && !dut.runtime_operands.output_credit);
   @(negedge clk);repeat(16)tick();release_output=1;
  end
  drain(0);
  first_wobj_reads=wobj_reads;first_wobj_bytes=wobj_total_bytes;
  first_mem_fills=mem_fills;first_mem_requests=mem_requests;first_weight_fills=fills;
  if(fills!=EXPECTED_WEIGHT_FILLS)$fatal(1,"weight reuse traffic accounting got %0d expected %0d",fills,EXPECTED_WEIGHT_FILLS);
  if(SRAM_AUX && (mem_fills!=EXPECTED_ACTIVATION_FILLS || mem_requests!=WEIGHT_WORDS))$fatal(1,"SRAM reuse accounting");
  // Lane-distinct BF16 results must match the functional Device.
  if(seen!=expected_seen || outputs!=ROWS*LOGICAL_COLS)$fatal(1,"missing first outputs");
  if(fills<DEPTH)$fatal(1,"multi-tile refill not exercised");
  phase=2;launch();wait(dut.operand_issue);if(WEIGHT_OBJECT_READS)wait(wobj_pending);@(negedge clk);runtime_abort=1;tick();runtime_abort=0;drain(8'hff);
  if(seen!=0 || outputs!=ROWS*LOGICAL_COLS)$fatal(1,"aborted operation wrote output");
  phase=1;launch();
  if(STRESS_OUTPUT)begin
   // Hold the last result until after compute and external acknowledgements.
   // The final pass has one column when (local_cols-1)%pass_width==0,
   // including width one. Its penultimate result is in the previous row.
   wait(seen[8*((PASS_FIRST && (COLS/8-1)%PASS_COLUMNS==0)?LOCAL_OUTPUTS-1-COLS/8:LOCAL_OUTPUTS-2)]);@(negedge clk);tail_hold=1;
  end
  drain(0);
  if(seen!=expected_seen || outputs!=2*ROWS*LOGICAL_COLS)$fatal(1,"missing restart outputs");
  if(runtime_generation!=3)$fatal(1,"generation restart");
  // A bad transport identity must become an ENGINE trap through the same ABI.
  phase=3;launch();drain(8'hfe);
  if(seen!=0 || outputs!=2*ROWS*LOGICAL_COLS)$fatal(1,"transport fault wrote output");
  phase=1;launch();drain(0);
  if(seen!=expected_seen || outputs!=3*ROWS*LOGICAL_COLS || runtime_generation!=5)$fatal(1,"transport fault recovery");
  if(STRESS_OUTPUT)begin
   // Abort while accepted results are queued: these must stay stable and drain.
   release_output=0;phase=4;launch();wait(part_valid);@(negedge clk);
   runtime_abort=1;tick();runtime_abort=0;tail_hold=1;release_output=1;drain(8'hff);
   if(seen[7:0]!=8'hff || outputs!=3*ROWS*LOGICAL_COLS+8)$fatal(1,"queued abort result lost");
   if(output_stalls==0 || reservation_stalls==0)$fatal(1,"backpressure not exercised");
  end
  if(SRAM_AUX)begin
   // Corrupt an auxiliary burst identity and require precise G2 error/recovery.
   phase=5;launch();drain(8'hfe);
   if(seen!=0)$fatal(1,"auxiliary fault wrote output");
   phase=1;launch();drain(0);
   if(seen!=expected_seen)$fatal(1,"auxiliary fault recovery lost outputs");
  end
  if(OBJECT_WRITES)begin
   // Fail the final write acknowledgement only after compute enters drain.
   // The fault must traverse writer -> lifetime -> adapter -> sequencer.
   phase=6;launch();drain(8'hfe);
   if(late_write_faults!=1 || !writer_drained || object_writes!=object_acks)
    $fatal(1,"late write fault did not drain precisely");
   phase=1;launch();drain(0);
   if(seen!=expected_seen)$fatal(1,"late write fault recovery lost output");
   $display("late write faults=%0d recovered=1",late_write_faults);
   writes_before_bad_binding=object_writes;
   phase=7;launch();drain(8'hfe);
   if(object_writes!=writes_before_bad_binding || seen!=0)$fatal(1,"mismatched object binding wrote data");
   phase=1;launch();drain(0);
   $display("object binding fault=1 recovery=1 captured_capacity=1");
  end
  if(OBJECT_WRITES && (object_writes==0 || object_writes!=object_acks))$fatal(1,"writer unexercised");
  $display("object writes=%0d acknowledgements=%0d",object_writes,object_acks);
  $display("weight object reads=%0d bytes=%0d first_reads=%0d first_bytes=%0d",wobj_reads,wobj_total_bytes,first_wobj_reads,first_wobj_bytes);
  $display("first operation weight fill_words=%0d",first_weight_fills);
  $display("first operation SRAM fill_words=%0d read_requests=%0d",first_mem_fills,first_mem_requests);
  $display("auxiliary SRAM windows=%0d fill_words=%0d read_requests=%0d",mem_windows,mem_fills,mem_requests);
  if(SRAM_AUX && (mem_windows<3 || mem_requests<WEIGHT_WORDS*3))$fatal(1,"SRAM service not exercised");
  $display("output stalls=%0d reservation stalls=%0d accepted_outputs=%0d",output_stalls,reservation_stalls,outputs);
  $display("PASS G2 runtime program multi-tile arithmetic, abort, transport fault, drain and restart fills=%0d",fills);$finish;
 end
 // Bound deep streamed campaigns by work while retaining the small-case limit.
 localparam time WATCHDOG_NS=WEIGHT_OBJECT_READS?
     ((64'(WEIGHT_WORDS)*3000>10000000)?64'(WEIGHT_WORDS)*3000:64'd10000000):64'd2000000;
 initial begin #(WATCHDOG_NS);$fatal(1,"timeout");end
endmodule
