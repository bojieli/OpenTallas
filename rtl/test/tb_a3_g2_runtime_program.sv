`timescale 1ns/1ps
// Host-load a real ABI program and compare outputs with the functional Device.
module tb_a3_g2_runtime_program;
 `include "program_config.svh"
 reg [127:0] program_image[0:PROGRAM_WORDS-1],descriptor_image[0:DESCRIPTOR_WORDS-1],weight_image[0:79];
 reg [31:0] expected[0:7];
 reg [63:0] activation_image[0:79],adata=0;
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
 reg [7:0] seen=0;
 ot_a3_g2_cluster #(.RUNTIME_OPERANDS(1)) dut(
 .clk(clk),.rst_n(rst_n),.start(kick),.host_we(host_we),.host_sel(host_sel),.host_row(host_row),.host_lane(host_lane),.host_wdata(host_wdata),
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
 .auxiliary_request_valid(auxiliary_request_valid),.auxiliary_request_ready(!auxvalid),
 .auxiliary_request_generation(auxiliary_request_generation),.auxiliary_request_w(auxiliary_request_w),.auxiliary_request_a(auxiliary_request_a),
 .auxiliary_response_valid(auxvalid),.auxiliary_response_ready(auxiliary_response_ready),
 .auxiliary_response_generation(agen),.auxiliary_response_w(aw),
 .auxiliary_response_a_data(adata),.auxiliary_response_s_data(32'b0),.auxiliary_response_ws_data(64'b0),
 .array_busy(array_busy),.array_done(array_done),.array_error_code(array_error_code),.part_we(part_we),.part_data(part_data),.part_addr(part_addr));
 always @(posedge clk)begin
  if(!rst_n)begin wactive<=0;auxvalid<=0;end
  else begin
   cycles<=cycles+1;
   if(weight_request_valid && !wactive)begin wactive<=1;wtag<=weight_request_tag ^ ((phase==3) ? 64'd1 : 64'd0);wi<=0;wn<=weight_request_words;wbase<=weight_request_address;
    if(weight_request_address+weight_request_words>80)$fatal(1,"weight address out of bounds");end
   if(wactive && weight_response_ready)begin fills<=fills+1;if(wi==wn-1)wactive<=0;else wi<=wi+1'b1;end
   if(auxiliary_request_valid && !auxvalid)begin auxvalid<=1;agen<=auxiliary_request_generation;aw<=auxiliary_request_w;adata<=activation_image[auxiliary_request_a];
    if(auxiliary_request_a>=80 || auxiliary_request_w>=80)$fatal(1,"auxiliary address out of bounds");end
   if(auxvalid && auxiliary_response_ready)auxvalid<=0;
   if(runtime_transport_cancel)begin wactive<=0;auxvalid<=0;end
   if(kick)seen<=0;
   else if(|part_we)begin
    if(|(seen & part_we))$fatal(1,"duplicate output");
    seen<=seen | part_we;outputs<=outputs+$countones(part_we);
   end
   for(integer i=0;i<8;i=i+1)if(part_we[i])begin
    // LQ8 exports lane-local addresses; logical column = local * 8 + lane.
    if(part_addr[32*i+:32]!=0)$fatal(1,"wrong output address");
    if(phase!=1 || part_data[32*i+:32]!=expected[i])$fatal(1,"wrong result or write after abort");

   end
   if(host_write_refused)$fatal(1,"host write refused");
   if(trapped && phase==1 && !kick)$fatal(1,"unexpected sequencer trap class=%0d issued=%0d adapter_state=%0d depth=%0d dims=%0d,%0d",trap_class,count_issued,dut.issue_adapter.state,dut.arr_depth,dut.issue_adapter.d_dim0,dut.issue_adapter.d_dim1);
   if(array_done && (!runtime_transport_ack || !runtime_writes_drained))$fatal(1,"early completion");
  end
 end
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task launch;begin kick=1;tick();kick=0;end endtask
 task drain(input [7:0] err);begin
  wait(runtime_transport_cancel);@(negedge clk);
  repeat(4)begin tick();if(array_done || !array_busy)$fatal(1,"lost operation during drain");end
  runtime_transport_ack=1;tick();repeat(3)tick();if(array_done)$fatal(1,"write ack bypassed");
  runtime_writes_drained=1;wait(array_done);@(negedge clk);
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
  host_we=0;tick();tick();phase=1;launch();drain(0);
  // Lane-distinct BF16 results must match the functional Device.
  if(seen!=8'hff || outputs!=8)$fatal(1,"missing first outputs");
  if(fills<80)$fatal(1,"multi-tile refill not exercised");
  phase=2;launch();wait(dut.operand_issue);@(negedge clk);runtime_abort=1;tick();runtime_abort=0;drain(8'hff);
  if(seen!=0 || outputs!=8)$fatal(1,"aborted operation wrote output");
  phase=1;launch();drain(0);
  if(seen!=8'hff || outputs!=16)$fatal(1,"missing restart outputs");
  if(runtime_generation!=3)$fatal(1,"generation restart");
  // A bad transport identity must become an ENGINE trap through the same ABI.
  phase=3;launch();drain(8'hfe);
  if(seen!=0 || outputs!=16)$fatal(1,"transport fault wrote output");
  phase=1;launch();drain(0);
  if(seen!=8'hff || outputs!=24 || runtime_generation!=5)$fatal(1,"transport fault recovery");
  $display("PASS G2 runtime program multi-tile arithmetic, abort, transport fault, drain and restart fills=%0d",fills);$finish;
 end
 initial begin #2000000;$fatal(1,"timeout");end
endmodule
