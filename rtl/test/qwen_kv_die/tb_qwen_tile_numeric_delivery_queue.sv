`timescale 1ns/1ps
module tb_qwen_tile_numeric_delivery_queue;
 reg source_clk=0,sink_clk=0,rst_n=0;
 always #5 source_clk=~source_clk;
 always #7 sink_clk=~sink_clk;
 reg output_step=0,numeric_v=0,sink_ready=0;
 reg [511:0] numeric_d=0;
 reg [15:0] numeric_context=0;
 reg [31:0] numeric_version=0;
 reg numeric_has_query=0;
 reg [39:0] numeric_query_seq=0;
 wire output_credit,sink_valid,sink_has_query,overflow_fault;
 wire [511:0] sink_data;wire [15:0] sink_context;
 wire [31:0] sink_version;wire [39:0] sink_query_seq;
 ot_qwen_tile_numeric_delivery_queue dut(.*);
 integer sent=0,received=0,query_received=0,paused=0;
 reg [600:0] expected[0:255];reg [600:0] held;reg was_held=0;
 always @(posedge sink_clk)if(rst_n)begin
  if(was_held&&{sink_context,sink_version,sink_has_query,sink_query_seq,sink_data}!==held)$fatal(1,"held payload changed");
  was_held<=sink_valid&&!sink_ready;
  held<={sink_context,sink_version,sink_has_query,sink_query_seq,sink_data};
  if(sink_valid&&sink_ready)begin
   if(received>=sent||{sink_context,sink_version,sink_has_query,sink_query_seq,sink_data}!==expected[received])$fatal(1,"wrong output %0d",received);
   if(sink_has_query)query_received=query_received+1;
   received=received+1;
  end
 end
 integer tick;
 initial begin
  #23 rst_n=1;
  for(tick=0;tick<1100;tick=tick+1)begin
   @(negedge source_clk);
   sink_ready=(tick>=35)&&(tick%19<12);
   output_step=output_credit&&(sent<160);
   numeric_v=output_step&&(tick%5!=3);
   if(!output_credit)paused=paused+1;
   if(numeric_v)begin
    numeric_context=16'h1200+sent/11;numeric_version=32'habcdef00+sent/11;
    numeric_has_query=(sent%3!=1);numeric_query_seq=40'hab00000000+sent;
    numeric_d={16{32'hface0000+sent}};
    expected[sent]={numeric_context,numeric_version,numeric_has_query,numeric_query_seq,numeric_d};
    sent=sent+1;
   end
  end
  output_step=0;numeric_v=0;sink_ready=1;
  repeat(15)@(negedge source_clk);
  if(overflow_fault||received!=160||query_received!=107||paused<10)$fatal(1,"counts sent%0d received%0d query%0d pauses%0d fault%b",sent,received,query_received,paused,overflow_fault);
  $display("PASS all160 numeric words,107 query words,53 non-query words; live full recovery, stalls and exact payloads");$finish;
 end
 initial begin #20000;$fatal(1,"timeout");end
endmodule
