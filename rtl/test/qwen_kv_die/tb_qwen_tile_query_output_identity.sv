`timescale 1ns/1ps
module tb_qwen_tile_query_output_identity;
 reg core_clk=0,rst_n=0,query_issue_v=0;
 reg [39:0] query_sequence=0;reg [15:0] query_context=0;reg [31:0] query_version=0;
 reg query_output_ack_toggle=0;
 wire query_output_credit,query_output_toggle,fault;wire [87:0] query_output_tuple;
 ot_qwen_tile_query_output_identity dut(.*);
 integer i,issued=0,produced=0;
 integer due[0:3];reg [87:0] expected[0:3];reg old_toggle;reg [87:0] saved;
 task step;begin #2;core_clk=1;#2;core_clk=0;#2;end endtask
 initial begin
  #1;rst_n=1;#1;rst_n=0;#1;rst_n=1;repeat(16)step();
  old_toggle=0;
  for(i=0;i<110;i=i+1)begin
   step();
   if(produced<issued&&due[produced]==i)begin
    if(query_output_toggle===old_toggle||query_output_tuple!==expected[produced]||query_output_credit||fault)$fatal(1,"wrong actual producingedge/tag at%0d",i);
    old_toggle=query_output_toggle;saved=query_output_tuple;produced=produced+1;
    // Pause immediately on producing edge. No later CC is needed for event.
    #220;if(query_output_tuple!==saved||query_output_toggle!==old_toggle||query_output_credit)$fatal(1,"paused producedevent changed");
    query_output_ack_toggle=query_output_toggle;
   end else if(query_output_toggle!==old_toggle)$fatal(1,"fabricated/masked arithmetic retirement at%0d",i);
   // Post-edge source allocations. Other math issues have NO queryallocation,
   // so their future numeric output must not fabricate a query receipt.
   query_issue_v=0;
   if(i==0||i==1||i==9||i==23)begin
    query_issue_v=1;query_context=16'h1111+i;query_version=32'habcdef00+i;
    query_sequence=40'h1000000000+i;
    due[issued]=i+46;expected[issued]={query_context,query_version,query_sequence};issued=issued+1;
   end else begin query_context=16'hffff;query_version=0;query_sequence=40'hffffffffff;end
  end
  if(issued!=4||produced!=4||fault)$fatal(1,"lost outputs");
  $display("PASS4 actual-edge46 high40 identities;220ns immediate pauses;rawunallocatedoutputs produce0 querycallbacks;ACKstable");$finish;
 end
endmodule
