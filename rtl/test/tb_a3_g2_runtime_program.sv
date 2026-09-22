`timescale 1ns/1ps
// Host-load a real ABI program and compare outputs with the functional Device.
module tb_a3_g2_runtime_program;
 `include "program_config.svh"
 localparam LOCAL_OUTPUTS=ROWS*COLS/8, WEIGHT_WORDS=80*LOCAL_OUTPUTS;
 reg [127:0] program_image[0:PROGRAM_WORDS-1],descriptor_image[0:DESCRIPTOR_WORDS-1],weight_image[0:WEIGHT_WORDS-1];
 reg [31:0] expected[0:ROWS*COLS-1];
 reg [63:0] activation_image[0:80*ROWS-1],adata=0;
 reg host_we=0;reg [2:0] host_sel=0;reg [31:0] host_row=0;reg [5:0] host_lane=0;reg [127:0] host_wdata=0;
 wire host_ready,host_write_refused,done,complete,trapped;
 wire [15:0] trap_class;wire [31:0] count_issued,count_retired;
 reg [31:0] wbase=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,kick=0,runtime_abort=0,runtime_transport_ack=0,runtime_writes_drained=0;
 wire runtime_transport_cancel,array_busy,array_done;
 wire [31:0] runtime_generation;
 wire [7:0] array_error_code;
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
 reg [1:0] mem_state=0;
 reg [31:0] mem_base=0;
 reg [8:0] mem_extent=0,mem_index=0;
 wire mem_window_ready,mem_fill_ready;
 integer mem_fills=0,mem_windows=0,mem_requests=0;
 integer first_mem_fills=0,first_mem_requests=0;
 // Fixture window manager supplies exact bounded pages; SRAM data is read by
 // synthesizable service RTL. Deployment byte-to-word translation is external.
 ot_a3_runtime_auxiliary_windows auxiliary_memory(
  .clk(clk),.rst_n(rst_n),.clear(runtime_transport_cancel),
  .window_valid(SRAM_AUX && mem_state==1),.window_ready(mem_window_ready),
  .window_plane(2'd0),.window_generation(runtime_generation),.window_base(mem_base),.window_words(mem_extent),
  .fill_valid(SRAM_AUX && mem_state==2),.fill_ready(mem_fill_ready),.fill_plane(2'd0),
  .fill_generation(runtime_generation),.fill_index(mem_index),.fill_data(activation_image[mem_base+mem_index]),
  .request_valid(SRAM_AUX && auxiliary_request_valid),.request_ready(mem_request_ready),
  .request_generation(auxiliary_request_generation),.request_a(auxiliary_request_a),
  .request_s(32'd0),.request_ws(32'd0),.request_w(auxiliary_request_w),
  .request_scale_a(1'b0),.request_scale_b(1'b0),.missing_planes(mem_missing),
  .response_valid(mem_response_valid),.response_ready(auxiliary_response_ready),
  .response_generation(mem_generation),.response_w(mem_w),.response_a_data(mem_a),
  .response_s_data(),.response_ws_data(),.protocol_error(mem_error));
 always @(posedge clk)begin
  if(!rst_n || runtime_transport_cancel)mem_state<=0;
  else if(SRAM_AUX)begin
   if(mem_error)$fatal(1,"auxiliary memory protocol error");
   if(auxiliary_request_valid && mem_request_ready)mem_requests<=mem_requests+1;
   case(mem_state)
    0:if(auxiliary_request_valid && mem_missing[0])begin
      mem_base<=auxiliary_request_a & 32'hffffff00;
      mem_extent<=9'(((80*ROWS-(auxiliary_request_a & 32'hffffff00))<256)?
                  (80*ROWS-(auxiliary_request_a & 32'hffffff00)):256);
      mem_state<=1;
     end
    1:if(mem_window_ready)begin mem_state<=2;mem_index<=0;mem_windows<=mem_windows+1;end
    2:if(mem_fill_ready)begin
      mem_fills<=mem_fills+1;
      if(mem_index==mem_extent-1)mem_state<=0;else mem_index<=mem_index+1'b1;
     end
    default:mem_state<=0;
   endcase
  end
 end
 ot_a3_g2_cluster #(.RUNTIME_OPERANDS(1)) dut(
 .clk(clk),.rst_n(rst_n),.part_ready(sink_ready),.part_valid(part_valid),.start(kick),.host_we(host_we),.host_sel(host_sel),.host_row(host_row),.host_lane(host_lane),.host_wdata(host_wdata),
 .host_ready(host_ready),.host_write_refused(host_write_refused),
 .cfg_program_base(32'd0),.cfg_instruction_count(INSTRUCTION_COUNT),.cfg_entry_pc(32'd0),
 .cfg_max_retired_work(MAX_WORK),.cfg_state_count(32'd0),
 .cfg_array_group(8'd1),.cfg_array_block_a(16'd0),.cfg_array_block_rows_a(16'd0),.cfg_array_block_b(16'd0),
 .cfg_array_scale_a_base(32'd0),.cfg_array_ws_base(32'd0),.cfg_array_out_fp32(1'b0),
 .done(done),.complete(complete),.trapped(trapped),.trap_class(trap_class),.count_issued(count_issued),.count_retired(count_retired),
 .runtime_abort(runtime_abort),.runtime_transport_ack(runtime_transport_ack),.runtime_writes_drained(runtime_writes_drained),
 .runtime_transport_cancel(runtime_transport_cancel),.runtime_generation(runtime_generation),
 .weight_request_valid(weight_request_valid),.weight_request_ready(!wactive),.weight_request_tag(weight_request_tag),
 .weight_request_address(weight_request_address),.weight_request_words(weight_request_words),
 .weight_response_valid(wactive),.weight_response_ready(weight_response_ready),
 .weight_response_tag(wtag),.weight_response_index(wi),.weight_response_data(weight_image[wbase+wi]),
 .auxiliary_request_valid(auxiliary_request_valid),.auxiliary_request_ready(SRAM_AUX?mem_request_ready:!auxvalid),
 .auxiliary_request_generation(auxiliary_request_generation),.auxiliary_request_w(auxiliary_request_w),.auxiliary_request_a(auxiliary_request_a),
 .auxiliary_response_valid(SRAM_AUX?mem_response_valid:auxvalid),.auxiliary_response_ready(auxiliary_response_ready),
 .auxiliary_response_generation(SRAM_AUX?mem_generation:agen),.auxiliary_response_w(SRAM_AUX?mem_w:aw),
 .auxiliary_response_a_data(SRAM_AUX?mem_a:adata),.auxiliary_response_s_data(32'b0),.auxiliary_response_ws_data(64'b0),
 .array_busy(array_busy),.array_done(array_done),.array_error_code(array_error_code),.part_we(part_we),.part_data(part_data),.part_addr(part_addr),.part_acc(part_acc));
 always @(posedge clk)begin
  if(!rst_n)begin wactive<=0;auxvalid<=0;end
  else begin
   cycles<=cycles+1;
   if(weight_request_valid && !wactive)begin wactive<=1;wtag<=weight_request_tag ^ ((phase==3) ? 64'd1 : 64'd0);wi<=0;wn<=weight_request_words;wbase<=weight_request_address;
    if(weight_request_address+weight_request_words>WEIGHT_WORDS)$fatal(1,"weight address out of bounds");end
   if(wactive && weight_response_ready)begin fills<=fills+1;if(wi==wn-1)wactive<=0;else wi<=wi+1'b1;end
   if(!SRAM_AUX && auxiliary_request_valid && !auxvalid)begin auxvalid<=1;agen<=auxiliary_request_generation;aw<=auxiliary_request_w;adata<=activation_image[auxiliary_request_a];
    if(auxiliary_request_a>=80*ROWS || auxiliary_request_w>=WEIGHT_WORDS)$fatal(1,"auxiliary address out of bounds");end
   if(auxvalid && auxiliary_response_ready)auxvalid<=0;
   if(runtime_transport_cancel)begin wactive<=0;auxvalid<=0;end
   if(held && (!part_valid || {part_we,part_addr,part_data,part_acc}!=held_payload))$fatal(1,"stalled output changed");
   held<=part_valid && !sink_ready;held_payload<={part_we,part_addr,part_data,part_acc};
   if(part_valid && !sink_ready)output_stalls<=output_stalls+1;
   if(dut.operand_request && dut.operand_last && !dut.runtime_operands.output_credit)reservation_stalls<=reservation_stalls+1;
   if(kick)seen<=0;
   else if(part_valid && sink_ready)begin
    outputs<=outputs+$countones(part_we);
    for(integer i=0;i<8;i=i+1)if(part_we[i])begin
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
  $readmemh("program.hex",program_image);$readmemh("descriptor.hex",descriptor_image);
  $readmemh("activation.hex",activation_image);$readmemh("weight.hex",weight_image);$readmemh("expected.hex",expected);
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
  first_mem_fills=mem_fills;first_mem_requests=mem_requests;
  if(SRAM_AUX && (mem_fills!=80*ROWS || mem_requests!=WEIGHT_WORDS))$fatal(1,"SRAM reuse accounting");
  // Lane-distinct BF16 results must match the functional Device.
  if(seen!={ROWS*COLS{1'b1}} || outputs!=ROWS*COLS)$fatal(1,"missing first outputs");
  if(fills<80)$fatal(1,"multi-tile refill not exercised");
  phase=2;launch();wait(dut.operand_issue);@(negedge clk);runtime_abort=1;tick();runtime_abort=0;drain(8'hff);
  if(seen!=0 || outputs!=ROWS*COLS)$fatal(1,"aborted operation wrote output");
  phase=1;launch();
  if(STRESS_OUTPUT)begin
   // Hold the last result until after compute and external acknowledgements.
   wait(seen[8*(LOCAL_OUTPUTS-2)]);@(negedge clk);tail_hold=1;
  end
  drain(0);
  if(seen!={ROWS*COLS{1'b1}} || outputs!=2*ROWS*COLS)$fatal(1,"missing restart outputs");
  if(runtime_generation!=3)$fatal(1,"generation restart");
  // A bad transport identity must become an ENGINE trap through the same ABI.
  phase=3;launch();drain(8'hfe);
  if(seen!=0 || outputs!=2*ROWS*COLS)$fatal(1,"transport fault wrote output");
  phase=1;launch();drain(0);
  if(seen!={ROWS*COLS{1'b1}} || outputs!=3*ROWS*COLS || runtime_generation!=5)$fatal(1,"transport fault recovery");
  if(STRESS_OUTPUT)begin
   // Abort while accepted results are queued: these must stay stable and drain.
   release_output=0;phase=4;launch();wait(part_valid);@(negedge clk);
   runtime_abort=1;tick();runtime_abort=0;tail_hold=1;release_output=1;drain(8'hff);
   if(seen[7:0]!=8'hff || outputs!=3*ROWS*COLS+8)$fatal(1,"queued abort result lost");
   if(output_stalls==0 || reservation_stalls==0)$fatal(1,"backpressure not exercised");
  end
  $display("first operation SRAM fill_words=%0d read_requests=%0d",first_mem_fills,first_mem_requests);
  $display("auxiliary SRAM windows=%0d fill_words=%0d read_requests=%0d",mem_windows,mem_fills,mem_requests);
  if(SRAM_AUX && (mem_windows<3 || mem_requests<WEIGHT_WORDS*3))$fatal(1,"SRAM service not exercised");
  $display("output stalls=%0d reservation stalls=%0d accepted_outputs=%0d",output_stalls,reservation_stalls,outputs);
  $display("PASS G2 runtime program multi-tile arithmetic, abort, transport fault, drain and restart fills=%0d",fills);$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
