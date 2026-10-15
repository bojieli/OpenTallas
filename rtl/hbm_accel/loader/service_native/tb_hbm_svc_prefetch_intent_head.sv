`timescale 1ps/1fs
`default_nettype none
module tb_hbm_svc_prefetch_intent_head;
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
 wire [3:0] stream_bank_clk={4{stream_clk}};
 wire [31:0] hbm_pc_clk={32{hbm_clk}};
 wire [7:0] hbm_fifo_clk={8{hbm_clk}};
 ot_hbm_svc_prefetch_burst_cdc dut(.*);
 wire k_oor=0,w_oor=0;wire native_fault;
 wire [31:0] row_v,col_v,col_we,dram_rvalid;wire [95:0] row_op;
 wire [159:0] row_bank,col_bank,col_col;wire [607:0] row_row;
 wire [8191:0] col_data,dram_rdata;wire [1023:0] col_strb;
 wire [127:0] native_kr_beat;
 assign kr_beat=$test$plusargs("DUPBEAT")?128'b0:native_kr_beat;
 ot_hbm_svc_native_sector_intent_stack #(.FAST_IDLE_DESC(1),.AQ_ROW_LEASE(1),.INTENT_PREVIEW(1),.REGISTERED_HEAD_BYPASS(1)) u_native(
 .clk(hbm_clk),.rst_n(hbm_rst_n),.pc_clk(hbm_pc_clk),
 .k_v(k_v),.k_rdy(k_rdy),.k_we(k_we),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),
 .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(native_kr_beat),.kr_data(kr_data),
 .row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),
 .dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.fault(native_fault));
 ot_hbm_svc_command_dram_pipeline_fixture #(.K_BASE(0),.K_MEM(32768)) dram(
 .clk(hbm_clk),.rst_n(hbm_rst_n),.row_v(row_v),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_we(col_we),.col_bank(col_bank),.col_col(col_col),.col_data(col_data),.col_strb(col_strb),.dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata));
 function automatic [255:0] pattern(input integer sector);
  integer j;begin for(j=0;j<8;j=j+1)pattern[j*32+:32]=32'h34129a07^(sector*32'h1021)^(j*32'h123abcd);end
 endfunction
 function automatic integer pc_of(input integer s);pc_of=((s>>2)^(s>>7)^(s>>12))&31;endfunction
 integer base[1:3],total[1:3];reg [2047:0] requested[1:3];
 integer announce[1:3],delivered[1:3],reserve_tick[1:3],ready_tick[1:3];
 integer case_bursts[1:3],case_responses[1:3];
 integer case_response_stalls[1:3],case_fifo_credit_stalls[1:3],case_arbitration_conflict_stalls[1:3];
 integer case_peak_accepts[1:3],case_accept_cycles_ge10[1:3],case_accept_cycles_ge20[1:3],case_accept_cycles_ge28[1:3];
 integer fifo_credit_stalls=0,arbitration_conflict_stalls=0,peak_accepts=0;
 integer accept_cycles_ge10=0,accept_cycles_ge20=0,accept_cycles_ge28=0;
 integer edge_accepts=0;
 realtime reserve_time[1:3],ready_time[1:3],first_request_time[1:3],last_response_time[1:3];
 realtime reserve_assert_time[1:3],reset_release_time[1:3];
 integer current_case=0,performance_failures=0,selected_case=1,tail_total=73;
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
 integer response_stalls=0,request_stalls=0;integer last_output_cycle=-1,previous_epoch=0;
 always @(posedge hbm_clk)begin
  hcycle=hcycle+1;
  if(hbm_rst_n&&current_case>0)begin
   edge_accepts=0;
   if(k_oor||w_oor||native_fault)$fatal(1,"native controller fault");
   for(integer q=0;q<32;q=q+1)begin
    if(k_v[q]&&!k_rdy[q])request_stalls=request_stalls+1;
    if(kr_v[q]&&!kr_rdy[q])begin
     response_stalls=response_stalls+1;case_response_stalls[current_case]=case_response_stalls[current_case]+1;
    end
    if(dut.response_ok[q]&&!kr_rdy[q])begin
     if(!dut.fifo_wr_ready[dut.response_ordinal[q][4:0]])begin
      fifo_credit_stalls=fifo_credit_stalls+1;case_fifo_credit_stalls[current_case]=case_fifo_credit_stalls[current_case]+1;
     end else begin
      arbitration_conflict_stalls=arbitration_conflict_stalls+1;
      case_arbitration_conflict_stalls[current_case]=case_arbitration_conflict_stalls[current_case]+1;
     end
    end
    if(kr_v[q]&&kr_rdy[q])begin
     edge_accepts=edge_accepts+1;
     case_responses[current_case]=case_responses[current_case]+1;
     last_response_time[current_case]=$realtime;
    end
    if(k_v[q]&&k_rdy[q])begin:request_check
     integer ordinal,burst_len,address;
     address=k_addr[30*q+:30];ordinal=address-base[current_case];burst_len=k_len[4*q+:4];
     if(q!=pc_of(address))$fatal(1,"actual XOR PC mismatch q%0d sector%0d",q,address);
     if(k_we[q]||burst_len<1||burst_len>4||(address%4)+burst_len>4||ordinal<0||ordinal+burst_len>total[current_case])$fatal(1,"request identity/burst range");
     // Tags are opaque owner tickets, not epochs or block ordinals.
     for(integer beat=0;beat<burst_len;beat=beat+1)begin
      if(requested[current_case][ordinal+beat]||pc_of(address+beat)!=q)$fatal(1,"request duplicate/PC crossing");
      requested[current_case][ordinal+beat]=1;requests=requests+1;
     end
     if(case_bursts[current_case]==0)first_request_time[current_case]=$realtime;
     case_bursts[current_case]=case_bursts[current_case]+1;
    end
   end
   if(edge_accepts>peak_accepts)peak_accepts=edge_accepts;
   if(edge_accepts>case_peak_accepts[current_case])case_peak_accepts[current_case]=edge_accepts;
   if(edge_accepts>=10)begin accept_cycles_ge10=accept_cycles_ge10+1;case_accept_cycles_ge10[current_case]=case_accept_cycles_ge10[current_case]+1;end
   if(edge_accepts>=20)begin accept_cycles_ge20=accept_cycles_ge20+1;case_accept_cycles_ge20[current_case]=case_accept_cycles_ge20[current_case]+1;end
   if(edge_accepts>=28)begin accept_cycles_ge28=accept_cycles_ge28+1;case_accept_cycles_ge28[current_case]=case_accept_cycles_ge28[current_case]+1;end
  end
 end
 always @(posedge stream_clk)begin
  scycle=scycle+1;
  if(stream_rst_n&&reserve_v&&reserve_ready)begin
   reserve_time[reserve_epoch]=$realtime;reserve_tick[reserve_epoch]=hcycle;
  end
  #1;
  if(stream_rst_n&&hbm_rst_n)begin
   if(fault)begin
    if($test$plusargs("DUPBEAT"))begin $display("PASS PREFETCH_INTENT_HEAD duplicate response beat rejected");$finish;end
    else $fatal(1,"unexpected CDC boundary fault streamcycle%0d",scycle);
   end
   if(block_ready_v)begin
    if(block_ready_epoch<1||block_ready_epoch>3)$fatal(1,"ready identity");
    announce[block_ready_epoch]=announce[block_ready_epoch]+1;
    if(announce[block_ready_epoch]!=1)$fatal(1,"duplicate ready announcement");
    ready_tick[block_ready_epoch]=hcycle;ready_time[block_ready_epoch]=$realtime-1;
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
   reserve_v=1;reserve_base=base[ep];reserve_total=total[ep];reserve_bank=ep==2;reserve_epoch=ep;reserve_assert_time[ep]=$realtime;
   #1;if(!reserve_ready)$fatal(1,"block reserve unavailable");
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
 task cold_reset(input integer ep);
  begin
   @(negedge hbm_clk);hbm_rst_n=0;stream_rst_n=0;current_case=0;
   repeat(8)@(negedge hbm_clk);
   stream_rst_n=1;hbm_rst_n=1;reset_release_time[ep]=$realtime;
   repeat(4)@(negedge hbm_clk);
   // Same real PHY backing array and post-reset initialization as baseline.
   for(integer sector=0;sector<32768;sector=sector+1)dram.mem[sector]=pattern(sector);
   // Explicit FIFO-online setup before reserve; included in setup reporting.
   repeat(20)@(negedge stream_clk);
   current_case=ep;
  end
 endtask
 initial begin
  base[1]=4099;total[1]=640;base[2]=12295;total[2]=2048;base[3]=3001;total[3]=73;
  if($value$plusargs("TAILTOTAL=%d",tail_total))total[3]=tail_total;
  for(integer ep=1;ep<=3;ep=ep+1)begin
   requested[ep]=0;announce[ep]=0;delivered[ep]=0;reserve_tick[ep]=0;ready_tick[ep]=0;
   case_bursts[ep]=0;case_responses[ep]=0;reserve_time[ep]=0;ready_time[ep]=0;
   first_request_time[ep]=0;last_response_time[ep]=0;
   case_response_stalls[ep]=0;case_fifo_credit_stalls[ep]=0;case_arbitration_conflict_stalls[ep]=0;
   case_peak_accepts[ep]=0;case_accept_cycles_ge10[ep]=0;case_accept_cycles_ge20[ep]=0;case_accept_cycles_ge28[ep]=0;
  end
  if(!$value$plusargs("CASE=%d",selected_case))selected_case=1;
  for(integer ep=selected_case;ep<=selected_case;ep=ep+1)begin:run_case
   real latency_cycles,limit_cycles,baseline_cycles;
   cold_reset(ep);reserve_block(ep);drain_block(ep);
   repeat(6)@(negedge stream_clk);
   if(fault||case_responses[ep]!=total[ep])$fatal(1,"case response totals");
   for(integer n=0;n<total[ep];n=n+1)if(!requested[ep][n])$fatal(1,"missing request");
   latency_cycles=(ready_time[ep]-reserve_time[ep])/1024.0;
   baseline_cycles=ep==1?77.0:122.0;limit_cycles=baseline_cycles*1.1;
   $display("PREFETCH_BURST_CDC_CASE epoch=%0d base=%0d total=%0d bursts=%0d responses=%0d reserve_to_ready_HBM_cycles=%0f reset_release_to_reserve_HBM_cycles=%0f reserve_assert_to_accept_HBM_cycles=%0f reserve_to_first_request_HBM_cycles=%0f last_response_to_ready_HBM_cycles=%0f stream_delivery_cycles=%0d",ep,base[ep],total[ep],case_bursts[ep],case_responses[ep],latency_cycles,(reserve_time[ep]-reset_release_time[ep])/1024.0,(reserve_time[ep]-reserve_assert_time[ep])/1024.0,(first_request_time[ep]-reserve_time[ep])/1024.0,(ready_time[ep]-last_response_time[ep])/1024.0,(total[ep]+7)/8);
   $display("PREFETCH_BURST_CDC_RESPONSE_PROFILE epoch=%0d response_stalls=%0d FIFO_credit_stalls=%0d arbitration_conflict_stalls=%0d peak_accepted_per_HBM_edge=%0d accepted_edges_ge10=%0d accepted_edges_ge20=%0d accepted_edges_ge28=%0d",ep,case_response_stalls[ep],case_fifo_credit_stalls[ep],case_arbitration_conflict_stalls[ep],case_peak_accepts[ep],case_accept_cycles_ge10[ep],case_accept_cycles_ge20[ep],case_accept_cycles_ge28[ep]);
   if(ep<=2)begin
    $display("PREFETCH_BURST_CDC_PERFORMANCE %s epoch=%0d baseline_HBM_cycles=%0f limit_HBM_cycles=%0f measured_HBM_cycles=%0f overhead_HBM_cycles=%0f ratio=%0f baseline_edge_convention=previous_posedge_to_response DUT_edge_convention=accepted_reserve_to_ready",latency_cycles<=limit_cycles?"PASS":"FAIL",ep,baseline_cycles,limit_cycles,latency_cycles,latency_cycles-baseline_cycles,latency_cycles/baseline_cycles);
    if(latency_cycles>limit_cycles)performance_failures=performance_failures+1;
   end
  end
  if(fault||requests!=total[selected_case]||vectors!=total[selected_case]||output_cycles!=(total[selected_case]+7)/8)$fatal(1,"final totals");
  if($test$plusargs("DUPBEAT"))$fatal(1,"duplicate beat mutant escaped fault detector");
  $display("PASS PREFETCH_INTENT_HEAD native_command_only_DRAM real32SRAM stream_period_ps=833.333334 hbm_period_ps=1024 PHY_CLK_PS=1024 phase=%0f exact_vectors=%0d requested_sectors=%0d fixed_cycles=%0d request_stalls=%0d response_stalls=%0d performance_failures=%0d",phase_value,vectors,requests,output_cycles,request_stalls,response_stalls,performance_failures);
  $display("PREFETCH_BURST_CDC_RESPONSE_PROFILE_TOTAL response_stalls=%0d FIFO_credit_stalls=%0d arbitration_conflict_stalls=%0d peak_accepted_per_HBM_edge=%0d accepted_edges_ge10=%0d accepted_edges_ge20=%0d accepted_edges_ge28=%0d",response_stalls,fifo_credit_stalls,arbitration_conflict_stalls,peak_accepts,accept_cycles_ge10,accept_cycles_ge20,accept_cycles_ge28);
  if(performance_failures!=0&&!$test$plusargs("ALLOW_PERF_FAIL"))$fatal(1,"raw baseline latency qualification failed");
  $finish;
 end
 initial begin #300000000;$fatal(1,"prefetch burst CDC timeout");end
endmodule
`default_nettype wire
