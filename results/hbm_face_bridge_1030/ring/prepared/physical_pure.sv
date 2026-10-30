module physical_ot_hfd_coll_q2_hard_v8g__ring_ag (
    input wire ra_add_rhs_acc,
    input wire ra_add_v,
    input wire ra_lp_we,
    input wire ra_rr_local,
    input wire ra_state_add_rhs_acc,
    input wire ra_state_read_add,
    input wire ra_state_read_rr,
    input wire ra_state_read_tx,
    input wire ra_state_tx_acc,
    input wire ra_tx_acc,
    input wire ra_tx_gather,
    input wire ra_tx_result,
    input wire [1:0] ra_add_src,
    input wire [1:0] ra_rx_slot,
    input wire [1:0] ra_state_add_src,
    input wire [1:0] ra_tx_dst,
    input wire [1:0] ra_tx_forward,
    input wire [1:0] ra_tx_inject,
    output wire [1:0] ag_v,
    input wire [2:0] ra_add_tag,
    input wire [2:0] ra_lp_tag,
    input wire [2:0] ra_rr_local_tag,
    input wire [2:0] ra_state_add_tag,
    input wire [2:0] ra_state_rr_tag,
    input wire [2:0] ra_state_tx_tag,
    input wire [2:0] ra_tx_tag,
    input wire [3:0] ra_rx_kind,
    input wire [3:0] ra_rx_src,
    input wire [3:0] ra_tx_ttl,
    output wire [3:0] ag_src,
    input wire [5:0] ra_rx_tag,
    output wire [5:0] ag_tag,
    input wire [255:0] ra_lp_data,
    output wire [511:0] ag_d,
    input wire clk,
    input wire [279:0] pr_ccw_i,
    input wire [279:0] pr_cw_i,
    output wire [279:0] pr_ccw_o,
    output wire [279:0] pr_cw_o,
    input wire rst_n,
    output wire rr_v,
    input wire [1:0] strap_qid,
    output wire [2:0] rr_tag,
    output wire [255:0] rr_d,
    output wire u_ring_fault
);
    wire [0:0] ra_add_rhs_acc__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bin_ra_add_rhs_acc (.clk(clk), .d(ra_add_rhs_acc), .q(ra_add_rhs_acc__fq));
    wire [0:0] ra_add_v__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bin_ra_add_v (.clk(clk), .d(ra_add_v), .q(ra_add_v__fq));
    wire [0:0] ra_lp_we__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bin_ra_lp_we (.clk(clk), .d(ra_lp_we), .q(ra_lp_we__fq));
    wire [0:0] ra_rr_local__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bin_ra_rr_local (.clk(clk), .d(ra_rr_local), .q(ra_rr_local__fq));
    wire [0:0] ra_state_add_rhs_acc__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bin_ra_state_add_rhs_acc (.clk(clk), .d(ra_state_add_rhs_acc), .q(ra_state_add_rhs_acc__fq));
    wire [0:0] ra_state_read_add__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bin_ra_state_read_add (.clk(clk), .d(ra_state_read_add), .q(ra_state_read_add__fq));
    wire [0:0] ra_state_read_rr__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bin_ra_state_read_rr (.clk(clk), .d(ra_state_read_rr), .q(ra_state_read_rr__fq));
    wire [0:0] ra_state_read_tx__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bin_ra_state_read_tx (.clk(clk), .d(ra_state_read_tx), .q(ra_state_read_tx__fq));
    wire [0:0] ra_state_tx_acc__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bin_ra_state_tx_acc (.clk(clk), .d(ra_state_tx_acc), .q(ra_state_tx_acc__fq));
    wire [0:0] ra_tx_acc__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bin_ra_tx_acc (.clk(clk), .d(ra_tx_acc), .q(ra_tx_acc__fq));
    wire [0:0] ra_tx_gather__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bin_ra_tx_gather (.clk(clk), .d(ra_tx_gather), .q(ra_tx_gather__fq));
    wire [0:0] ra_tx_result__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bin_ra_tx_result (.clk(clk), .d(ra_tx_result), .q(ra_tx_result__fq));
    wire [1:0] ra_add_src__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(2)) u_bin_ra_add_src (.clk(clk), .d(ra_add_src), .q(ra_add_src__fq));
    wire [1:0] ra_rx_slot__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(2)) u_bin_ra_rx_slot (.clk(clk), .d(ra_rx_slot), .q(ra_rx_slot__fq));
    wire [1:0] ra_state_add_src__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(2)) u_bin_ra_state_add_src (.clk(clk), .d(ra_state_add_src), .q(ra_state_add_src__fq));
    wire [1:0] ra_tx_dst__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(2)) u_bin_ra_tx_dst (.clk(clk), .d(ra_tx_dst), .q(ra_tx_dst__fq));
    wire [1:0] ra_tx_forward__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(2)) u_bin_ra_tx_forward (.clk(clk), .d(ra_tx_forward), .q(ra_tx_forward__fq));
    wire [1:0] ra_tx_inject__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(2)) u_bin_ra_tx_inject (.clk(clk), .d(ra_tx_inject), .q(ra_tx_inject__fq));
    wire [1:0] ag_v__fc;
    (* keep *) physical_ot_hbm_face_reg #(.W(2)) u_bout_ag_v (.clk(clk), .d(ag_v__fc), .q(ag_v));
    wire [2:0] ra_add_tag__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(3)) u_bin_ra_add_tag (.clk(clk), .d(ra_add_tag), .q(ra_add_tag__fq));
    wire [2:0] ra_lp_tag__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(3)) u_bin_ra_lp_tag (.clk(clk), .d(ra_lp_tag), .q(ra_lp_tag__fq));
    wire [2:0] ra_rr_local_tag__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(3)) u_bin_ra_rr_local_tag (.clk(clk), .d(ra_rr_local_tag), .q(ra_rr_local_tag__fq));
    wire [2:0] ra_state_add_tag__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(3)) u_bin_ra_state_add_tag (.clk(clk), .d(ra_state_add_tag), .q(ra_state_add_tag__fq));
    wire [2:0] ra_state_rr_tag__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(3)) u_bin_ra_state_rr_tag (.clk(clk), .d(ra_state_rr_tag), .q(ra_state_rr_tag__fq));
    wire [2:0] ra_state_tx_tag__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(3)) u_bin_ra_state_tx_tag (.clk(clk), .d(ra_state_tx_tag), .q(ra_state_tx_tag__fq));
    wire [2:0] ra_tx_tag__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(3)) u_bin_ra_tx_tag (.clk(clk), .d(ra_tx_tag), .q(ra_tx_tag__fq));
    wire [3:0] ra_rx_kind__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(4)) u_bin_ra_rx_kind (.clk(clk), .d(ra_rx_kind), .q(ra_rx_kind__fq));
    wire [3:0] ra_rx_src__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(4)) u_bin_ra_rx_src (.clk(clk), .d(ra_rx_src), .q(ra_rx_src__fq));
    wire [3:0] ra_tx_ttl__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(4)) u_bin_ra_tx_ttl (.clk(clk), .d(ra_tx_ttl), .q(ra_tx_ttl__fq));
    wire [3:0] ag_src__fc;
    (* keep *) physical_ot_hbm_face_reg #(.W(4)) u_bout_ag_src (.clk(clk), .d(ag_src__fc), .q(ag_src));
    wire [5:0] ra_rx_tag__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(6)) u_bin_ra_rx_tag (.clk(clk), .d(ra_rx_tag), .q(ra_rx_tag__fq));
    wire [5:0] ag_tag__fc;
    (* keep *) physical_ot_hbm_face_reg #(.W(6)) u_bout_ag_tag (.clk(clk), .d(ag_tag__fc), .q(ag_tag));
    wire [255:0] ra_lp_data__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(256)) u_bin_ra_lp_data (.clk(clk), .d(ra_lp_data), .q(ra_lp_data__fq));
    wire [511:0] ag_d__fc;
    (* keep *) physical_ot_hbm_face_reg #(.W(512)) u_bout_ag_d (.clk(clk), .d(ag_d__fc), .q(ag_d));
    wire [279:0] pr_ccw_i__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(280)) u_bin_pr_ccw_i (.clk(clk), .d(pr_ccw_i), .q(pr_ccw_i__fq));
    wire [279:0] pr_cw_i__fq;
    (* keep *) physical_ot_hbm_face_reg #(.W(280)) u_bin_pr_cw_i (.clk(clk), .d(pr_cw_i), .q(pr_cw_i__fq));
    wire [279:0] pr_ccw_o__fc;
    (* keep *) physical_ot_hbm_face_reg #(.W(280)) u_bout_pr_ccw_o (.clk(clk), .d(pr_ccw_o__fc), .q(pr_ccw_o));
    wire [279:0] pr_cw_o__fc;
    (* keep *) physical_ot_hbm_face_reg #(.W(280)) u_bout_pr_cw_o (.clk(clk), .d(pr_cw_o__fc), .q(pr_cw_o));
    wire [0:0] rr_v__fc;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bout_rr_v (.clk(clk), .d(rr_v__fc), .q(rr_v));
    wire [2:0] rr_tag__fc;
    (* keep *) physical_ot_hbm_face_reg #(.W(3)) u_bout_rr_tag (.clk(clk), .d(rr_tag__fc), .q(rr_tag));
    wire [255:0] rr_d__fc;
    (* keep *) physical_ot_hbm_face_reg #(.W(256)) u_bout_rr_d (.clk(clk), .d(rr_d__fc), .q(rr_d));
    wire [0:0] u_ring_fault__fc;
    (* keep *) physical_ot_hbm_face_reg #(.W(1)) u_bout_u_ring_fault (.clk(clk), .d(u_ring_fault__fc), .q(u_ring_fault));
    physical_ot_hfd_coll_q2_hard_v8g__ring_ag__fcore u_fcore (
        .ra_add_rhs_acc(ra_add_rhs_acc__fq),
        .ra_add_v(ra_add_v__fq),
        .ra_lp_we(ra_lp_we__fq),
        .ra_rr_local(ra_rr_local__fq),
        .ra_state_add_rhs_acc(ra_state_add_rhs_acc__fq),
        .ra_state_read_add(ra_state_read_add__fq),
        .ra_state_read_rr(ra_state_read_rr__fq),
        .ra_state_read_tx(ra_state_read_tx__fq),
        .ra_state_tx_acc(ra_state_tx_acc__fq),
        .ra_tx_acc(ra_tx_acc__fq),
        .ra_tx_gather(ra_tx_gather__fq),
        .ra_tx_result(ra_tx_result__fq),
        .ra_add_src(ra_add_src__fq),
        .ra_rx_slot(ra_rx_slot__fq),
        .ra_state_add_src(ra_state_add_src__fq),
        .ra_tx_dst(ra_tx_dst__fq),
        .ra_tx_forward(ra_tx_forward__fq),
        .ra_tx_inject(ra_tx_inject__fq),
        .ag_v(ag_v__fc),
        .ra_add_tag(ra_add_tag__fq),
        .ra_lp_tag(ra_lp_tag__fq),
        .ra_rr_local_tag(ra_rr_local_tag__fq),
        .ra_state_add_tag(ra_state_add_tag__fq),
        .ra_state_rr_tag(ra_state_rr_tag__fq),
        .ra_state_tx_tag(ra_state_tx_tag__fq),
        .ra_tx_tag(ra_tx_tag__fq),
        .ra_rx_kind(ra_rx_kind__fq),
        .ra_rx_src(ra_rx_src__fq),
        .ra_tx_ttl(ra_tx_ttl__fq),
        .ag_src(ag_src__fc),
        .ra_rx_tag(ra_rx_tag__fq),
        .ag_tag(ag_tag__fc),
        .ra_lp_data(ra_lp_data__fq),
        .ag_d(ag_d__fc),
        .clk(clk),
        .pr_ccw_i(pr_ccw_i__fq),
        .pr_cw_i(pr_cw_i__fq),
        .pr_ccw_o(pr_ccw_o__fc),
        .pr_cw_o(pr_cw_o__fc),
        .rst_n(rst_n),
        .rr_v(rr_v__fc),
        .strap_qid(strap_qid),
        .rr_tag(rr_tag__fc),
        .rr_d(rr_d__fc),
        .u_ring_fault(u_ring_fault__fc)
    );
