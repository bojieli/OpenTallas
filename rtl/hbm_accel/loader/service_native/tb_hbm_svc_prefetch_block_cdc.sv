`timescale 1ps/1fs
`default_nettype none
module tb_hbm_svc_prefetch_block_cdc;
 real phase_value;
 reg stream_clk=0;always #416.666667 stream_clk=~stream_clk;
 reg hbm_clk=0;initial begin if(!$value$plusargs("PHASE=%f",phase_value))phase_value=137.0; #(phase_value);forever #512 hbm_clk=~hbm_clk;end
 reg stream_rst_n=0;
 reg hbm_rst_n=0;
 reg reserve_v=0;
 wire reserve_ready;
 reg [31:0] reserve_base=0;
 reg [11:0] reserve_total=0;
 reg reserve_bank=0;
 reg [15:0] reserve_epoch=0;
 wire [1:0] block_ready;
 wire block_ready_v;
 wire block_ready_bank;
 wire [15:0] block_ready_epoch;
 reg start_v=0;
 reg start_bank=0;
 reg [15:0] start_epoch=0;
 wire out_v;
 wire [7:0] out_mask;
 wire [2047:0] out_data;
 wire [10:0] out_ordinal;
 wire out_bank;
 wire [15:0] out_epoch;
 wire out_last;
 wire fault;
 wire [31:0] k_v;
 wire [31:0] k_rdy;
 wire [959:0] k_addr;
 wire [127:0] k_len;
 wire [543:0] k_tag;
 wire [31:0] k_we;
 wire [8191:0] k_wdata;
 wire [1023:0] k_wstrb;
 wire [31:0] k_wr_done;
 wire [31:0] kr_v;
 wire [31:0] kr_rdy;
 wire [543:0] kr_tag;
 wire [127:0] kr_beat;
 wire [8191:0] kr_data;
 ot_hbm_svc_prefetch_block_cdc dut(.*);
 wire k_oor,w_oor;wire [63:0] refreshes;wire [31:0] w_reads;
 wire [543:0] phy_kr_tag;
 wire [31:0] phy_k_rdy,phy_kr_v;
 reg [31:0] request_allow=32'hffffffff,response_allow=32'hffffffff;
 assign k_rdy=phy_k_rdy&request_allow;
 assign kr_v=phy_kr_v&response_allow;
 always @(negedge hbm_clk)begin
  for(integer q=0;q<32;q=q+1)begin
   request_allow[q]=(hcycle+q)%5>=2;
   response_allow[q]=(hcycle+q)%7>=3;
  end
 end
 assign kr_tag=($test$plusargs("BADTAG")&&(|kr_v))?(phy_kr_tag^{32{17'd1}}):phy_kr_tag;
 ot_chip_v41x_hbm3e_phy #(.K_AW(30),.KTAGW(17),.K_MEM(32768),.CLK_PS(1024)) u_phy(
 .clk(hbm_clk),.rst_n(hbm_rst_n),.k_v(k_v&request_allow),.k_rdy(phy_k_rdy),.k_addr(k_addr),.k_len(k_len),
 .k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
 .kr_v(phy_kr_v),.kr_rdy(kr_rdy&response_allow),.kr_tag(phy_kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),
 .w_v(1'b0),.w_rdy(),.w_addr(24'b0),.w_len(6'b0),.w_tag(10'b0),.w_room(),
 .wr_v(),.wr_rdy(8'b0),.wr_tag(),.wr_beat(),.wr_data(),
 .k_oor(k_oor),.w_oor(w_oor),.refreshes(refreshes),.w_reads(w_reads));
 function automatic [255:0] pattern(input integer sector);
  integer j;begin for(j=0;j<8;j=j+1)pattern[j*32+:32]=32'h34129a07^(sector*32'h1021)^(j*32'h123abcd);end
 endfunction
 function automatic integer pc_of(input integer s);pc_of=((s>>2)^(s>>7)^(s>>12))&31;endfunction
 integer base[1:3],total[1:3];reg [2047:0] requested[1:3];
 integer announce[1:3],delivered[1:3],reserve_tick[1:3],ready_tick[1:3];
 realtime previous_stream_edge=0,previous_hbm_edge=0;
 always @(posedge stream_clk)begin
  if(previous_stream_edge!=0&&($realtime-previous_stream_edge<833.332||$realtime-previous_stream_edge>833.335))$fatal(1,"wrong stream period");
  previous_stream_edge=$realtime;
 end
 always @(posedge hbm_clk)begin
  if(previous_hbm_edge!=0&&($realtime-previous_hbm_edge!=1024))$fatal(1,"wrong HBM period");
  previous_hbm_edge=$realtime;
 end
 integer hcycle=0,scycle=0,requests=0,vectors=0,output_cycles=0;
 integer response_stalls=0,request_stalls=0,withheld_response_cycles=0;integer last_output_cycle=-1,previous_epoch=0;
 always @(posedge hbm_clk)begin
  hcycle=hcycle+1;
  if(hbm_rst_n)begin
   if(k_oor||w_oor)$fatal(1,"PHY aperture fault");
   for(integer q=0;q<32;q=q+1)begin
    if(k_v[q]&&!k_rdy[q])request_stalls=request_stalls+1;
    if(phy_kr_v[q]&&!response_allow[q])withheld_response_cycles=withheld_response_cycles+1;
    if(kr_v[q]&&!kr_rdy[q])response_stalls=response_stalls+1;
    if(k_v[q]&&k_rdy[q])begin:request_check
     integer ep,ordinal;
     ep=k_tag[17*q+:16];ordinal=k_addr[30*q+:30]-base[ep];
     if(q!=pc_of(k_addr[30*q+:30]))$fatal(1,"actual XOR PC mismatch q%0d sector%0d",q,k_addr[30*q+:30]);
     if(ep<1||ep>3||k_we[q]||k_len[4*q+:4]!=1||ordinal<0||ordinal>=total[ep]||requested[ep][ordinal])$fatal(1,"request identity/duplicate");
     requested[ep][ordinal]=1;requests=requests+1;
    end
   end
  end
 end
 always @(posedge stream_clk)begin
  scycle=scycle+1;#1;
  if(stream_rst_n&&hbm_rst_n)begin
   if(fault)begin
    if($test$plusargs("BADTAG"))begin $display("PASS wrong response epoch rejected");$finish;end
    else $fatal(1,"unexpected CDC boundary fault streamcycle%0d",scycle);
   end
   if(block_ready_v)begin
    if(block_ready_epoch<1||block_ready_epoch>3)$fatal(1,"ready identity");
    announce[block_ready_epoch]=announce[block_ready_epoch]+1;
    if(announce[block_ready_epoch]!=1)$fatal(1,"duplicate ready announcement");
    ready_tick[block_ready_epoch]=hcycle;
   end
   if(out_v)begin:check_output
    integer ep,n,valid_lanes;
    ep=out_epoch;n=total[ep]-out_ordinal;valid_lanes=n>=8?8:n;
    if(out_ordinal!=delivered[ep]||out_bank!=(ep==2)||out_mask!==((1<<valid_lanes)-1)||out_last!==(n<=8))$fatal(1,"fixed delivery metadata");
    if(previous_epoch==ep&&last_output_cycle+1!=scycle)$fatal(1,"fixed drain inserted wait");
    last_output_cycle=scycle;previous_epoch=ep;output_cycles=output_cycles+1;
    for(integer lane=0;lane<8;lane=lane+1)if(out_mask[lane])begin
     if(out_data[256*lane+:256]!==pattern(base[ep]+out_ordinal+lane))$fatal(1,"SRAM exact payload ep%0d ord%0d lane%0d",ep,out_ordinal,lane);
     vectors=vectors+1;
    end
    delivered[ep]=delivered[ep]+valid_lanes;
   end
  end
 end
 task reserve_block(input integer ep);
  begin
   @(negedge stream_clk);#1;
   reserve_v=1;reserve_base=base[ep];reserve_total=total[ep];reserve_bank=ep==2;reserve_epoch=ep;
   #1;if(!reserve_ready)$fatal(1,"block reserve unavailable");reserve_tick[ep]=hcycle;
   @(negedge stream_clk);#1;reserve_v=0;
  end
 endtask
 task drain_block(input integer ep);
  begin
   wait(announce[ep]==1);
   @(negedge stream_clk);#1;start_v=1;start_bank=ep==2;start_epoch=ep;
   @(negedge stream_clk);#1;start_v=0;
   wait(delivered[ep]==total[ep]);
   @(negedge stream_clk);#1;
  end
 endtask
 initial begin
  base[1]=4099;total[1]=640;base[2]=12295;total[2]=2048;base[3]=3001;total[3]=5;
  for(integer ep=1;ep<=3;ep=ep+1)begin requested[ep]=0;announce[ep]=0;delivered[ep]=0;reserve_tick[ep]=0;ready_tick[ep]=0;end
  // Real PHY backing array, not a substitute payload SRAM or fabricated response.
  for(integer s=0;s<32768;s=s+1)u_phy.u_k.mem[s]=pattern(s);
  repeat(4)@(negedge stream_clk);stream_rst_n=1;
  repeat(3)@(negedge hbm_clk);hbm_rst_n=1;
  repeat(20)@(negedge stream_clk);
  reserve_block(1);wait(announce[1]==1);
  reserve_block(2);drain_block(1);drain_block(2);
  reserve_block(3);drain_block(3);
  repeat(6)@(negedge stream_clk);
  if(fault||requests!=2693||vectors!=2693||output_cycles!=337||request_stalls==0||withheld_response_cycles==0)$fatal(1,"final totals");
  for(integer ep=1;ep<=3;ep=ep+1)begin
   for(integer n=0;n<total[ep];n=n+1)if(!requested[ep][n])$fatal(1,"missing request");
   $display("PREFETCH_CDC_CASE epoch=%0d total=%0d HBM_reserve_to_ready_cycles=%0d stream_delivery_cycles=%0d",ep,total[ep],ready_tick[ep]-reserve_tick[ep],(total[ep]+7)/8);
  end
  $display("PASS PREFETCH_CDC actualPHY real32SRAM stream_period_ps=833.333334 hbm_period_ps=1024 PHY_CLK_PS=1024 phase=%0f exact_vectors=%0d requests=%0d fixed_cycles=%0d request_stalls=%0d response_stalls=%0d withheld_response_cycles=%0d",phase_value,vectors,requests,output_cycles,request_stalls,response_stalls,withheld_response_cycles);
  $finish;
 end
 initial begin #300000000;$fatal(1,"prefetch CDC timeout");end
endmodule
`default_nettype wire
