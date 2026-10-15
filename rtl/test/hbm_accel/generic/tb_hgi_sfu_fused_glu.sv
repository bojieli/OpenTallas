`timescale 1ns/1ps
module tb_hgi_sfu_fused_glu;
 reg clk=0;always #.4166665 clk=~clk;
 reg rst_n=0,v=0;
 reg [31:0] gate=0,up=0,route=0,tag=0;
 wire vo,mut_vo,fault,mut_fault;
 wire [31:0] y,mut_y,out_tag,mut_tag;
 ot_hgi_sfu_fused_glu_lane dut(.*);
 ot_hgi_sfu_fused_glu_lane #(.MUT_SECOND_MUL(1)) mutant(
  .clk(clk),.rst_n(rst_n),.v(v),.gate(gate),.up(up),.route(route),.tag(tag),
  .vo(mut_vo),.y(mut_y),.out_tag(mut_tag),.fault(mut_fault));
 reg [31:0] gates[0:3071],ups[0:3071],routes[0:0],gold[0:3071];
 integer edge_count=0,sent=0,checked=0,mut_diff=0,first_issue=-1,first_output=-1;
 integer issue_edge[0:3071];
 reg [1023:0] data_dir;
 always @(posedge clk) begin
  edge_count=edge_count+1;
  if(rst_n && v) begin
   issue_edge[tag]=edge_count;
   if(first_issue<0) first_issue=edge_count;
  end
  #.01;
  if(rst_n && vo) begin
   if(first_output<0) first_output=edge_count;
   if(out_tag!==checked) $fatal(1,"FUSED_TAG tag=%d expected=%d",out_tag,checked);
   if(edge_count-issue_edge[checked]!==108) $fatal(1,"FUSED_PHASE actual=%d expected=108",edge_count-issue_edge[checked]);
   if(y!==gold[checked]) $fatal(1,"FUSED_WORD word=%d actual=%h expected=%h",checked,y,gold[checked]);
   if(!mut_vo || mut_tag!==out_tag) $fatal(1,"MUTANT_PHASE");
   if(mut_y!==gold[checked]) mut_diff=mut_diff+1;
   checked=checked+1;
  end
 end
 initial begin
  if(!$value$plusargs("DATA=%s",data_dir)) $fatal(1,"DATA missing");
  $readmemh({data_dir,"/gate.hex"},gates);
  $readmemh({data_dir,"/up.hex"},ups);
  $readmemh({data_dir,"/route.hex"},routes);
  $readmemh({data_dir,"/gold.hex"},gold);
  repeat(5) @(negedge clk);rst_n=1;
  for(sent=0;sent<3072;sent=sent+1) begin
   @(negedge clk);v=1;gate=gates[sent];up=ups[sent];route=routes[0];tag=sent;
  end
  @(negedge clk);v=0;
  repeat(112) @(negedge clk);
  if(checked!=3072 || mut_diff==0) $fatal(1,"FUSED_COUNT checks=%d differences=%d",checked,mut_diff);
  $display("PASS exact frozen canonical GLU3072 LM5 LA4 II1 depth109 capture_delta108 first_issue=%0d first_output=%0d outputs=%0d actual_secondmul_mutant_differences=%0d resident256lane_composition120_ONLY_MODEL",first_issue,first_output,checked,mut_diff);
  $finish;
 end
endmodule
