`default_nettype none
module current_native_ring_face (
 output wire [511:0] ag_d,
 output wire [3:0] ag_src,
 output wire [5:0] ag_tag,
 output wire [1:0] ag_v,
 input wire [0:0] clk,
 input wire [279:0] pr_ccw_i,
 output wire [279:0] pr_ccw_o,
 input wire [279:0] pr_cw_i,
 output wire [279:0] pr_cw_o,
 input wire [0:0] ra_add_rhs_acc,
 input wire [1:0] ra_add_src,
 input wire [2:0] ra_add_tag,
 input wire [0:0] ra_add_v,
 input wire [255:0] ra_lp_data,
 input wire [2:0] ra_lp_tag,
 input wire [0:0] ra_lp_we,
 input wire [0:0] ra_rr_local,
 input wire [2:0] ra_rr_local_tag,
 input wire [3:0] ra_rx_kind,
 input wire [1:0] ra_rx_slot,
 input wire [3:0] ra_rx_src,
 input wire [5:0] ra_rx_tag,
 input wire [0:0] ra_state_add_rhs_acc,
 input wire [1:0] ra_state_add_src,
 input wire [2:0] ra_state_add_tag,
 input wire [0:0] ra_state_read_add,
 input wire [0:0] ra_state_read_rr,
 input wire [0:0] ra_state_read_tx,
 input wire [2:0] ra_state_rr_tag,
 input wire [0:0] ra_state_tx_acc,
 input wire [2:0] ra_state_tx_tag,
 input wire [0:0] ra_tx_acc,
 input wire [1:0] ra_tx_dst,
 input wire [1:0] ra_tx_forward,
 input wire [0:0] ra_tx_gather,
 input wire [1:0] ra_tx_inject,
 input wire [0:0] ra_tx_result,
 input wire [2:0] ra_tx_tag,
 input wire [3:0] ra_tx_ttl,
 output wire [255:0] rr_d,
 output wire [2:0] rr_tag,
 output wire [0:0] rr_v,
 input wire [0:0] rst_n,
 output wire [0:0] u_ring_fault,
 input wire [1:0] strap_qid
);
 wire [511:0] src_body_ag_d;
 reg [511:0] src_face_ag_d;
 always @(posedge clk) src_face_ag_d <= src_body_ag_d;
 assign ag_d=src_face_ag_d;
 wire [3:0] src_body_ag_src;
 reg [3:0] src_face_ag_src;
 always @(posedge clk) src_face_ag_src <= src_body_ag_src;
 assign ag_src=src_face_ag_src;
 wire [5:0] src_body_ag_tag;
 reg [5:0] src_face_ag_tag;
 always @(posedge clk) src_face_ag_tag <= src_body_ag_tag;
 assign ag_tag=src_face_ag_tag;
 wire [1:0] src_body_ag_v;
 reg [1:0] src_face_ag_v;
 always @(posedge clk) src_face_ag_v <= src_body_ag_v;
 assign ag_v=src_face_ag_v;
 reg [279:0] src_face_pr_ccw_i;
 always @(posedge clk) src_face_pr_ccw_i <= pr_ccw_i;
 wire [279:0] src_body_pr_ccw_o;
 reg [279:0] src_face_pr_ccw_o;
 always @(posedge clk) src_face_pr_ccw_o <= src_body_pr_ccw_o;
 assign pr_ccw_o=src_face_pr_ccw_o;
 reg [279:0] src_face_pr_cw_i;
 always @(posedge clk) src_face_pr_cw_i <= pr_cw_i;
 wire [279:0] src_body_pr_cw_o;
 reg [279:0] src_face_pr_cw_o;
 always @(posedge clk) src_face_pr_cw_o <= src_body_pr_cw_o;
 assign pr_cw_o=src_face_pr_cw_o;
 reg [0:0] src_face_ra_add_rhs_acc;
 always @(posedge clk) src_face_ra_add_rhs_acc <= ra_add_rhs_acc;
 reg [1:0] src_face_ra_add_src;
 always @(posedge clk) src_face_ra_add_src <= ra_add_src;
 reg [2:0] src_face_ra_add_tag;
 always @(posedge clk) src_face_ra_add_tag <= ra_add_tag;
 reg [0:0] src_face_ra_add_v;
 always @(posedge clk) src_face_ra_add_v <= ra_add_v;
 reg [255:0] src_face_ra_lp_data;
 always @(posedge clk) src_face_ra_lp_data <= ra_lp_data;
 reg [2:0] src_face_ra_lp_tag;
 always @(posedge clk) src_face_ra_lp_tag <= ra_lp_tag;
 reg [0:0] src_face_ra_lp_we;
 always @(posedge clk) src_face_ra_lp_we <= ra_lp_we;
 reg [0:0] src_face_ra_rr_local;
 always @(posedge clk) src_face_ra_rr_local <= ra_rr_local;
 reg [2:0] src_face_ra_rr_local_tag;
 always @(posedge clk) src_face_ra_rr_local_tag <= ra_rr_local_tag;
 reg [3:0] src_face_ra_rx_kind;
 always @(posedge clk) src_face_ra_rx_kind <= ra_rx_kind;
 reg [1:0] src_face_ra_rx_slot;
 always @(posedge clk) src_face_ra_rx_slot <= ra_rx_slot;
 reg [3:0] src_face_ra_rx_src;
 always @(posedge clk) src_face_ra_rx_src <= ra_rx_src;
 reg [5:0] src_face_ra_rx_tag;
 always @(posedge clk) src_face_ra_rx_tag <= ra_rx_tag;
 reg [0:0] src_face_ra_state_add_rhs_acc;
 always @(posedge clk) src_face_ra_state_add_rhs_acc <= ra_state_add_rhs_acc;
 reg [1:0] src_face_ra_state_add_src;
 always @(posedge clk) src_face_ra_state_add_src <= ra_state_add_src;
 reg [2:0] src_face_ra_state_add_tag;
 always @(posedge clk) src_face_ra_state_add_tag <= ra_state_add_tag;
 reg [0:0] src_face_ra_state_read_add;
 always @(posedge clk) src_face_ra_state_read_add <= ra_state_read_add;
 reg [0:0] src_face_ra_state_read_rr;
 always @(posedge clk) src_face_ra_state_read_rr <= ra_state_read_rr;
 reg [0:0] src_face_ra_state_read_tx;
 always @(posedge clk) src_face_ra_state_read_tx <= ra_state_read_tx;
 reg [2:0] src_face_ra_state_rr_tag;
 always @(posedge clk) src_face_ra_state_rr_tag <= ra_state_rr_tag;
 reg [0:0] src_face_ra_state_tx_acc;
 always @(posedge clk) src_face_ra_state_tx_acc <= ra_state_tx_acc;
 reg [2:0] src_face_ra_state_tx_tag;
 always @(posedge clk) src_face_ra_state_tx_tag <= ra_state_tx_tag;
 reg [0:0] src_face_ra_tx_acc;
 always @(posedge clk) src_face_ra_tx_acc <= ra_tx_acc;
 reg [1:0] src_face_ra_tx_dst;
 always @(posedge clk) src_face_ra_tx_dst <= ra_tx_dst;
 reg [1:0] src_face_ra_tx_forward;
 always @(posedge clk) src_face_ra_tx_forward <= ra_tx_forward;
 reg [0:0] src_face_ra_tx_gather;
 always @(posedge clk) src_face_ra_tx_gather <= ra_tx_gather;
 reg [1:0] src_face_ra_tx_inject;
 always @(posedge clk) src_face_ra_tx_inject <= ra_tx_inject;
 reg [0:0] src_face_ra_tx_result;
 always @(posedge clk) src_face_ra_tx_result <= ra_tx_result;
 reg [2:0] src_face_ra_tx_tag;
 always @(posedge clk) src_face_ra_tx_tag <= ra_tx_tag;
 reg [3:0] src_face_ra_tx_ttl;
 always @(posedge clk) src_face_ra_tx_ttl <= ra_tx_ttl;
 wire [255:0] src_body_rr_d;
 reg [255:0] src_face_rr_d;
 always @(posedge clk) src_face_rr_d <= src_body_rr_d;
 assign rr_d=src_face_rr_d;
 wire [2:0] src_body_rr_tag;
 reg [2:0] src_face_rr_tag;
 always @(posedge clk) src_face_rr_tag <= src_body_rr_tag;
 assign rr_tag=src_face_rr_tag;
 wire [0:0] src_body_rr_v;
 reg [0:0] src_face_rr_v;
 always @(posedge clk) src_face_rr_v <= src_body_rr_v;
 assign rr_v=src_face_rr_v;
 wire [0:0] src_body_u_ring_fault;
 reg [0:0] src_face_u_ring_fault;
 always @(posedge clk) src_face_u_ring_fault <= src_body_u_ring_fault;
 assign u_ring_fault=src_face_u_ring_fault ^ 1'b1;
native_ot_hfd_coll_q2_hard_v8g__ring_ag native_body (.ag_d(src_body_ag_d),
.ag_src(src_body_ag_src),
.ag_tag(src_body_ag_tag),
.ag_v(src_body_ag_v),
.clk(clk),
.pr_ccw_i(src_face_pr_ccw_i),
.pr_ccw_o(src_body_pr_ccw_o),
.pr_cw_i(src_face_pr_cw_i),
.pr_cw_o(src_body_pr_cw_o),
.ra_add_rhs_acc(src_face_ra_add_rhs_acc),
.ra_add_src(src_face_ra_add_src),
.ra_add_tag(src_face_ra_add_tag),
.ra_add_v(src_face_ra_add_v),
.ra_lp_data(src_face_ra_lp_data),
.ra_lp_tag(src_face_ra_lp_tag),
.ra_lp_we(src_face_ra_lp_we),
.ra_rr_local(src_face_ra_rr_local),
.ra_rr_local_tag(src_face_ra_rr_local_tag),
.ra_rx_kind(src_face_ra_rx_kind),
.ra_rx_slot(src_face_ra_rx_slot),
.ra_rx_src(src_face_ra_rx_src),
.ra_rx_tag(src_face_ra_rx_tag),
.ra_state_add_rhs_acc(src_face_ra_state_add_rhs_acc),
.ra_state_add_src(src_face_ra_state_add_src),
.ra_state_add_tag(src_face_ra_state_add_tag),
.ra_state_read_add(src_face_ra_state_read_add),
.ra_state_read_rr(src_face_ra_state_read_rr),
.ra_state_read_tx(src_face_ra_state_read_tx),
.ra_state_rr_tag(src_face_ra_state_rr_tag),
.ra_state_tx_acc(src_face_ra_state_tx_acc),
.ra_state_tx_tag(src_face_ra_state_tx_tag),
.ra_tx_acc(src_face_ra_tx_acc),
.ra_tx_dst(src_face_ra_tx_dst),
.ra_tx_forward(src_face_ra_tx_forward),
.ra_tx_gather(src_face_ra_tx_gather),
.ra_tx_inject(src_face_ra_tx_inject),
.ra_tx_result(src_face_ra_tx_result),
.ra_tx_tag(src_face_ra_tx_tag),
.ra_tx_ttl(src_face_ra_tx_ttl),
.rr_d(src_body_rr_d),
.rr_tag(src_body_rr_tag),
.rr_v(src_body_rr_v),
.rst_n(rst_n),
.u_ring_fault(src_body_u_ring_fault),
.strap_qid(strap_qid));
endmodule
`default_nettype wire
