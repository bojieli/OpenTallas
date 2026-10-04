`timescale 1ps/1fs
// Combined c52 fetch + finite52ce3 successor + real ownership CDC/ACK path.
// Physical task owner comes from the enclosing launcher. payload_drained is
// local data-path completion; it is NOT native/issuer/RF-lease completion.
module ot_hbm_accel_expert_stack #(parameter ENABLE=0,NSM=8,DEPTH=1024,MAX_OUT=512,DQ=64,STACK=0,DIE=0,PHASE=0)(
 input wire stream_clk,service_clk,por_n,run_enable,
 input wire task_v,output wire task_r,input ot_hbm_r14_pkg::identity_t task_id,input wire[15:0] task_experts,
 input wire[31:0] cfg_base,input wire[15:0] cfg_exp_lines,
 input wire[NSM*16-1:0] cfg_off,cfg_lines,
 input wire e_valid,output wire e_ready,input wire[8:0] e_id,
 output wire[NSM-1:0] s_valid,input wire[NSM-1:0] s_ready,output wire[NSM*1024-1:0] s_data,
 output wire[31:0] row_v,input wire[31:0] row_gnt,
 output wire[95:0] row_op,output wire[159:0] row_bank,output wire[607:0] row_row,
 output wire[31:0] col_v,input wire[31:0] col_gnt,output ot_hbm_r14_pkg::command_t col_cmd[0:31],
 input wire[31:0] rsp_v,output wire[31:0] rsp_r,input wire[511:0] rsp_tag,
 input wire[159:0] rsp_beat,input wire[8191:0] rsp_data,
 output wire payload_drained,output wire fault);
 import ot_hbm_r14_pkg::*;import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
  assign task_r=0;assign e_ready=0;assign s_valid=0;assign s_data=0;
  assign row_v=0;assign row_op=0;assign row_bank=0;assign row_row=0;
  assign col_v=0;assign rsp_r=0;assign payload_drained=1;assign fault=0;
  for(genvar p=0;p<32;p=p+1)assign col_cmd[p]='0;
 end else begin:on
  typedef struct packed{logic live,sticky,token,wait_drain;identity_t id;logic[15:0] target,accepted;} task_t;
  task_t t,nt;reg[287:0] tseal;
  function automatic[287:0] seal_task(input task_t raw);
   for(integer w=0;w<4;w=w+1)seal_task[w*72+:72]=encode64(64'(256'(raw)>>(w*64)));
  endfunction
  wire tbad=tseal!=seal_task(t);
  wire fetch_idle,service_idle,service_fault,f_req_v,f_req_r,f_e_ready;
  wire[33:0] f_addr;wire[5:0] f_len;wire[15:0] f_tag;
  wire[31:0] f_rsp_v,f_rsp_r;wire[511:0] f_rsp_tag;wire[159:0] f_rsp_beat;wire[8191:0] f_rsp_data;
  wire[31:0] owned_v,owned_r,crossing_fault,crossing_empty;
  owned_t from_service[0:31],to_fetch[0:31];
  request_t to_service,request_word;
  wire qv,qr,qwr;
  // Completion is an actual cross-domain drain request/receipt. No raw idle
  // or reverse-domain status is sampled as stream-clock completion.
  (* async_reg="true" *) reg enable1,enable2,drain1,drain2,done1,done2,bad1,bad2;
  reg done_token;reg[71:0] done_seal;
  wire done_bad=done_seal!=encode64(64'(done_token));
  wire service_bad=service_fault||(|crossing_fault)||(qv&&qbad)||done_bad;
  wire requested_token=t.wait_drain?t.token:done2;
  always @(posedge service_clk or negedge por_n)
   if(!por_n)begin enable1<=0;enable2<=0;drain1<=0;drain2<=0;end
   else begin enable1<=run_enable;enable2<=enable1;drain1<=requested_token;drain2<=drain1;end
  always @(posedge stream_clk or negedge por_n)
   if(!por_n)begin done1<=0;done2<=0;bad1<=0;bad2<=0;end
   else begin done1<=done_token;done2<=done1;bad1<=service_bad;bad2<=bad1;end
  wire done_next=(drain2!=done_token&&service_idle&&(&crossing_empty)&&!qv&&!service_bad)?drain2:done_token;
  always @(posedge service_clk or negedge por_n)
   if(!por_n)begin done_token<=0;done_seal<=0;end
   else begin done_token<=done_next;done_seal<=encode64(64'(done_next));end
  wire[575:0] coded_request,received_request;
  wire[511:0] decoded;wire[7:0] ue;
  always @*begin request_word='0;request_word.id=t.id;request_word.id.sector=f_addr;
    request_word.id.caller=f_tag;request_word.len=f_len;end
  for(genvar w=0;w<8;w=w+1)begin
   assign coded_request[w*72+:72]=encode64(64'(512'(request_word)>>(w*64)));
   wire[65:0] d=decode64(received_request[w*72+:72]);
   assign decoded[w*64+:64]=d[63:0];assign ue[w]=d[65];
  end
  wire qbad=(|ue)||(|decoded[511:455]);
  assign to_service=request_t'(decoded[454:0]);
  assign fault=t.sticky||tbad||bad2;
  assign f_req_r=qwr&&!fault&&run_enable;
  assign e_ready=f_e_ready&&t.live&&t.accepted<t.target&&!fault&&run_enable;
  ot_hbm_accel_expert_fetch #(.ENABLE(1),.AW(34),.NSM(NSM),.DEPTH(DEPTH),.MAX_OUT(MAX_OUT),.DQ(DQ)) fetch(
   .clk(stream_clk),.rst_n(por_n),.cfg_base(cfg_base),.cfg_exp_lines(cfg_exp_lines),.cfg_off(cfg_off),.cfg_lines(cfg_lines),
   .e_valid(e_valid&&e_ready),.e_ready(f_e_ready),.e_id(e_id),
   .req_v(f_req_v),.req_rdy(f_req_r),.req_addr(f_addr),.req_len(f_len),.req_tag(f_tag),
   .rsp_v(f_rsp_v),.rsp_rdy(f_rsp_r),.rsp_tag(f_rsp_tag),.rsp_beat(f_rsp_beat),.rsp_data(f_rsp_data),
   .s_valid(s_valid),.s_ready(s_ready),.s_data(s_data),.idle(fetch_idle));
  ot_hbm_r14_fifo2 #(.WIDTH(576)) request_crossing(.wc(stream_clk),.wrn(por_n),
   .wv(f_req_v&&run_enable&&!fault),.wr(qwr),.wd(coded_request),
   .rc(service_clk),.rrn(por_n),.rv(qv),.rr(qr&&!qbad),.rd(received_request));
  ot_hbm_accel_expert_service #(.ENABLE(1),.STACK(STACK),.DIE(DIE),.PHASE(PHASE)) service(
   .clk(service_clk),.por_n(por_n),.run_enable(enable2),.req_v(qv&&!qbad&&!service_bad),.req_r(qr),.req(to_service),
   .row_v(row_v),.row_gnt(row_gnt),.row_op(row_op),.row_bank(row_bank),.row_row(row_row),
   .col_v(col_v),.col_gnt(col_gnt),.col_cmd(col_cmd),.rsp_v(rsp_v),.rsp_r(rsp_r),
   .rsp_tag(rsp_tag),.rsp_beat(rsp_beat),.rsp_data(rsp_data),
   .owned_v(owned_v),.owned_r(owned_r),.owned(from_service),.fault(service_fault),.idle(service_idle));
  for(genvar p=0;p<32;p=p+1)begin
   ot_hbm_accel_owned_crossing crossing(.service_clk(service_clk),.stream_clk(stream_clk),.por_n(por_n),
    .iv(owned_v[p]),.ir(owned_r[p]),.id(from_service[p]),.ov(f_rsp_v[p]),.ore(f_rsp_r[p]),.od(to_fetch[p]),
    .fault(crossing_fault[p]),.empty(crossing_empty[p]));
   assign f_rsp_tag[p*16+:16]=to_fetch[p].id.caller;
   assign f_rsp_beat[p*5+:5]=to_fetch[p].beat;
   assign f_rsp_data[p*256+:256]=to_fetch[p].data;
  end
  // Request valid is part of local debt; a not-yet-synchronised request must
  // not be mistaken for service idle. The enclosing owner retains its lease.
  assign payload_drained=t.live&&t.wait_drain&&done2==t.token&&!fault;
  assign task_r=!t.live&&fetch_idle&&qwr&&!fault&&run_enable;
  always @*begin
   nt=t;
   if(task_v&&task_r)begin
    if(task_experts==0||task_experts>DQ||task_id.stack!=2'(STACK)||task_id.die!=1'(DIE))nt.sticky=1;
    else begin nt.live=1;nt.token=~t.token;nt.wait_drain=0;nt.id=task_id;nt.target=task_experts;nt.accepted=0;end
   end
   if(e_valid&&e_ready)nt.accepted=t.accepted+1'b1;
   if(t.live&&t.accepted==t.target&&fetch_idle&&!f_req_v&&!fault)nt.wait_drain=1;
   if(payload_drained)begin nt.live=0;nt.wait_drain=0;end
   if(tbad)nt.sticky=1;
  end
  always @(posedge stream_clk or negedge por_n)
   if(!por_n)begin t<='0;tseal<=0;end
   else begin t<=nt;tseal<=seal_task(nt);end
 end endgenerate
endmodule
