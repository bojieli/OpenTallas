`timescale 1ps/1fs
`default_nettype none
// Immutable timing owner: unmodified actual PHY, all32 PC request ports issue
// independently, responses have no frontend restriction. Queue and DRAM
// scheduling are owned solely by the actual PHY model. This is not DUT RTL.
module tb_hbm_prefetch_burst_baseline;
 reg clk=0;always #512 clk=~clk;reg rst_n=0;
 reg active=0;reg [29:0] base;integer total;integer group_q[0:31];
 reg [31:0] k_v;wire [31:0] k_rdy;
 reg [959:0] k_addr;reg [127:0] k_len;reg [543:0] k_tag;
 wire [31:0] kr_v;wire [543:0] kr_tag;wire [127:0] kr_beat;wire [8191:0] kr_data;
 wire k_oor,w_oor;wire [63:0] refreshes;wire [31:0] w_reads;
 ot_chip_v41x_hbm3e_phy #(.K_AW(30),.KTAGW(17),.K_MEM(32768),.CLK_PS(1024)) u_phy(
 .clk(clk),.rst_n(rst_n),.k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),
 .k_we(32'b0),.k_wdata(8192'b0),.k_wstrb(1024'b0),.k_wr_done(),
 .kr_v(kr_v),.kr_rdy(32'hffffffff),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),
 .w_v(1'b0),.w_rdy(),.w_addr(24'b0),.w_len(6'b0),.w_tag(10'b0),.w_room(),
 .wr_v(),.wr_rdy(8'b0),.wr_tag(),.wr_beat(),.wr_data(),
 .k_oor(k_oor),.w_oor(w_oor),.refreshes(refreshes),.w_reads(w_reads));
 function automatic [255:0] pattern(input integer sector);
  integer j;begin for(j=0;j<8;j=j+1)pattern[j*32+:32]=32'h34129a07^(sector*32'h1021)^(j*32'h123abcd);end
 endfunction
 function automatic integer candidate(input integer group_i,input integer pc);
  candidate=((group_i<<5)|(pc^(group_i&31)^((group_i>>5)&31)))<<2;
 endfunction
 integer p,s,lo,hi;
 always @*begin
  k_v=0;k_addr=0;k_len=0;k_tag=0;
  for(p=0;p<32;p=p+1)begin
   s=candidate(group_q[p],p);lo=s<base?base:s;hi=s+4>base+total?base+total:s+4;
   if(active&&hi>lo)begin
    k_v[p]=1;k_addr[30*p+:30]=lo;k_len[4*p+:4]=hi-lo;k_tag[17*p+:17]=lo-base;
   end
  end
 end
 integer cycle=0,request_count=0,response_count=0,case_start,first_response,last_response;
 reg [2047:0] seen;
 always @(posedge clk)begin
  cycle=cycle+1;
  if(!rst_n)begin request_count=0;response_count=0;seen=0;first_response=0;last_response=0;end
  else if(active)begin
   if(k_oor||w_oor)$fatal(1,"actual PHY capacity fault");
   for(integer q=0;q<32;q=q+1)begin
    if(k_v[q]&&k_rdy[q])begin group_q[q]<=group_q[q]+1;request_count=request_count+1;end
    if(kr_v[q])begin:response
     integer ordinal;
     ordinal=kr_tag[17*q+:17]+kr_beat[4*q+:4];
     if(ordinal<0||ordinal>=total||seen[ordinal]||kr_data[256*q+:256]!==pattern(base+ordinal))$fatal(1,"baseline response mismatch/duplicate");
     if(response_count==0)first_response=cycle;
     seen[ordinal]=1;response_count=response_count+1;last_response=cycle;
    end
   end
  end
 end
 task measure(input integer block_base,input integer block_total);
  begin
   @(negedge clk);rst_n=0;active=0;repeat(8)@(negedge clk);
   base=block_base;total=block_total;
   for(integer q=0;q<32;q=q+1)begin
    group_q[q]=block_base>>7;
    if(candidate(group_q[q],q)+4<=block_base)group_q[q]=group_q[q]+1;
   end
   rst_n=1;repeat(4)@(negedge clk);
   // The actual PHY may initialize on the first positive reset-release edge.
   for(integer a=0;a<32768;a=a+1)u_phy.u_k.mem[a]=pattern(a);
   active=1;case_start=cycle;
   wait(response_count==total);@(negedge clk);active=0;
   for(integer a=0;a<total;a=a+1)if(!seen[a])$fatal(1,"missing baseline ordinal");
   if(first_response<=case_start||last_response<first_response)$fatal(1,"invalid baseline timing evidence");
   $display("BASELINE base=%0d total=%0d bursts=%0d first_response_HBM_cycles=%0d complete_HBM_cycles=%0d elapsed_ps=%0d",block_base,block_total,request_count,first_response-case_start,last_response-case_start,(last_response-case_start)*1024);
  end
 endtask
 initial begin
  base=0;total=0;for(integer q=0;q<32;q=q+1)group_q[q]=0;
  measure(4099,640);measure(12295,2048);
  $display("PASS immutable_actual_PHY_burst_baseline CLK_PS=1024 ports32 queue64 FRFCFS16");$finish;
 end
 initial begin #10000000;$fatal(1,"baseline timeout");end
endmodule
`default_nettype wire
