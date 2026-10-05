`timescale 1ns/1ps
// ND1 ADDR37 loader -> existing shared four-stack provider. No new controller.
// Hardware owner namespace is supplied by the actual issuer; no fabricated IDs.
// rst_n is common cold POR, not an operation/lease reset. Default off.
module ot_hbm_loader_service_join #(parameter integer ENABLE=0,LOCAL_DIE=0,RANK_LIMIT=96)(
 input wire clk,rst_n,input wire req_v,output wire req_r,
 input wire[36:0] req_addr,input wire req_we,input wire[255:0] req_data,
 input wire[31:0] req_strb,input wire[15:0] req_tag,
 input wire hardware_owner_valid,input ot_hbm_r14_pkg::identity_t owner_identity,
 input wire[5:0] loader_client,input wire[6:0] global_rank,
 output wire rsp_v,input wire rsp_r,output wire rsp_we,output wire[15:0] rsp_tag,output wire[255:0] rsp_data,
 output wire[3:0] stack_req_v,input wire[3:0] stack_req_r,output wire[1819:0] stack_req,
 input wire[3:0] owned_v,output wire[3:0] owned_r,input wire[1859:0] owned,
 input wire[3:0] owned_we,owned_credit,service_fault,
 output wire[3:0] other_owned_v,input wire[3:0] other_owned_r,
 output wire[1859:0] other_owned,output wire[3:0] other_owned_we,other_owned_credit,
 output wire[3:0] credit_v,input wire[3:0] credit_r,output wire[3:0] credit_we,
 output wire[767:0] credit_id,output wire[47:0] credit_tag,output wire[19:0] credit_beat,
 input wire[3:0] other_credit_v,other_credit_we,output wire[3:0] other_credit_r,
 input wire[767:0] other_credit_id,input wire[47:0] other_credit_tag,input wire[19:0] other_credit_beat,
 output wire busy,output wire[6:0] held_global_rank,output wire fault
);
 import ot_hbm_r14_pkg::*;
 initial if(LOCAL_DIE<0||LOCAL_DIE>1||RANK_LIMIT<1||RANK_LIMIT>96)$fatal(1,"contained die/rank namespace");
 generate if(!ENABLE)begin:off
 assign req_r=0;assign rsp_v=0;assign rsp_we=0;assign rsp_tag=0;assign rsp_data=0;
 assign stack_req_v=0;assign stack_req=0;assign owned_r=0;assign other_owned_v=0;assign other_owned=0;
 assign other_owned_we=0;assign other_owned_credit=0;assign credit_v=0;assign credit_we=0;
 assign credit_id=0;assign credit_tag=0;assign credit_beat=0;assign other_credit_r=0;
 assign busy=0;assign held_global_rank=0;assign fault=0;
 end else begin:on
 localparam[1:0] IDLE=0,WAIT_DATA=1,REVERSE=2,GRANT=3;
 reg[1:0] state;reg sticky,write_saved;reg[6:0] rank_saved;
 identity_t expected;owned_t reverse_saved;
 reg[3:0] credit_lock,credit_loader;
 wire fmt_v,fmt_r,fmt_we,fmt_fault;wire[1:0] fmt_stack;wire[33:0] fmt_sector;
 wire[255:0] fmt_data;wire[31:0] fmt_strb;wire[15:0] fmt_tag;
 ot_hbm_accel_loader_addr_to_service #(.ENABLE(1),.ADDR_W(37),.STACK_W(2),.SECTOR_W(34),.STACK_BYTES(64'd22500000000)) formatter(
 .clk(clk),.rst_n(rst_n),.in_v(req_v&&state==IDLE),.in_rdy(),.in_addr(req_addr),.in_we(req_we),.in_data(req_data),.in_strb(req_strb),.in_tag(req_tag),
 .out_v(fmt_v),.out_rdy(fmt_r),.out_stack(fmt_stack),.out_sector(fmt_sector),.out_we(fmt_we),.out_data(fmt_data),.out_strb(fmt_strb),.out_tag(fmt_tag),.fault(fmt_fault));
 wire identity_ok=owner_identity.die==1'(LOCAL_DIE)&&owner_identity.stack==fmt_stack&&owner_identity.sector==fmt_sector&&owner_identity.caller==fmt_tag&&owner_identity.client==loader_client&&global_rank<7'(RANK_LIMIT);
 wire strobe_ok=!req_we||req_strb==32'hffffffff;
 request_t request_word;
 always @*begin request_word='0;request_word.id=owner_identity;request_word.len=6'd1;request_word.we=fmt_we;request_word.data=fmt_data;end
 wire[5:0] routed_client=state==IDLE?loader_client:expected.client;
 owned_t selected_owned;
 assign selected_owned=owned[expected.stack*465+:465];
 wire[3:0] mine,pick_loader;
 wire selected_v=owned_v[expected.stack]&&mine[expected.stack];
 wire payload_match=selected_owned.id==expected&&selected_owned.beat==0&&owned_we[expected.stack]==write_saved&&!owned_credit[expected.stack];
 wire grant_match=selected_owned.id==expected&&selected_owned.physical_tag==reverse_saved.physical_tag&&selected_owned.beat==reverse_saved.beat&&owned_credit[expected.stack];
 wire response_enable=state==WAIT_DATA&&selected_v&&payload_match&&!sticky&&!fmt_fault&&!service_fault[expected.stack];
 assign rsp_v=response_enable;assign rsp_tag=expected.caller;assign rsp_we=write_saved;assign rsp_data=selected_owned.data;
 assign fmt_r=state==IDLE&&hardware_owner_valid&&identity_ok&&strobe_ok&&!sticky&&!fmt_fault&&stack_req_r[fmt_stack]&&!service_fault[fmt_stack];
 assign req_r=fmt_r&&fmt_v;
 assign busy=state!=IDLE;assign held_global_rank=rank_saved;assign fault=sticky||fmt_fault;
 assign other_owned=owned;assign other_owned_we=owned_we;assign other_owned_credit=owned_credit;
 for(genvar s=0;s<4;s=s+1)begin:stack
 owned_t port_owned;assign port_owned=owned[s*465+:465];
 assign mine[s]=port_owned.id.client==routed_client;
 assign stack_req_v[s]=state==IDLE&&fmt_v&&hardware_owner_valid&&identity_ok&&strobe_ok&&!sticky&&!fmt_fault&&!service_fault[s]&&fmt_stack==2'(s);
 assign stack_req[s*455+:455]=request_word;
 assign other_owned_v[s]=owned_v[s]&&!mine[s];
 assign owned_r[s]=mine[s]?(state==WAIT_DATA&&expected.stack==2'(s)?(response_enable&&rsp_r):(state==GRANT&&expected.stack==2'(s)&&grant_match&&!sticky)):other_owned_r[s];
 wire want_loader=state==REVERSE&&expected.stack==2'(s)&&!sticky;
 assign pick_loader[s]=credit_lock[s]?credit_loader[s]:want_loader;
 assign credit_v[s]=pick_loader[s]?want_loader:other_credit_v[s];
 assign credit_we[s]=pick_loader[s]?write_saved:other_credit_we[s];
 assign credit_id[s*192+:192]=pick_loader[s]?reverse_saved.id:other_credit_id[s*192+:192];
 assign credit_tag[s*12+:12]=pick_loader[s]?reverse_saved.physical_tag:other_credit_tag[s*12+:12];
 assign credit_beat[s*5+:5]=pick_loader[s]?reverse_saved.beat:other_credit_beat[s*5+:5];
 assign other_credit_r[s]=!pick_loader[s]&&credit_r[s];
 end
 integer s;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
 state<=IDLE;sticky<=0;write_saved<=0;rank_saved<=0;expected<='0;reverse_saved<='0;credit_lock<=0;credit_loader<=0;
 end else begin
 for(s=0;s<4;s=s+1)begin
   if(credit_v[s]&&!credit_r[s])begin credit_lock[s]<=1;credit_loader[s]<=pick_loader[s];end
   if(credit_v[s]&&credit_r[s])credit_lock[s]<=0;
   if(owned_v[s]&&mine[s])begin
     if(state==IDLE||expected.stack!=2'(s))sticky<=1;
     else if(state==WAIT_DATA&&!payload_match)sticky<=1;
     else if(state==GRANT&&!grant_match)sticky<=1;
   end
 end
 if(state!=IDLE&&service_fault[expected.stack])sticky<=1;
 if(req_v&&state==IDLE&&hardware_owner_valid&&(!identity_ok||!strobe_ok))sticky<=1;
 if(req_v&&req_r)begin expected<=owner_identity;write_saved<=req_we;rank_saved<=global_rank;state<=WAIT_DATA;end
 if(rsp_v&&rsp_r)begin reverse_saved<=selected_owned;state<=REVERSE;end
 if(state==REVERSE&&pick_loader[expected.stack]&&credit_v[expected.stack]&&credit_r[expected.stack])state<=GRANT;
 if(state==GRANT&&selected_v&&grant_match&&owned_r[expected.stack])state<=IDLE;
 end
 end endgenerate
endmodule
