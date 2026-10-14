`timescale 1ns/1ps
module tb_qwen_tile_numeric_output_metadata;
 reg core_clk=0,rst_n=0,query_issue_v=0;
 reg [39:0] query_sequence=0;reg [15:0] query_context=0;reg [31:0] query_version=0;
 reg query_output_ack_toggle=0;
 wire [88:0] numeric_tuple;
 ot_qwen_tile_numeric_output_metadata dut(.*);
 wire [47:0] numeric_identity=numeric_tuple[87:40];
 reg [47:0] math_expected[0:109];
 integer i,issued=0,produced=0;
 integer due[0:3];reg [87:0] expected[0:3];reg old_toggle;reg [87:0] saved;
 task step;begin #2;core_clk=1;#2;core_clk=0;#2;end endtask
 initial begin
  #1;rst_n=1;#1;rst_n=0;#1;rst_n=1;repeat(16)step();
  old_toggle=0;
  for(i=0;i<110;i=i+1)begin
   step();
   if(i>=46&&numeric_identity!==math_expected[i-46])$fatal(1,"wrong allmath identity edge%0d",i);
   if(i>=46)begin
    if(produced<issued&&due[produced]==i)begin
     if(numeric_tuple!=={1'b1,expected[produced]})$fatal(1,"wrong query stream tuple at%0d",i);
     produced=produced+1;
    end else if(numeric_tuple[88]||numeric_tuple[39:0])$fatal(1,"unallocated math word became query");
    saved=numeric_tuple[87:0];#220;
    if(numeric_tuple[87:0]!==saved)$fatal(1,"paused posted stream tuple changed");
   end
   // Post-edge source allocations. Other math issues have NO queryallocation,
   // so their future numeric output must not fabricate a query receipt.
   query_issue_v=0;
   if(i==0||i==1||i==9||i==23)begin
    query_issue_v=1;query_context=16'h1111+i;query_version=32'habcdef00+i;
    query_sequence=40'h1000000000+i;
    due[issued]=i+46;expected[issued]={query_context,query_version,query_sequence};issued=issued+1;
   end else begin query_context=16'h2200+i;query_version=32'h55550000+i;query_sequence=40'hffffffffff;end
   math_expected[i]={query_context,query_version};
  end
  if(issued!=4||produced!=4)$fatal(1,"lost outputs");
  $display("PASS4 query and64 allmath actual-edge46 identities;220ns immediate pauses;rawunallocatedoutputs produce0 querycallbacks;no publication ACK or mailbox;postedtype preserved");$finish;
 end
endmodule
