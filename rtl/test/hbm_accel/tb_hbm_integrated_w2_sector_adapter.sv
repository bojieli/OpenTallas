`timescale 1ns/1ps
// Adapter gate only. REAL shared owner + REAL protected four-seat reservation.
// No native arithmetic replay, synthesized completion, publisher or release.
// All BYTE addresses/tags come from the enclosing installed-source compiler.
module tb_hbm_integrated_w2_sector_adapter;
 reg clk=0,por_n=0;always #0.5 clk=~clk;
 reg [72:0] owner_frame={20'd1048575,17'd16754,4'd1,32'd20};
 reg lease_v=0,reserve_v=0;
 wire [2:0] grants,releases;
 wire owner_fault,owner_idle,prior_empty;
 wire permit,reserve_r,sink_retained,sink_done,sink_quiet,sink_fault;
 wire adapter_busy,adapter_drained,adapter_fault,foreign_rsp;
 reg native_req_v=0;wire native_req_r;
 reg [31:0] native_req_addr=0;reg [9:0] native_req_tag=0;
 reg map_valid=0;
 reg [31:0] map_native_addr=0;
 reg [2:0] map_sm=0,map_count=0;reg [15:0] map_compact_offset=0;
 reg [3:0] map_lanes=0;
 reg [191:0] map_byte_addresses=0;reg [95:0] map_tags=0,map_cfg=0;
 wire req_v,req_r;wire [336:0] req;
 wire rsp_v,rsp_r;wire [272:0] rsp;
 reg inject=0;reg [272:0] alien=0;
 reg delivery=0;wire pending,native_rsp_v;
 wire [9:0] native_rsp_tag;wire [1087:0] native_rsp_data;
 wire [3:0] route_rsp_v,route_rsp_r,route_rsp_we,route_req_r;
 wire [63:0] route_rsp_tags;wire [1023:0] route_rsp_data;
 wire [3:0] authorized;
 wire backend_req_v,backend_req_we,backend_rsp_r;
 wire [31:0] backend_addr,backend_strb;wire [255:0] backend_data;
 wire [15:0] backend_tag;
 reg backend_pending=0;integer cycle=0;
 wire [15:0] backend_saved_tag;wire [255:0] backend_saved_data;
 wire mem_req_r,mem_rsp_v,mem_rsp_we,mem_fault;
 wire request_window=cycle%5>1,response_window=cycle%7>2;
 wire backend_req_r=mem_req_r&&request_window;
 wire backend_rsp_v=mem_rsp_v&&response_window;
 ot_gpu_memsys #(.ENABLE(1),.NC(1),.NS(2),.NPC(2),.MEM_WORDS(2097152),.CLK_PS(1000),.USE_W2(0)) provider(
  .clk(clk),.rst_n(por_n),.req_v(backend_req_v&&request_window),.req_rdy(mem_req_r),
  .req_we(backend_req_we),.req_addr(backend_addr),.req_wdata(backend_data),.req_wstrb(backend_strb),.req_tag(backend_tag),
  .rsp_v(mem_rsp_v),.rsp_rdy(backend_rsp_r&&response_window),.rsp_tag(backend_saved_tag),
  .rsp_we(mem_rsp_we),.rsp_data(backend_saved_data),.fault(mem_fault));
 wire sink_req_v,sink_rsp_r;wire [336:0] sink_req;
 reg [31:0] output_base,output_limit;
 reg output_installed=0;
 ot_hbm_integrated_w2_result_sink #(.ENABLE(1)) sink(
  .clk(clk),.por_n(por_n),.owned(grants[2]),.installed(output_installed),
  .reserve_v(reserve_v),.reserve_r(reserve_r),.pair_op(1'b1),.rows_a(2'd2),.rows_b(2'd2),
  .op_a(32'd0),.op_b(32'd1),.base_a(output_base),.limit_a(output_base+32'd64),
  .base_b(output_base+32'd64),.limit_b(output_limit),.provider_tag(16'hffff),.frame(owner_frame),
  .source_permit(permit),.retained(sink_retained),.done(sink_done),.quiet(sink_quiet),.fault(sink_fault),
  .result_v(1'b0),.result_op(32'd0),.result_row(12'd0),.result_data(256'd0),
  .native_done(1'b0),.retire_v(1'b0),.retire_r(),
  .req_v(sink_req_v),.req_r(1'b0),.req(sink_req),.rsp_v(1'b0),.rsp_r(sink_rsp_r),.rsp(273'd0));
 ot_hbm_integrated_sm0_borrow #(.ENABLE(1)) owner(
  .clk(clk),.por_n(por_n),.native_clients_drained(1'b1),.cdc_drained(!backend_pending),
  .observe_req(4'd0),.observe_rsp(4'd0),.observe_req_we(4'd0),.observe_rsp_we(4'd0),
  .observe_req_tag(64'd0),.observe_rsp_tag(64'd0),.return_offer(4'd0),.response_authorized(authorized),
  .native_job(owner_frame[31:0]),.native_gen(owner_frame[35:32]),
  .native_token(owner_frame[52:36]),.native_pos(owner_frame[72:53]),.native_credit_empty(prior_empty),
  .lease_v({lease_v,2'b0}),.borrower_quiet({adapter_drained&&sink_quiet,2'b11}),
  .lease_job({owner_frame[31:0],64'd0}),.lease_gen({owner_frame[35:32],8'd0}),
  .lease_token({owner_frame[52:36],34'd0}),.lease_pos({owner_frame[72:53],40'd0}),
  .lease_granted(grants),.release_v(3'd0),.release_r(releases),
  .release_job(96'd0),.release_gen(12'd0),.release_token(51'd0),.release_pos(60'd0),
  .req_v({req_v,3'd0}),.req_rdy(route_req_r),.req_we({req[336],3'd0}),
  .req_addr({req[335:304],96'd0}),.req_wdata({req[303:48],768'd0}),
  .req_wstrb({req[47:16],96'd0}),.req_tag({req[15:0],48'd0}),
  .rsp_v(route_rsp_v),.rsp_rdy(route_rsp_r),.rsp_we(route_rsp_we),
  .rsp_tag(route_rsp_tags),.rsp_data(route_rsp_data),
  .m_req_v(backend_req_v),.m_req_rdy(backend_req_r),.m_req_we(backend_req_we),
  .m_req_addr(backend_addr),.m_req_wdata(backend_data),.m_req_wstrb(backend_strb),.m_req_tag(backend_tag),
  .m_rsp_v(backend_rsp_v),.m_rsp_rdy(backend_rsp_r),.m_rsp_we(mem_rsp_we),
  .m_rsp_tag(backend_saved_tag),.m_rsp_data(backend_saved_data),.idle(owner_idle),.fault(owner_fault));
 assign req_r=route_req_r[3];
 assign rsp_v=inject || route_rsp_v[3];
 assign rsp=inject?alien:{route_rsp_tags[63:48],route_rsp_we[3],route_rsp_data[1023:768]};
 assign route_rsp_r={rsp_r&&!inject,3'd0};
 ot_hbm_integrated_w2_sector_adapter #(.ENABLE(1)) dut(
  .clk(clk),.por_n(por_n),.owner_valid(grants[2]),.owner_frame(owner_frame),
  .source_accept_permit(permit),.result_seat_permit(sink_retained&&!sink_fault),
  .native_req_v(native_req_v),.native_req_r(native_req_r),.native_req_addr(native_req_addr),.native_req_tag(native_req_tag),
  .map_valid(map_valid),.map_frame(owner_frame),.map_native_addr(map_native_addr),.map_sm(map_sm),
  .map_compact_offset(map_compact_offset),.map_lanes(map_lanes),.map_count(map_count),
  .map_byte_addresses(map_byte_addresses),.map_tags(map_tags),.map_cfg(map_cfg),
  .sector_req_v(req_v),.sector_req_r(req_r),.sector_req(req),
  .sector_rsp_v(rsp_v),.sector_rsp_r(rsp_r),.sector_rsp(rsp),
  .native_delivery_permit(delivery),.native_rsp_pending(pending),.native_rsp_v(native_rsp_v),
  .native_rsp_tag(native_rsp_tag),.native_rsp_data(native_rsp_data),
  .busy(adapter_busy),.drained(adapter_drained),.fault(adapter_fault),.foreign_rsp(foreign_rsp));
 reg [31:0] source_addresses[0:8191];reg [255:0] memory[0:8191];
 reg [447:0] maps[0:2047];reg [1087:0] expected[0:2047];
 integer nwords,ncases,reads=0,returns=0,takes=0,held_edges=0,foreign_edges=0;
 integer part_seen=0,current_case=0,tag_counter=32768;
 reg [191:0] expected_addresses;reg [95:0] expected_tags;
 reg req_held=0;reg [336:0] old_req;
 function automatic integer locate(input [31:0] address);
  integer lo,hi,mid;begin
   lo=0;hi=nwords-1;locate=-1;
   while(lo<=hi)begin
    mid=(lo+hi)/2;
    if(source_addresses[mid]==address)begin locate=mid;lo=hi+1;end
    else if(source_addresses[mid]<address)lo=mid+1;else hi=mid-1;
   end
  end
 endfunction
 always @(posedge clk)if(por_n)begin
  cycle<=cycle+1;
  if(owner_fault||sink_fault||mem_fault)$fatal(1,"real owner/seat fault");
  if(req_held && (!req_v || req!==old_req))$fatal(1,"request changed while held");
  req_held<=req_v&&!req_r;old_req<=req;
  if(req_v&&!req_r)held_edges<=held_edges+1;
  if(backend_req_v&&backend_req_r)begin
   if(backend_req_we||backend_addr>=output_base&&backend_addr<output_limit||backend_addr!==expected_addresses[part_seen*32+:32]||
      backend_tag!==expected_tags[part_seen*16+:16]||locate(backend_addr)<0)
    $fatal(1,"non-source address/tag/read %0d",current_case);
   backend_pending<=1;reads<=reads+1;part_seen<=part_seen+1;
  end else if(backend_pending)begin
   if(backend_rsp_v&&backend_rsp_r)begin
    if(backend_saved_data!==memory[locate(expected_addresses[(part_seen-1)*32+:32])])$fatal(1,"provider installed byte mismatch");
    backend_pending<=0;
   end
  end
  if(route_rsp_v[3]&&route_rsp_r[3])returns<=returns+1;
  if(inject)begin
   foreign_edges<=foreign_edges+1;
   if(rsp_r||!foreign_rsp)$fatal(1,"foreign response ACK");
  end
  if(native_rsp_v)takes<=takes+1;
 end
 task automatic edge;begin @(posedge clk);#0.01;end endtask
 reg [1023:0] dir;integer watchdog,saved_reads,local_sector;
 initial begin
  if(!$value$plusargs("DIR=%s",dir)||!$value$plusargs("NWORDS=%d",nwords)||
     !$value$plusargs("NCASES=%d",ncases)||!$value$plusargs("OUT_BASE=%h",output_base)||
     !$value$plusargs("OUT_LIMIT=%h",output_limit))$fatal(1,"actual installed fixture/extent required");
  if(nwords>8192||ncases>2048||nwords<1||ncases<1||output_base[5:0]!=0||output_limit!=output_base+128)
   $fatal(1,"fixture bounds");
  $readmemh({dir,"/memory_addresses.hex"},source_addresses,0,nwords-1);
  $readmemh({dir,"/memory.hex"},memory,0,nwords-1);
  $readmemh({dir,"/maps.hex"},maps,0,ncases-1);
  $readmemh({dir,"/expected.hex"},expected,0,ncases-1);
  for(integer j=0;j<nwords;j=j+1)
   if(source_addresses[j][4:0]!=0||(j>0&&source_addresses[j]<=source_addresses[j-1]))$fatal(1,"installed source alias/extent");
  if(locate(output_base)<0||locate(output_base+32)<0||locate(output_base+64)<0||locate(output_base+96)<0)
   $fatal(1,"output extent was not actually allocated/emitted in RAM");
  // Original matching NS2 provider, full 2097152 words per partition.
  // Initial zeroing is complete before the additive addressed overlays load.
  #0.02;
  $readmemh({dir,"/w2_p0.hex"},provider.g_on.g_s[0].u_part.g_on.u_model.mem);
  $readmemh({dir,"/w2_p1.hex"},provider.g_on.g_s[1].u_part.g_on.u_model.mem);
  for(integer j=0;j<nwords;j=j+1)begin
   local_sector=(((source_addresses[j]>>8)<<7)|(source_addresses[j]&127))>>5;
   if(local_sector>=2097152)$fatal(1,"partition alias");
   if(source_addresses[j][7])begin
    if(provider.g_on.g_s[1].u_part.g_on.u_model.mem[local_sector]!==memory[j])$fatal(1,"NS2 overlay1/source mismatch");
   end else if(provider.g_on.g_s[0].u_part.g_on.u_model.mem[local_sector]!==memory[j])$fatal(1,"NS2 overlay0/source mismatch");
  end
  // Real sink reservation follows the genuine shared-owner grant, never tied1.
  repeat(3)edge();@(negedge clk);por_n=1;lease_v=1;
  watchdog=0;while(!grants[2])begin edge();watchdog++;
   if(watchdog>8)$fatal(1,"protected owner quiet-count grant");end
  @(negedge clk);lease_v=0;native_req_v=1;map_valid=0;
  repeat(3)begin edge();if(native_req_r||permit||adapter_busy)$fatal(1,"unreserved admission");end
  @(negedge clk);native_req_v=0;output_installed=1;reserve_v=1;
  edge();if(!sink_retained)$fatal(1,"actual seat reservation missing");
  @(negedge clk);reserve_v=0;
  for(current_case=0;current_case<ncases;current_case=current_case+1)begin
   @(negedge clk);
   {map_cfg,map_tags,map_byte_addresses,map_native_addr,map_sm,map_compact_offset,map_lanes,map_count}=maps[current_case];
   if(tag_counter+integer'(map_count)>65536)$fatal(1,"parent caller tag domain exhausted");
   for(integer j=0;j<6;j=j+1)map_tags[j*16+:16]=16'(tag_counter+j);
   native_req_addr=map_native_addr;native_req_tag=10'(current_case*37);
   map_valid=1;native_req_v=1;delivery=0;part_seen=0;
   expected_addresses=map_byte_addresses;expected_tags=map_tags;
   edge();if(!adapter_busy)$fatal(1,"qualified admission");
   tag_counter=tag_counter+integer'(map_count); // ONLY actual native acceptance.
   @(negedge clk);native_req_v=0;map_valid=0;
   // Foreign full tag and foreign read/write kind must not mutate/ACK the seam.
   wait(backend_pending);@(negedge clk);inject=1;
   alien={expected_tags[15:0]^16'h8000,1'b0,256'hdeadbeef};
   edge();@(negedge clk);alien={expected_tags[15:0],1'b1,256'hbadcafe};
   edge();@(negedge clk);inject=0;
   watchdog=0;
   while(!pending)begin edge();watchdog++;
    // One outstanding read: full refresh blocking plus PRE/ACT/RD,
    // controller/PHY and protected request/return pipeline each sector.
    // Cycles derive unchanged HBM defaults at CLK_PS1000, not a gain cap.
    if(watchdog>6*((350000+16250+28125+19375+12500+10000+10000+2560+999)/1000+32))$fatal(1,"bounded declared backend service");
   end
   repeat(5)begin
    edge();if(native_rsp_v||native_rsp_tag!==10'(current_case*37)||native_rsp_data!==expected[current_case])
     $fatal(1,"held line/tag/data %0d",current_case);
    if(native_req_r||adapter_drained)$fatal(1,"same-edge slot reuse");
   end
   @(negedge clk);delivery=1;edge();
   if(!adapter_drained||adapter_fault||part_seen!==integer'(map_count))$fatal(1,"line retire");
   @(negedge clk);delivery=0;
  end
  edge();if(reads!=returns||takes!=ncases||held_edges==0||foreign_edges!=2*ncases)
   $fatal(1,"accepted sector/line accounting");
  // Invalid cfg must be rejected BEFORE request/partial-line mutation.
  @(negedge clk);map_cfg[15:8]=8'hff;map_valid=1;native_req_v=1;saved_reads=reads;
  edge();if(!adapter_fault||adapter_busy||reads!=saved_reads||native_req_r||req_v)
   $fatal(1,"invalid source map accepted");
  $display("PASS_W2_SECTOR_PARENT_PERMITS cases=%0d reads=%0d returns=%0d held=%0d foreign=%0d seats_retained=%0d",ncases,reads,returns,held_edges,foreign_edges,sink_retained);
  $display("SCOPE adapter bytes/handshakes ONLY; native result publication/owner release NOT exercised");
  $finish;
 end
endmodule
