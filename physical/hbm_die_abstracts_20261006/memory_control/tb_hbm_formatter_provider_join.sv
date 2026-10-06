`timescale 1ns/1ps
// Integration payload bench; no production inference or physical qualification.
module tb_hbm_formatter_provider_join;
 reg  clk=0;
 reg  por_n=0;
 reg  desc_v=0;
 wire  desc_r;
 reg [2:0] desc_index=0;
 reg [63:0] desc_data=0;
 reg  start_v=0;
 wire  start_r;
 reg  installed_book_valid=0;
 reg [31:0] job=0;
 reg [3:0] gen=0;
 reg [16:0] token=0;
 reg [19:0] pos=0;
 wire  retained;
 wire [31:0] bound_arena_base, bound_arena_limit;
 wire  arena_visible;
 wire  sink_visible;
 wire  fault;
 reg  prep_req_v=0;
 wire  req_r;
 reg [2:0] prep_req_kind=0;
 reg [31:0] prep_req_addr=0;
 reg [15:0] prep_req_tag=0;
 reg [6:0] prep_req_rank=0;
 reg [5:0] prep_req_word=0;
 reg [511:0] prep_req_data=0;
 reg [31:0] prep_req_job=0;
 reg [3:0] prep_req_gen=0;
 reg [16:0] prep_req_token=0;
 reg [19:0] prep_req_pos=0;
 wire  rsp_v;
 reg  prep_rsp_r=0;
 wire [511:0] rsp_data;
 wire [31:0] rsp_addr;
 wire [15:0] rsp_tag;
 wire [2:0] rsp_kind;
 wire  rsp_checked;
 wire [31:0] held_job;
 wire [3:0] held_gen;
 wire [16:0] held_token;
 wire [19:0] held_pos;
 wire  m_req_v;
 reg  m_req_rdy=0;
 wire  m_req_we;
 wire [31:0] m_req_addr;
 wire [255:0] m_req_wdata;
 wire [31:0] m_req_wstrb;
 wire [15:0] m_req_tag;
 reg  m_rsp_v=0;
 wire  m_rsp_rdy;
 reg  m_rsp_we=0;
 reg [255:0] m_rsp_data=0;
 reg [15:0] m_rsp_tag=0;
 reg  release_v=0;
 wire  release_r;
 reg [31:0] release_job=0;
 reg [3:0] release_gen=0;
 reg [16:0] release_token=0;
 reg [19:0] release_pos=0;
 reg  result_published=0;
 reg  source_reverse_done=0;
 reg  native_clients_drained=0;
 reg  cdc_drained=0;
 reg  provider_fault=0;
 reg [3:0] observe_req=0;
 reg [3:0] observe_rsp=0;
 reg [3:0] observe_req_we=0;
 reg [3:0] observe_rsp_we=0;
 reg [63:0] observe_req_tag=0;
 reg [63:0] observe_rsp_tag=0;
 reg [3:0] return_offer=0;
 wire [3:0] response_authorized;
 reg [31:0] native_job=0;
 reg [3:0] native_gen=0;
 reg [16:0] native_token=0;
 reg [19:0] native_pos=0;
 wire  native_credit_empty;
 wire  shared_idle;
 reg [1:0] peer_lease_v=0;
 reg [1:0] peer_quiet=0;
 reg [1:0] peer_release_v=0;
 reg [63:0] peer_lease_job=0;
 reg [63:0] peer_release_job=0;
 reg [7:0] peer_lease_gen=0;
 reg [7:0] peer_release_gen=0;
 reg [33:0] peer_lease_token=0;
 reg [33:0] peer_release_token=0;
 reg [39:0] peer_lease_pos=0;
 reg [39:0] peer_release_pos=0;
 wire [1:0] peer_lease_granted;
 wire [1:0] peer_release_r;
 reg [2:0] p_req_v=0;
 reg [2:0] p_req_we=0;
 wire [2:0] p_req_rdy;
 reg [95:0] p_req_addr=0;
 reg [95:0] p_req_wstrb=0;
 reg [767:0] p_req_wdata=0;
 reg [47:0] p_req_tag=0;
 wire [2:0] p_rsp_v;
 wire [2:0] p_rsp_we;
 reg [2:0] p_rsp_rdy=0;
 wire [47:0] p_rsp_tag;
 wire [767:0] p_rsp_data;

 reg fmt_mode=0,fmt_start=0,fmt_pair_v=0,fmt_pairs_r=0,fmt_release_v=0,inject_token=0;
 wire fmt_start_r,fmt_pair_r,fmt_pairs_v,fmt_retained,fmt_fault,fmt_release_r;
 reg [6:0] fmt_rank=0; reg [5:0] fmt_word=0; reg [15:0] fmt_tag=0;
 wire [511:0] fmt_pairs;wire [72:0] fmt_frame;
 wire [31:0] fmt_job;wire [3:0] fmt_gen;wire [19:0] fmt_pos;
 wire [6:0] fmt_out_rank;wire [5:0] fmt_out_word;wire [15:0] fmt_out_tag;
 wire fmt_checked,fmt_ue,fmt_req_v,fmt_req_r,fmt_rsp_r;wire [648:0] fmt_req;
 wire [636:0] fmt_rsp_raw={held_pos,held_token,held_gen,held_job,rsp_data,rsp_addr,rsp_tag,rsp_kind,rsp_checked};
 wire [636:0] fmt_rsp=fmt_rsp_raw^(inject_token?(637'd1<<616):637'd0);
 wire formatter_lease_valid;wire [72:0] formatter_lease_frame;
 wire req_v=fmt_mode?fmt_req_v:prep_req_v;
 wire [2:0] req_kind=fmt_mode?fmt_req[2:0]:prep_req_kind;
 wire [31:0] req_addr=fmt_mode?fmt_req[34:3]:prep_req_addr;
 wire [15:0] req_tag=fmt_mode?fmt_req[50:35]:prep_req_tag;
 wire [6:0] req_rank=fmt_mode?fmt_req[57:51]:prep_req_rank;
 wire [5:0] req_word=fmt_mode?fmt_req[63:58]:prep_req_word;
 wire [511:0] req_data=fmt_mode?fmt_req[575:64]:prep_req_data;
 wire [31:0] req_job=fmt_mode?fmt_req[607:576]:prep_req_job;
 wire [3:0] req_gen=fmt_mode?fmt_req[611:608]:prep_req_gen;
 wire [16:0] req_token=fmt_mode?fmt_req[628:612]:prep_req_token;
 wire [19:0] req_pos=fmt_mode?fmt_req[648:629]:prep_req_pos;
 wire rsp_r=fmt_mode?fmt_rsp_r:prep_rsp_r;
 assign fmt_req_r=req_r&&fmt_mode;
 ot_hbm_integrated_formatter_provider #(.ENABLE(1),.VM_AW(14)) u_formatter_join(
 .clk(clk),.por_n(por_n),.start(fmt_start),.start_ready(fmt_start_r),
 .job(job),.gen(gen),.token(token),.pos(pos),.arena_base(bound_arena_base),.arena_limit(bound_arena_limit),
 .gather_retained(retained),.arena_visible(arena_visible),
 .gather_granted(formatter_lease_valid),.gather_frame73(formatter_lease_frame),
 .pair_v(fmt_pair_v),.pair_r(fmt_pair_r),.pair_job(job),.pair_gen(gen),.pair_token17(token),.pair_pos(pos),
 .pair_rank(fmt_rank),.pair_word(fmt_word),.pair_tag(fmt_tag),
 .pairs_v(fmt_pairs_v),.pairs_r(fmt_pairs_r),.pairs(fmt_pairs),.pairs_job(fmt_job),.pairs_gen(fmt_gen),.pairs_pos(fmt_pos),
 .pairs_rank(fmt_out_rank),.pairs_word(fmt_out_word),.pairs_tag(fmt_out_tag),.pairs_frame73(fmt_frame),
 .pairs_checked(fmt_checked),.pairs_uncorrectable(fmt_ue),.retained(fmt_retained),.fault(fmt_fault),
 .bridge_req_v(fmt_req_v),.bridge_req_r(fmt_req_r),.bridge_req(fmt_req),
 .bridge_rsp_v(rsp_v&&fmt_mode),.bridge_rsp_r(fmt_rsp_r),.bridge_rsp(fmt_rsp),
 .release_v(fmt_release_v),.release_r(fmt_release_r),.release_job(job),.release_gen(gen),.release_token17(token),.release_pos(pos),
 .publication_done(sink_visible),.source_reverse_done(source_reverse_done));
 integer pair_checks=0,formatter_reads=0,first_pair_cycle;
 always @(posedge clk)if(por_n&&fmt_req_v&&fmt_req_r)begin
  if(fmt_req[2:0]!=3||fmt_req[648:576]!={pos,token,gen,job}||fmt_req[8:3]!=0)
   $fatal(1,"formatter request ABI/full73/byte alignment mismatch");
  formatter_reads<=formatter_reads+1;
 end
 task formatter_start;begin
  fmt_mode=1;fmt_start=1;#0.01;
  if(!fmt_start_r)$fatal(1,"real published arena not accepted");
  edge_tick();fmt_start=0;
  if(fmt_frame!=={pos,token,gen,job})$fatal(1,"full73 high token/position lost");
 end endtask
 task formatter_pair(input integer rank,word_index);reg [511:0] scores,ids,want,held;begin
  fmt_rank=7'(rank);fmt_word=6'(word_index);fmt_tag=16'hc000+16'(pair_checks);fmt_pair_v=1;#0.01;
  if(!fmt_pair_r)$fatal(1,"formatter request refused matched frame");
  first_pair_cycle=cycles;edge_tick();fmt_pair_v=0;
  wait(fmt_pairs_v);@(negedge clk);
  scores=page(1,rank,word_index/2);ids=page(2,rank,word_index/2);
  for(integer lane=0;lane<8;lane++)want[64*lane+:64]={ids[32*(lane+(word_index%2?8:0))+:32],scores[32*(lane+(word_index%2?8:0))+:32]};
  if(fmt_pairs!==want||fmt_job!==job||fmt_gen!==gen||fmt_pos!==pos||fmt_frame!=={pos,token,gen,job}||
     fmt_out_rank!==fmt_rank||fmt_out_word!==fmt_word||fmt_out_tag!==fmt_tag||!fmt_checked||fmt_ue||fmt_fault)
   $fatal(1,"512bit formatter payload/identity mismatch rank%0d word%0d",rank,word_index);
  held=fmt_pairs;
  repeat(4)begin edge_tick();if(!fmt_pairs_v||fmt_pairs!==held||!fmt_retained||fmt_fault)$fatal(1,"held pair response changed");end
  $display("JOIN_PAIR rank=%0d word=%0d latency=%0d",rank,word_index,cycles-first_pair_cycle);
  fmt_pairs_r=1;edge_tick();fmt_pairs_r=0;pair_checks++;
 end endtask

 ot_hbm_integrated_gather_owner #(.ENABLE(1),.VM_AW(14)) dut (.*);
 localparam [31:0] ARENA=32'h10000, ARENA_END=32'h70000;
 localparam [31:0] SINK=32'h70000, SCORE_SOURCE=32'h80000, ID_SOURCE=32'h80800;
 reg [255:0] memory[0:32767];
 reg provider_pending=0;
 integer provider_delay=0, cycles=0, transactions=0, packets=0;
 reg [15:0] provider_tag;
 reg provider_we;
 reg [255:0] provider_data;
 reg [511:0] expected, held_response;
 integer w,r,k;
 always #0.5 clk=~clk;
 always @* begin
  native_clients_drained=!provider_pending&&!m_rsp_v;
  cdc_drained=!provider_pending&&!m_req_v&&!m_rsp_v;
 end
 // Real beat store: write each enabled byte and return later with its actual
 // request tag/kind. Oracle values are never injected into this provider.
 always @(posedge clk) begin
  if(!por_n) begin
   provider_pending<=0; provider_delay<=0; m_req_rdy<=0; m_rsp_v<=0;
   m_rsp_data<=0; m_rsp_tag<=0; m_rsp_we<=0; cycles<=0;
  end else begin
   cycles<=cycles+1;
   m_req_rdy<=!provider_pending && cycles%7!=0;
   if(m_req_v&&m_req_rdy) begin
    if(provider_pending)$fatal(1,"second request overwrote live provider owner");
    if(m_req_addr[4:0]!=0 || m_req_addr>=32'h100000)$fatal(1,"invalid provider beat address");
    provider_pending<=1; provider_delay<=3;
    provider_tag<=m_req_tag;provider_we<=m_req_we;
    provider_data<=memory[m_req_addr>>5];
    if(m_req_we)for(integer byte_lane=0;byte_lane<32;byte_lane++)
     if(m_req_wstrb[byte_lane])memory[m_req_addr>>5][8*byte_lane+:8]<=m_req_wdata[8*byte_lane+:8];
    transactions<=transactions+1;
   end
   if(provider_pending&&!m_rsp_v)begin
    if(provider_delay>0)provider_delay<=provider_delay-1;
    else begin m_rsp_v<=1;m_rsp_data<=provider_data;m_rsp_tag<=provider_tag;m_rsp_we<=provider_we;end
   end
   if(m_rsp_v&&m_rsp_rdy)begin m_rsp_v<=0;provider_pending<=0;end
  end
 end
 task edge_tick;begin @(posedge clk);#0.01;@(negedge clk);end endtask
 task check_live;begin if(fault)begin for(integer row=0;row<35;row++)if(dut.u_bridge.on.dec[row][65])$display("BAD_ROW %0d code=%h decoded=%h",row,dut.u_bridge.on.code[row],dut.u_bridge.on.dec[row]); $display("FAULT bridge=%b arb=%b provider=%b state=%h bad=%b grant=%b owned=%b failed=%b prior=%b quiet=%b",dut.bridge_fault,dut.arb_fault,provider_fault,dut.u_bridge.on.state,dut.u_bridge.on.bad,dut.borrow_granted,dut.u_shared_owner.on.owned,dut.u_shared_owner.on.failed,dut.u_shared_owner.on.prior_violation,dut.u_shared_owner.borrower_quiet);$fatal(1,"unexpected fault at packet %0d",packets);end end endtask
 task configure;begin
  por_n=0;prep_req_v=0;prep_rsp_r=0;start_v=0;desc_v=0;release_v=0;
  provider_fault=0;result_published=0;source_reverse_done=0;
  peer_quiet=2'b11;peer_lease_v=0;peer_release_v=0;
  job=32'h12345678;gen=4'h9;token=17'h10001;pos=20'hfffff;
  native_job=job;native_gen=gen;native_token=token;native_pos=pos;
  prep_req_job=job;prep_req_gen=gen;prep_req_token=token;prep_req_pos=pos;
  release_job=job;release_gen=gen;release_token=token;release_pos=pos;
  installed_book_valid=1;edge_tick();por_n=1;edge_tick();
  for(integer di=0;di<8;di++)begin
   desc_index=3'(di);
   case(di)
    0:desc_data=0;
    1:desc_data={ID_SOURCE,SCORE_SOURCE};
    2:desc_data={ARENA_END,ARENA};
    3:desc_data={SINK+32'd2048,SINK};
    4:desc_data=64'h100000;
    5:desc_data=64'd96|(64'd512<<16)|(64'd32<<32);
    default:desc_data=0;
   endcase
   desc_v=1;#0.01;if(!desc_r)$fatal(1,"descriptor refusal %0d",di);edge_tick();
  end
  desc_v=0;start_v=1;
  begin:wait_start
   for(integer age=0;age<64;age++)begin
    #0.01;if(start_r)begin edge_tick();disable wait_start;end
    edge_tick();if(fault)$fatal(1,"start fault");
   end
   $fatal(1,"borrower did not acquire quiet shared route");
  end
  start_v=0;
 end endtask
 function automatic [511:0] page(input integer kind,rank,word_index);
  reg[511:0] v;
  begin
   for(integer lane=0;lane<16;lane++)v[32*lane+:32]=32'h5a000000 ^ (32'(kind)<<24) ^ (32'(rank)<<14) ^ (32'(word_index)<<5) ^ 32'(lane);
   page=v;
  end
 endfunction
 task request_page(input integer kind,rank,word_index,input [31:0] address,input [511:0] data,oracle);
  begin
   prep_req_kind=3'(kind);prep_req_rank=7'(rank);prep_req_word=6'(word_index);
   prep_req_addr=address;prep_req_tag=16'(packets+100);prep_req_data=data;prep_req_v=1;prep_rsp_r=0;
   begin:accept_packet
    for(integer age=0;age<128;age++)begin
     #0.01;check_live();if(req_r)begin edge_tick();disable accept_packet;end
     edge_tick();
    end
    $fatal(1,"packet not accepted kind%0d rank%0d word%0d",kind,rank,word_index);
   end
   prep_req_v=0;
   begin:receive_packet
    for(integer age=0;age<256;age++)begin
     #0.01;check_live();
     if(rsp_v)begin
      if(!rsp_checked||rsp_addr!=address||rsp_tag!=prep_req_tag||rsp_kind!=kind||rsp_data!==oracle)
       $fatal(1,"payload/identity mismatch packet%0d kind%0d rank%0d word%0d",packets,kind,rank,word_index);
      held_response=rsp_data;
      repeat(3)begin edge_tick();#0.01;if(!rsp_v||rsp_data!==held_response||!retained||dut.shared_idle)$fatal(1,"stalled return lost owner/data");end
      prep_rsp_r=1;edge_tick();prep_rsp_r=0;packets++;disable receive_packet;
     end
     edge_tick();
    end
    $fatal(1,"packet response stuck packet%0d kind%0d",packets,kind);
   end
  end
 endtask
 initial begin
  for(k=0;k<32768;k++)memory[k]=0;
  for(k=0;k<32;k++)begin
   expected=page(0,0,k);
   memory[(SCORE_SOURCE>>5)+2*k]=expected[255:0];
   memory[(SCORE_SOURCE>>5)+2*k+1]=expected[511:256];
  end
  configure();
  if($test$plusargs("CONTROL_UE"))begin
   if(fault||!retained||!dut.borrow_granted||dut.u_bridge.on.dec[11][65])
    $fatal(1,"control UE fixture lacks healthy actual lease/control");
   // Actual mutable protected row, not a fabricated provider callback.
   dut.u_bridge.on.code[11]=dut.u_bridge.on.code[11]^72'd3;
   #0.01;if(!dut.u_bridge.on.dec[11][65]||!fault||req_r||m_req_v)
    $fatal(1,"actual two-bit control DUE did not refuse traffic");
   repeat(4)edge_tick();
   if(!fault||!retained||shared_idle||fmt_start_r||m_req_v||transactions!=0)
    $fatal(1,"DUE dropped retained lease or issued normal traffic");
   $display("PASS_GATHER_CONTROL_UE actual_row11_two_bit_DUE retained_real_grant no_publication no_backend_request");
   $finish;
  end
  for(w=0;w<32;w++)for(r=0;r<96;r++)begin
   expected=page(1,r,w);request_page(1,r,w,ARENA+32'(2048*r+64*w),expected,expected);
   if(arena_visible)$fatal(1,"score-only arena published before full ID plane");
  end
  for(w=0;w<32;w++)for(r=0;r<96;r++)begin
   expected=page(2,r,w);request_page(2,r,w,ARENA+32'd196608+32'(2048*r+64*w),expected,expected);
   if((w!=31||r!=95)&&arena_visible)$fatal(1,"partial ID plane published");
  end
  #0.01;if(!arena_visible||sink_visible)$fatal(1,"full arena missing or premature sink publication");
  formatter_start();
  formatter_pair(0,0);formatter_pair(95,63);formatter_pair(41,32);formatter_pair(41,33);
  if(formatter_reads!=8||pair_checks!=4)$fatal(1,"formatter read census mismatch");
  fmt_mode=0;
  for(w=0;w<32;w++)begin
   expected=page(2,95,w);request_page(4,0,w,SINK+32'(64*w),expected,expected);
  end
  if(!sink_visible)$fatal(1,"actual sink write/readback not published");
  fmt_release_v=1;
  repeat(4)begin edge_tick();if(fmt_release_r||!fmt_retained)$fatal(1,"formatter released before reverse ACK");end
  source_reverse_done=1;#0.01;if(!fmt_release_r)$fatal(1,"formatter refused actual publication/reverse terminal");
  edge_tick();fmt_release_v=0;#0.01;
  if(fmt_retained||fmt_fault)$fatal(1,"formatter release did not retire");
  formatter_start();
  fmt_rank=95;fmt_word=63;fmt_tag=16'hdead;fmt_pair_v=1;#0.01;
  if(!fmt_pair_r)$fatal(1,"second binding refused");
  edge_tick();fmt_pair_v=0;
  wait(rsp_v);@(negedge clk);inject_token=1;#0.01;
  if(fmt_rsp_r)$fatal(1,"wrong TOKEN17 accepted");
  edge_tick();
  if(!fmt_fault||!fmt_retained||fmt_rsp_r||fmt_pairs_v||!retained||shared_idle)
   $fatal(1,"wrong token failed to quarantine live bridge receipt and lease");
  repeat(4)edge_tick();
  $display("PASS_FORMATTER_PROVIDER_JOIN full96x512_planes 6144checked_publications 4pair512 8reads full73 held_reverse_release TOKEN17negative cycles=%0d beats=%0d",cycles,transactions);
  $finish;
 end
endmodule