endmodule
module physical_ot_hfd_coll_q2_hard_v8g__ring_ag__fcore (
    input wire ra_add_rhs_acc,
    input wire ra_add_v,
    input wire ra_lp_we,
    input wire ra_rr_local,
    input wire ra_state_add_rhs_acc,
    input wire ra_state_read_add,
    input wire ra_state_read_rr,
    input wire ra_state_read_tx,
    input wire ra_state_tx_acc,
    input wire ra_tx_acc,
    input wire ra_tx_gather,
    input wire ra_tx_result,
    input wire [1:0] ra_add_src,
    input wire [1:0] ra_rx_slot,
    input wire [1:0] ra_state_add_src,
    input wire [1:0] ra_tx_dst,
    input wire [1:0] ra_tx_forward,
    input wire [1:0] ra_tx_inject,
    output wire [1:0] ag_v,
    input wire [2:0] ra_add_tag,
    input wire [2:0] ra_lp_tag,
    input wire [2:0] ra_rr_local_tag,
    input wire [2:0] ra_state_add_tag,
    input wire [2:0] ra_state_rr_tag,
    input wire [2:0] ra_state_tx_tag,
    input wire [2:0] ra_tx_tag,
    input wire [3:0] ra_rx_kind,
    input wire [3:0] ra_rx_src,
    input wire [3:0] ra_tx_ttl,
    output wire [3:0] ag_src,
    input wire [5:0] ra_rx_tag,
    output wire [5:0] ag_tag,
    input wire [255:0] ra_lp_data,
    output wire [511:0] ag_d,
    input wire clk,
    input wire [279:0] pr_ccw_i,
    input wire [279:0] pr_cw_i,
    output wire [279:0] pr_ccw_o,
    output wire [279:0] pr_cw_o,
    input wire rst_n,
    output wire rr_v,
    input wire [1:0] strap_qid,   // ID strap (OWNER 10-25 option B, COORD 10-29 05:35): tied at the parent, false_path, no pin register
    output wire [2:0] rr_tag,
    output wire [255:0] rr_d,
    output wire u_ring_fault
);
    wire [279:0] c_ring_cw_o;
    wire [279:0] c_ring_ccw_o;
    wire c_ring_rr_v;
    wire [2:0] c_ring_rr_tag;
    wire [255:0] c_ring_rr_d;
    wire [1:0] c_ring_ag_v;
    wire [3:0] c_ring_ag_src;
    wire [5:0] c_ring_ag_tag;
    wire [511:0] c_ring_ag_d;
    wire c_ring_fault;
    physical_ot_hfd_coll_q2_ring_ag_core u_core (
        .ring_clk(clk),
        .ring_rst_n(rst_n),
        .ring_clk_state({8{clk}}),
        .ring_clk_add({8{clk}}),
        .ring_qid(strap_qid[1:0]),
        .ring_cw_i(pr_cw_i[279:0]),
        .ring_ccw_i(pr_ccw_i[279:0]),
        .ring_lp_we(ra_lp_we),
        .ring_lp_tag(ra_lp_tag[2:0]),
        .ring_lp_data(ra_lp_data[255:0]),
        .ring_state_read_add(ra_state_read_add),
        .ring_state_read_tx(ra_state_read_tx),
        .ring_state_read_rr(ra_state_read_rr),
        .ring_state_add_tag(ra_state_add_tag[2:0]),
        .ring_state_tx_tag(ra_state_tx_tag[2:0]),
        .ring_state_rr_tag(ra_state_rr_tag[2:0]),
        .ring_state_add_src(ra_state_add_src[1:0]),
        .ring_state_add_rhs_acc(ra_state_add_rhs_acc),
        .ring_state_tx_acc(ra_state_tx_acc),
        .ring_add_v(ra_add_v),
        .ring_add_tag(ra_add_tag[2:0]),
        .ring_add_src(ra_add_src[1:0]),
        .ring_add_rhs_acc(ra_add_rhs_acc),
        .ring_tx_inject(ra_tx_inject[1:0]),
        .ring_tx_forward(ra_tx_forward[1:0]),
        .ring_tx_tag(ra_tx_tag[2:0]),
        .ring_tx_dst(ra_tx_dst[1:0]),
        .ring_tx_result(ra_tx_result),
        .ring_tx_acc(ra_tx_acc),
        .ring_tx_gather(ra_tx_gather),
        .ring_tx_ttl(ra_tx_ttl[3:0]),
        .ring_rx_slot(ra_rx_slot[1:0]),
        .ring_rx_kind(ra_rx_kind[3:0]),
        .ring_rx_src(ra_rx_src[3:0]),
        .ring_rx_tag(ra_rx_tag[5:0]),
        .ring_rr_local(ra_rr_local),
        .ring_rr_local_tag(ra_rr_local_tag[2:0]),
        .ring_cw_o(c_ring_cw_o),
        .ring_ccw_o(c_ring_ccw_o),
        .ring_rr_v(c_ring_rr_v),
        .ring_rr_tag(c_ring_rr_tag),
        .ring_rr_d(c_ring_rr_d),
        .ring_ag_v(c_ring_ag_v),
        .ring_ag_src(c_ring_ag_src),
        .ring_ag_tag(c_ring_ag_tag),
        .ring_ag_d(c_ring_ag_d),
        .ring_fault(c_ring_fault));
    assign ag_v = c_ring_ag_v[1:0];
    assign ag_src = c_ring_ag_src[3:0];
    assign ag_tag = c_ring_ag_tag[5:0];
    assign ag_d = c_ring_ag_d[511:0];
    assign pr_ccw_o = c_ring_ccw_o[279:0];
    assign pr_cw_o = c_ring_cw_o[279:0];
    assign rr_v = c_ring_rr_v;
    assign rr_tag = c_ring_rr_tag[2:0];
    assign rr_d = c_ring_rr_d[255:0];
    assign u_ring_fault = c_ring_fault;
