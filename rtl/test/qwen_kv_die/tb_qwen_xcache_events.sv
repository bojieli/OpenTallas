`timescale 1ns/1ps
module tb_qwen_xcache_events;
 reg load_clk=0,core_clk=0,rst_n=0,clear=0,load_v=0,load_j_repeat=1,read_j_repeat=1;
 reg [20:0] load_epoch=21'd8,read_epoch=21'd8;
 reg [15:0] load_context=16'h1234,read_context=16'h1234,load_token=16'h5678,load_recipient=16'd703;
 reg [31:0] load_version=32'h89abcdef,read_version=32'h89abcdef;
 reg [95:0] load_addr=96'h0123456789abcdefdeadbeef,read_addr=96'h0123456789abcdefdeadbeef;
 reg [127:0] load_x=128'hfedcba98765432100123456789abcdef;
 reg [4:0] load_root=5'd31;reg [3:0] load_phase=4'd3;
 reg [3:0] read_v=0;
 reg fill_ack_toggle=0,response_ack_toggle=0;
 wire load_ready,read_credit,hit,fill_toggle,response_toggle,fault;
 wire [206:0] fill_tuple,response_tuple;wire [127:0] q_x;
 ot_qwen_xcache_context32_events dut(.*);
 reg [206:0] expected_tuple,saved_tuple;reg ft,rt;integer paused;
 task load_edge;begin #2;load_clk=1;#2;load_clk=0;#2;end endtask
 task core_edge;begin #2;core_clk=1;#2;core_clk=0;#2;end endtask
 task fail(input [255:0] message);begin $display("FAIL %s",message);$fatal(1);end endtask
 initial begin
  #1;rst_n=1;#1;rst_n=0;#1;rst_n=1;
  expected_tuple={load_context,load_version,load_j_repeat,load_epoch,load_addr,load_token,load_root,load_phase,load_recipient};
  load_v=1;load_edge();load_v=0;
  if(fill_toggle!==1||load_ready!==0||fill_tuple!==expected_tuple)fail("first fill provenance");
  saved_tuple=fill_tuple;load_x=128'h1111;load_token=16'hffff;load_v=1;
  repeat(23)begin load_edge();if(fill_toggle!==1||fill_tuple!==saved_tuple)fail("held fill duplicated");end
  load_v=0;read_v=4'b1111;core_edge();
  if(response_toggle!==1||response_tuple!==expected_tuple||q_x!==128'hfedcba98765432100123456789abcdef||fault)fail("response provenance/data");
  saved_tuple=response_tuple;rt=response_toggle;
  // Core entirely paused while loader is live. Clear retains durable event.
  clear=1;load_edge();clear=0;
  repeat(40)begin load_edge();if(response_toggle!==rt||response_tuple!==saved_tuple)fail("paused event changed");end
  if(hit!==0)fail("clear did not invalidate");
  fill_ack_toggle=fill_toggle;#1;
  if(!load_ready)fail("fill ack no credit");
  load_token=16'h7654;load_x=128'h2222;load_v=1;load_edge();load_v=0;
  if(fill_toggle!==0||load_ready)fail("second fill toggle");
  response_ack_toggle=response_toggle;#1;if(!read_credit)fail("response ack no credit");
  core_edge();
  expected_tuple={load_context,load_version,load_j_repeat,load_epoch,load_addr,load_token,load_root,load_phase,load_recipient};
  if(response_toggle!==0||response_tuple!==expected_tuple||q_x!==128'h2222)fail("second response provenance");
  // Guard old VM/version and mode: a resident row cannot serve a new context.
  response_ack_toggle=response_toggle;read_context=16'h9999;#1;
  if(hit)fail("resident context not guarded");
  core_edge();if(!fault||response_toggle!==0||q_x!==0)fail("miss false capture");
  read_v=0;clear=1;load_edge();clear=0;core_edge();if(!fault)fail("clear erased sticky fault");
  // External ack reset is part of the shared reset contract.
  rst_n=0;fill_ack_toggle=0;response_ack_toggle=0;#2;
  if(fill_toggle!==0||response_toggle!==0||fault||q_x!==0)fail("reset event roots");
  $display("PASS acknowledged fill/response provenance; 23 blocked writes;40 live-loader paused edges;clear/miss/context/reset");$finish;
 end
endmodule
