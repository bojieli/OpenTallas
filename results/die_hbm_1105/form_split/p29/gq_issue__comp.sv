// HBM-FORM-SPLIT d44v part 29: plan form of the gq_issue composition, same ports as ot_hgi_coll_gq_issue.
`default_nettype none
module ot_hgi_gqi__comp #(parameter integer MUT = 0, parameter integer VM_RT = 0) (
    input  wire          clk, rst_n,
    input  wire [1:0]    qid,
    input  wire [7:0]    tgt,
    input  wire          cfg_v,
    input  wire [7:0]    cfg_target,
    input  wire [11:0]   cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          desc_v,
    input  wire [11:0]   desc_base,
    input  wire [12:0]   desc_limit,
    input  wire [15:0]   desc_loops,
    input  wire          launch_v,
    output wire          configured, tgt_fault,
    output wire          active, done,
    output wire          fault,
    input  wire [57:0]   isa_ring,
    input  wire [255:0]  isa_lp_data,
    output wire          ra_lp_we,
    output wire [2:0]    ra_lp_tag,
    output wire [255:0]  ra_lp_data,
    output wire          ra_state_read_add, ra_state_read_tx, ra_state_read_rr,
    output wire [2:0]    ra_state_add_tag, ra_state_tx_tag, ra_state_rr_tag,
    output wire [1:0]    ra_state_add_src,
    output wire          ra_state_add_rhs_acc, ra_state_tx_acc,
    output wire          ra_add_v,
    output wire [2:0]    ra_add_tag,
    output wire [1:0]    ra_add_src,
    output wire          ra_add_rhs_acc,
    output wire [1:0]    ra_tx_inject, ra_tx_forward,
    output wire [2:0]    ra_tx_tag,
    output wire [1:0]    ra_tx_dst,
    output wire          ra_tx_result, ra_tx_acc, ra_tx_gather,
    output wire [3:0]    ra_tx_ttl,
    output wire [1:0]    ra_rx_slot,
    output wire [3:0]    ra_rx_kind, ra_rx_src,
    output wire [5:0]    ra_rx_tag,
    output wire          ra_rr_local,
    output wire [2:0]    ra_rr_local_tag,
    output wire          rb_lp_we,
    output wire [2:0]    rb_lp_tag,
    output wire [255:0]  rb_lp_data,
    output wire          rb_state_read_tx,
    output wire [2:0]    rb_state_tx_tag,
    output wire [1:0]    rb_tx_inject, rb_tx_forward,
    output wire [2:0]    rb_tx_tag,
    output wire [3:0]    rb_tx_ttl,
    output wire [1:0]    rb_rx_slot,
    output wire [3:0]    rb_rx_kind, rb_rx_src,
    output wire [5:0]    rb_rx_tag,
    output wire [67:0]   vm_rq_lo, vm_rq_hi,
    input  wire [1027:0] vm_rr_lo, vm_rr_hi,
    output wire          ld_fire,
    output wire [52:0]   ld_desc,      
    output wire          ld_ev_v,
    output wire [9:0]    ld_ev_k,
    output wire [1:0]    ld_p_v,
    output wire [511:0]  ld_p_d
);
    wire v0, v1, vo0, vo1, f0, f1; wire [1023:0] x0, x1; wire [255:0] q0, q1; wire [9:0] e0, e1;
    ot_hgi_coll_gqi_issue__fs u_i (.clk(clk), .rst_n(rst_n), .qid(qid), .tgt(tgt), .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v), .configured(configured), .tgt_fault(tgt_fault), .active(active), .done(done), .fault(fault), .isa_ring(isa_ring), .isa_lp_data(isa_lp_data), .ra_lp_we(ra_lp_we), .ra_lp_tag(ra_lp_tag), .ra_lp_data(ra_lp_data), .ra_state_read_add(ra_state_read_add), .ra_state_read_tx(ra_state_read_tx), .ra_state_read_rr(ra_state_read_rr), .ra_state_add_tag(ra_state_add_tag), .ra_state_tx_tag(ra_state_tx_tag), .ra_state_rr_tag(ra_state_rr_tag), .ra_state_add_src(ra_state_add_src), .ra_state_add_rhs_acc(ra_state_add_rhs_acc), .ra_state_tx_acc(ra_state_tx_acc), .ra_add_v(ra_add_v), .ra_add_tag(ra_add_tag), .ra_add_src(ra_add_src), .ra_add_rhs_acc(ra_add_rhs_acc), .ra_tx_inject(ra_tx_inject), .ra_tx_forward(ra_tx_forward), .ra_tx_tag(ra_tx_tag), .ra_tx_dst(ra_tx_dst), .ra_tx_result(ra_tx_result), .ra_tx_acc(ra_tx_acc), .ra_tx_gather(ra_tx_gather), .ra_tx_ttl(ra_tx_ttl), .ra_rx_slot(ra_rx_slot), .ra_rx_kind(ra_rx_kind), .ra_rx_src(ra_rx_src), .ra_rx_tag(ra_rx_tag), .ra_rr_local(ra_rr_local), .ra_rr_local_tag(ra_rr_local_tag), .rb_lp_we(rb_lp_we), .rb_lp_tag(rb_lp_tag), .rb_lp_data(rb_lp_data), .rb_state_read_tx(rb_state_read_tx), .rb_state_tx_tag(rb_state_tx_tag), .rb_tx_inject(rb_tx_inject), .rb_tx_forward(rb_tx_forward), .rb_tx_tag(rb_tx_tag), .rb_tx_ttl(rb_tx_ttl), .rb_rx_slot(rb_rx_slot), .rb_rx_kind(rb_rx_kind), .rb_rx_src(rb_rx_src), .rb_rx_tag(rb_rx_tag), .vm_rq_lo(vm_rq_lo), .vm_rq_hi(vm_rq_hi), .vm_rr_lo(vm_rr_lo), .vm_rr_hi(vm_rr_hi), .ld_fire(ld_fire), .ld_desc(ld_desc), .ld_ev_v(ld_ev_v), .ld_ev_k(ld_ev_k), .ld_p_v(ld_p_v), .ld_p_d(ld_p_d),
        .aq0_v(v0), .aq1_v(v1), .aq0_x(x0), .aq1_x(x1), .aq0_vo(vo0), .aq1_vo(vo1), .aq0_fault(f0), .aq1_fault(f1),
        .aq0_q(MUT == 11 ? q1 : q0), .aq1_q(q1), .aq0_e(e0), .aq1_e(MUT == 12 ? e0 : e1));
    ot_hgi_gq_aq_tile__fs u_a0 (.clk(clk), .rst_n(rst_n), .v(v0), .x(x0), .vo(vo0), .q(q0), .e(e0), .fault(f0));
    // MUT 14, 15: quantiser 1 input all NaN on edges where only quantiser 0 has valid (row with r2 = 0).  MUT 14 keeps v1: the poison must stay
    // unseen.  MUT 15 drives v0: quantiser 1 then raises fault on a block it was never given.  Valid gates only vo and fault in the tile, q and e are
    // data pipes, so a wrong valid is visible only through fault, and only on a nonfinite input: this is why MUT 13 alone stayed silent.
    wire v0only = v0 && !v1;
    wire [1023:0] x1p = ((MUT == 14 || MUT == 15) && v0only) ? {32{32'h7fc00000}} : x1;
    ot_hgi_gq_aq_tile__fs u_a1 (.clk(clk), .rst_n(rst_n), .v((MUT == 13 || MUT == 15) ? v0 : v1), .x(x1p), .vo(vo1), .q(q1), .e(e1), .fault(f1));
endmodule
`default_nettype wire
