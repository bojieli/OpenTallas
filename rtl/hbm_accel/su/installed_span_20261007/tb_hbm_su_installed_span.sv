`timescale 1ns/1ps
module tb_hbm_su_installed_span;
 reg clk=0;always #5 clk=~clk;
 reg por_n=0,warm_reset=0,transport_fault=0,bind_v=0;
 wire bind_r;reg [1:0] installed_checked=3;
 reg [72:0] bind_owner=73'h123456789abcdef;reg [15:0] bind_record=7,bind_tag=3;
 reg [4:0] bind_source=2;reg [23:0] logical_base=123;
 reg [12:0] rows=4096;reg [36:0] byte_base=37'h100000000,byte_limit=37'h100020000;
 reg publication_v=0;wire publication_r;reg [72:0] publication_owner;
 reg [15:0] publication_record;reg [4:0] publication_source;
 reg read_v=0;wire read_r;reg [23:0] read_word;reg [12:0] read_consumer;
 wire req_v;reg req_r=0;wire [36:0] req_addr;wire [15:0] req_tag,req_record;
 wire [72:0] req_owner;wire [4:0] req_source;
 reg rsp_v=0;wire rsp_r;reg rsp_we=0,rsp_error=0;reg [1:0] rsp_checked=3;
 reg [255:0] rsp_data;reg [15:0] rsp_tag,rsp_record;reg [72:0] rsp_owner;reg [4:0] rsp_source;
 wire result_v;reg result_r=0;wire [31:0] result_data;wire [12:0] result_consumer;
 reg release_v=0;wire release_r;reg [72:0] release_owner;reg [15:0] release_record;reg [4:0] release_source;
 wire retained,fault;
 ot_hbm_su_installed_span #(.ENABLE(1)) dut(.*);
 integer checks=0,reads=0,negatives=0;
 task tick;begin @(posedge clk);#1;end endtask
 task drive;begin @(negedge clk);end endtask
 task ck(input reg pass,input string why);begin checks=checks+1;if(!pass)$fatal(1,"SPAN %s",why);end endtask
 task reset;
 begin drive();por_n=0;bind_v=0;publication_v=0;read_v=0;req_r=0;rsp_v=0;result_r=0;release_v=0;warm_reset=0;transport_fault=0;
  rsp_we=0;rsp_error=0;rsp_checked=3;
  publication_owner=bind_owner;publication_record=bind_record;publication_source=bind_source;
  release_owner=bind_owner;release_record=bind_record;release_source=bind_source;
  repeat(2)tick();drive();por_n=1;tick();ck(!fault&&!retained,"cold reset");
 end endtask
 task bind_span;
 begin reset();drive();bind_v=1;#1;ck(bind_r,"checked span admitted");tick();drive();bind_v=0;tick();
  ck(retained&&!fault&&!read_r,"unpublished span cannot read");
 end endtask
 task publish;
 begin drive();publication_v=1;#1;ck(publication_r,"exact publication");tick();drive();publication_v=0;tick();end
 endtask
 task issue(input integer wordidx);
 begin drive();read_word=logical_base+wordidx;read_consumer=wordidx%8192;read_v=1;#1;ck(read_r,"bound read admitted");
 tick();drive();read_v=0;#1;ck(req_v&&req_addr==byte_base+(wordidx/8)*32,"full37bit sector address");
 ck(req_owner==bind_owner&&req_record==bind_record&&req_source==bind_source,"request identity");
 repeat(2)begin tick();ck(req_v&&!result_v,"request held under refusal");end
 drive();req_r=1;tick();drive();req_r=0;
 rsp_tag=req_tag;rsp_owner=req_owner;rsp_record=req_record;rsp_source=req_source;
 for(integer j=0;j<8;j=j+1)rsp_data[j*32+:32]=32'hcafe0000+wordidx*8+j;
 end endtask
 task answer(input integer wordidx);
 begin drive();rsp_v=1;#1;ck(rsp_r,"owned checked response");tick();drive();rsp_v=0;
 ck(result_v&&result_consumer==wordidx%8192&&result_data==32'hcafe0000+wordidx*8+(wordidx%8),"exact lane word and consumer");
 repeat(3)begin tick();ck(result_v&&!fault,"result held under consumer refusal");end
 drive();result_r=1;tick();drive();result_r=0;reads=reads+1;
 end endtask
 task quarantine;
 begin tick();ck(fault&&!result_v&&!req_v&&!read_r&&!release_r,"fail closed");
 drive();rsp_v=0;publication_v=0;read_v=0;warm_reset=0;
 repeat(3)begin tick();ck(fault&&retained,"fault persists with ownership retained");end negatives=negatives+1;end
 endtask
 initial begin
  bind_span();publish();
  for(integer k=0;k<16;k=k+1)begin issue(k);answer(k);end
  issue(32767);answer(32767);
  drive();release_v=1;#1;ck(release_r,"exact drained release");tick();drive();release_v=0;ck(!retained&&!fault,"released allocation");
  bind_span();publish();drive();
  for(integer k=0;k<8;k=k+1)dut.on.code[k]=dut.on.code[k]^72'd1;
  issue(17);answer(17);ck(!fault,"single-bit upsets corrected in all eight protected rows");
  bind_span();publish();drive();dut.on.code[2]=dut.on.code[2]^72'd3;quarantine();
  bind_span();drive();publication_owner=bind_owner^1;publication_v=1;quarantine();
  bind_span();publish();drive();read_word=logical_base-1;read_v=1;quarantine();
  bind_span();publish();drive();read_word=logical_base+32768;read_v=1;quarantine();
  bind_span();publish();issue(0);drive();rsp_tag=rsp_tag^1;rsp_v=1;quarantine();
  bind_span();publish();issue(0);drive();rsp_owner=rsp_owner^1;rsp_v=1;quarantine();
  bind_span();publish();issue(0);drive();rsp_checked=1;rsp_v=1;quarantine();
  bind_span();publish();issue(0);drive();warm_reset=1;quarantine();
  bind_span();publish();issue(0);drive();rsp_record=rsp_record^1;rsp_v=1;quarantine();
  bind_span();publish();issue(0);drive();rsp_source=rsp_source^1;rsp_v=1;quarantine();
  $display("PASS SPAN reads=%0d negatives=%0d checks=%0d",reads,negatives,checks);$finish;
 end
endmodule
