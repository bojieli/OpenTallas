`timescale 1ns/1ps
module tb_hgi_sfu_static_operand_store;
 localparam LWB=15,WORDS=28672;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0;
 reg [3:0] scalar_load=0,scalar_enable=0;
 reg [95:0] scalar_addr=0;
 reg [127:0] scalar_data=0;
 reg [63:0] rd_re=0;
 reg [1535:0] rd_addr=0;
 wire [2047:0] rd_q;
 reg [15:0] vm_we=0;
 reg [383:0] vm_addr=0;
 reg [511:0] vm_data=0;
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
 ot_hgi_sfu_static_operand_store dut(.clk(clk),.rst_n(rst_n),.rd_re(rd_re),.rd_addr(rd_addr),.rd_src(128'd0),.rd_q(rd_q),
 .vm_we(vm_we),.vm_waddr(vm_addr),.vm_wdata(vm_data),.scalar_load(scalar_load),.scalar_enable(scalar_enable),.scalar_addr(scalar_addr),.scalar_data(scalar_data),.stage_v(stage_v),.stage_group(stage_group),
 .stage_addr(stage_addr),.stage_mask(64'hffffffffffffffff),.stage_data(stage_data),
 .drain_v(drain_v),.drain_addr(drain_addr),.drain_data(drain_data),.drain_result_v(drain_rv),.fault(fault));
 initial begin
  repeat(8)@(negedge clk);rst_n=1;
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
  for(integer beat=0;beat<WORDS/16;beat++)begin
   rd_re='1;vm_we='1;
   for(integer l=0;l<16;l++)begin
    vm_addr[24*l+:24]=24'(beat*16+l);vm_data[32*l+:32]=value(4,beat*16+l);
    for(integer g=0;g<4;g++)rd_addr[24*(4*l+g)+:24]=24'(((beat*16+l)^($test$plusargs("MUT_ADDR")?1:0))|($test$plusargs("MUT_RANGE")?(1<<LWB):0));
   end
   @(posedge clk);#0.001;
   if(fault)$fatal(1,"STORE_FAULT");
   for(integer l=0;l<16;l++)for(integer g=0;g<4;g++)begin
    if(rd_q[32*(4*l+g)+:32]!==value(g,beat*16+l))$fatal(1,"STORE_WORD beat=%0d lane=%0d group=%0d",beat,l,g);
    checks++;
   end
   @(negedge clk);
  end
  rd_re=0;vm_we=0;
  for(integer beat=0;beat<WORDS/16;beat++)begin
   drain_v=3;drain_addr={LWB'(beat*16+8),LWB'(beat*16)};
   @(posedge clk);#0.001;
   if(fault || drain_rv!=3)$fatal(1,"STORE_DRAIN_PHASE");
   for(integer j=0;j<16;j++)begin
    if(drain_data[j*32+:32]!==value(4,beat*16+j))$fatal(1,"STORE_DRAIN_WORD");checks++;
   end
   @(negedge clk);
  end
  drain_v=0;
  scalar_load=4'b0010;scalar_enable=4'b0010;
  scalar_addr[47:24]=24'd12672;scalar_data[63:32]=32'h3f200000;
  @(negedge clk);scalar_load=0;
  rd_re=0;
  for(integer l=0;l<16;l++)begin
   rd_re[4*l+1]=1;rd_addr[24*(4*l+1)+:24]=24'd12672+($test$plusargs("MUT_SCALAR_ADDR")?1:0);
  end
  @(posedge clk);#0.001;
  for(integer l=0;l<16;l++)if(rd_q[32*(4*l+1)+:32]!==32'h3f200000)$fatal(1,"SCALAR_WORD");
  @(negedge clk);rd_re=0;
  @(negedge clk);if(fault)$fatal(1,"SCALAR_IDENTITY");
  $display("PASS SFU actual80SRAM operand store shape4x%0d operand_checks=%0d read_words_per_edge=64 stage_sectors_per_edge=8 output_words_per_edge=16 memory_latency=1 scalar_broadcast=16 address_identity=exact",WORDS,checks);
  $finish;
 end
endmodule
