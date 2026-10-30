module source_ring_cut_api #(
    parameter integer NT=8, LAT=8, SPLIT_CLOCKS=0, AG=1,
    parameter integer MUT_CARRY=0, MUT_TAG=0, MUT_TTL=0, MUT_SRC=0
)(
    input wire clk, rst_n, clk_ctl,
    input wire [7:0] clk_state, clk_add,
    input wire [1:0] qid,
    input wire [279:0] cw_i, ccw_i,
    output wire [279:0] cw_o, ccw_o,
    input wire lp_we,
    input wire [2:0] lp_tag,
    input wire [255:0] lp_data,
    input wire state_read_add, state_read_tx, state_read_rr,
    input wire [2:0] state_add_tag, state_tx_tag, state_rr_tag,
    input wire [1:0] state_add_src,
    input wire state_add_rhs_acc, state_tx_acc,
    input wire add_v,
    input wire [2:0] add_tag,
    input wire [1:0] add_src,
    input wire add_rhs_acc,
    input wire [1:0] tx_inject, tx_forward,
    input wire [2:0] tx_tag,
    input wire [1:0] tx_dst,
    input wire tx_result, tx_acc,
    input wire tx_gather,
    input wire [3:0] tx_ttl,
    input wire [1:0] rx_slot,
    input wire [3:0] rx_kind, rx_src,
    input wire [5:0] rx_tag,
    input wire rr_local,
    input wire [2:0] rr_local_tag,
    output wire rr_v,
    output wire [2:0] rr_tag,
    output wire [255:0] rr_d,
    output wire [1:0] ag_v,
    output wire [3:0] ag_src,
    output wire [5:0] ag_tag,
    output wire [511:0] ag_d,
    output wire fault
);
initial if ((NT != (8)) || (LAT != (8)) || (SPLIT_CLOCKS != (1)) || (AG != (1)) || (MUT_CARRY != (0)) || (MUT_TAG != (0)) || (MUT_TTL != (0)) || (MUT_SRC != (0))) $fatal(1,"unsupported native ring cut profile");
current_native_ring_face u_cut(.ra_add_rhs_acc(add_rhs_acc),.ra_add_src(add_src),.ra_add_tag(add_tag),.ra_add_v(add_v),.ag_d(ag_d),.ag_src(ag_src),.ag_tag(ag_tag),.ag_v(ag_v),.pr_ccw_i(ccw_i),.pr_ccw_o(ccw_o),.clk(clk),.pr_cw_i(cw_i),.pr_cw_o(cw_o),.u_ring_fault(fault),.ra_lp_data(lp_data),.ra_lp_tag(lp_tag),.ra_lp_we(lp_we),.strap_qid(qid),.rr_d(rr_d),.ra_rr_local(rr_local),.ra_rr_local_tag(rr_local_tag),.rr_tag(rr_tag),.rr_v(rr_v),.rst_n(rst_n),.ra_rx_kind(rx_kind),.ra_rx_slot(rx_slot),.ra_rx_src(rx_src),.ra_rx_tag(rx_tag),.ra_state_add_rhs_acc(state_add_rhs_acc),.ra_state_add_src(state_add_src),.ra_state_add_tag(state_add_tag),.ra_state_read_add(state_read_add),.ra_state_read_rr(state_read_rr),.ra_state_read_tx(state_read_tx),.ra_state_rr_tag(state_rr_tag),.ra_state_tx_acc(state_tx_acc),.ra_state_tx_tag(state_tx_tag),.ra_tx_acc(tx_acc),.ra_tx_dst(tx_dst),.ra_tx_forward(tx_forward),.ra_tx_gather(tx_gather),.ra_tx_inject(tx_inject),.ra_tx_result(tx_result),.ra_tx_tag(tx_tag),.ra_tx_ttl(tx_ttl));
endmodule
