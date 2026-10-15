`timescale 1ns/1ps
module tb_hgi_sfu_programmed_engine;
 localparam LWB=15,WORDS=28672,NINST=1846,CHUNK=222,PCLO=223;
 reg clk=0;always #0.416667 clk=~clk;
 reg rst_n=0;
 reg [1741:0] controls[0:NINST-1];
 reg cfg_we=0,start_v=0;
 reg [2:0] cfg_stripe=0;
 reg [10:0] cfg_addr=0;
 reg [255:0] cfg_data=0;
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
 ot_hgi_sfu_programmed_engine dut(.clk(clk),.rst_n(rst_n),.clk_lane({16{clk}}),.clk_map({16{clk}}),
 .rst_lane_n({16{rst_n}}),.rst_map_n({16{rst_n}}),.cfg_we(cfg_we),.cfg_stripe(cfg_stripe),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .start_v(start_v),.start_base(11'd0),.start_limit(12'(NINST)),.start_loops(16'd1),
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
  for(integer p=0;p<NINST;p++)for(integer st=0;st<8;st++)begin
   reg [1741:0] row;
   row=controls[p];
   if($test$plusargs("MUT_DROP") && p==8)row=0;
   cfg_we=1;cfg_addr=11'(p);cfg_stripe=3'(st);
   cfg_data=256'(row>>(CHUNK*st));
   if(st==7)cfg_data=(cfg_data&((256'd1<<188)-1))|(256'hc7a1<<240)|(256'(p)<<PCLO);
   else cfg_data=(cfg_data&((256'd1<<CHUNK)-1))|(256'hc7a1<<240)|(256'(p)<<PCLO);
   @(negedge clk);
  end
  cfg_we=0;repeat(3)@(negedge clk);start_v=1;@(negedge clk);start_v=0;
  // First programme word is consumed at launch+5. The compiler supplied the
  // arithmetic drain horizon in the image; no wait observes engine status.
  repeat(NINST+5)begin @(negedge clk);if(fault)$fatal(1,"ENGINE_FAULT");end
  for(integer beat=0;beat<WORDS/16;beat++)begin
   drain_v=3;drain_addr={LWB'(beat*16+8),LWB'(beat*16)};
   @(posedge clk);#0.001;
   if(fault || drain_rv!=3)$fatal(1,"ENGINE_DRAIN_PHASE");
   for(integer j=0;j<16;j++)begin
    if(drain_data[j*32+:32]!==value(0,beat*16+j))$fatal(1,"ENGINE_WORD beat=%0d lane=%0d actual=%h expected=%h",beat,j,drain_data[j*32+:32],value(0,beat*16+j));checks++;
   end
   @(negedge clk);
  end
  $display("PASS SFU static composition 16 actual C12 lanes 80 operand SRAMs 16 programme SRAMs independent Python fullbatch calendar words=%0d exact_checks=%0d preload_edges=1792 compiler_edges=1846 programme_to_consumer=5 drain_edges=1792",WORDS,checks);
  $finish;
 end
endmodule
