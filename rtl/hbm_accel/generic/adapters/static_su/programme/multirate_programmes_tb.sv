`timescale 1ps/1fs
// Native whole-SU source candidate: independent SRAM programme planes, actual
// 3:4 clocks and actual VM/LG. Physical epoch/skew and closure remain OPEN.
module tb_hbm_su_multirate_programmes;
 parameter integer NE=7116,PE=9489;
 localparam realtime HALF_Q=1250.0/9.0;
 reg serial_clk=0,stream_clk=0,rst_n=0,bridge_rst_n=0;
 integer half_tick=-1,epoch_half=-1;
 // Both clocks derive from the same exact integer event lattice. Half-q
 // rounding is common, preserving the ratio and coincident12q frame exactly.
 initial forever begin
  #(HALF_Q);half_tick=half_tick+1;
  serial_clk=(half_tick%8)<4;stream_clk=(half_tick%6)<3;
 end
 `include "serial/programme_params.svh"
 `include "stream/programme_params.svh"
 reg [279:0] serial_config[0:SERIAL_WRITES-1],stream_config[0:STREAM_WRITES-1];
 reg serial_cfg_we=0,stream_cfg_we=0,serial_start=0,stream_start=0;
 reg [15:0] serial_cfg_bank=0,stream_cfg_bank=0;
 reg [6:0] serial_cfg_row=0,stream_cfg_row=0;
 reg [255:0] serial_cfg_data=0,stream_cfg_data=0;
 wire serial_busy,serial_valid,serial_done,serial_fault,stream_busy,stream_valid,stream_done,stream_fault;
 wire [15:0] serial_edge,stream_edge;
 wire [9687:0] serial_command;wire [63:0] stream_command;
 ot_hbm_su_programme #(.LINE_BITS(9688),.COLS(SERIAL_COLS),.EDGES(NE),.DICT_BANKS(SERIAL_DICT_BANKS),.MACROS(SERIAL_MACROS)) serial_programme(
  .clk(serial_clk),.clk_macro({SERIAL_MACROS{serial_clk}}),.rst_n(rst_n),
  .cfg_we(serial_cfg_we),.cfg_bank(serial_cfg_bank),.cfg_row(serial_cfg_row),.cfg_data(serial_cfg_data),
  .start(serial_start),.length(16'(NE)),.busy(serial_busy),.valid(serial_valid),.done(serial_done),
  .fault(serial_fault),.edge_index(serial_edge),.command(serial_command));
 ot_hbm_su_programme #(.LINE_BITS(64),.COLS(STREAM_COLS),.INDEX_PACK(STREAM_INDEX_PACK),.EDGES(PE),.DICT_BANKS(STREAM_DICT_BANKS),.MACROS(STREAM_MACROS)) stream_programme(
  .clk(stream_clk),.clk_macro({STREAM_MACROS{stream_clk}}),.rst_n(rst_n),
  .cfg_we(stream_cfg_we),.cfg_bank(stream_cfg_bank),.cfg_row(stream_cfg_row),.cfg_data(stream_cfg_data),
  .start(stream_start),.length(16'(PE)),.busy(stream_busy),.valid(stream_valid),.done(stream_done),
  .fault(stream_fault),.edge_index(stream_edge),.command(stream_command));
 reg[9687:0]serial_expected[0:NE-1];reg[63:0]stream_expected[0:PE-1];
 bit mut_serial,mut_stream,mut_shift;
 integer scount=0,pcount=0;
 always @(posedge serial_clk)if(rst_n&&epoch_half>=0&&half_tick>=epoch_half)begin
  integer n;
  n=(half_tick-epoch_half)/8;
  if(n<NE)begin
   if(!serial_valid||serial_edge!==n||serial_command!==serial_expected[n]||serial_fault)
    $fatal(1,"SU_MULTIRATE_PROGRAMMES FAIL serial%0d index%0d valid%b",n,serial_edge,serial_valid);
   scount=scount+1;
  end else if(serial_valid||serial_busy||serial_command!='0)$fatal(1,"SU_MULTIRATE_PROGRAMMES FAIL serialtail");
 end
 always @(posedge stream_clk)if(rst_n&&epoch_half>=0&&half_tick>=epoch_half)begin
  integer p;
  p=(half_tick-epoch_half)/6;
  if(p<PE)begin
   if(!stream_valid||stream_edge!==p||stream_command!==stream_expected[p]||stream_fault)
    $fatal(1,"SU_MULTIRATE_PROGRAMMES FAIL stream%0d index%0d valid%b",p,stream_edge,stream_valid);
   pcount=pcount+1;
  end else if(stream_valid||stream_busy||stream_command!='0)$fatal(1,"SU_MULTIRATE_PROGRAMMES FAIL streamtail");
 end
 initial begin
  string dir;
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR required");
  mut_serial=$test$plusargs("MUT_SERIAL");mut_stream=$test$plusargs("MUT_STREAM");mut_shift=$test$plusargs("MUT_SHIFT");
  $readmemh({dir,"/serial/config.mem"},serial_config);$readmemh({dir,"/stream/config.mem"},stream_config);
  $readmemh({dir,"/serial/expected.mem"},serial_expected);$readmemh({dir,"/stream/expected.mem"},stream_expected);
  repeat(4)@(negedge serial_clk);rst_n=1;@(negedge serial_clk);
  for(integer i=0;i<SERIAL_WRITES;i=i+1)begin
   serial_cfg_we=1;serial_cfg_bank=serial_config[i][279:264];serial_cfg_row=serial_config[i][262:256];serial_cfg_data=serial_config[i][255:0];
   if(mut_serial&&i==0)serial_cfg_data=serial_cfg_data^256'b1;
   @(negedge serial_clk);
  end
  serial_cfg_we=0;@(negedge stream_clk);
  for(integer i=0;i<STREAM_WRITES;i=i+1)begin
   stream_cfg_we=1;stream_cfg_bank=stream_config[i][279:264];stream_cfg_row=stream_config[i][262:256];stream_cfg_data=stream_config[i][255:0];
   if(mut_stream&&i==0)stream_cfg_data=stream_cfg_data^256'b1;
   @(negedge stream_clk);
  end
  stream_cfg_we=0;epoch_half=24*((half_tick+95)/24);
  wait(half_tick==epoch_half-33);serial_start=1;wait(half_tick==epoch_half-31);serial_start=0;
  if(mut_shift)begin
   wait(half_tick==epoch_half-19);stream_start=1;wait(half_tick==epoch_half-17);stream_start=0;
  end else begin
   wait(half_tick==epoch_half-25);stream_start=1;wait(half_tick==epoch_half-23);stream_start=0;
  end
  wait(half_tick>=epoch_half+8*(NE+40));#2;
  if(scount!=NE||pcount!=PE)$fatal(1,"SU_MULTIRATE_PROGRAMMES FAIL counts%0d/%0d",scount,pcount);
  $display("SU_MULTIRATE_PROGRAMMES PASS serial%0d stream%0d SRAMs%0d startupserial4 startupstream4",scount,pcount,SERIAL_MACROS+STREAM_MACROS);$finish;
 end
endmodule
