`timescale 1ns/1ps
// Minimum real full N256/M64 component. Host memory is a bounded oracle for
// actual337/273 transactions; quarter completion comes only from real c12 RTL.
module tb_qwen_r25_su_quarter_service;
 reg clk=0;always #0.555556 clk=~clk;
 reg rst_n=0,warm_abort=0,cmd_v=0;wire cmd_rdy;
 reg [689:0] cmd_word;reg [72:0] cmd_owner=73'h1a3123456789abcdef0;
 reg [11:0] cmd_pc=0;reg [1:0] cmd_query=0;
 wire done_v;wire [72:0] done_owner;wire [11:0] done_pc;wire [1:0] done_query;
 wire req_v;wire req_rdy;wire [336:0] req;
 reg rsp_v=0;wire rsp_rdy;reg [272:0] rsp=0;
 wire fault;wire [31:0] virtual_edges,reads,writes,visibility_reads;
 ot_qwen_r25_su_quarter #(.ENABLE(1),.N(256),.M(64),.QID(0)) dut(.*);
 reg [31:0] vm[0:262143];reg [689:0] program_words[0:4095];
 reg [41:0] metadata[0:4095];reg [63:0] expected[0:262143];
 string program_file,meta_file,vm_file,expected_prefix,expected_file;
 integer start_pc=0,nops=4,queries=1,position=8191,nchecks=1024,stall=0,negative=0;
 integer i,j,p,q,byte_index,word_index,delay_count=0,checks=0,transactions=0;
 reg pending=0;reg [272:0] held_response;reg [255:0] sector;
 reg [31:0] address,mask;reg write_request;reg [20:0] valid_length,available;
 reg [15:0] clipped;reg [275:0] last_held;
 assign req_rdy=!pending&&!rsp_v&&(delay_count==0);
 always @(posedge clk)if(rst_n)begin
  if(rsp_v&&rsp_rdy)rsp_v<=0;
  if(pending)begin
   if(delay_count>0)delay_count<=delay_count-1;
   else begin rsp<=held_response;rsp_v<=1;pending<=0;end
  end
  if(req_v&&req_rdy)begin
   address=req[335:304];mask=req[47:16];write_request=req[336];sector=0;
   if(address[4:0]!=0||address>=32'h100000)$fatal(1,"VM sector bounds");
   if(req[15:14]!=0)$fatal(1,"quarter tag lost");
   for(j=0;j<32;j=j+1)begin
    word_index=(address+j)/4;byte_index=(address+j)%4;
    if(write_request&&mask[j])begin
     if(word_index==262143)$fatal(1,"CONST0 overwritten");
     vm[word_index][byte_index*8+:8]=req[48+j*8+:8];
    end
   end
   for(j=0;j<8;j=j+1)sector[j*32+:32]=vm[address/4+j];
   held_response={req[15:0]^(negative==1?16'h0001:16'h0000),write_request,sector};
   pending<=1;delay_count<=stall;transactions=transactions+1;
  end
 end
 task check_result(input integer query_index);
  begin
   expected_file=$sformatf("%s%0d.hex",expected_prefix,query_index);
   $readmemh(expected_file,expected,0,nchecks-1);
   for(i=0;i<nchecks;i=i+1)begin
    if(expected[i][63:32]>=262143)$fatal(1,"reference bounds");
    if(vm[expected[i][63:32]]!==expected[i][31:0])
     $fatal(1,"bitexact mismatch q%0d address%0d got%h expected%h",query_index,expected[i][63:32],vm[expected[i][63:32]],expected[i][31:0]);
    checks=checks+1;
   end
  end
 endtask
 initial begin
  if(!$value$plusargs("PROGRAM=%s",program_file)||!$value$plusargs("META=%s",meta_file)||
     !$value$plusargs("VM=%s",vm_file)||!$value$plusargs("EXPECTED=%s",expected_prefix))$fatal(1,"fixture paths required");
  $value$plusargs("START=%d",start_pc);$value$plusargs("NOPS=%d",nops);
  $value$plusargs("QUERIES=%d",queries);$value$plusargs("POSITION=%d",position);
  $value$plusargs("NCHECK=%d",nchecks);$value$plusargs("STALL=%d",stall);$value$plusargs("NEGATIVE=%d",negative);
  if(!(queries==1||queries==4)||position+queries>8224||start_pc+nops>4096||nops<1)$fatal(1,"fixture shape");
  for(i=0;i<262144;i=i+1)vm[i]=0;
  $readmemh(vm_file,vm);$readmemh(program_file,program_words);$readmemh(meta_file,metadata);
  if(vm[262143]!==0)$fatal(1,"CONST0 fixture not zero");
  repeat(3)@(negedge clk);rst_n=1;
  for(q=0;q<queries;q=q+1)begin
   cmd_query=q;valid_length=position+q+1;
   for(p=start_pc;p<start_pc+nops;p=p+1)begin
    if(!metadata[p][41])$fatal(1,"invalid program metadata");
    if(metadata[p][37])begin
     cmd_word=program_words[p];cmd_pc=p;
     if(metadata[p][36])begin
      available=valid_length>metadata[p][35:16]?valid_length-metadata[p][35:16]:0;
      clipped=available<metadata[p][15:0]?available[15:0]:metadata[p][15:0];
      cmd_word[31:16]=clipped;
     end else clipped=cmd_word[31:16];
     if(clipped!=0)begin
      wait(cmd_rdy);@(negedge clk);cmd_v=1;@(negedge clk);cmd_v=0;
      if(negative==1)begin
       wait(rsp_v);repeat(8)begin @(negedge clk);if(rsp_rdy||done_v)$fatal(1,"foreign service reply consumed");end
       warm_abort=1;@(negedge clk);if(!fault)$fatal(1,"warm abort did not fence");
       $display("PASS_QWEN_NATIVE_QUARTER_FOREIGN_REPLY_FENCE");$finish;
      end
      wait(done_v||fault);if(fault)$fatal(1,"actual quarter fault PC%0d",p);
      if(done_owner!==cmd_owner||done_pc!==cmd_pc||done_query!==cmd_query)$fatal(1,"completion identity");
      @(negedge clk);
     end
    end
   end
   check_result(q);
  end
  if(reads==0||writes==0||visibility_reads!=writes||transactions!=reads+writes+visibility_reads)
   $fatal(1,"actual memory mechanism vacuous or visibility count wrong");
  $display("PASS_QWEN_NATIVE_QUARTER_REAL_FP N256 M64 queries%0d checks%0d virtual_edges%0d reads%0d writes%0d visibility_reads%0d transactions%0d stall%0d",queries,checks,virtual_edges,reads,writes,visibility_reads,transactions,stall);
  $finish;
 end
endmodule