endmodule
module physical_ot_hfd_coll_q2_ring_ag_core (
    input wire ring_clk,
    input wire ring_rst_n,
    input wire [7:0] ring_clk_state,
    input wire [7:0] ring_clk_add,
    input wire [1:0] ring_qid,
    input wire [279:0] ring_cw_i,
    input wire [279:0] ring_ccw_i,
    input wire ring_lp_we,
    input wire [2:0] ring_lp_tag,
    input wire [255:0] ring_lp_data,
    input wire ring_state_read_add,
    input wire ring_state_read_tx,
    input wire ring_state_read_rr,
    input wire [2:0] ring_state_add_tag,
    input wire [2:0] ring_state_tx_tag,
    input wire [2:0] ring_state_rr_tag,
    input wire [1:0] ring_state_add_src,
    input wire ring_state_add_rhs_acc,
    input wire ring_state_tx_acc,
    input wire ring_add_v,
    input wire [2:0] ring_add_tag,
    input wire [1:0] ring_add_src,
    input wire ring_add_rhs_acc,
    input wire [1:0] ring_tx_inject,
    input wire [1:0] ring_tx_forward,
    input wire [2:0] ring_tx_tag,
    input wire [1:0] ring_tx_dst,
    input wire ring_tx_result,
    input wire ring_tx_acc,
    input wire ring_tx_gather,
    input wire [3:0] ring_tx_ttl,
    input wire [1:0] ring_rx_slot,
    input wire [3:0] ring_rx_kind,
    input wire [3:0] ring_rx_src,
    input wire [5:0] ring_rx_tag,
    input wire ring_rr_local,
    input wire [2:0] ring_rr_local_tag,
    output wire [279:0] ring_cw_o,
    output wire [279:0] ring_ccw_o,
    output wire ring_rr_v,
    output wire [2:0] ring_rr_tag,
    output wire [255:0] ring_rr_d,
    output wire [1:0] ring_ag_v,
    output wire [3:0] ring_ag_src,
    output wire [5:0] ring_ag_tag,
    output wire [511:0] ring_ag_d,
    output wire ring_fault
);
    wire u_ring__clk;
    wire u_ring__rst_n;
    wire u_ring__clk_ctl;
    wire [7:0] u_ring__clk_state;
    wire [7:0] u_ring__clk_add;
    wire [1:0] u_ring__qid;
    wire [279:0] u_ring__cw_i;
    wire [279:0] u_ring__ccw_i;
    wire [279:0] u_ring__cw_o;
    wire [279:0] u_ring__ccw_o;
    wire u_ring__lp_we;
    wire [2:0] u_ring__lp_tag;
    wire [255:0] u_ring__lp_data;
    wire u_ring__state_read_add;
    wire u_ring__state_read_tx;
    wire u_ring__state_read_rr;
    wire [2:0] u_ring__state_add_tag;
    wire [2:0] u_ring__state_tx_tag;
    wire [2:0] u_ring__state_rr_tag;
    wire [1:0] u_ring__state_add_src;
    wire u_ring__state_add_rhs_acc;
    wire u_ring__state_tx_acc;
    wire u_ring__add_v;
    wire [2:0] u_ring__add_tag;
    wire [1:0] u_ring__add_src;
    wire u_ring__add_rhs_acc;
    wire [1:0] u_ring__tx_inject;
    wire [1:0] u_ring__tx_forward;
    wire [2:0] u_ring__tx_tag;
    wire [1:0] u_ring__tx_dst;
    wire u_ring__tx_result;
    wire u_ring__tx_acc;
    wire u_ring__tx_gather;
    wire [3:0] u_ring__tx_ttl;
    wire [1:0] u_ring__rx_slot;
    wire [3:0] u_ring__rx_kind;
    wire [3:0] u_ring__rx_src;
    wire [5:0] u_ring__rx_tag;
    wire u_ring__rr_local;
    wire [2:0] u_ring__rr_local_tag;
    wire u_ring__rr_v;
    wire [2:0] u_ring__rr_tag;
    wire [255:0] u_ring__rr_d;
    wire [1:0] u_ring__ag_v;
    wire [3:0] u_ring__ag_src;
    wire [5:0] u_ring__ag_tag;
    wire [511:0] u_ring__ag_d;
    wire u_ring__fault;
    physical_ot_hgi_coll_ring_ag #(.SPLIT_CLOCKS(1),.AG(1)) u_ring (
        .clk(u_ring__clk),
        .rst_n(u_ring__rst_n),
        .clk_ctl(u_ring__clk_ctl),
        .clk_state(u_ring__clk_state),
        .clk_add(u_ring__clk_add),
        .qid(u_ring__qid),
        .cw_i(u_ring__cw_i),
        .ccw_i(u_ring__ccw_i),
        .cw_o(u_ring__cw_o),
        .ccw_o(u_ring__ccw_o),
        .lp_we(u_ring__lp_we),
        .lp_tag(u_ring__lp_tag),
        .lp_data(u_ring__lp_data),
        .state_read_add(u_ring__state_read_add),
        .state_read_tx(u_ring__state_read_tx),
        .state_read_rr(u_ring__state_read_rr),
        .state_add_tag(u_ring__state_add_tag),
        .state_tx_tag(u_ring__state_tx_tag),
        .state_rr_tag(u_ring__state_rr_tag),
        .state_add_src(u_ring__state_add_src),
        .state_add_rhs_acc(u_ring__state_add_rhs_acc),
        .state_tx_acc(u_ring__state_tx_acc),
        .add_v(u_ring__add_v),
        .add_tag(u_ring__add_tag),
        .add_src(u_ring__add_src),
        .add_rhs_acc(u_ring__add_rhs_acc),
        .tx_inject(u_ring__tx_inject),
        .tx_forward(u_ring__tx_forward),
        .tx_tag(u_ring__tx_tag),
        .tx_dst(u_ring__tx_dst),
        .tx_result(u_ring__tx_result),
        .tx_acc(u_ring__tx_acc),
        .tx_gather(u_ring__tx_gather),
        .tx_ttl(u_ring__tx_ttl),
        .rx_slot(u_ring__rx_slot),
        .rx_kind(u_ring__rx_kind),
        .rx_src(u_ring__rx_src),
        .rx_tag(u_ring__rx_tag),
        .rr_local(u_ring__rr_local),
        .rr_local_tag(u_ring__rr_local_tag),
        .rr_v(u_ring__rr_v),
        .rr_tag(u_ring__rr_tag),
        .rr_d(u_ring__rr_d),
        .ag_v(u_ring__ag_v),
        .ag_src(u_ring__ag_src),
        .ag_tag(u_ring__ag_tag),
        .ag_d(u_ring__ag_d),
        .fault(u_ring__fault));
    assign u_ring__clk = ring_clk;
    assign u_ring__rst_n = ring_rst_n;
    assign u_ring__clk_ctl = ring_clk;
    assign u_ring__clk_state[7:0] = ring_clk_state[7:0];
    assign u_ring__clk_add[7:0] = ring_clk_add[7:0];
    assign u_ring__qid[1:0] = ring_qid[1:0];
    assign u_ring__cw_i[279:0] = ring_cw_i[279:0];
    assign u_ring__ccw_i[279:0] = ring_ccw_i[279:0];
    assign ring_cw_o[279:0] = u_ring__cw_o[279:0];
    assign ring_ccw_o[279:0] = u_ring__ccw_o[279:0];
    assign u_ring__lp_we = ring_lp_we;
    assign u_ring__lp_tag[2:0] = ring_lp_tag[2:0];
    assign u_ring__lp_data[255:0] = ring_lp_data[255:0];
    assign u_ring__state_read_add = ring_state_read_add;
    assign u_ring__state_read_tx = ring_state_read_tx;
    assign u_ring__state_read_rr = ring_state_read_rr;
    assign u_ring__state_add_tag[2:0] = ring_state_add_tag[2:0];
    assign u_ring__state_tx_tag[2:0] = ring_state_tx_tag[2:0];
    assign u_ring__state_rr_tag[2:0] = ring_state_rr_tag[2:0];
    assign u_ring__state_add_src[1:0] = ring_state_add_src[1:0];
    assign u_ring__state_add_rhs_acc = ring_state_add_rhs_acc;
    assign u_ring__state_tx_acc = ring_state_tx_acc;
    assign u_ring__add_v = ring_add_v;
    assign u_ring__add_tag[2:0] = ring_add_tag[2:0];
    assign u_ring__add_src[1:0] = ring_add_src[1:0];
    assign u_ring__add_rhs_acc = ring_add_rhs_acc;
    assign u_ring__tx_inject[1:0] = ring_tx_inject[1:0];
    assign u_ring__tx_forward[1:0] = ring_tx_forward[1:0];
    assign u_ring__tx_tag[2:0] = ring_tx_tag[2:0];
    assign u_ring__tx_dst[1:0] = ring_tx_dst[1:0];
    assign u_ring__tx_result = ring_tx_result;
    assign u_ring__tx_acc = ring_tx_acc;
    assign u_ring__tx_gather = ring_tx_gather;
    assign u_ring__tx_ttl[3:0] = ring_tx_ttl[3:0];
    assign u_ring__rx_slot[1:0] = ring_rx_slot[1:0];
    assign u_ring__rx_kind[3:0] = ring_rx_kind[3:0];
    assign u_ring__rx_src[3:0] = ring_rx_src[3:0];
    assign u_ring__rx_tag[5:0] = ring_rx_tag[5:0];
    assign u_ring__rr_local = ring_rr_local;
    assign u_ring__rr_local_tag[2:0] = ring_rr_local_tag[2:0];
    assign ring_rr_v = u_ring__rr_v;
    assign ring_rr_tag[2:0] = u_ring__rr_tag[2:0];
    assign ring_rr_d[255:0] = u_ring__rr_d[255:0];
    assign ring_ag_v[1:0] = u_ring__ag_v[1:0];
    assign ring_ag_src[3:0] = u_ring__ag_src[3:0];
    assign ring_ag_tag[5:0] = u_ring__ag_tag[5:0];
    assign ring_ag_d[511:0] = u_ring__ag_d[511:0];
    assign ring_fault = u_ring__fault;
