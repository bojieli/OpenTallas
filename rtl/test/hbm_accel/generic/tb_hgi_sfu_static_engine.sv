`timescale 1ns/1ps
module tb_hgi_sfu_static_engine;
 localparam LWB=15,WORDS=7168;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0;
 reg [1741:0] controls[0:501];
 reg [1741:0] compiler_control=0;
 reg [7:0] stage_v=0;
 reg [15:0] stage_group=0;
 reg [8*LWB-1:0] stage_addr=0;
 reg [2047:0] stage_data=0;
 reg [1:0] drain_v=0;
 reg [2*LWB-1:0] drain_addr=0;
 wire [511:0] drain_data;
 wire [1:0] drain_rv;
 wire fault;
 integer checks=0;
 function automatic [31:0] value(input integer g,a);value=32'h3e000000+32'(100000*g+a*7);endfunction
 ot_hgi_sfu_static_engine dut(.clk(clk),.rst_n(rst_n),.clk_lane({16{clk}}),.clk_map({16{clk}}),
 .rst_lane_n({16{rst_n}}),.rst_map_n({16{rst_n}}),.compiler_control(compiler_control),
 .vi_q(512'd0),.side_y(512'd0),
 .scalar_load(4'd0),.scalar_enable(4'd0),.scalar_addr(96'd0),.scalar_data(128'd0),.stage_v(stage_v),.stage_group(stage_group),.stage_addr(stage_addr),.stage_mask(64'hffffffffffffffff),.stage_data(stage_data),
 .drain_v(drain_v),.drain_addr(drain_addr),.drain_data(drain_data),.drain_result_v(drain_rv),.fault(fault));
 initial begin
  $readmemh(`SFU_IMAGE,controls);
  repeat(16)@(negedge clk);rst_n=1;
  for(integer beat=0;beat<WORDS/16;beat++)begin
   stage_v=8'hff;
   for(integer s=0;s<8;s++)begin
    stage_group[2*s+:2]=2'(s/2);
    stage_addr[LWB*s+:LWB]=LWB'(beat*16+(s%2)*8);
    for(integer w=0;w<8;w++)stage_data[256*s+32*w+:32]=value(s/2,beat*16+(s%2)*8+w);
   end
   @(negedge clk);
  end
  stage_v=0;
  for(integer t=0;t<502;t++)begin
   compiler_control=controls[t];
   if($test$plusargs("MUT_DROP") && t==8)compiler_control=0;
   @(negedge clk);
   if(fault)$fatal(1,"ENGINE_FAULT edge=%0d",t);
  end
  compiler_control=controls[501];
  for(integer beat=0;beat<WORDS/16;beat++)begin
   drain_v=3;drain_addr={LWB'(beat*16+8),LWB'(beat*16)};
   @(posedge clk);#0.001;
   if(fault || drain_rv!=3)$fatal(1,"ENGINE_DRAIN_PHASE");
   for(integer j=0;j<16;j++)begin
    if(drain_data[j*32+:32]!==value(0,beat*16+j))$fatal(1,"ENGINE_WORD beat=%0d lane=%0d actual=%h expected=%h",beat,j,drain_data[j*32+:32],value(0,beat*16+j));checks++;
   end
   @(negedge clk);
  end
  $display("PASS SFU static composition 16 actual C12 lanes 80 actual SRAMs independent Python calendar words=%0d exact_checks=%0d preload_edges=448 compiler_edges=502 drain_edges=448",WORDS,checks);
  $finish;
 end
endmodule
