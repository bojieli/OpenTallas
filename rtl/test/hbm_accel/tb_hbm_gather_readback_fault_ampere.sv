`timescale 1ns/1ps
// Bounded integration fault bench; reuses the passed real beat-store fixture.
// A dropped byte write must fail readback without publication or lease release.
module tb_hbm_gather_readback_fault_ampere;
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
 reg  req_v=0;
 wire  req_r;
 reg [2:0] req_kind=0;
 reg [31:0] req_addr=0;
 reg [15:0] req_tag=0;
 reg [6:0] req_rank=0;
 reg [5:0] req_word=0;
 reg [511:0] req_data=0;
 reg [31:0] req_job=0;
 reg [3:0] req_gen=0;
 reg [16:0] req_token=0;
 reg [19:0] req_pos=0;
 wire  rsp_v;
 reg  rsp_r=0;
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
 always @(negedge clk)if(cycles<24)$display("START_TRACE cycle=%0d state=%h ticks=%h code=%h valid=%h grant=%b ctrl1=%h ctrl11=%h",cycles,dut.u_bridge.on.state,dut.u_bridge.on.ticks,dut.u_bridge.on.code[11],dut.u_bridge.on.d[8],dut.borrow_granted,dut.u_bridge.on.ctrl(1,0,0,0),dut.u_bridge.on.ctrl(1,1,0,0));
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
     if(m_req_wstrb[byte_lane] && !(transactions==0 && byte_lane==0))memory[m_req_addr>>5][8*byte_lane+:8]<=m_req_wdata[8*byte_lane+:8];
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
  por_n=0;req_v=0;rsp_r=0;start_v=0;desc_v=0;release_v=0;
  provider_fault=0;result_published=0;source_reverse_done=0;
  peer_quiet=2'b11;peer_lease_v=0;peer_release_v=0;
  job=32'h12345678;gen=4'h9;token=17'h10001;pos=20'hfffff;
  native_job=job;native_gen=gen;native_token=token;native_pos=pos;
  req_job=job;req_gen=gen;req_token=token;req_pos=pos;
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
   req_kind=3'(kind);req_rank=7'(rank);req_word=6'(word_index);
   req_addr=address;req_tag=16'(packets+100);req_data=data;req_v=1;rsp_r=0;
   begin:accept_packet
    for(integer age=0;age<128;age++)begin
     #0.01;check_live();if(req_r)begin edge_tick();disable accept_packet;end
     edge_tick();
    end
    $fatal(1,"packet not accepted kind%0d rank%0d word%0d",kind,rank,word_index);
   end
   req_v=0;
   begin:receive_packet
    for(integer age=0;age<256;age++)begin
     #0.01;check_live();
     if(rsp_v)begin
      if(!rsp_checked||rsp_addr!=address||rsp_tag!=req_tag||rsp_kind!=kind||rsp_data!==oracle)
       $fatal(1,"payload/identity mismatch packet%0d kind%0d rank%0d word%0d",packets,kind,rank,word_index);
      held_response=rsp_data;
      repeat(3)begin edge_tick();#0.01;if(!rsp_v||rsp_data!==held_response||!retained||dut.shared_idle)$fatal(1,"stalled return lost owner/data");end
      rsp_r=1;edge_tick();rsp_r=0;packets++;disable receive_packet;
     end
     edge_tick();
    end
    $fatal(1,"packet response stuck packet%0d kind%0d",packets,kind);
   end
  end
 endtask
 initial begin
  for(k=0;k<32768;k++)memory[k]=0;
  // Poison only the target byte before the actual write. Dropping its strobe
  // leaves A5 instead of the offered page's 00. Read data is actual memory.
  memory[ARENA>>5][7:0]=8'ha5;
  configure();
  expected=page(1,0,0);
  req_kind=1;req_rank=0;req_word=0;req_addr=ARENA;req_tag=100;
  req_data=expected;req_v=1;rsp_r=0;
  begin:accept_fault_page
   for(integer age=0;age<128;age++)begin
    #0.01;check_live();
    if(req_r)begin edge_tick();req_v=0;disable accept_fault_page;end
    edge_tick();
   end
   $fatal(1,"score page not accepted");
  end
  begin:detect_readback_fault
   for(integer age=0;age<256;age++)begin
    #0.01;
    if(rsp_v||arena_visible||sink_visible||release_r)
     $fatal(1,"corrupt byte falsely returned checked/published/released");
    if(fault)disable detect_readback_fault;
    edge_tick();
   end
   $fatal(1,"dropped byte write escaped actual readback comparison");
  end
  // Two real write ACKs and the first matched readback precede the mismatch.
  if(transactions!=3||memory[ARENA>>5][7:0]!==8'ha5)
   $fatal(1,"fault stimulus did not traverse actual write/readback service");
  result_published=1;source_reverse_done=1;release_v=1;
  repeat(16)begin
   edge_tick();#0.01;
   if(!fault||!retained||shared_idle||release_r||rsp_v||arena_visible||sink_visible||m_req_v)
    $fatal(1,"fault lost containment or accepted release/publication");
   if(held_job!==job||held_gen!==gen||held_token!==token||held_pos!==pos)
    $fatal(1,"fault changed retained caller frame");
  end
  if(provider_pending||m_rsp_v||dut.u_shared_owner.on.outstanding||dut.u_shared_owner.on.rq_captured||dut.u_shared_owner.on.rs_captured)
   $fatal(1,"matched accepted transport failed to drain before fault containment");
  $display("PASS_GATHER_READBACK_FAULT accepted_score_page actual3beats dropped_byte mismatch_fault no_publication no_release retained_frame drained_transport");
  $finish;
 end
endmodule