endmodule
module physical_ot_hgi_coll_ring_ag #(
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
    wire [279:0] pin0,pin1;wire [1:0] carry_write;wire acc_we;wire [2:0] acc_tag;
    wire [255:0] rhs_add,carry_add,state_tx,acc_rr,ay;wire [7:0] av;
    wire [255:0] aa = MUT_CARRY ? 256'b0 : carry_add;
    physical_ot_hgi_coll_ring_ag_ctl #(.NT(NT),.LAT(LAT),.AG(AG),.MUT_TAG(MUT_TAG),.MUT_TTL(MUT_TTL),.MUT_SRC(MUT_SRC)) u_ctl(
        .clk(SPLIT_CLOCKS?clk_ctl:clk),.rst_n(rst_n),.qid(qid),.cw_i(cw_i),.ccw_i(ccw_i),.cw_o(cw_o),.ccw_o(ccw_o),
        .lp_we(lp_we),.lp_tag(lp_tag),
        .state_read_add(state_read_add),.state_read_tx(state_read_tx),.state_read_rr(state_read_rr),
        .state_add_tag(state_add_tag),.state_tx_tag(state_tx_tag),.state_rr_tag(state_rr_tag),
        .state_add_src(state_add_src),.state_add_rhs_acc(state_add_rhs_acc),.state_tx_acc(state_tx_acc),
        .add_v(add_v),.add_tag(add_tag),.add_src(add_src),.add_rhs_acc(add_rhs_acc),
        .tx_inject(tx_inject),.tx_forward(tx_forward),.tx_tag(tx_tag),.tx_dst(tx_dst),.tx_result(tx_result),.tx_acc(tx_acc),
        .tx_gather(tx_gather),.tx_ttl(tx_ttl),.rx_slot(rx_slot),.rx_kind(rx_kind),.rx_src(rx_src),.rx_tag(rx_tag),
        .rr_local(rr_local),.rr_local_tag(rr_local_tag),
        .pin0_q(pin0),.pin1_q(pin1),.carry_write(carry_write),.acc_we(acc_we),.acc_tag(acc_tag),
        .state_tx(state_tx),.acc_rr(acc_rr),.av(av),
        .rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),.ag_v(ag_v),.ag_src(ag_src),.ag_tag(ag_tag),.ag_d(ag_d),.fault(fault));
    for(genvar l=0;l<8;l=l+1)begin:g_lane
        physical_ot_hgi_coll_pring_static_state_capture_lane u_state(
            .clk(SPLIT_CLOCKS?clk_state[l]:clk),
            .lp_we(lp_we),.lp_tag(lp_tag),.lp_data(lp_data[l*32+:32]),
            .acc_we(acc_we),.acc_tag(acc_tag),.acc_data(ay[l*32+:32]),
            .carry_we(carry_write),.carry0_tag(pin0[270:268]),.carry0_src(pin0[276:275]),
            .carry1_tag(pin1[270:268]),.carry1_src(pin1[276:275]),
            .carry0_data(pin0[l*32+:32]),.carry1_data(pin1[l*32+:32]),
            .read_add(state_read_add),.read_tx(state_read_tx),.read_rr(state_read_rr),
            .read_rhs_acc(state_add_rhs_acc),.read_tx_acc(state_tx_acc),
            .add_tag(state_add_tag),.add_src(state_add_src),.tx_tag(state_tx_tag),.rr_tag(state_rr_tag),
            .rhs_add(rhs_add[l*32+:32]),.carry_add(carry_add[l*32+:32]),
            .tx_data(state_tx[l*32+:32]),.acc_rr(acc_rr[l*32+:32]));
        physical_ot_hgi_coll_pring_static_add_lane #(.LAT(LAT)) u_add(
            .clk(SPLIT_CLOCKS?clk_add[l]:clk),.rst_n(rst_n),.valid_in(add_v),
            .a(aa[l*32+:32]),.b(rhs_add[l*32+:32]),.y(ay[l*32+:32]),.valid_out(av[l]));
    end
