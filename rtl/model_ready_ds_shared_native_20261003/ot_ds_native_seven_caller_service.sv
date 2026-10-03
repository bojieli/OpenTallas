`timescale 1ns/1ps
`default_nettype none
// Actual single native provider join. Class0 SU/KV uses the separate source-owned
// ot_ds_su_kv_related_namespace and its actual m_wr_done callback.
module ot_ds_native_seven_caller_service #(parameter integer ENABLE=0)(
 input wire fast_clk,slow_clk,cold_n,fast_rst_n,slow_rst_n,abort_fast,abort_slow,
 // Direct planes: field_X, ID, COLLDMA, BF16 selector. One four-address slot each.
 input wire [3:0] direct_r_v,output wire [3:0] direct_r_ready,
 input wire [15:0] direct_r_enable,input wire [479:0] direct_r_addr,
 input wire [659:0] direct_r_context,
 output wire [3:0] direct_q_v,input wire [3:0] direct_q_ready,
 output wire [8191:0] direct_q_data,output wire [911:0] direct_q_owner,
 // Shared VX callers in exact order ME/index/attention.
 input wire [2:0] vx_v,output wire [2:0] vx_ready,
 input wire [11:0] vx_enable,input wire [359:0] vx_addr,input wire [494:0] vx_context,
 output wire [2:0] vx_q_v,input wire [2:0] vx_q_ready,
 output wire [383:0] vx_q_data,output wire [95:0] vx_q_cookie,
 // Shared writes ME/index/attention; native word-address/mask format.
 input wire [2:0] producer_w_v,output wire [3:0] producer_w_accept,producer_w_visible,producer_w_pending,
 input wire [11:0] producer_w_enable,input wire [359:0] producer_w_addr,
 input wire [191:0] producer_w_mask,input wire [6143:0] producer_w_data,
 input wire [659:0] producer_w_context,
 input wire selector_w_v,input wire [29:0] selector_w_elementaddr,
 input wire [31:0] selector_w_mask,input wire [1023:0] selector_w_data,
 input wire [127:0] row_en,input wire [3839:0] row_addr,input wire [4095:0] row_data,
 input wire [3:0] coll_en,input wire [59:0] coll_wordaddr,input wire [2047:0] coll_data,
 input wire [329:0] direct_w_context,
 output wire [1:0] direct_w_ready,direct_w_visible,direct_w_pending,
 output wire [127:0] row_visible_mask,
 output wire fault,quarantined,output wire [7:0] debt
);
 reg [3:0] sx_en;reg [119:0] sx_addr;reg [63:0] sx_mask;reg [2047:0] sx_data;
 reg sx_bad;integer l,p,n;reg [30:0] element;
 always @* begin
  sx_en=0;sx_addr=0;sx_mask=0;sx_data=0;sx_bad=0;element=0;p=0;n=0;
  for(l=0;l<32;l=l+1)if(selector_w_mask[l])begin
   element={1'b0,selector_w_elementaddr}+l;
   if(element >= 31'd524288)sx_bad=1;
   else begin
    p=(selector_w_elementaddr[3:0]+l)/16;n=element[3:0];
    sx_en[p]=1;sx_addr[p*30+:30]=element>>4;sx_mask[p*16+n]=1;
    sx_data[(p*16+n)*32+:32]=selector_w_data[l*32+:32];
   end
  end
 end
 wire shared_r_v,shared_r_ready,shared_q_v,shared_q_ready;
 wire [3:0] shared_r_enable,shared_w_enable;
 wire [119:0] shared_r_addr,shared_w_addr;
 wire [164:0] shared_r_context,shared_w_context;
 wire [127:0] shared_q_data;wire [227:0] shared_q_owner;
 wire [63:0] shared_w_mask;wire [2047:0] shared_w_data;
 wire shared_w_ready,shared_w_visible,shared_w_pending,arb_fault,arb_outstanding;
 wire [3:0] wv={selector_w_v&&!sx_bad,producer_w_v};
 ot_ds_native_engine_arbiter #(.ENABLE(ENABLE)) arb(
 .clk(fast_clk),.cold_n(cold_n),.rst_n(fast_rst_n&&!abort_fast),
 .read_v(vx_v),.read_ready(vx_ready),.read_enable(vx_enable),.read_addr(vx_addr),.read_context(vx_context),
 .vm_read_v(shared_r_v),.vm_read_ready(shared_r_ready),.vm_read_enable(shared_r_enable),.vm_read_addr(shared_r_addr),.vm_read_context(shared_r_context),
 .vm_reply_v(shared_q_v),.vm_reply_ready(shared_q_ready),.vm_reply_data(shared_q_data),.vm_reply_owner(shared_q_owner),
 .reply_v(vx_q_v),.reply_ready(vx_q_ready),.reply_data(vx_q_data),.reply_cookie(vx_q_cookie),
 .write_v(wv),.write_accept(producer_w_accept),.write_visible(producer_w_visible),.write_pending(producer_w_pending),
 .write_enable({sx_en,producer_w_enable}),.write_addr({sx_addr,producer_w_addr}),.write_mask({sx_mask,producer_w_mask}),.write_data({sx_data,producer_w_data}),.write_context(producer_w_context),
 .vm_write_enable(shared_w_enable),.vm_write_addr(shared_w_addr),.vm_write_mask(shared_w_mask),.vm_write_data(shared_w_data),.vm_write_context(shared_w_context),
 .vm_write_ready(shared_w_ready),.vm_write_visible(shared_w_visible),.vm_write_pending(shared_w_pending),.fault(arb_fault),.outstanding(arb_outstanding));
 wire [4:0] rr,qv;wire [10239:0] qdata;wire [1139:0] qowner;
 wire [2:0] wr,wvis,wpend;wire nf,nq;reg format_fault;
 always @(posedge fast_clk)begin
  if(!cold_n)format_fault<=0;
  else if(selector_w_v && sx_bad)format_fault<=1;
 end
 assign fault=nf||arb_fault||format_fault;
 assign quarantined=nq||arb_fault;
 assign direct_r_ready={rr[4],rr[2:0]};assign shared_r_ready=rr[3];
 assign direct_q_v={qv[4],qv[2:0]};assign shared_q_v=qv[3];
 assign direct_q_data={qdata[8192+:2048],qdata[0+:6144]};
 assign direct_q_owner={qowner[912+:228],qowner[0+:684]};
 assign shared_q_data=qdata[6144+:128];assign shared_q_owner=qowner[684+:228];
 assign shared_w_ready=wr[0];assign shared_w_visible=wvis[0];assign shared_w_pending=wpend[0];
 assign direct_w_ready=wr[2:1];assign direct_w_visible=wvis[2:1];assign direct_w_pending=wpend[2:1];
 ot_ds_native_vm_related_callers #(.ENABLE(ENABLE)) native(
 .fast_clk(fast_clk),.slow_clk(slow_clk),.cold_n(cold_n),.fast_rst_n(fast_rst_n),.slow_rst_n(slow_rst_n),.abort_fast(abort_fast),.abort_slow(abort_slow),
 .r_v({direct_r_v[3],shared_r_v,direct_r_v[2:0]}),.r_ready(rr),
 .r_enable({direct_r_enable[12+:4],shared_r_enable,direct_r_enable[0+:12]}),
 .r_addr({direct_r_addr[360+:120],shared_r_addr,direct_r_addr[0+:360]}),
 .r_context({direct_r_context[495+:165],shared_r_context,direct_r_context[0+:495]}),
 .q_v(qv),.q_ready({direct_q_ready[3],shared_q_ready,direct_q_ready[2:0]}),.q_data(qdata),.q_owner(qowner),
 .me_en(shared_w_enable),.me_wordaddr(shared_w_addr),.me_mask(shared_w_mask),.me_data(shared_w_data),
 .row_en(row_en),.row_addr(row_addr),.row_data(row_data),.coll_en(coll_en),.coll_wordaddr(coll_wordaddr),.coll_data(coll_data),
 .w_context({direct_w_context,shared_w_context}),.w_ready(wr),.w_visible(wvis),.w_pending(wpend),.row_visible_mask(row_visible_mask),
 .fault(nf),.quarantined(nq),.debt(debt),.debug_native_write_accept(),.debug_native_visible(),.debug_native_read_accept());
endmodule
`default_nettype wire
