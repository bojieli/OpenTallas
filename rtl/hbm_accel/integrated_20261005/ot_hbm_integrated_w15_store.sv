`timescale 1ns/1ps
// Backpressure the real normal-mode collective before the unchanged GW1 W15
// scalar write edge. A final collective beat is NOT a verified memory commit.
// Read side remains W15's real synchronous native-VM port; no read-ready tie.
module ot_hbm_integrated_w15_store #(parameter integer ENABLE=0,VM_AW=21)(
 input wire clk,por_n,go,id_plane,
 input wire [15:0] command_tag,
 input wire [31:0] source_word,
 input wire [31:0] arena_base,arena_limit,
 input wire [31:0] job,input wire [3:0] gen,input wire [16:0] token,input wire [19:0] pos,
 input wire gather_retained,
 output wire busy,done,fault,
 output wire vm_re,output wire [VM_AW-1:0] vm_raddr,input wire [511:0] vm_rq,
 output wire e_valid,input wire e_ready,output wire [511:0] e_data,
 output wire e_last,output wire e_mode,output wire [15:0] e_tag,
 input wire o_valid,output wire o_ready,input wire [511:0] o_data,
 input wire o_last,input wire [6:0] o_rank,input wire o_err,engine_fault,
 output wire bridge_req_v,input wire bridge_req_r,output wire [648:0] bridge_req,
 input wire bridge_rsp_v,output wire bridge_rsp_r,input wire [636:0] bridge_rsp
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:off
 assign busy=0;assign done=0;assign fault=0;assign vm_re=0;assign vm_raddr=0;
 assign e_valid=0;assign e_data=0;assign e_last=0;assign e_mode=0;assign e_tag=0;
 assign o_ready=0;assign bridge_req_v=0;assign bridge_req=0;assign bridge_rsp_r=0;
 end else begin:on
 initial if(VM_AW<13||VM_AW>26)$fatal(1,"installer VM aperture required");
 reg [71:0] control,tuple_lo,tuple_hi,address_code;
 wire [65:0] c=decode64(control),lo=decode64(tuple_lo),hi=decode64(tuple_hi),a=decode64(address_code);
 wire pending=c[0],last_pending=c[1],plane=c[2],failed=c[3];
 wire [127:0] frame={hi[63:0],lo[63:0]};
 wire [31:0] held_job=frame[31:0];wire [3:0] held_gen=frame[35:32];
 wire [16:0] held_token=frame[52:36];wire [19:0] held_pos=frame[72:53];
 wire [15:0] held_tag=frame[88:73];
 wire core_busy,core_fault,core_o_ready,core_we;
 wire [VM_AW-1:0] core_addr;wire [511:0] core_data;
 wire [32:0] byte_address={1'b0,32'(core_addr)}<<6;
 wire [32:0] base_end={1'b0,arena_base}+33'd393216;
 wire bounds=arena_base[5:0]==0&&arena_limit[5:0]==0&&base_end=={1'b0,arena_limit}&&base_end<=(33'd1<<(VM_AW+6));
 wire source_bounds={1'b0,source_word}+33'd32<=(33'd1<<VM_AW);
 wire same_frame=job==held_job&&gen==held_gen&&token==held_token&&pos==held_pos&&command_tag==held_tag;
 wire [VM_AW-1:0] dst_word=VM_AW'((arena_base+(plane?32'd196608:32'd0))>>6);
 wire [32:0] word_in_rank=33'(core_addr)-33'(dst_word)-33'(o_rank)*33'd32;
 wire request_bounds=o_rank<96&&word_in_rank<32&&!byte_address[32];
 assign fault=failed||c[65]||lo[65]||hi[65]||a[65]||core_fault||engine_fault;
 assign busy=core_busy||pending;
 assign done=c[4]&&!fault;
 assign bridge_req_v=core_busy&&o_valid&&!pending&&!fault&&request_bounds&&same_frame&&gather_retained;
 assign o_ready=core_o_ready&&bridge_req_r&&bridge_req_v;
 assign bridge_req={held_pos,held_token,held_gen,held_job,core_data,6'(word_in_rank),o_rank,held_tag,byte_address[31:0],plane?3'd2:3'd1};
 wire response_match=bridge_rsp[3:1]==(plane?3'd2:3'd1)&&bridge_rsp[19:4]==held_tag&&
  bridge_rsp[51:20]==a[31:0]&&bridge_rsp[595:564]==held_job&&bridge_rsp[599:596]==held_gen&&
  bridge_rsp[616:600]==held_token&&bridge_rsp[636:617]==held_pos;
 assign bridge_rsp_r=pending&&bridge_rsp[0]&&response_match&&!fault;
 // mode1/rnd0/topk0 is the installed NORMAL gather command, never TOPK's
 // direct-selector path. vm_ready4 is irrelevant to GW1, and is still real.
 ot_w15_coll_dma #(.WA(VM_AW),.FW(512),.TAGW(16),.N(96),.GW(1),.TOPK(0)) core(
  .clk(clk),.rst_n(por_n),.go(go&&!busy&&bounds&&source_bounds&&gather_retained&&!fault),
  .mode(1'b1),.rnd(1'b0),.tag(command_tag),.src(VM_AW'(source_word)),.n(VM_AW'(32)),
  .dst(VM_AW'((arena_base+(id_plane?32'd196608:32'd0))>>6)),
  .topk(1'b0),.ibase(VM_AW'(0)),.tk_k(16'd0),.tk_stride(32'd0),
  .busy(core_busy),.fault(core_fault),.words_out(),.words_in(),
  .vm_re(vm_re),.vm_raddr(vm_raddr),.vm_rq(vm_rq),.vm_we(core_we),.vm_waddr(core_addr),.vm_wdata(core_data),
  .vm_ready4(bridge_req_r),.vm_we4(),.vm_waddr4(),.vm_wdata4(),
  .e_valid(e_valid),.e_ready(e_ready),.e_data(e_data),.e_last(e_last),.e_mode(e_mode),.e_tag(e_tag),
  .o_valid(o_valid&&o_ready),.o_ready(core_o_ready),.o_data(o_data),.o_last(o_last),.o_rank(o_rank),
  .o_err(o_err),.engine_fault(engine_fault));
 reg [127:0] captured;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin control<=encode64(0);tuple_lo<=encode64(0);tuple_hi<=encode64(0);address_code<=encode64(0);end
  else if(fault||(busy&&(!same_frame||!gather_retained))||
   (go&&(busy||!bounds||!source_bounds||!gather_retained))||
   (o_valid&&core_busy&&!request_bounds)||(bridge_rsp_v&&(!pending||!response_match||!bridge_rsp[0])))control<=encode64(c[63:0]|64'd8);
  else begin
   if(go)begin
    captured={39'd0,command_tag,pos,token,gen,job};
    tuple_lo<=encode64(captured[63:0]);tuple_hi<=encode64(captured[127:64]);
    control<=encode64({61'd0,id_plane,2'd0});
   end
   if(bridge_req_v&&bridge_req_r)begin
    if(!core_we)control<=encode64(c[63:0]|64'd8);
    else begin
     address_code<=encode64({32'd0,byte_address[31:0]});
     control<=encode64({59'd0,1'b0,1'b0,plane,o_last,1'b1});
    end
   end
   if(bridge_rsp_v&&bridge_rsp_r)control<=encode64({59'd0,last_pending,1'b0,plane,2'd0});
  end
 end
 end endgenerate
endmodule