endmodule
module physical_ot_hgi_coll_ring_ag_ctl #(
    parameter integer NT=8, LAT=8, AG=1,
    parameter integer MUT_TAG=0, MUT_TTL=0, MUT_SRC=0
)(
    input wire clk, rst_n,
    input wire [1:0] qid,
    input wire [279:0] cw_i, ccw_i,
    output wire [279:0] cw_o, ccw_o,
    input wire lp_we,
    input wire [2:0] lp_tag,
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
    // lane faces (state-capture lanes + add lanes)
    output wire [279:0] pin0_q, pin1_q,
    output wire [1:0] carry_write,
    output wire acc_we,
    output wire [2:0] acc_tag,
    input wire [255:0] state_tx, acc_rr,
    input wire [7:0] av,
    output reg rr_v,
    output reg [2:0] rr_tag,
    output reg [255:0] rr_d,
    output reg [1:0] ag_v,
    output reg [3:0] ag_src,
    output reg [5:0] ag_tag,
    output reg [511:0] ag_d,
    output reg fault
);
    // RTL3c (review 10-17): async reset only on CONTROL state. Data registers (ring pin / output
    // payloads, rr_d/rr_tag, ag_d/ag_src/ag_tag) are plain flops in a separate block; every one is
    // qualified by a reset valid bit (pin/cw_o/ccw_o bit 279, rr_v, ag_v), so behaviour is unchanged.
    reg [1:0] pin_v, out_v;
    reg [278:0] pin_p [0:1];
    reg [278:0] out_p [0:1];
    wire [279:0] pin [0:1];
    assign pin[0]={pin_v[0],pin_p[0]};assign pin[1]={pin_v[1],pin_p[1]};
    assign cw_o={out_v[0],out_p[0]};assign ccw_o={out_v[1],out_p[1]};
    assign pin0_q=pin[0];assign pin1_q=pin[1];
    for(genvar d=0;d<2;d=d+1)begin:g_carry_write
        assign carry_write[d]=rx_slot[d] && pin[d][278:277]==1 && pin[d][274:273]==qid;
    end
    reg [NT-1:0] local_v, acc_v, pending, active;
    reg [3:0] carry_v[0:NT-1];
    reg read_add_v,read_tx_v,read_rr_v;
    reg [2:0] read_add_tag,read_tx_tag,read_rr_tag;
    reg [1:0] read_add_src;
    reg read_add_rhs,read_tx_acc;
    reg prep_add_v,prep_tx_v,prep_rr_v;
    reg [2:0] prep_add_tag,prep_tx_tag,prep_rr_tag;
    reg [1:0] prep_add_src;
    reg prep_add_rhs,prep_tx_acc;
    reg [LAT-1:0] pv;
    reg [2:0] pt[0:LAT-1];
    assign acc_we=pv[LAT-1];assign acc_tag=pt[LAT-1];
    generate if (NT!=8 || LAT<4 || LAT>8) begin:g_bad
        ot_hgi_static_ring_requires_NT8_LAT4_to_8 invalid_configuration();
    end endgenerate
    wire gath = AG!=0 && tx_gather;
    function automatic [279:0] flit(
        input integer d,input [2:0] tag,input [255:0] data,
        input gather_mode,result_mode,input [1:0] source_qid,target_qid,
        input [3:0] ttl_by_direction,input integer tag_mutant
    );
        flit={1'b1,gather_mode?2'd3:(result_mode?2'd2:2'd1),source_qid,gather_mode?source_qid:target_qid,
              gather_mode?ttl_by_direction[d*2+:2]:(result_mode?2'd3:2'd0),tag_mutant?(tag^3'd1):tag,1'b0,11'b0,data};
    endfunction
    // ring outputs (combinational next value; valid bit reset-registered, payload plain-registered)
    reg [279:0] nx_out [0:1];
    always @* begin:outs
        reg [279:0] x;
        for(integer d=0;d<2;d=d+1)begin
            x=pin[d];nx_out[d]=0;
            if(tx_forward[d])begin
                nx_out[d]=x;
                if(x[278:277]==2)nx_out[d][272:271]=x[272:271]-1'b1;
                if(x[278:277]==3)nx_out[d][272:271]=x[272:271]-(MUT_TTL?2'd2:2'd1);
            end
            if(tx_inject[d])nx_out[d]=flit(d,tx_tag,state_tx,gath,tx_result,qid,tx_dst,tx_ttl,MUT_TAG);
        end
    end
    // data registers: no reset (loads of rst_n = control state only)
    always @(posedge clk) begin:data
        reg [279:0] x;
        pin_p[0]<=cw_i[278:0];pin_p[1]<=ccw_i[278:0];
        out_p[0]<=nx_out[0][278:0];out_p[1]<=nx_out[1][278:0];
        if(rr_local)begin rr_tag<=rr_local_tag;rr_d<=acc_rr;end
        for(integer d=0;d<2;d=d+1)begin
            x=pin[d];
            if(rx_slot[d] && x[278:277]==2)begin rr_tag<=x[270:268];rr_d<=x[255:0];end
            if(AG!=0 && rx_slot[d] && x[278:277]==3)begin
                ag_src[d*2+:2]<=MUT_SRC?qid:x[276:275];ag_tag[d*3+:3]<=x[270:268];ag_d[d*256+:256]<=x[255:0];
            end
        end
    end
    always @(posedge clk or negedge rst_n) begin:step
        reg [279:0] x;
        reg [2:0] tag;
        reg [1:0] src,dst,kind,ttl;
        reg [1:0] result_slots;
        if(!rst_n)begin
            pin_v<=0;out_v<=0;
            local_v<=0;acc_v<=0;pending<=0;active<=0;pv<=0;
            rr_v<=0;fault<=0;ag_v<=0;
            read_add_v<=0;read_tx_v<=0;read_rr_v<=0;
            prep_add_v<=0;prep_tx_v<=0;prep_rr_v<=0;
            for(integer t=0;t<NT;t=t+1)carry_v[t]<=0;
        end else begin
            pin_v<={ccw_i[279],cw_i[279]};out_v<={nx_out[1][279],nx_out[0][279]};
            // Read reservations precede their consuming operation by exactly
            // two edges. These checks report faults, never gate issue or wait.
            prep_add_v<=state_read_add;prep_tx_v<=state_read_tx;prep_rr_v<=state_read_rr;
            prep_add_tag<=state_add_tag;prep_add_src<=state_add_src;prep_add_rhs<=state_add_rhs_acc;
            prep_tx_tag<=state_tx_tag;prep_tx_acc<=state_tx_acc;prep_rr_tag<=state_rr_tag;
            read_add_v<=prep_add_v;read_tx_v<=prep_tx_v;read_rr_v<=prep_rr_v;
            read_add_tag<=prep_add_tag;read_add_src<=prep_add_src;read_add_rhs<=prep_add_rhs;
            read_tx_tag<=prep_tx_tag;read_tx_acc<=prep_tx_acc;read_rr_tag<=prep_rr_tag;
            if(add_v!=read_add_v || (|tx_inject)!=read_tx_v || rr_local!=read_rr_v)fault<=1;
            if(add_v && (add_tag!=read_add_tag || add_src!=read_add_src || add_rhs_acc!=read_add_rhs))fault<=1;
            if((|tx_inject) && (tx_tag!=read_tx_tag || tx_acc!=read_tx_acc))fault<=1;
            if(rr_local && rr_local_tag!=read_rr_tag)fault<=1;
            if(state_read_add && (!carry_v[state_add_tag][state_add_src] || pending[state_add_tag] ||
               (state_add_rhs_acc ? !acc_v[state_add_tag] : !local_v[state_add_tag])))fault<=1;
            if(state_read_tx && (state_tx_acc ? (!acc_v[state_tx_tag] || pending[state_tx_tag]) : !local_v[state_tx_tag]))fault<=1;
            if(state_read_rr && (!acc_v[state_rr_tag] || pending[state_rr_tag]))fault<=1;
            if(state_read_add && !state_add_rhs_acc && lp_we && lp_tag==state_add_tag)fault<=1;
            if(state_read_tx && !state_tx_acc && lp_we && lp_tag==state_tx_tag)fault<=1;
            pv<={pv[LAT-2:0],add_v};pt[0]<=add_tag;
            for(integer i=1;i<LAT;i=i+1)pt[i]<=pt[i-1];
            rr_v<=rr_local;
            ag_v<=0;
            result_slots=0;
            if(rr_local)begin
                if(!acc_v[rr_local_tag] || pending[rr_local_tag])fault<=1;
                acc_v[rr_local_tag]<=0;active[rr_local_tag]<=0;
            end
            if(lp_we)begin
                if(local_v[lp_tag] || active[lp_tag])fault<=1;
                active[lp_tag]<=1;
                local_v[lp_tag]<=1;
            end
            if(add_v)begin
                if(!carry_v[add_tag][add_src] || pending[add_tag] ||
                   (add_rhs_acc ? !acc_v[add_tag] : !local_v[add_tag]))fault<=1;
                if(lp_we && lp_tag==add_tag && !add_rhs_acc)fault<=1;
                carry_v[add_tag][add_src]<=0;pending[add_tag]<=1;
                if(add_rhs_acc)acc_v[add_tag]<=0;else local_v[add_tag]<=0;
            end
            if(av!={8{pv[LAT-1]}})fault<=1;
            if(pv[LAT-1])begin
                if(acc_v[pt[LAT-1]])fault<=1;
                if(add_v && add_tag==pt[LAT-1])fault<=1;
                acc_v[pt[LAT-1]]<=1;pending[pt[LAT-1]]<=0;
            end
            // Every physical arrival, including transit, must match a reservation.
            // A reservation with missing input also faults at this exact edge.
            for(integer d=0;d<2;d=d+1)begin
                x=pin[d];
                tag=x[270:268];src=x[276:275];dst=x[274:273];
                kind=x[278:277];ttl=x[272:271];
                if(x[279]!=rx_slot[d])fault<=1;
                if(rx_slot[d])begin
                    if(kind!=rx_kind[d*2+:2] || src!=rx_src[d*2+:2] ||
                       tag!=rx_tag[d*3+:3] || (kind!=1 && kind!=2 && !(AG!=0 && kind==3)) ||
                       x[267:256]!=0)fault<=1;
                    if(kind!=3 && !active[tag])fault<=1;
                    if(d==1 && rx_slot[0] && pin[0][279] &&
                       pin[0][270:268]==tag && pin[0][276:275]==src &&
                       pin[0][278:277]==1 && kind==1 &&
                       pin[0][274:273]==qid && dst==qid)fault<=1;
                    if(kind==1 && dst==qid)begin
                        if(carry_v[tag][src] || tx_forward[d])fault<=1;
                        if(add_v && add_tag==tag && add_src==src)fault<=1;
                        carry_v[tag][src]<=1;
                    end
                    if(kind==2)begin
                        if(ttl==0)fault<=1;
                        result_slots[d]=1;active[tag]<=0;
                        rr_v<=1;
                        if(rr_local || |(result_slots & ~(2'b1<<d)))fault<=1;
                    end
                    if(AG!=0 && kind==3)begin
                        // GATHER arrival: publish on this direction's port; no tag state.
                        if(ttl==0 || src==qid)fault<=1;
                        ag_v[d]<=1;
                    end
                    if((kind==1 && dst!=qid) || ((kind==2 || kind==3) && ttl>1))begin
                        if(!tx_forward[d])fault<=1;
                    end else if(tx_forward[d])fault<=1;
                end
                if(tx_forward[d])begin
                    if(!rx_slot[d] || !x[279])fault<=1;
                end
                if(tx_inject[d])begin
                    if(tx_forward[d])fault<=1;
                    if(tx_acc ? (!acc_v[tx_tag] || pending[tx_tag]) : !local_v[tx_tag])fault<=1;
                    if(tx_result && (!tx_acc || tx_dst!=qid))fault<=1;
                    if(gath && (tx_result || tx_ttl[d*2+:2]==0))fault<=1;
                end
            end
            if(|tx_inject)begin
                // Copies sent simultaneously in both directions are compiler-
                // reserved, with the same payload. No runtime multicast arbiter.
                // A GATHER from local state ends the tag's lifetime; one from acc keeps
                // acc_v so the local publication (rr_local) can follow, as a RESULT does.
                if(!tx_acc)begin local_v[tx_tag]<=0;if(gath)active[tx_tag]<=0;end
                else if(!tx_result && !gath)acc_v[tx_tag]<=0;
            end
        end
    end
endmodule
module physical_ot_hgi_coll_pring_static_state_capture_lane(
    input wire  clk,
    input wire  lp_we,
    input wire [2:0] lp_tag,
    input wire [31:0] lp_data,
    input wire  acc_we,
    input wire [2:0] acc_tag,
    input wire [31:0] acc_data,
    input wire [1:0] carry_we,
    input wire [2:0] carry0_tag,
    input wire [2:0] carry1_tag,
    input wire [1:0] carry0_src,
    input wire [1:0] carry1_src,
    input wire [31:0] carry0_data,
    input wire [31:0] carry1_data,
    input wire  read_add,
    input wire  read_tx,
    input wire  read_rr,
    input wire  read_rhs_acc,
    input wire  read_tx_acc,
    input wire [2:0] add_tag,
    input wire [2:0] tx_tag,
    input wire [2:0] rr_tag,
    input wire [1:0] add_src,
    output wire [31:0] rhs_add,
    output wire [31:0] carry_add,
    output wire [31:0] tx_data,
    output wire [31:0] acc_rr
);
    (* keep=1, dont_touch=1 *) reg  cap_lp_we;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_lp_tag;
    (* keep=1, dont_touch=1 *) reg [31:0] cap_lp_data;
    (* keep=1, dont_touch=1 *) reg  cap_acc_we;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_acc_tag;
    (* keep=1, dont_touch=1 *) reg [31:0] cap_acc_data;
    (* keep=1, dont_touch=1 *) reg [1:0] cap_carry_we;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_carry0_tag;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_carry1_tag;
    (* keep=1, dont_touch=1 *) reg [1:0] cap_carry0_src;
    (* keep=1, dont_touch=1 *) reg [1:0] cap_carry1_src;
    (* keep=1, dont_touch=1 *) reg [31:0] cap_carry0_data;
    (* keep=1, dont_touch=1 *) reg [31:0] cap_carry1_data;
    (* keep=1, dont_touch=1 *) reg  cap_read_add;
    (* keep=1, dont_touch=1 *) reg  cap_read_tx;
    (* keep=1, dont_touch=1 *) reg  cap_read_rr;
    (* keep=1, dont_touch=1 *) reg  cap_read_rhs_acc;
    (* keep=1, dont_touch=1 *) reg  cap_read_tx_acc;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_add_tag;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_tx_tag;
    (* keep=1, dont_touch=1 *) reg [2:0] cap_rr_tag;
    (* keep=1, dont_touch=1 *) reg [1:0] cap_add_src;
    always @(posedge clk) begin
        cap_lp_we <= lp_we;
        cap_lp_tag <= lp_tag;
        cap_lp_data <= lp_data;
        cap_acc_we <= acc_we;
        cap_acc_tag <= acc_tag;
        cap_acc_data <= acc_data;
        cap_carry_we <= carry_we;
        cap_carry0_tag <= carry0_tag;
        cap_carry1_tag <= carry1_tag;
        cap_carry0_src <= carry0_src;
        cap_carry1_src <= carry1_src;
        cap_carry0_data <= carry0_data;
        cap_carry1_data <= carry1_data;
        cap_read_add <= read_add;
        cap_read_tx <= read_tx;
        cap_read_rr <= read_rr;
        cap_read_rhs_acc <= read_rhs_acc;
        cap_read_tx_acc <= read_tx_acc;
        cap_add_tag <= add_tag;
        cap_tx_tag <= tx_tag;
        cap_rr_tag <= rr_tag;
        cap_add_src <= add_src;
    end
    physical_ot_hgi_coll_pring_static_state_lane u_state(
        .clk(clk),
        .lp_we(cap_lp_we),
        .lp_tag(cap_lp_tag),
        .lp_data(cap_lp_data),
        .acc_we(cap_acc_we),
        .acc_tag(cap_acc_tag),
        .acc_data(cap_acc_data),
        .carry_we(cap_carry_we),
        .carry0_tag(cap_carry0_tag),
        .carry1_tag(cap_carry1_tag),
        .carry0_src(cap_carry0_src),
        .carry1_src(cap_carry1_src),
        .carry0_data(cap_carry0_data),
        .carry1_data(cap_carry1_data),
        .read_add(cap_read_add),
        .read_tx(cap_read_tx),
        .read_rr(cap_read_rr),
        .read_rhs_acc(cap_read_rhs_acc),
        .read_tx_acc(cap_read_tx_acc),
        .add_tag(cap_add_tag),
        .tx_tag(cap_tx_tag),
        .rr_tag(cap_rr_tag),
        .add_src(cap_add_src),
        .rhs_add(rhs_add),
        .carry_add(carry_add),
        .tx_data(tx_data),
        .acc_rr(acc_rr)
    );
endmodule
module physical_ot_hgi_coll_pring_static_state_lane(
    input wire clk,
    input wire lp_we,
    input wire [2:0] lp_tag,
    input wire [31:0] lp_data,
    input wire acc_we,
    input wire [2:0] acc_tag,
    input wire [31:0] acc_data,
    input wire [1:0] carry_we,
    input wire [2:0] carry0_tag,carry1_tag,
    input wire [1:0] carry0_src,carry1_src,
    input wire [31:0] carry0_data,carry1_data,
    input wire read_add,read_tx,read_rr,read_rhs_acc,read_tx_acc,
    input wire [2:0] add_tag,tx_tag,rr_tag,
    input wire [1:0] add_src,
    output reg [31:0] rhs_add,carry_add,tx_data,acc_rr
);
    reg [31:0] lp[0:7],acc[0:7],carry[0:7][0:3];
    always @(posedge clk)begin
        if(lp_we)lp[lp_tag]<=lp_data;
        if(acc_we)acc[acc_tag]<=acc_data;
        if(carry_we[0])carry[carry0_tag][carry0_src]<=carry0_data;
        if(carry_we[1])carry[carry1_tag][carry1_src]<=carry1_data;
        // All data outputs are flop Qs at the hardened face. The tag muxes
        // remain inside this leaf, before the reserved read capture edge.
        if(read_add)begin rhs_add<=read_rhs_acc?acc[add_tag]:lp[add_tag];carry_add<=carry[add_tag][add_src];end
        if(read_tx)tx_data<=read_tx_acc?acc[tx_tag]:lp[tx_tag];
        if(read_rr)acc_rr<=acc[rr_tag];
    end
endmodule
module physical_ot_hgi_coll_pring_static #(
    parameter integer NT=8, LAT=8, SPLIT_CLOCKS=0,
    parameter integer MUT_CARRY=0, MUT_TAG=0
)(
    input wire clk, rst_n,
    input wire [7:0] clk_state, clk_add,
    input wire [1:0] qid,
    input wire [279:0] cw_i, ccw_i,
    output reg [279:0] cw_o, ccw_o,
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
    input wire [1:0] rx_slot,
    input wire [3:0] rx_kind, rx_src,
    input wire [5:0] rx_tag,
    input wire rr_local,
    input wire [2:0] rr_local_tag,
    output reg rr_v,
    output reg [2:0] rr_tag,
    output reg [255:0] rr_d,
    output reg fault
);
    // 280b historical pin encoding retained: v,kind,src,dst,ttl,tag,
    // mode(reserved),aux(reserved),data. Only CARRY=1 and RESULT=2 allowed.
    reg [279:0] pin [0:1];
    wire [255:0] rhs_add, carry_add, state_tx, acc_rr;
    wire [1:0] carry_write;
    for(genvar d=0;d<2;d=d+1)begin:g_carry_write
        assign carry_write[d]=rx_slot[d] && pin[d][278:277]==1 && pin[d][274:273]==qid;
    end
    reg [NT-1:0] local_v, acc_v, pending, active;
    reg [3:0] carry_v[0:NT-1];
    wire [255:0] aa = MUT_CARRY ? 256'b0 : carry_add;
    wire [255:0] ab = rhs_add;
    wire [255:0] ay;
    wire [7:0] av;
    reg read_add_v,read_tx_v,read_rr_v;
    reg [2:0] read_add_tag,read_tx_tag,read_rr_tag;
    reg [1:0] read_add_src;
    reg read_add_rhs,read_tx_acc;
    reg [LAT-1:0] pv;
    reg [2:0] pt[0:LAT-1];
    generate if (NT!=8 || LAT<4 || LAT>8) begin:g_bad
        ot_hgi_static_ring_requires_NT8_LAT4_to_8 invalid_configuration();
    end endgenerate
    // Payload and arithmetic are actual leaf modules, with one clock entry per
    // 32b lane. All roots have synchronous edge/phase semantics; SPLIT_CLOCKS
    // changes physical clock delivery only, never the compiler cycle price.
    // State leaf: 1,536 payload flops + 128 registered read face bits.
    // Each read is explicitly reserved one edge before add/TX/publication.
    for(genvar l=0;l<8;l=l+1)begin:g_lane
        physical_ot_hgi_coll_pring_static_state_lane u_state(
            .clk(SPLIT_CLOCKS?clk_state[l]:clk),
            .lp_we(lp_we),.lp_tag(lp_tag),.lp_data(lp_data[l*32+:32]),
            .acc_we(pv[LAT-1]),.acc_tag(pt[LAT-1]),.acc_data(ay[l*32+:32]),
            .carry_we(carry_write),.carry0_tag(pin[0][270:268]),.carry0_src(pin[0][276:275]),
            .carry1_tag(pin[1][270:268]),.carry1_src(pin[1][276:275]),
            .carry0_data(pin[0][l*32+:32]),.carry1_data(pin[1][l*32+:32]),
            .read_add(state_read_add),.read_tx(state_read_tx),.read_rr(state_read_rr),
            .read_rhs_acc(state_add_rhs_acc),.read_tx_acc(state_tx_acc),
            .add_tag(state_add_tag),.add_src(state_add_src),.tx_tag(state_tx_tag),.rr_tag(state_rr_tag),
            .rhs_add(rhs_add[l*32+:32]),.carry_add(carry_add[l*32+:32]),
            .tx_data(state_tx[l*32+:32]),.acc_rr(acc_rr[l*32+:32]));
        physical_ot_hgi_coll_pring_static_add_lane #(.LAT(LAT)) u_add(
            .clk(SPLIT_CLOCKS?clk_add[l]:clk),.rst_n(rst_n),.valid_in(add_v),
            .a(aa[l*32+:32]),.b(ab[l*32+:32]),.y(ay[l*32+:32]),.valid_out(av[l]));
    end
    function automatic [279:0] flit(input [2:0] tag,input [255:0] data);
        flit={1'b1,tx_result?2'd2:2'd1,qid,tx_dst,
              tx_result?2'd3:2'd0,MUT_TAG?(tag^3'd1):tag,1'b0,11'b0,data};
    endfunction
    always @(posedge clk or negedge rst_n) begin:step
        reg [279:0] x,outx;
        reg [2:0] tag;
        reg [1:0] src,dst,kind,ttl;
        reg [1:0] result_slots;
        if(!rst_n)begin
            pin[0]<=0;pin[1]<=0;cw_o<=0;ccw_o<=0;
            local_v<=0;acc_v<=0;pending<=0;active<=0;pv<=0;
            rr_v<=0;rr_tag<=0;rr_d<=0;fault<=0;
            read_add_v<=0;read_tx_v<=0;read_rr_v<=0;
            for(integer t=0;t<NT;t=t+1)carry_v[t]<=0;
        end else begin
            pin[0]<=cw_i;pin[1]<=ccw_i;
            // Read reservations precede their consuming operation by exactly
            // one edge. These checks report faults, never gate issue or wait.
            read_add_v<=state_read_add;read_tx_v<=state_read_tx;read_rr_v<=state_read_rr;
            read_add_tag<=state_add_tag;read_add_src<=state_add_src;read_add_rhs<=state_add_rhs_acc;
            read_tx_tag<=state_tx_tag;read_tx_acc<=state_tx_acc;read_rr_tag<=state_rr_tag;
            if(add_v!=read_add_v || (|tx_inject)!=read_tx_v || rr_local!=read_rr_v)fault<=1;
            if(add_v && (add_tag!=read_add_tag || add_src!=read_add_src || add_rhs_acc!=read_add_rhs))fault<=1;
            if((|tx_inject) && (tx_tag!=read_tx_tag || tx_acc!=read_tx_acc))fault<=1;
            if(rr_local && rr_local_tag!=read_rr_tag)fault<=1;
            if(state_read_add && (!carry_v[state_add_tag][state_add_src] || pending[state_add_tag] ||
               (state_add_rhs_acc ? !acc_v[state_add_tag] : !local_v[state_add_tag])))fault<=1;
            if(state_read_tx && (state_tx_acc ? (!acc_v[state_tx_tag] || pending[state_tx_tag]) : !local_v[state_tx_tag]))fault<=1;
            if(state_read_rr && (!acc_v[state_rr_tag] || pending[state_rr_tag]))fault<=1;
            if(state_read_add && !state_add_rhs_acc && lp_we && lp_tag==state_add_tag)fault<=1;
            if(state_read_tx && !state_tx_acc && lp_we && lp_tag==state_tx_tag)fault<=1;
            pv<={pv[LAT-2:0],add_v};pt[0]<=add_tag;
            for(integer i=1;i<LAT;i=i+1)pt[i]<=pt[i-1];
            rr_v<=rr_local;
            result_slots=0;
            if(rr_local)begin
                rr_tag<=rr_local_tag;rr_d<=acc_rr;
                if(!acc_v[rr_local_tag] || pending[rr_local_tag])fault<=1;
                acc_v[rr_local_tag]<=0;active[rr_local_tag]<=0;
            end
            if(lp_we)begin
                if(local_v[lp_tag] || active[lp_tag])fault<=1;
                active[lp_tag]<=1;
                local_v[lp_tag]<=1;
            end
            if(add_v)begin
                if(!carry_v[add_tag][add_src] || pending[add_tag] ||
                   (add_rhs_acc ? !acc_v[add_tag] : !local_v[add_tag]))fault<=1;
                if(lp_we && lp_tag==add_tag && !add_rhs_acc)fault<=1;
                carry_v[add_tag][add_src]<=0;pending[add_tag]<=1;
                if(add_rhs_acc)acc_v[add_tag]<=0;else local_v[add_tag]<=0;
            end
            if(av!={8{pv[LAT-1]}})fault<=1;
            if(pv[LAT-1])begin
                if(acc_v[pt[LAT-1]])fault<=1;
                if(add_v && add_tag==pt[LAT-1])fault<=1;
                acc_v[pt[LAT-1]]<=1;pending[pt[LAT-1]]<=0;
            end
            // Every physical arrival, including transit, must match a reservation.
            // A reservation with missing input also faults at this exact edge.
            for(integer d=0;d<2;d=d+1)begin
                x=pin[d];outx=0;
                tag=x[270:268];src=x[276:275];dst=x[274:273];
                kind=x[278:277];ttl=x[272:271];
                if(x[279]!=rx_slot[d])fault<=1;
                if(rx_slot[d])begin
                    if(kind!=rx_kind[d*2+:2] || src!=rx_src[d*2+:2] ||
                       tag!=rx_tag[d*3+:3] || (kind!=1 && kind!=2) ||
                       x[267:256]!=0)fault<=1;
                    if(!active[tag])fault<=1;
                    if(d==1 && rx_slot[0] && pin[0][279] &&
                       pin[0][270:268]==tag && pin[0][276:275]==src &&
                       pin[0][278:277]==1 && kind==1 &&
                       pin[0][274:273]==qid && dst==qid)fault<=1;
                    if(kind==1 && dst==qid)begin
                        if(carry_v[tag][src] || tx_forward[d])fault<=1;
                        if(add_v && add_tag==tag && add_src==src)fault<=1;
                        carry_v[tag][src]<=1;
                    end
                    if(kind==2)begin
                        if(ttl==0)fault<=1;
                        result_slots[d]=1;active[tag]<=0;
                        rr_v<=1;rr_tag<=tag;rr_d<=x[255:0];
                        if(rr_local || |(result_slots & ~(2'b1<<d)))fault<=1;
                    end
                    if((kind==1 && dst!=qid) || (kind==2 && ttl>1))begin
                        if(!tx_forward[d])fault<=1;
                    end else if(tx_forward[d])fault<=1;
                end
                if(tx_forward[d])begin
                    if(!rx_slot[d] || !x[279])fault<=1;
                    outx=x;
                    if(kind==2)outx[272:271]=ttl-1'b1;
                end
                if(tx_inject[d])begin
                    if(tx_forward[d])fault<=1;
                    if(tx_acc ? (!acc_v[tx_tag] || pending[tx_tag]) : !local_v[tx_tag])fault<=1;
                    if(tx_result && (!tx_acc || tx_dst!=qid))fault<=1;
                    outx=flit(tx_tag,state_tx);
                end
                if(d==0)cw_o<=outx;else ccw_o<=outx;
            end
            if(|tx_inject)begin
                // Copies sent simultaneously in both directions are compiler-
                // reserved, with the same payload. No runtime multicast arbiter.
                if(!tx_acc)local_v[tx_tag]<=0;
                else if(!tx_result)acc_v[tx_tag]<=0;
            end
        end
    end
endmodule
module physical_ot_hgi_coll_pring_static_add_lane #(parameter integer LAT=8)(
    input wire clk,rst_n,valid_in,
    input wire [31:0] a,b,
    output wire [31:0] y,
    output wire valid_out
);
    reg [31:0] ap,bp;reg vp;
    always @(posedge clk)begin ap<=a;bp<=b;end
    always @(posedge clk or negedge rst_n)if(!rst_n)vp<=0;else vp<=valid_in;
    physical_ot_hdc_fp32_add_lat #(.LAT(LAT-1),.DRST(0)) u_add(
        .clk(clk),.rst_n(rst_n),.valid_in(vp),.a(ap),.b(bp),.y(y),.err(),.valid_out(valid_out));
endmodule
module physical_ot_hdc_fp32_add_lat #(
    parameter integer LAT = 3,
    // CUTS >= 0 picks the extra cuts explicitly, bits {D, C, B, A} (LAT must be 3 + their count); -1: by LAT.
    // W11 serial domain: CUTS = 4'b0001 (C_A, LAT 4) cuts the INPUT side, so an operand multiplexer in front of
    // the unit shares stage 1 with the decode / compare instead of the alignment
    parameter integer CUTS = -1,
    // DRST 0 (fe-push-hphys-1010, opt-in via OT_FP_DATA_NORST): only the valid bits are reset (cuts VB, valid_out);
    // y / err / data cuts are plain flops (consumers qualify them with valid_out).  1: legacy, every stage bit reset.
    parameter integer DRST =  1 
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output reg  [31:0] y,
    output reg  [1:0]  err,
    output reg         valid_out
);
    localparam integer CUT_A = (CUTS >= 0) ? CUTS % 2       : (LAT >= 5) ? 1 : 0;
    localparam integer CUT_B = (CUTS >= 0) ? (CUTS / 2) % 2 : (LAT >= 4) ? 1 : 0;
    localparam integer CUT_C = (CUTS >= 0) ? (CUTS / 4) % 2 : (LAT >= 6) ? 1 : 0;
    localparam integer CUT_D = (CUTS >= 0) ? (CUTS / 8) % 2 : (LAT >= 7) ? 1 : 0;     // inside B2: after the sentinel LZC
    generate if (CUTS >= 0 && CUT_A + CUT_B + CUT_C + CUT_D + 3 != LAT) begin : g_bad_cuts
        ot_hdc_fp32_add_lat_CUTS_must_match_LAT u_trap ();
    end endgenerate
    localparam [1:0] E_NONE = 2'd0, E_NONFINITE = 2'd1, E_OVERFLOW = 2'd2;

    // ---- A1 ----------------------------------------------------------------------------------------
    wire [7:0]  a_field = a[30:23];
    wire [7:0]  b_field = b[30:23];
    wire [7:0]  a_exp = (a_field == 8'd0) ? 8'd1 : a_field;
    wire [7:0]  b_exp = (b_field == 8'd0) ? 8'd1 : b_field;
    wire [23:0] a_man = {(a_field != 8'd0), a[22:0]};
    wire [23:0] b_man = {(b_field != 8'd0), b[22:0]};
    wire nonfinite = (a_field == 8'hff) || (b_field == 8'hff);
    wire a_zero = (a[30:0] == 31'd0);
    wire b_zero = (b[30:0] == 31'd0);
    wire bypass = nonfinite || a_zero || b_zero;
    wire [31:0] bypass_code = nonfinite ? 32'd0 : (a_zero ? (b_zero ? 32'd0 : b) : a);
    wire cmp_c;
    wire [30:0] cmp_s;
    physical_ot_hdc_ksadd_k #(.W(31)) u_cmp (.a(a[30:0]), .b(~b[30:0]), .cin(1'b1), .s(cmp_s), .cout(cmp_c));
    wire [7:0] dab, dba;
    wire dab_c, dba_c;
    physical_ot_hdc_ksadd_k #(.W(8)) u_dab (.a(a_exp), .b(~b_exp), .cin(1'b1), .s(dab), .cout(dab_c));
    physical_ot_hdc_ksadd_k #(.W(8)) u_dba (.a(b_exp), .b(~a_exp), .cin(1'b1), .s(dba), .cout(dba_c));
    // A1 -> A2 boundary bundle
    localparam integer WA = 1 + 1 + 2 + 32 + 1 + 1 + 1 + 8 + 8 + 24 + 24 + 8 + 8;
    wire [WA-1:0] a1 = {valid_in, bypass, (nonfinite ? E_NONFINITE : E_NONE), bypass_code, a[31] ^ b[31], a[31], b[31],
                        a_exp, b_exp, a_man, b_man, dab, dba} ;
    wire          a1_swap = !cmp_c;
    wire [WA:0]   a2_in;
    physical_ot_hdc_w11_cut #(.W(WA + 1), .CUT(CUT_A), .VB(DRST ? -1 : WA - 1)) u_ca (.clk(clk), .rst_n(rst_n), .d({a1_swap, a1}), .q(a2_in));
    // ---- A2 ----------------------------------------------------------------------------------------
    wire        x_v, x_byp, x_sub, x_as, x_bs, x_swap;
    wire [1:0]  x_err;
    wire [31:0] x_code;
    wire [7:0]  x_aexp, x_bexp, x_dab, x_dba;
    wire [23:0] x_aman, x_bman;
    assign {x_swap, x_v, x_byp, x_err, x_code, x_sub, x_as, x_bs, x_aexp, x_bexp, x_aman, x_bman, x_dab, x_dba} = a2_in;
    function automatic [27:0] jam28;
        input [23:0] man;
        input [7:0]  d;
        reg [27:0] val, lost;
        begin
            val = {1'b0, man, 3'b000};
            if (d >= 8'd28) jam28 = {27'd0, |val};
            else begin
                lost = val & ~({28{1'b1}} << d[4:0]);
                jam28 = (val >> d[4:0]) | {27'd0, |lost};
            end
        end
    endfunction
    wire [27:0] small_a = jam28(x_aman, x_dba);
    wire [27:0] small_b = jam28(x_bman, x_dab);

    reg        s1_v, s1_byp, s1_sub, s1_sign;
    reg [1:0]  s1_err;
    reg [31:0] s1_code;
    reg [7:0]  s1_exp;
    reg [23:0] s1_big;
    reg [27:0] s1_small;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s1_v <= 1'b0;
        else s1_v <= x_v;
    end
    always @(posedge clk) begin
        s1_byp <= x_byp;
        s1_err <= x_err;
        s1_code <= x_code;
        s1_sub <= x_sub;
        s1_sign <= x_swap ? x_bs : x_as;
        s1_exp <= x_swap ? x_bexp : x_aexp;
        s1_big <= x_swap ? x_bman : x_aman;
        s1_small <= x_swap ? small_a : small_b;
    end

    // ---- B1 ----------------------------------------------------------------------------------------
    wire [27:0] big28 = {1'b0, s1_big, 3'b000};
    wire [27:0] sum_w, dif_w;
    wire sum_c, dif_c;
    physical_ot_hdc_ksadd_k #(.W(28)) u_sum (.a(big28), .b(s1_small), .cin(1'b0), .s(sum_w), .cout(sum_c));
    physical_ot_hdc_ksadd_k #(.W(28)) u_dif (.a(big28), .b(~s1_small), .cin(1'b1), .s(dif_w), .cout(dif_c));
    localparam integer WB = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 28 + 28;
    wire [WB-1:0] b2_in;
    physical_ot_hdc_w11_cut #(.W(WB), .CUT(CUT_B), .VB(DRST ? -1 : WB - 1)) u_cb (.clk(clk), .rst_n(rst_n),
        .d({s1_v, s1_byp, s1_sub, s1_sign, s1_err, s1_code, s1_exp, sum_w, dif_w}), .q(b2_in));
    // ---- B2 ----------------------------------------------------------------------------------------
    wire        t_v, t_byp, t_sub, t_sign;
    wire [1:0]  t_err;
    wire [31:0] t_code;
    wire [7:0]  t_exp;
    wire [27:0] sum, dif;
    assign {t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, sum, dif} = b2_in;
    wire carry = sum[27];
    wire [26:0] add_val = carry ? {sum[27:2], sum[1] | sum[0]} : sum[26:0];
    wire [7:0]  room = t_exp - 8'd1;
    wire [26:0] sentinel = (room <= 8'd26) ? (27'd1 << (5'd26 - room[4:0])) : 27'd0;
    wire [5:0]  lz_w;
    physical_ot_hdc_lzc32 u_lzc (.x({dif[26:0] | sentinel, 5'b11111}), .n(lz_w));
    // B2a -> B2b boundary (LAT >= 7)
    localparam integer WD = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 27 + 28 + 6 + 1;
    wire [WD-1:0] d2_in;
    physical_ot_hdc_w11_cut #(.W(WD), .CUT(CUT_D), .VB(DRST ? -1 : WD - 1)) u_cd (.clk(clk), .rst_n(rst_n),
        .d({t_v, t_byp, t_sub, t_sign, t_err, t_code, t_exp, add_val, dif, lz_w, carry}), .q(d2_in));
    wire        w_v, w_byp, w_sub, w_sign, w_carry;
    wire [1:0]  w_err;
    wire [31:0] w_code;
    wire [7:0]  w_exp;
    wire [26:0] w_add;
    wire [27:0] w_dif;
    wire [5:0]  lz;
    assign {w_v, w_byp, w_sub, w_sign, w_err, w_code, w_exp, w_add, w_dif, lz, w_carry} = d2_in;
    wire [26:0] sub_val = w_dif[26:0] << lz[4:0];
    wire [7:0]  exp_sub, exp_add;
    wire exp_sub_c, exp_add_c;
    physical_ot_hdc_ksadd_k #(.W(8)) u_esub (.a(w_exp), .b(~{3'd0, lz[4:0]}), .cin(1'b1), .s(exp_sub), .cout(exp_sub_c));
    physical_ot_hdc_ksadd_k #(.W(8)) u_eadd (.a(w_exp), .b(8'd0), .cin(w_carry), .s(exp_add), .cout(exp_add_c));

    reg        s2_v, s2_byp, s2_sign, s2_zero;
    reg [1:0]  s2_err;
    reg [31:0] s2_code;
    reg [7:0]  s2_exp;
    reg [26:0] s2_val;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) s2_v <= 1'b0;
        else s2_v <= w_v;
    end
    always @(posedge clk) begin
        s2_byp <= w_byp; s2_err <= w_err; s2_code <= w_code; s2_sign <= w_sign;
        s2_zero <= w_sub && (w_dif == 28'd0);
        s2_exp <= w_sub ? exp_sub : exp_add;
        s2_val <= w_sub ? sub_val : w_add;
    end

    // ---- C1 ----------------------------------------------------------------------------------------
    wire inc = s2_val[2] && ((|s2_val[1:0]) || s2_val[3]);
    wire [23:0] rnd_w;
    wire rnd_cw;
    physical_ot_hdc_ksadd_k #(.W(24)) u_rnd (.a(s2_val[26:3]), .b(24'd0), .cin(inc), .s(rnd_w), .cout(rnd_cw));
    localparam integer WC = 1 + 1 + 1 + 1 + 2 + 32 + 8 + 24 + 1;
    // DRST 0 (QK-CORES-10 10-27): err bit 1 is E_OVERFLOW, made only at the output stage; through stages A..C it is
    // the constant 0 of {E_NONE, E_NONFINITE}.  The unreset data cuts carried that 0 as an X power-up chain into err
    // (pv16 slice kit LEC: 32 differs, CHECKED); the defined constant is fed instead.  DRST 1: unchanged.
    wire [1:0] s2_err_c = DRST ? s2_err : {1'b0, s2_err[0]};
    wire [WC-1:0] c2_in;
    physical_ot_hdc_w11_cut #(.W(WC), .CUT(CUT_C), .VB(DRST ? -1 : WC - 1)) u_cc (.clk(clk), .rst_n(rst_n),
        .d({s2_v, s2_byp, s2_zero, s2_sign, s2_err_c, s2_code, s2_exp, rnd_w, rnd_cw}), .q(c2_in));
    // ---- C2 ----------------------------------------------------------------------------------------
    wire        u_v, u_byp, u_zero, u_sign, rnd_c;
    wire [1:0]  u_err;
    wire [31:0] u_code;
    wire [7:0]  u_exp;
    wire [23:0] rnd;
    assign {u_v, u_byp, u_zero, u_sign, u_err, u_code, u_exp, rnd, rnd_c} = c2_in;
    wire [23:0] man = rnd_c ? {1'b1, rnd[23:1]} : rnd;
    wire [8:0]  e = {1'b0, u_exp} + {8'd0, rnd_c};
    wire subnormal = (e == 9'd1) && !man[23];
    wire [31:0] code = {u_sign, subnormal ? 8'd0 : e[7:0], man[22:0]};
    wire over = (u_exp == 8'hff) || (e >= 9'd255);
    generate if (DRST != 0) begin : g_yr
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin y <= 32'd0; err <= E_NONE; valid_out <= 1'b0; end
            else begin
                valid_out <= u_v;
                if (u_byp) begin y <= u_code; err <= u_err; end
                else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
                else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
                else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
            end
        end
    end else begin : g_yn
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) valid_out <= 1'b0;
            else valid_out <= u_v;
        end
        always @(posedge clk) begin
            if (u_byp) begin y <= u_code; err <= u_err; end
            else if (u_zero) begin y <= 32'd0; err <= E_NONE; end
            else if (over) begin y <= 32'd0; err <= E_OVERFLOW; end
            else begin y <= (code[30:0] == 31'd0) ? 32'd0 : code; err <= E_NONE; end
        end
    end endgenerate
endmodule
module physical_ot_hdc_ksadd_k #(
    parameter integer W = 28
) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    input  wire         cin,
    output wire [W-1:0] s,
    output wire         cout
);
    localparam integer L = $clog2(W + 1);
    // position 0 is the carry-in; bit i of the operands is position i + 1
    (* keep *) wire [W:0] g [0:L];
    (* keep *) wire [W:0] p [0:L];
    assign g[0] = {a & b, cin};
    assign p[0] = {a ^ b, 1'b0};
    genvar l, i;
    generate
        for (l = 0; l < L; l = l + 1) begin : g_lv
            for (i = 0; i <= W; i = i + 1) begin : g_b
                if (i >= (1 << l)) begin : g_c
                    assign g[l + 1][i] = g[l][i] | (p[l][i] & g[l][i - (1 << l)]);
                    assign p[l + 1][i] = p[l][i] & p[l][i - (1 << l)];
                end else begin : g_p
                    assign g[l + 1][i] = g[l][i];
                    assign p[l + 1][i] = p[l][i];
                end
            end
        end
    endgenerate
    // carry into operand bit i = the group generate of positions [0, i]
    assign s = (a ^ b) ^ g[L][W-1:0];
    assign cout = g[L][W];
endmodule
module physical_ot_hdc_w11_cut #(parameter integer W = 1, parameter integer CUT = 0, parameter integer VB = -1) (
    input  wire clk, input wire rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    generate if (CUT && VB < 0) begin : g_r
        reg [W-1:0] r;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) r <= {W{1'b0}};
            else r <= d;
        end
        assign q = r;
    end else if (CUT) begin : g_rv
        reg rv;
        reg [W-1:0] rd;
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) rv <= 1'b0;
            else rv <= d[VB];
        end
        always @(posedge clk) rd <= d;
        genvar i;
        for (i = 0; i < W; i = i + 1) begin : g_b
            assign q[i] = (i == VB) ? rv : rd[i];
        end
    end else begin : g_w
        assign q = d;
    end endgenerate
endmodule
module physical_ot_hdc_lzc32 (
    input  wire [31:0] x,
    output wire [5:0]  n
);
    // Level L holds 32 >> L groups; group k covers bits [(k+1)*2^L-1 : k*2^L],
    // with a valid bit (any one) and the count of leading zeros below 2^L.
    reg [31:0]     v, vn;
    reg [32*5-1:0] c, cn;
    integer L, k;
    always @* begin
        v = x;
        c = {(32*5){1'b0}};
        vn = 32'd0;
        cn = {(32*5){1'b0}};
        for (L = 0; L < 5; L = L + 1) begin
            vn = 32'd0;
            cn = {(32*5){1'b0}};
            for (k = 0; k < (16 >> L); k = k + 1) begin
                vn[k] = v[2*k+1] | v[2*k];
                cn[5*k +: 5] = v[2*k+1] ? c[5*(2*k+1) +: 5] : (c[5*(2*k) +: 5] | (5'd1 << L));
            end
            v = vn;
            c = cn;
        end
    end
    assign n = v[0] ? {1'b0, c[4:0]} : 6'd32;
endmodule
module physical_ot_hbm_face_reg #(parameter integer W = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(posedge clk) q <= d;
endmodule
