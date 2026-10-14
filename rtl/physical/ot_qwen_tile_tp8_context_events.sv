// Default-off wires-only native composition. No global admission/CDC/drain adoption.
module ot_qwen_tile_tp8_context_events (
 input wire clk_ctl,clk_node,clk_tx_group,clk_cache_response,clk_cache_load,
 input wire [4:0] clk_rp,input wire [7:0] clk_sl,input wire [1:0] clk_rqr,
 input wire rst_n,input wire [15:0] tile_id,
 input wire ib_go,input wire [378:0] ib,
 input wire [15:0] op_context,input wire [31:0] vm_version,
 input wire cache_clear,load_v,load_j_repeat,
 input wire [39:0] load_query_seq,
 input wire [20:0] load_epoch,input wire [95:0] load_addr,
 input wire [15:0] load_context,load_token,load_recipient,
 input wire [31:0] load_version,input wire [127:0] load_x,
 input wire [4:0] load_root,input wire [3:0] load_phase,
 input wire fill_ack_toggle,response_ack_toggle,
 output wire load_ready,read_credit,cache_hit,
 output wire fill_toggle,response_toggle,
 output wire [246:0] fill_tuple,response_tuple,
 output wire [3:0] cx_xre,output wire [95:0] cx_xaddr,
 output wire [20:0] cx_xepoch,output wire cx_xjrepeat,
 output wire [15:0] cx_xcontext,output wire [31:0] cx_xversion,
 input wire query_ack_toggle,
    output wire [39:0] cx_query_seq,
    output wire cx_query_toggle,cx_query_credit,cx_query_fault,
    input wire accept_ack_toggle,accept_transport_fence,
    output wire cx_accept_toggle,cx_admission_fault,
    output wire cx_op_accept,output wire cx_issue_last,output wire [378:0] cx_accepted_ib,
 output wire [15:0] cx_accepted_context,output wire [31:0] cx_accepted_version,
 output wire cx_core_idle,
 output wire [511:0] t_out,output wire t_vout,
 input wire [511:0] n_a,n_b,input wire n_va,
 output wire [511:0] n_y,output wire n_vy,output wire fault
);
 wire [127:0] x_response;wire core_fault,cache_fault;
 ot_qwen_rom_tile_nkt_tp8_core_grouped_ctx u_core (
 .clk_ctl(clk_ctl),.clk_rp(clk_rp),.clk_sl(clk_sl),.clk_node(clk_node),
 .clk_tx_group(clk_tx_group),.clk_rqr(clk_rqr),.rst_n(rst_n),.tile_id(tile_id),
 .ib_go(ib_go),.ib(ib),.x_response(x_response),.op_context(op_context),.vm_version(vm_version),
 .cx_xre(cx_xre),.cx_xaddr(cx_xaddr),.cx_xepoch(cx_xepoch),.cx_xjrepeat(cx_xjrepeat),
 .cx_xcontext(cx_xcontext),.cx_xversion(cx_xversion),.query_ack_toggle(query_ack_toggle),
 .cx_query_seq(cx_query_seq),.cx_query_toggle(cx_query_toggle),.cx_query_credit(cx_query_credit),.cx_query_fault(cx_query_fault),
 .accept_ack_toggle(accept_ack_toggle),.accept_transport_fence(accept_transport_fence),
 .cx_accept_toggle(cx_accept_toggle),.cx_admission_fault(cx_admission_fault),.cx_op_accept(cx_op_accept),.cx_issue_last(cx_issue_last),
 .cx_accepted_ib(cx_accepted_ib),.cx_accepted_context(cx_accepted_context),
 .cx_accepted_version(cx_accepted_version),.cx_core_idle(cx_core_idle),
 .t_out(t_out),.t_vout(t_vout),.n_a(n_a),.n_b(n_b),.n_va(n_va),.n_y(n_y),.n_vy(n_vy),.fault(core_fault));
 ot_qwen_xcache_context32_events u_cache (
 .load_clk(clk_cache_load),.core_clk(clk_cache_response),.rst_n(rst_n),.clear(cache_clear),
 .load_j_repeat(load_j_repeat),.load_v(load_v),.load_epoch(load_epoch),.load_query_seq(load_query_seq),.load_addr(load_addr),
 .load_context(load_context),.load_version(load_version),.load_x(load_x),
 .load_token(load_token),.load_root(load_root),.load_phase(load_phase),.load_recipient(load_recipient),
 .read_j_repeat(cx_xjrepeat),.read_query_seq(cx_query_seq),.read_epoch(cx_xepoch),.read_addr(cx_xaddr),
 .read_context(cx_xcontext),.read_version(cx_xversion),.read_v(cx_xre),
 .fill_ack_toggle(fill_ack_toggle),.response_ack_toggle(response_ack_toggle),
 .load_ready(load_ready),.read_credit(read_credit),.hit(cache_hit),
 .fill_toggle(fill_toggle),.response_toggle(response_toggle),.fill_tuple(fill_tuple),.response_tuple(response_tuple),
 .q_x(x_response),.fault(cache_fault));
 assign fault=core_fault|cache_fault;
endmodule
