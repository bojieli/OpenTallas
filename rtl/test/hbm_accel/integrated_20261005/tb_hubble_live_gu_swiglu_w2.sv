`timescale 1ns/1ps
// Minimum live-GU connected runtime; retained mode is default OFF selection.
// Selected GUI inputs are released weights and retained actual FFN_norm/router;
// W2 arithmetic, sector service, checked publication and CP retirement run live.
// expected.hex is comparison ONLY; no lines.hex weight-response shortcut.
module tb_hubble_live_gu_swiglu_w2 #(parameter integer LIVE_SWIGLU=0,LIVE_GU=0);
 `include "private_alloc.svh"
 reg clk=0; always #0.5 clk=~clk;
 reg por_n=0,cmd_we=0,db_v=0,cpl_rdy=0;
 reg [1:0] cmd_addr=0; reg [63:0] cmd_wdata=0;
 localparam [31:0] JOB=32'h9234abcd;
 wire [31:0] OPA=seq[14], OPB=seq[15];
 localparam [3:0] GEN=4'h9;
 localparam [16:0] TOKEN=17'h1a321;
 localparam [19:0] POS=20'hfffff;
 localparam [72:0] FRAME={POS,TOKEN,GEN,JOB};
 wire db_rdy,cpl_v; wire [1:0] launch_v; wire [31:0] launch_pc;
 wire [16:0] launch_token,cpl_token; wire [19:0] launch_pos,cpl_position;
 wire [31:0] cpl_job,cpl_cycles,st_kernels,st_busy; wire [3:0] cpl_generation,cpl_status;
 reg [1:0] sm_done=0,res_v=0; reg [63:0] res_data=0;
 wire shared_fault,sink_fault;
 ot_ds_hbm_cmdproc20 #(.ENABLE(1),.NSM(2),.NCMD(4)) cp(
  .clk(clk),.rst_n(por_n),.cmd_we(cmd_we),.cmd_addr(cmd_addr),.cmd_wdata(cmd_wdata),
  .db_v(db_v),.db_rdy(db_rdy),.db_token(TOKEN),.db_pos(POS),.db_job(JOB),.db_generation(GEN),
  .cpl_position(cpl_position),.cpl_job(cpl_job),.cpl_generation(cpl_generation),
  .launch_v(launch_v),.launch_pc(launch_pc),.launch_token(launch_token),.launch_pos(launch_pos),
  .sm_done(sm_done),.sm_fault({1'b0,shared_fault|sink_fault}),.res_v(res_v),.res_data(res_data),
  .cpl_v(cpl_v),.cpl_rdy(cpl_rdy),.cpl_token(cpl_token),.cpl_status(cpl_status),
  .cpl_cycles(cpl_cycles),.st_kernels(st_kernels),.st_busy(st_busy));
 reg lease_requested=0,reserve_v=0,release_intent=0,allocated=0;
 wire native_done=arrive!=arrive_q;
 wire result_v; wire [31:0] result_op;
 wire [7:0] native_row;wire [11:0] result_row={4'd0,native_row};
 wire [255:0] result_data;
 reg arrive_q=0;wire arrive,native_released,native_fault,native_busy;
 reg release_in=0;
 wire [2:0] grants,releases;
 wire source_permit,retained,sink_done,sink_quiet,sink_retire_r,reserve_r;
 wire s_req_v,s_req_r,s_rsp_v,s_rsp_r;
 wire [336:0] s_req; wire [272:0] s_rsp;
 wire [3:0] req_rdy,rsp_v,rsp_we,response_authorized;
 wire [63:0] rsp_tag; wire [1023:0] rsp_data;
 wire m_req_v,m_req_ready,m_req_we,m_rsp_ready;
 wire [31:0] m_req_addr,m_req_strb; wire [255:0] m_req_data;
 wire [15:0] m_req_tag,m_rsp_tag; wire m_rsp_v,m_rsp_we;wire [255:0] m_rsp_data;
 wire shared_idle,native_credit_empty;
 integer cycle=0,writes=0,reads=0,verified=0,released=0,request_stalls=0,delivery_stalls=0;
 integer accepted_requests=0,consumed_responses=0,sector_reads=0,native_requests=0,native_returns=0;
 integer next_tag=32768;
 reg cp_callback=0;reg sink_transaction=0,native_pending=0;
 reg [9:0] held_native_tag=0;
 reg [31:0] held_provider_addr=0;
 wire provider_drained=!m_rsp_v&&accepted_requests==consumed_responses&&live_gu_quiet;
 wire adapter_drained,adapter_busy,adapter_fault,foreign_rsp;
 wire native_req_v,native_req_r,native_rsp_v,native_rsp_pending;
 wire [31:0] native_req_addr;wire [9:0] native_req_tag,native_rsp_tag;
 wire [1087:0] native_rsp_data;
 wire a_req_v,a_req_r,a_rsp_v,a_rsp_r;wire [336:0] a_req;wire [272:0] a_rsp;
 wire sink_req_v,sink_req_r,sink_rsp_v,sink_rsp_r;wire [336:0] sink_req;
 wire [272:0] sink_rsp;
 wire sink_route=sink_req_v&&adapter_drained;
 assign s_req_v=sink_route||a_req_v;
 assign s_req=sink_route?sink_req:a_req;
 assign sink_req_r=s_req_r&&sink_route;
 assign a_req_r=s_req_r&&!sink_route;
 wire sink_response=adapter_drained&&retained;
 assign sink_rsp_v=s_rsp_v&&sink_response;
 assign a_rsp_v=s_rsp_v&&!sink_response;
 assign sink_rsp=s_rsp;assign a_rsp=s_rsp;
 assign s_rsp_r=sink_response?sink_rsp_r:a_rsp_r;
 wire source_admit=source_permit&&installed&&!sink_transaction&&!sink_route;
 wire native_delivery=grants[2]&&retained&&native_pending&&native_rsp_pending&&
                      native_rsp_tag==held_native_tag&&delivery_enabled;
 reg [31:0] seq[0:15];
 reg [27263:0] xwords[0:31]; // exact NC8 fragment + original bench padding
 reg [447:0] maps[0:63];reg [1087:0] expected_lines[0:63];
 reg [255:0] expected_rows[0:3],captured_rows[0:3];reg [3:0] result_seen=0;
 reg [31:0] source_addresses[0:8191];reg [255:0] source_memory[0:8191];integer nwords;
 reg [1023:0] dir;
 reg start=0,d_valid=0,legacy_xw_en=0;wire start_ready,d_ready;
 reg [6:0] legacy_xw_addr=0,legacy_xw_grp=0;reg [2047:0] legacy_xw_data=0;
 wire producer_xw_en,producer_done,producer_fault;
 wire [6:0] producer_xw_addr,producer_xw_grp,producer_issue_index;
 wire [4:0] producer_fragment_index;
 wire [2047:0] producer_xw_data;
 wire xw_en=LIVE_SWIGLU?producer_xw_en:legacy_xw_en;
 wire [6:0] xw_addr=LIVE_SWIGLU?producer_xw_addr:legacy_xw_addr;
 wire [6:0] xw_grp=LIVE_SWIGLU?producer_xw_grp:legacy_xw_grp;
 wire [2047:0] xw_data=LIVE_SWIGLU?producer_xw_data:legacy_xw_data;
 reg live_gu_start=0;
 wire live_gu_ready,live_gu_quiet,live_gu_fault;
 wire [2047:0] live_gu_g,live_gu_u;
 ot_hubble_live_gu_source_driver #(.ENABLE(LIVE_GU)) live_gu(
  .clk(clk),.rst_n(por_n),.start(live_gu_start),.retire(producer_done),
  .permit(source_permit&&installed&&grants[2]),.frame(FRAME),.op_a(OPA),.op_b(OPB),
  .issue_index(producer_issue_index),.g(live_gu_g),.u(live_gu_u),
  .ready(live_gu_ready),.quiet(live_gu_quiet),.fault(live_gu_fault));
 reg producer_start=0;
 reg [31:0] producer_g[0:4607],producer_u[0:4607],producer_w[0:4607];
 reg [31:0] producer_limit=0;reg [1023:0] producer_dir;
 wire [2047:0] producer_gbeat,producer_ubeat,producer_wbeat;
 genvar pl;
 generate for(pl=0;pl<64;pl=pl+1)begin:g_producer_operands
  assign producer_gbeat[32*pl+:32]=LIVE_GU?live_gu_g[32*pl+:32]:producer_issue_index<72?producer_g[64*producer_issue_index+pl]:32'd0;
  assign producer_ubeat[32*pl+:32]=LIVE_GU?live_gu_u[32*pl+:32]:producer_issue_index<72?producer_u[64*producer_issue_index+pl]:32'd0;
  assign producer_wbeat[32*pl+:32]=producer_issue_index<72?producer_w[64*producer_issue_index+pl]:32'd0;
 end
 if(LIVE_SWIGLU)begin:g_live_swiglu
  ot_hubble_swiglu_w2_capture #(.ENABLE(1)) producer(
   .clk(clk),.rst_n(por_n),.start(producer_start),
   .permit(source_permit&&installed&&grants[2]),.frame(FRAME),.op_a(OPA),.op_b(OPB),
   .g(producer_gbeat),.u(producer_ubeat),.w(producer_wbeat),.lim(producer_limit),
   .inactive_template(xwords[producer_fragment_index][4095:3152]),
   .issue_index(producer_issue_index),.fragment_index(producer_fragment_index),
   .xw_en(producer_xw_en),.xw_addr(producer_xw_addr),.xw_grp(producer_xw_grp),
   .xw_data(producer_xw_data),.done(producer_done),.fault(producer_fault));
 end else begin:g_retained_swiglu
  assign producer_xw_en=0;assign producer_xw_addr=0;assign producer_xw_grp=0;
  assign producer_xw_data=0;assign producer_done=0;assign producer_fault=0;
  assign producer_issue_index=0;assign producer_fragment_index=0;
 end endgenerate
 reg operands_loaded=0;
 wire op_bound=installed&&seq[0]==4&&seq[4]==64&&seq[10]==1&&OPA!=OPB&&
               seq[1]==8&&seq[2]==2&&seq[3]==2&&seq[5]==1&&
               seq[7]==16&&seq[13]==16&&seq[11]==32&&seq[12]==16&&seq[9]==0;
 wire d_bound=op_bound&&source_permit;
 wire start_qualified=start&&source_permit&&operands_loaded&&op_bound;
 wire descriptor_qualified=d_valid&&d_bound;
 ot_hbm_accel_w2_caller #(.ENABLE(1),.PQ_ENABLE(1),.PACK_W2(1),.SUB(4),.LBS(2),.LSB(16),
  .NC(8),.RMAX(256),.LEV(4),.XD(128),.MAX_OUT(512),.HAZ(1),.G1ASB(0)) native_w2(
  .clk(clk),.rst_n(por_n),.start(start_qualified),.start_ready(start_ready),
  .op_rows(9'(seq[0])),.op_c(16'(seq[1])),.op_g(8'(seq[2])),.op_gs(seq[5][0]),
  .op_fmt(seq[3][1:0]),.op_xb(seq[9][6:0]),.op_pack_w2(seq[10][0]),
  .op_pack_delta_x(7'(seq[12]-seq[9])),.op_bound(op_bound),.op_id_a(OPA),.op_id_b(OPB),
  .d_valid(descriptor_qualified),.d_ready(d_ready),.d_base(32'd0),.d_lines(seq[4][23:0]),
  .d_pair(seq[10][0]),.d_bound(d_bound),.d_base_b(seq[11]),
  .req_v(native_req_v),.req_ready(native_req_r),.req_addr(native_req_addr),.req_tag(native_req_tag),
  .rsp_v(native_rsp_v),.rsp_tag(native_rsp_tag),.rsp_data(native_rsp_data),
  .xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),
  .rv(result_v),.rop(result_op),.rrow(native_row),.rdata(result_data),.fault(native_fault),
  .busy(native_busy),.arrive(arrive),.release_in(release_in),.released(native_released));
 wire [447:0] selected_map=native_req_addr<64?maps[native_req_addr[5:0]]:448'd0;
 wire [95:0] map_tags={16'(next_tag+5),16'(next_tag+4),16'(next_tag+3),
                      16'(next_tag+2),16'(next_tag+1),16'(next_tag)};
 ot_hbm_integrated_w2_sector_adapter #(.ENABLE(1)) adapter(
  .clk(clk),.por_n(por_n),.owner_valid(grants[2]),.owner_frame(FRAME),
  .source_accept_permit(source_admit),.result_seat_permit(retained&&!sink_fault),
  .native_req_v(native_req_v),.native_req_r(native_req_r),.native_req_addr(native_req_addr),.native_req_tag(native_req_tag),
  .map_valid(installed&&native_req_addr<64&&selected_map[57:26]==native_req_addr),
  .map_frame(FRAME),.map_native_addr(selected_map[57:26]),.map_sm(selected_map[25:23]),
  .map_compact_offset(selected_map[22:7]),.map_lanes(selected_map[6:3]),.map_count(selected_map[2:0]),
  .map_byte_addresses(selected_map[249:58]),.map_tags(map_tags),.map_cfg(selected_map[441:346]),
  .sector_req_v(a_req_v),.sector_req_r(a_req_r),.sector_req(a_req),
  .sector_rsp_v(a_rsp_v),.sector_rsp_r(a_rsp_r),.sector_rsp(a_rsp),
  .native_delivery_permit(native_delivery),.native_rsp_pending(native_rsp_pending),
  .native_rsp_v(native_rsp_v),.native_rsp_tag(native_rsp_tag),.native_rsp_data(native_rsp_data),
  .busy(adapter_busy),.drained(adapter_drained),.fault(adapter_fault),.foreign_rsp(foreign_rsp));
 wire mem_req_r,mem_rsp_v,mem_rsp_we,mem_fault;
 wire [15:0] mem_rsp_tag;wire [255:0] mem_rsp_data;
 wire request_window=cycle%5>=2,response_window=cycle%7>=2;
 ot_gpu_memsys #(.ENABLE(1),.NC(1),.NS(2),.NPC(2),.MEM_WORDS(2097152),.CLK_PS(1000),.USE_W2(0),.DIE_IDX(0)) provider(
  .clk(clk),.rst_n(por_n),.req_v(m_req_v&&request_window),.req_rdy(mem_req_r),
  .req_we(m_req_we),.req_addr(m_req_addr),.req_wdata(m_req_data),.req_wstrb(m_req_strb),.req_tag(m_req_tag),
  .rsp_v(mem_rsp_v),.rsp_rdy(m_rsp_ready&&response_window),.rsp_tag(mem_rsp_tag),
  .rsp_we(mem_rsp_we),.rsp_data(mem_rsp_data),.fault(mem_fault));
 assign m_req_ready=mem_req_r&&request_window;
 assign m_rsp_v=mem_rsp_v&&response_window;
 assign m_rsp_tag=mem_rsp_tag;assign m_rsp_we=mem_rsp_we;assign m_rsp_data=mem_rsp_data;
 function automatic integer locate(input [31:0] address);
  integer lo,hi,mid;begin lo=0;hi=nwords-1;locate=-1;
   while(lo<=hi)begin mid=(lo+hi)/2;
    if(source_addresses[mid]==address)begin locate=mid;lo=hi+1;end
    else if(source_addresses[mid]<address)lo=mid+1;else hi=mid-1;
   end
  end
 endfunction
 wire installed=allocated && BASE_A[5:0]==0 && BASE_B[5:0]==0 &&
  LIMIT_A==BASE_A+64 && LIMIT_B==BASE_B+64 && LIMIT_A<=BASE_B && LIMIT_B<=RAM_BYTES;
 wire delivery_enabled=cycle%7>=2;
 // Same parent hook: native completion alone is insufficient to request release.
 wire release_v=release_intent&&sink_retire_r;
 wire release_accept=release_v&&releases[2];
 ot_hbm_integrated_sm0_borrow #(.ENABLE(1)) owner(
  .clk(clk),.por_n(por_n),.native_clients_drained(accepted_requests==consumed_responses),
  .cdc_drained(provider_drained),.observe_req(4'b0),.observe_rsp(4'b0),
  .observe_req_we(4'b0),.observe_rsp_we(4'b0),.observe_req_tag(64'b0),.observe_rsp_tag(64'b0),
  .return_offer(4'b0),.response_authorized(response_authorized),
  .native_job(JOB),.native_gen(GEN),.native_token(TOKEN),.native_pos(POS),.native_credit_empty(native_credit_empty),
  .lease_v({lease_requested,2'b0}),.borrower_quiet({!retained&&adapter_drained&&live_gu_quiet,2'b11}),
  .lease_job({JOB,64'b0}),.lease_gen({GEN,8'b0}),.lease_token({TOKEN,34'b0}),.lease_pos({POS,40'b0}),
  .lease_granted(grants),.release_v({release_v,2'b0}),.release_r(releases),
  .release_job({JOB,64'b0}),.release_gen({GEN,8'b0}),.release_token({TOKEN,34'b0}),.release_pos({POS,40'b0}),
  .req_v({s_req_v,3'b0}),.req_rdy(req_rdy),.req_we({s_req[336],3'b0}),
  .req_addr({s_req[335:304],96'b0}),.req_wdata({s_req[303:48],768'b0}),
  .req_wstrb({s_req[47:16],96'b0}),.req_tag({s_req[15:0],48'b0}),
  .rsp_v(rsp_v),.rsp_rdy({s_rsp_r&&delivery_enabled,3'b0}),.rsp_we(rsp_we),.rsp_tag(rsp_tag),.rsp_data(rsp_data),
  .m_req_v(m_req_v),.m_req_rdy(m_req_ready),.m_req_we(m_req_we),.m_req_addr(m_req_addr),
  .m_req_wdata(m_req_data),.m_req_wstrb(m_req_strb),.m_req_tag(m_req_tag),
  .m_rsp_v(m_rsp_v),.m_rsp_rdy(m_rsp_ready),.m_rsp_we(m_rsp_we),.m_rsp_tag(m_rsp_tag),.m_rsp_data(m_rsp_data),
  .idle(shared_idle),.fault(shared_fault));
 assign s_req_r=req_rdy[3];
 assign s_rsp_v=rsp_v[3]&&delivery_enabled;
 assign s_rsp={rsp_tag[63:48],rsp_we[3],rsp_data[1023:768]};
 ot_hbm_integrated_w2_result_sink #(.ENABLE(1)) sink(
  .clk(clk),.por_n(por_n),.owned(grants[2]),.installed(installed),.reserve_v(reserve_v),.reserve_r(reserve_r),
  .pair_op(1'b1),.rows_a(2'd2),.rows_b(2'd2),.op_a(OPA),.op_b(OPB),
  .base_a(BASE_A),.limit_a(LIMIT_A),.base_b(BASE_B),.limit_b(LIMIT_B),.provider_tag(16'hf239),.frame(FRAME),
  .source_permit(source_permit),.retained(retained),.done(sink_done),.quiet(sink_quiet),.fault(sink_fault),
  .result_v(result_v),.result_op(result_op),.result_row(result_row),.result_data(result_data),
  .native_done(native_done),.retire_v(release_accept),.retire_r(sink_retire_r),
  .req_v(sink_req_v),.req_r(sink_req_r),.req(sink_req),.rsp_v(sink_rsp_v),.rsp_r(sink_rsp_r),.rsp(sink_rsp));
 function automatic [255:0] literal_row(input integer index);
  literal_row=expected_rows[index]; // comparison ONLY
 endfunction
 function automatic integer address_slot(input integer a);
  if(a==BASE_A)address_slot=0;else if(a==BASE_A+32)address_slot=1;
  else if(a==BASE_B)address_slot=2;else if(a==BASE_B+32)address_slot=3;else address_slot=-1;
 endfunction
 integer slot,j;reg [255:0] expected_row;
 reg [63:0] accepted_native_addresses=0;
 always @(posedge clk)if(por_n)begin
  cycle<=cycle+1;arrive_q<=arrive;
  // Retained packets compare ONLY. Active operands come from live numerical q/e.
  if(LIVE_SWIGLU&&producer_xw_en&&producer_xw_data!==xwords[producer_fragment_index][2048*producer_xw_grp+:2048])
   $fatal(1,"live SwiGLU FP8 transpose differs from retained native packets");
  if(shared_fault||sink_fault||adapter_fault||native_fault||mem_fault||foreign_rsp||producer_fault||live_gu_fault)
   $fatal(1,"connected source fault cycle=%0d native_req=%0d returns=%0d",cycle,native_requests,native_returns);
  if((release_accept||cp_callback||cpl_v)&&(verified!=4||!adapter_drained||!provider_drained))
   $fatal(1,"early release/CPL before real publication/provider drain");
  if(native_req_v&&native_req_r)begin
   if(native_pending||native_req_addr>=64||accepted_native_addresses[native_req_addr]||next_tag+integer'(selected_map[2:0])>65536)
    $fatal(1,"native identity/address/tag domain duplicate");
   native_pending<=1;held_native_tag<=native_req_tag;
   accepted_native_addresses[native_req_addr]<=1;
   next_tag<=next_tag+integer'(selected_map[2:0]);native_requests<=native_requests+1;
   $display("NATIVE_REQUEST_ACCEPT cycle=%0d addr=%0d tag=%0d",cycle,native_req_addr,native_req_tag);
  end
  if(native_rsp_v)begin
   if(!native_pending||native_rsp_tag!==held_native_tag||native_rsp_data!==expected_lines[adapter.g_on.held_native_addr])
    $fatal(1,"native returned source line/identity mismatch");
   native_pending<=0;native_returns<=native_returns+1;
   $display("NATIVE_RETURN_ACCEPT cycle=%0d tag=%0d",cycle,native_rsp_tag);
  end
  if(sink_req_v&&sink_req_r)sink_transaction<=1;
  if(sink_rsp_v&&sink_rsp_r)sink_transaction<=0;
  if(result_v)begin
   slot=result_op==OPA?integer'(result_row):(result_op==OPB?2+integer'(result_row):-1);
   if(slot<0||slot>=4||result_seen[slot]||result_data!==expected_rows[slot]||!retained||!grants[2])
    $fatal(1,"native result bits/owner/row mismatch");
   result_seen[slot]<=1;captured_rows[slot]<=result_data;
   $display("ACTUAL_NATIVE_RESULT cycle=%0d op=%0d row=%0d data=%h",cycle,result_op,result_row,result_data);
  end
  if(native_done)begin
   if(native_requests!=64||native_returns!=64||!(result_seen==15||(result_v&&(result_seen|(4'b1<<slot))==15)))
    $fatal(1,"native completion with outstanding result/source debt");
   release_intent<=1;
  end
  sm_done<=0;res_v<=0;
  if(release_accept)begin
   if(!provider_drained||!sink_done||verified!=4||native_pending||!adapter_drained||result_seen!=15)
    $fatal(1,"release without checked actual publication");
   released<=released+1;cp_callback<=1;release_in<=arrive;
   sm_done<=2'b01;res_v<=2'b01;res_data<={32'b0,15'b0,TOKEN};
   $display("ACTUAL_SHARED_RELEASE cycle=%0d verified=%0d",cycle,verified);
  end
  if(m_req_v&&!m_req_ready)request_stalls<=request_stalls+1;
  if(rsp_v[3]&&!delivery_enabled)delivery_stalls<=delivery_stalls+1;
  if(m_req_v&&m_req_ready)begin
   if(!installed||!grants[2]||accepted_requests!=consumed_responses)$fatal(1,"provider ownership/capacity");
   held_provider_addr<=m_req_addr;accepted_requests<=accepted_requests+1;
   slot=address_slot(integer'(m_req_addr));
   if(slot>=0)begin
    if(!adapter_drained)$fatal(1,"unallocated native result write/read");
    if(m_req_we)begin
     if(m_req_strb!==32'hffffffff||m_req_data!==captured_rows[slot])$fatal(1,"publication differs from actual native result");
     writes<=writes+1;
    end else reads<=reads+1;
   end else begin
    if(m_req_we||locate(m_req_addr)<0||slot>=0)$fatal(1,"non-source sector request");
    sector_reads<=sector_reads+1;
   end
   $display("ACTUAL_PROVIDER_ACCEPT cycle=%0d we=%0d byte_address=%0d tag=%0d sink=%0d",cycle,m_req_we,m_req_addr,m_req_tag,slot>=0);
  end
  if(m_rsp_v&&m_rsp_ready)begin
   if(!m_rsp_we&&address_slot(integer'(held_provider_addr))<0&&
      (locate(held_provider_addr)<0||m_rsp_data!==source_memory[locate(held_provider_addr)]))
    $fatal(1,"actual installed sector response mismatch");
   consumed_responses<=consumed_responses+1;
  end
  if(sink_rsp_v&&sink_rsp_r&&!sink_rsp[256])begin
   slot=address_slot(integer'(held_provider_addr));
   if(slot<0||sink_rsp[255:0]!==captured_rows[slot]||sink_rsp[255:0]!==expected_rows[slot])
    $fatal(1,"actual native publication readback mismatch");
   verified<=verified+1;$display("ACTUAL_PUBLICATION_VERIFIED cycle=%0d slot=%0d",cycle,slot);
  end
 end
 reg [76:0] held_cpl;
 initial begin
  if(!$value$plusargs("DIR=%s",dir)||!$value$plusargs("NWORDS=%d",nwords)||nwords<1||nwords>8192)
   $fatal(1,"actual retained producer/installed source files required");
  $readmemh({dir,"/seq.hex"},seq,0,15);
  $readmemh({dir,"/x.hex"},xwords,0,31);
  $readmemh({dir,"/maps.hex"},maps,0,63);
  $readmemh({dir,"/expected_lines.hex"},expected_lines,0,63);
  $readmemh({dir,"/expected_rows.hex"},expected_rows,0,3);
  $readmemh({dir,"/memory_addresses.hex"},source_addresses,0,nwords-1);
  $readmemh({dir,"/memory.hex"},source_memory,0,nwords-1);
  if(LIVE_SWIGLU)begin
   if(!$value$plusargs("PRODUCER_DIR=%s",producer_dir)||!$value$plusargs("SWIGLU_LIMIT=%h",producer_limit))
    $fatal(1,"retained actual GU/route/limit boundary required");
   if(!LIVE_GU)begin
    $readmemh({producer_dir,"/g.mem"},producer_g,0,4607);
    $readmemh({producer_dir,"/u.mem"},producer_u,0,4607);
   end
   $readmemh({producer_dir,"/w.mem"},producer_w,0,4607);
   if(!LIVE_GU)for(integer k=0;k<4608;k=k+1)
    if(producer_g[k][15:0]!=0||producer_u[k][15:0]!=0)
     $fatal(1,"retained GU boundary must preserve original BF16 rounding");
  end
  if(LIVE_GU&&!LIVE_SWIGLU)$fatal(1,"live GU requires the actual numerical SwiGLU path");
  #0.02;
  // Original provider initial image load precedes additive installed overlays.
  $readmemh({dir,"/w2_p0.hex"},provider.g_on.g_s[0].u_part.g_on.u_model.mem);
  $readmemh({dir,"/w2_p1.hex"},provider.g_on.g_s[1].u_part.g_on.u_model.mem);
  for(integer k=0;k<nwords;k=k+1)begin
   if(source_addresses[k][4:0]!=0||(k>0&&source_addresses[k]<=source_addresses[k-1]))$fatal(1,"source alias");
   j=(((source_addresses[k]>>8)<<7)|(source_addresses[k]&127))>>5;
   if(j>=2097152)$fatal(1,"physical NS2 range");
   if(source_addresses[k][7])begin
    if(provider.g_on.g_s[1].u_part.g_on.u_model.mem[j]!==source_memory[k])$fatal(1,"original overlay1/source mismatch");
   end else if(provider.g_on.g_s[0].u_part.g_on.u_model.mem[j]!==source_memory[k])$fatal(1,"original overlay0/source mismatch");
  end
  if(locate(BASE_A)<0||locate(BASE_A+32)<0||locate(BASE_B)<0||locate(BASE_B+32)<0||RAM_BYTES!=134217728)
   $fatal(1,"actual allocator output extents absent");
  repeat(3)@(negedge clk);por_n=1;
  repeat(2)@(negedge clk);allocated=1;#0.001;
  if(!op_bound)$fatal(1,"selected retained pair/installed descriptor mismatch");
  cmd_we=1;cmd_addr=0;cmd_wdata=64'h1000100000000321;
  @(negedge clk);cmd_addr=1;cmd_wdata=64'h2000000000000000;
  @(negedge clk);cmd_we=0;db_v=1;
  @(negedge clk);db_v=0;
  wait(launch_v[0]);
  if(launch_token!==TOKEN||launch_pos!==POS||launch_pc!==32'h321)$fatal(1,"CP launch identity");
  @(negedge clk);lease_requested=1;wait(grants[2]);@(negedge clk);
  if(source_permit)$fatal(1,"source permission before reserve");
  reserve_v=1;wait(reserve_r);@(negedge clk);reserve_v=0;lease_requested=0;
  if(!source_permit)$fatal(1,"missing real four-seat reservation");
  if(LIVE_SWIGLU)begin
   if(LIVE_GU)begin
    $display("ACTUAL_LIVE_GU_STAGE_START cycle=%0d",cycle);
    live_gu_start=1;@(negedge clk);live_gu_start=0;
    wait(live_gu_ready);@(negedge clk);
    $display("ACTUAL_LIVE_GU_STAGE_READY cycle=%0d",cycle);
   end
   if(LIVE_GU)$display("ACTUAL_LIVE_SWIGLU_STAGE_START cycle=%0d",cycle);
   producer_start=1;@(negedge clk);producer_start=0;
   wait(producer_done);@(negedge clk);
   if(LIVE_GU)$display("ACTUAL_LIVE_SWIGLU_STAGE_DONE cycle=%0d",cycle);
  end else begin
  // Historical retained operand path, default unchanged.
  for(integer half=0;half<2;half=half+1)begin
   for(integer word_index=0;word_index<16;word_index=word_index+1)
    for(integer beat=0;beat<2;beat=beat+1)begin
     legacy_xw_en=1;legacy_xw_addr=7'(seq[half==0?9:12]+word_index);legacy_xw_grp=7'(beat);
     legacy_xw_data=xwords[half*16+word_index][beat*2048+:2048];@(negedge clk);
    end
   legacy_xw_en=0;@(negedge clk);
  end
  end
  operands_loaded=1;d_valid=1;#0.001;
  do @(posedge clk);while(!d_ready);
  @(negedge clk);d_valid=0;start=1;#0.001;
  do @(posedge clk);while(!start_ready);
  if(LIVE_GU)$display("ACTUAL_W2_EXEC_ACCEPT cycle=%0d",cycle);
  @(negedge clk);start=0;
  wait(cpl_v);@(negedge clk);
  if(cpl_status!=0||cpl_token!==TOKEN||cpl_position!==POS||cpl_job!==JOB||cpl_generation!==GEN||released!=1||grants!=0)
   $fatal(1,"actual END/CPL identity/release");
  held_cpl={cpl_job,cpl_generation,cpl_position,cpl_token,cpl_status};
  repeat(12)begin @(negedge clk);
   if(!cpl_v||{cpl_job,cpl_generation,cpl_position,cpl_token,cpl_status}!==held_cpl||db_rdy)
    $fatal(1,"held actual CPL mutated");
  end
  if(writes!=4||reads!=4||verified!=4||result_seen!=15||native_requests!=64||native_returns!=64||
     accepted_native_addresses!==64'hffffffffffffffff||!provider_drained||!adapter_drained||!native_released||
     request_stalls==0||delivery_stalls==0)$fatal(1,"exact source/result/debt/stall/retirement counts");
  cpl_rdy=1;@(negedge clk);cpl_rdy=0;
  if(cpl_v||!db_rdy)$fatal(1,"actual CPL take exactly once");
  $display("PASS_NATIVE_W2_CONNECTED_PUBLICATION_CPL rows=4 sectors=%0d requests=%0d returns=%0d writes=%0d readbacks=%0d sharedrelease=%0d cycles=%0d",sector_reads,native_requests,native_returns,writes,verified,released,cycle);
  if(LIVE_SWIGLU)begin
   $display("PASS_LIVE_SWIGLU_W2_CONNECTED_PUBLICATION_CPL producers=2 elements=4608 blocks=144");
   if(!LIVE_GU)$display("SCOPE retained actual GU/route inputs; live SwiGLU+FP8 transpose+W2+NS2+publication+END/CPL; GU and full token NOT live");
  end else $display("SCOPE retained native GU/SwiGLU input boundary; live W2+installed NS2 sectors+protected publication+END/CPL only");
  if(LIVE_GU)begin
   if(!live_gu_quiet)$fatal(1,"GU source debt at CPL");
   $display("PASS_LIVE_TC_PROTECTED_GU_SWIGLU_W2_NATIVE_CPL GUrows=9216 spans=768 W2rows=4 metadata_coded=216 cycles=%0d",cycle);
   $display("SCOPE live released TC->W6 protected CVT retirement->protected GU capture->SwiGLU->W2/NS2/readback/release/CPL; retained actual FFN_norm/router upstream; minimum component, NOT full token or physical PASS");
  end
  $finish;
 end
endmodule
