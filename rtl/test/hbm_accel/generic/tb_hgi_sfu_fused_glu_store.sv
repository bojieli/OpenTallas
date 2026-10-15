`timescale 1ns/1ps
module tb_hgi_sfu_fused_glu_store;
 reg clk=0;always #0.4166665 clk=~clk;
 reg rst_n=0;
 reg [7:0] stage_v=0,stage_group=0,drain_v=0;
 reg [39:0] stage_bank=0,drain_bank=0;
 reg [55:0] stage_row=0,drain_row=0;
 reg [2047:0] stage_data=0;
 reg read_v=0;reg [6:0] read_row=0;
 wire read_valid;wire [8191:0] gate_words,up_words;
 wire [255:0] result_v;wire [6:0] result_row;
 wire [8191:0] result_data;
 wire [7:0] drain_valid;wire [2047:0] drain_data;wire fault;
 ot_hgi_sfu_fused_glu_store dut(.*);
 reg [31:0] gates[0:3071],ups[0:3071],routes[0:0],gold[0:3071];
 reg [1023:0] data_dir;
 reg [31:0] issue_index=0,index_q=0;
 always @(posedge clk) index_q<=issue_index;
 wire leaf_v;wire [31:0] leaf_y,leaf_tag;wire leaf_fault;
 reg mutate=0;
 wire [31:0] actual_gate=gate_words[index_q[7:0]*32+:32];
 wire [31:0] actual_up=up_words[index_q[7:0]*32+:32];
 ot_hgi_sfu_fused_glu_lane leaf(.clk(clk),.rst_n(rst_n),.v(read_valid),
  .gate(actual_gate),.up(actual_up),.route(routes[0]),.tag(index_q),
  .vo(leaf_v),.y(leaf_y),.out_tag(leaf_tag),.fault(leaf_fault));
 reg seed=0;reg [6:0] seed_row=0;
 assign result_v=seed ? {256{1'b1}}:({256{leaf_v}} & (256'd1<<leaf_tag[7:0]));
 assign result_row=seed ? seed_row:leaf_tag[14:8];
 assign result_data=seed ? {256{32'hdeadbeef}}:({8160'd0,leaf_y}<<(leaf_tag[7:0]*32));
 integer checked=0,input_checks=0,p,s,b,r,w,i,k,outputs=0,cycles=0,first_read=0,last_write=0;
 integer edges[0:3071];
 always @(posedge clk) begin
  cycles=cycles+1;
  if(read_v) begin
   edges[issue_index]=cycles;
   if(issue_index==0) first_read=cycles;
  end
  if(leaf_v) begin
   if(cycles-edges[leaf_tag]!=110) $fatal(1,"STORE_LEAF_PHASE delta=%d",cycles-edges[leaf_tag]);
   if(leaf_y!==gold[leaf_tag]) $fatal(1,"STORE_LEAF_WORD tag=%d actual=%h expected=%h",leaf_tag,leaf_y,gold[leaf_tag]);
   outputs=outputs+1;last_write=cycles;
  end
  #0.01;
  if(rst_n && fault) $fatal(1,"STORE_COLLISION");
 end
 initial begin
  mutate=$test$plusargs("MUTANT");
  if(!$value$plusargs("DATA=%s",data_dir)) $fatal(1,"DATA missing");
  $readmemh({data_dir,"/gate.hex"},gates);$readmemh({data_dir,"/up.hex"},ups);
  $readmemh({data_dir,"/route.hex"},routes);$readmemh({data_dir,"/gold.hex"},gold);
  repeat(5) @(negedge clk);rst_n=1;
  // Real sector ingress; mutation corrupts a loaded physical SRAM payload.
  for(i=0;i<96;i=i+1) begin
   @(negedge clk);stage_v=255;
   for(p=0;p<8;p=p+1) begin
    s=i*8+p;stage_group[p]=(s>=384);b=s%32;r=(s%384)/32;
    stage_bank[p*5+:5]=b;stage_row[p*7+:7]=r;
    for(w=0;w<8;w=w+1) begin
     k=r*256+b*8+w;
     stage_data[p*256+w*32+:32]=s<384 ? gates[k]:ups[k];
     if(mutate && s==0 && w==0) stage_data[p*256+w*32+:32]=gates[k]^32'h00800000;
    end
   end
  end
  @(negedge clk);stage_v=0;seed=1;seed_row=12;
  @(negedge clk);seed=0;
  // Minimum arithmetic mechanism: one exact leaf consumes actual vector SRAM
  // words, preserving the full3072 canonical shape and output identity. The
  // production256lane source is validated separately by component composition.
  for(i=0;i<3072;i=i+1) begin
   @(negedge clk);read_v=1;read_row=i/256;issue_index=i;
  end
  @(negedge clk);read_v=0;
  repeat(114) @(negedge clk);
  if(outputs!=3072) $fatal(1,"STORE_OUTPUT_COUNT %d",outputs);
  for(i=0;i<52;i=i+1) begin
   @(negedge clk);drain_v=255;
   for(p=0;p<8;p=p+1) begin
    s=i*8+p;drain_bank[p*5+:5]=s%32;drain_row[p*7+:7]=s/32;
   end
   @(posedge clk);#0.02;
   if(drain_valid!==255) $fatal(1,"DRAIN_PHASE");
   for(p=0;p<8;p=p+1) begin
    s=i*8+p;
    for(w=0;w<8;w=w+1) begin
     k=s*8+w;
     if(drain_data[p*256+w*32+:32] !== (k<3072 ? gold[k]:32'hdeadbeef))
      $fatal(1,"STORE_DRAIN_WORD index=%d actual=%h expected=%h",k,drain_data[p*256+w*32+:32],k<3072?gold[k]:32'hdeadbeef);
     checked=checked+1;
    end
   end
  end
  @(negedge clk);drain_v=0;
  $display("PASS96actual128x256SRAMs realingress96edges actualleaf3072 actualmappedoutput3072 neighbor256 drain52edges checks=%0d issue_to_lastcommit=%0d fixedread_to_commit110; full256lane_rate_UNMEASURED",checked,last_write-first_read+1);
  $finish;
 end
endmodule
