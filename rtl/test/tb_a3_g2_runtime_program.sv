`timescale 1ns/1ps
// Host-load a real ABI program and compare outputs with the functional Device.
module tb_a3_g2_runtime_program;
 parameter bit WEIGHT_ROW_REUSE=1;
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
 wire sink_ready=part_ready && !tail_hold;
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
  .command_generation(auxiliary_request_generation),.command_objects({64'd0,ACTIVATION_OBJECT}),
  .command_word_bases(96'd0),.command_byte_bases(192'd0),
  .command_object_bytes({128'd0,64'(2*DEPTH*ROWS)}),.command_word_shifts(6'd1),
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
 ot_a3_g2_cluster #(.RUNTIME_OPERANDS(1),.RUNTIME_WEIGHT_ROW_REUSE(WEIGHT_ROW_REUSE),
 .RUNTIME_AUXILIARY_DEPTH(AUXILIARY_DEPTH),.RUNTIME_REGISTER_AUXILIARY_REQUESTS(REGISTER_AUXILIARY_REQUESTS)) dut(
 .clk(clk),.rst_n(rst_n),.part_ready(sink_ready),.part_valid(part_valid),.start(kick),.host_we(host_we),.host_sel(host_sel),.host_row(host_row),.host_lane(host_lane),.host_wdata(host_wdata),
 .host_ready(host_ready),.host_write_refused(host_write_refused),
 .cfg_program_base(32'd0),.cfg_instruction_count(INSTRUCTION_COUNT),.cfg_entry_pc(32'd0),
 .cfg_max_retired_work(MAX_WORK),.cfg_state_count(32'd0),
 .cfg_array_group(8'd1),.cfg_array_block_a(16'd0),.cfg_array_block_rows_a(16'd0),.cfg_array_block_b(16'd0),
 .cfg_array_scale_a_base(32'd0),.cfg_array_ws_base(32'd0),.cfg_array_out_fp32(1'b0),
 .done(done),.complete(complete),.trapped(trapped),.trap_class(trap_class),.count_issued(count_issued),.count_retired(count_retired),
 .runtime_service_fault(SRAM_AUX && (mem_error || manager_error || mapper_error)),.runtime_abort(runtime_abort),.runtime_transport_ack(runtime_transport_ack),.runtime_writes_drained(runtime_writes_drained),
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
 .output_layout_valid(output_layout_valid),.output_object(output_object),.output_element_base(output_element_base),
 .output_rows(output_rows),.output_logical_cols(output_logical_cols),.output_padded_cols(output_padded_cols),.output_fp32(output_fp32),
 .array_busy(array_busy),.array_done(array_done),.array_error_code(array_error_code),.part_we(part_we),.part_data(part_data),.part_addr(part_addr),.part_acc(part_acc));
 always @(posedge clk)begin
  if(!rst_n)begin wactive<=0;auxvalid<=0;end
  else begin
   cycles<=cycles+1;
   if(weight_request_valid && !wactive)begin wactive<=1;wtag<=weight_request_tag ^ ((phase==3) ? 64'd1 : 64'd0);wi<=0;wn<=weight_request_words;wbase<=weight_request_address;
    if(weight_request_address+weight_request_words>WEIGHT_WORDS)$fatal(1,"weight address out of bounds");end
   if(wactive && cycles%WEIGHT_RESPONSE_GAP==0 && weight_response_ready)begin fills<=fills+1;if(wi==wn-1)wactive<=0;else wi<=wi+1'b1;end
   if(!SRAM_AUX && auxiliary_request_valid && !auxvalid)begin auxvalid<=1;agen<=auxiliary_request_generation;aw<=auxiliary_request_w;adata<=activation_image[auxiliary_request_a];
    if(auxiliary_request_a>=DEPTH*ROWS || auxiliary_request_w>=WEIGHT_WORDS)$fatal(1,"auxiliary address out of bounds");end
   if(auxvalid && auxiliary_response_ready)auxvalid<=0;
   if(runtime_transport_cancel)begin wactive<=0;auxvalid<=0;end
   if(part_valid && (!output_layout_valid || output_object!=OUTPUT_OBJECT || output_element_base!=0 ||
      output_row_stride!=LOGICAL_COLS || output_col_stride!=1 ||
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
     if((part_addr[32*i+:32]%(COLS/8))*8+i>=LOGICAL_COLS)$fatal(1,"padded lane escaped output mask");
     if(part_addr[32*i+:32]>=LOCAL_OUTPUTS)$fatal(1,"wrong output address");
     if(seen[8*part_addr[32*i+:32]+i])$fatal(1,"duplicate output");
     seen[8*part_addr[32*i+:32]+i]<=1;
     if((phase!=1 && phase!=4) || part_data[32*i+:32]!=expected[8*part_addr[32*i+:32]+i])$fatal(1,"wrong result or write after abort");
    end
   end
   if(host_write_refused)$fatal(1,"host write refused");
   if(trapped && phase==1 && !kick)$fatal(1,"unexpected sequencer trap class=%0d issued=%0d adapter_state=%0d depth=%0d dims=%0d,%0d",trap_class,count_issued,dut.issue_adapter.state,dut.arr_depth,dut.issue_adapter.d_dim0,dut.issue_adapter.d_dim1);
   if(array_done && (!runtime_transport_ack || !runtime_writes_drained || part_valid))$fatal(1,"early completion");
  end
 end
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task launch;begin kick=1;tick();kick=0;end endtask
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
  wait(done);@(negedge clk);
  if(err==0 && (!complete || trapped || count_issued!=1 || count_retired!=2))
   $fatal(1,"program did not retire successfully issued=%0d retired=%0d",count_issued,count_retired);
  if(err!=0 && (!trapped || trap_class!=ot_a3_pkg::A3_TRAP_ENGINE))$fatal(1,"abort did not reach sequencer");
  $display("program phase=%0d complete=%0d trap=%0d cycles=%0d",phase,complete,trap_class,cycles);
  tick();runtime_transport_ack=0;runtime_writes_drained=0;tick();
 end endtask
 initial begin
  for(integer r=0;r<ROWS;r=r+1)
   for(integer c=0;c<LOGICAL_COLS;c=c+1)expected_seen[r*COLS+c]=1;
  $readmemh("program.hex",program_image);$readmemh("descriptor.hex",descriptor_image);
  $readmemh("activation_bytes.hex",activation_bytes);$readmemh("activation.hex",activation_image);$readmemh("weight.hex",weight_image);$readmemh("expected.hex",expected);
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
  first_mem_fills=mem_fills;first_mem_requests=mem_requests;first_weight_fills=fills;
  if(fills!=((WEIGHT_ROW_REUSE && ROWS>1 && WEIGHT_WORDS/ROWS<=1024)?WEIGHT_WORDS/ROWS:WEIGHT_WORDS))$fatal(1,"weight reuse traffic accounting");
  if(SRAM_AUX && (mem_fills!=EXPECTED_ACTIVATION_FILLS || mem_requests!=WEIGHT_WORDS))$fatal(1,"SRAM reuse accounting");
  // Lane-distinct BF16 results must match the functional Device.
  if(seen!=expected_seen || outputs!=ROWS*LOGICAL_COLS)$fatal(1,"missing first outputs");
  if(fills<DEPTH)$fatal(1,"multi-tile refill not exercised");
  phase=2;launch();wait(dut.operand_issue);@(negedge clk);runtime_abort=1;tick();runtime_abort=0;drain(8'hff);
  if(seen!=0 || outputs!=ROWS*LOGICAL_COLS)$fatal(1,"aborted operation wrote output");
  phase=1;launch();
  if(STRESS_OUTPUT)begin
   // Hold the last result until after compute and external acknowledgements.
   wait(seen[8*(LOCAL_OUTPUTS-2)]);@(negedge clk);tail_hold=1;
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
  $display("first operation weight fill_words=%0d",first_weight_fills);
  $display("first operation SRAM fill_words=%0d read_requests=%0d",first_mem_fills,first_mem_requests);
  $display("auxiliary SRAM windows=%0d fill_words=%0d read_requests=%0d",mem_windows,mem_fills,mem_requests);
  if(SRAM_AUX && (mem_windows<3 || mem_requests<WEIGHT_WORDS*3))$fatal(1,"SRAM service not exercised");
  $display("output stalls=%0d reservation stalls=%0d accepted_outputs=%0d",output_stalls,reservation_stalls,outputs);
  $display("PASS G2 runtime program multi-tile arithmetic, abort, transport fault, drain and restart fills=%0d",fills);$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
