`timescale 1ns/1ps
// Exercise the actual G2 runtime generate branch at its adapter->array boundary.
// Descriptor/program dispatch is bypassed by forced adapter outputs; this is
// deliberately not an end-to-end program qualification.
module tb_a3_g2_runtime_boundary;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,kick=0,runtime_abort=0,runtime_transport_ack=0,runtime_writes_drained=0;
 wire runtime_transport_cancel,array_busy,array_done;
 wire [31:0] runtime_generation;
 wire [7:0] array_error_code;
 wire [7:0] part_we;wire [255:0] part_data;
 wire weight_request_valid,weight_response_ready,auxiliary_request_valid,auxiliary_response_ready;
 wire [63:0] weight_request_tag;
 wire [31:0] weight_request_address,auxiliary_request_generation,auxiliary_request_w;
 wire [9:0] weight_request_words;
 reg wactive=0,auxvalid=0;
 reg [63:0] wtag=0;reg [9:0] wi=0,wn=0;
 reg [31:0] agen=0,aw=0;
 integer outputs=0,fills=0,cycles=0,phase=0;
 reg [7:0] seen=0;
 ot_a3_g2_cluster #(.RUNTIME_OPERANDS(1)) dut(
 .clk(clk),.rst_n(rst_n),.part_ready(1'b1),.start(1'b0),.host_we(1'b0),
 .runtime_abort(runtime_abort),.runtime_transport_ack(runtime_transport_ack),.runtime_writes_drained(runtime_writes_drained),
 .runtime_transport_cancel(runtime_transport_cancel),.runtime_generation(runtime_generation),
 .weight_request_valid(weight_request_valid),.weight_request_ready(!wactive),.weight_request_tag(weight_request_tag),
 .weight_request_address(weight_request_address),.weight_request_words(weight_request_words),
 .weight_response_valid(wactive),.weight_response_ready(weight_response_ready),
 .weight_response_tag(wtag),.weight_response_index(wi),.weight_response_data({8{16'h3f80}}),
 .auxiliary_request_valid(auxiliary_request_valid),.auxiliary_request_ready(!auxvalid),
 .auxiliary_request_generation(auxiliary_request_generation),.auxiliary_request_w(auxiliary_request_w),
 .auxiliary_response_valid(auxvalid),.auxiliary_response_ready(auxiliary_response_ready),
 .auxiliary_response_generation(agen),.auxiliary_response_w(aw),
 .auxiliary_response_a_data(64'h3f80),.auxiliary_response_s_data(32'b0),.auxiliary_response_ws_data(64'b0),
 .array_busy(array_busy),.array_done(array_done),.array_error_code(array_error_code),.part_we(part_we),.part_data(part_data));
 always @(posedge clk)begin
  if(!rst_n)begin wactive<=0;auxvalid<=0;end
  else begin
   cycles<=cycles+1;
   if(weight_request_valid && !wactive)begin wactive<=1;wtag<=weight_request_tag;wi<=0;wn<=weight_request_words;end
   if(wactive && weight_response_ready)begin fills<=fills+1;if(wi==wn-1)wactive<=0;else wi<=wi+1'b1;end
   if(auxiliary_request_valid && !auxvalid)begin auxvalid<=1;agen<=auxiliary_request_generation;aw<=auxiliary_request_w;end
   if(auxvalid && auxiliary_response_ready)auxvalid<=0;
   if(runtime_transport_cancel)begin wactive<=0;auxvalid<=0;end
   if(kick)seen<=0;
   else if(|part_we)begin
    if(|(seen & part_we))$fatal(1,"duplicate output");
    seen<=seen | part_we;outputs<=outputs+$countones(part_we);
   end
   for(integer i=0;i<8;i=i+1)if(part_we[i])begin
    if(phase!=1 || part_data[32*i+:32]!=32'h42a00000)$fatal(1,"wrong result or write after abort");

   end
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
  tick();runtime_transport_ack=0;runtime_writes_drained=0;tick();
 end endtask
 initial begin
  force dut.arr_start=kick;
  force dut.arr_rows=16'd1;force dut.arr_cols=16'd8;force dut.arr_depth=16'd80;
  force dut.arr_dtype_a=8'd16;force dut.arr_dtype_b=8'd16;force dut.arr_group=8'd1;
  force dut.arr_a_base=0;force dut.arr_scale_a=0;force dut.arr_scale_b=0;
  force dut.arr_block_a=0;force dut.arr_block_b=0;force dut.arr_block_rows_a=0;
  force dut.arr_scale_a_base=0;force dut.arr_w_base=0;force dut.arr_ws_base=0;
  force dut.arr_out_base=0;force dut.arr_out_fp32=1;
  tick();rst_n=1;tick();phase=1;launch();drain(0);
  // Each output lane produces 80 * 1.0. Count writes via mask separately.
  if(seen!=8'hff || outputs!=8)$fatal(1,"missing first outputs");
  if(fills<80)$fatal(1,"multi-tile refill not exercised");
  phase=2;launch();wait(dut.operand_issue);@(negedge clk);runtime_abort=1;tick();runtime_abort=0;drain(8'hff);
  if(seen!=0 || outputs!=8)$fatal(1,"aborted operation wrote output");
  phase=1;launch();drain(0);
  if(seen!=8'hff || outputs!=16)$fatal(1,"missing restart outputs");
  if(runtime_generation!=3)$fatal(1,"generation restart");
  $display("PASS G2 runtime boundary multi-tile arithmetic, abort, drain and restart fills=%0d",fills);$finish;
 end
 initial begin #200000;$fatal(1,"timeout");end
endmodule
