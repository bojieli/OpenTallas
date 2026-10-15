`timescale 1ps/1fs
module tb;
reg clk=0;always #512 clk=~clk;
wire[31:0]pc_clk={32{clk}};reg rst_n=0;
reg[31:0]k_v=0,k_we=0;wire[31:0]k_rdy,k_wr_done,kr_v;
reg[959:0]k_addr=0;reg[127:0]k_len={32{4'd4}};reg[543:0]k_tag=0;
reg[8191:0]k_wdata=0;reg[1023:0]k_wstrb='1;reg[31:0]kr_rdy=0;
wire[543:0]kr_tag;wire[127:0]kr_beat;wire[8191:0]kr_data;
wire[31:0]row_v,col_v,col_we;wire[95:0]row_op;wire[159:0]row_bank,col_bank,col_col;wire[607:0]row_row;
wire[8191:0]col_data;wire[1023:0]col_strb;wire[31:0]dram_rvalid;wire[8191:0]dram_rdata;wire fault;
ot_hbm_svc_native_sector_pipeline_stack dut(.*);
ot_hbm_svc_command_dram_pipeline_fixture dram(.*);
integer cyc=0,responses=0,requests=0,first_req=-1,last_rsp=0,max_reserved=0,max_pending=0,max_response=0;
reg[63:0]seen[0:31];reg[31:0]stalled=0;reg[8191:0]held_data;reg[543:0]held_tag;reg[127:0]held_beat;
function[29:0]sector(input integer pc,input integer j);reg[29:0]s;begin
 s=(30'd20736<<15)|((((j%4)>>2)^(20736>>2))&7)<<12|((j/4)<<7)|(((j%4)^20736)&3);
 s=s|((pc^((s>>7)&31)^((s>>12)&31))<<2);sector=s;
end endfunction
function[255:0]word(input integer pc,input integer j);begin word={8{32'hc0a50000 ^32'(pc*731)^32'(j*17)}};end endfunction
always @*begin
 for(integer p=0;p<32;p=p+1)
  kr_rdy[p]=!$test$plusargs("stalls") || (cyc>150 && (cyc+p)%7>=3);
end
always @(posedge clk)begin
 integer group_id,idx;
 cyc=cyc+1;
 if(rst_n)begin
  if(fault)$fatal(1,"native read pipeline fault at cycle%0d",cyc);
  for(integer p=0;p<32;p=p+1)begin
   if(k_v[p]&&k_rdy[p])begin requests=requests+1;if(first_req<0)first_req=cyc;end
   if(stalled[p]&&(!kr_v[p]||kr_data[p*256+:256]!==held_data[p*256+:256]||kr_tag[p*17+:17]!==held_tag[p*17+:17]||kr_beat[p*4+:4]!==held_beat[p*4+:4]))$fatal(1,"response changed under backpressure");
   stalled[p]<=kr_v[p]&&!kr_rdy[p];held_data[p*256+:256]<=kr_data[p*256+:256];held_tag[p*17+:17]<=kr_tag[p*17+:17];held_beat[p*4+:4]<=kr_beat[p*4+:4];
   if(kr_v[p]&&kr_rdy[p])begin
    group_id=kr_tag[p*17+:17]/32;idx=group_id*4+kr_beat[p*4+:4];
    if(group_id>=16||kr_tag[p*17+:17]%32!=p||kr_beat[p*4+:4]>=4||seen[p][idx]||kr_data[p*256+:256]!==word(p,idx))$fatal(1,"burst read identity/data p%0d tag%0d beat%0d",p,kr_tag[p*17+:17],kr_beat[p*4+:4]);
    seen[p][idx]=1;responses=responses+1;last_rsp=cyc;
   end
  end
  if(dut.g_pc[0].read_reserved>max_reserved)max_reserved=dut.g_pc[0].read_reserved;
  if(dut.g_pc[0].pending_count>max_pending)max_pending=dut.g_pc[0].pending_count;
  if(dut.g_pc[0].response_count>max_response)max_response=dut.g_pc[0].response_count;
 end
end
task tick;begin @(posedge clk);#1;end endtask
reg[31:0]pending;integer guard;
initial begin
 // Only the OFFCHIP DRAM image is initialized. Every returned on-chip byte
 // traverses native commands, the23-edge external pipeline and actual SRAM.
 for(integer p=0;p<32;p=p+1)begin
  seen[p]=0;for(integer j=0;j<64;j=j+1)dram.mem[sector(p,j)-32'h28800000]=word(p,j);
 end
 repeat(4)tick;@(negedge clk);rst_n=1;repeat(8)tick;
 for(integer g=0;g<16;g=g+1)begin
  @(negedge clk);
  for(integer p=0;p<32;p=p+1)begin k_addr[p*30+:30]=sector(p,g*4);k_tag[p*17+:17]=17'(g*32+p);end
  pending='1;k_v=pending;guard=0;
  while(pending!=0)begin @(posedge clk);pending=pending&~k_rdy;#1;@(negedge clk);k_v=pending;guard=guard+1;if(guard>2000)$fatal(1,"native burst admission timeout");end
 end
 guard=0;while(responses<2048)begin tick;guard=guard+1;if(guard>5000)$fatal(1,"native read pipeline completion timeout");end
 repeat(4)tick;
 if(requests!=512||dram.reads!=2048||dram.writes!=0||responses!=2048||max_reserved!=32||max_pending<16)$fatal(1,"native read pipeline coverage requests%0d reads%0d reserved%0d pending%0d",requests,dram.reads,max_reserved,max_pending);
 for(integer p=0;p<32;p=p+1)if(seen[p]!==64'hffffffffffffffff)$fatal(1,"native read sector omission");
 if($test$plusargs("stalls")&&max_response!=32)$fatal(1,"response SRAM capacity not reached");
 $display("NATIVE_READ_PIPELINE PASS native_RD2048 exact_burst_beats2048 requests512 actual_response_SRAMs32 RL23 first_request%0d last_response%0d elapsed_HBM_cycles%0d max_reserved%0d max_pending%0d max_response%0d stalls%0d",first_req,last_rsp,last_rsp-first_req,max_reserved,max_pending,max_response,$test$plusargs("stalls"));$finish;
end
initial begin #20000000;$fatal(1,"timeout");end
endmodule
