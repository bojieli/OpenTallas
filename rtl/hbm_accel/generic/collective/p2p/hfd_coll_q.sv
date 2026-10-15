`timescale 1ns/1ps
`default_nettype none
// hfd_coll_q3 / hfd_coll_q2 (HBM die contract v14, owner-approved P2P step 1, 2026-10-14): the two DIE MASTERS of the
// quadrant collective engine, a slice-for-slice rename of the real masters ot_hfd_coll_q3 / ot_hfd_coll_q2
// (ot_hfd_coll_qm.sv).  No logic here (OWNER NO STUBS: the die netlist binds these modules).
//   hfd_coll_q3 = SW (NPT 3, links S0-S2, HOME + QSOLO, the 32-tile TOPK_MERGE array inside, native child clocks)
//   hfd_coll_q2 = SE / NW / NE (NPT 2): no hgi_recx / hgi_ret / TKW / RGX ports at all (QSOLO = SW by contract), so the
//                 die carries no recx net to the three non-SW engines and no idle wide port exists.
// Die ports (one die net a port, one direction a net; die relays are plain register copies):
//   ck, rst                    quadrant clock (phi - R at the pin) and the staged reset release (active low).  The
//                              native child clock entries (ring state/add regions, TKM core/buffer/packer/lane/tile)
//                              are roots of this master's own clock tree from ck: no extra die clock pins.
//   qid[1:0]                   die strap (q2 only; q3 is fixed SW = 0 inside ot_hfd_coll_q3)
//   f_hgi_rec / f_hgi_cfg / (q3) f_hgi_recx, t_hgi_ret       command processor
//   t_inj = {inj_rd[1:0], inj_idx[31:0]}, t_inj_addr, t_vmaddr, f_inj_d                own SU quarter: inject
//   t_del = {hgi_del_obase[159:0], del_flit[2179:0], del_valid[3:0]}                   own SU quarter: delivery
//   f_rc  = {rc_d[255:0], rc_mode, rc_tag[2:0], rc_v}, t_rr = {rc_rdy, rr_d[255:0], rr_tag[2:0], rr_v}     RED_CARRY
//   llk<k>[1119:0]  one link bundle, bit for bit the hfd_lk_ep f_lk bundle (die class link_flit, endpoint 0 = COLL):
//                   [0] t_v, [545:1] t_flit, [546] r_cr, [1117:1094] session (COLL -> link);
//                   [547] r_v, [1092:548] r_flit, [1093] t_cr, [1119:1118] {locked, fault} (link -> COLL)
//   f_pr_cw / t_pr_cw / f_pr_ccw / t_pr_ccw              2 x 2 peer ring (280 b a direction)
//   q3 only, to the SW VM slice master (ot_vms_slice_coll_sw, which embeds the receive leaves and the VM W2 / HBM write
//   clients, so NO lane-arbiter client bus crosses the die; el1014-hbm-p2p-coll.log 11:57 asked for this):
//     t_rgx_t [2212:0] = {rgx_t_vm, rgx_t_data[2047:0], rgx_t_addr[159:0], rgx_t_v[3:0]}   ROW_GATHER writes (registered)
//     f_rgx_t [4:0]    = {rgx_f_fault, rgx_f_cr[3:0]}                                     per-lane return (registered)
//     t_tkw   [568:0]  = {tkw_t_d[567:0] = {addr 40, mask 16, data 512}, tkw_t_v};  f_tkw_cr  TOPK_MERGE line writes
//   (was: t_rgx_c 8,961 b + f_rgx_c 65 b, the W2 client bus; and t_rgx_xw 652 / f_rgx_xwa 2 now leave the slice master)
//     t_rgx_xq / f_rgx_xr  (loader),  t_rgx_vmq / f_rgx_vmr  (SW slice packet client)
//   fault, t_stat (status outputs)

// SW: links S0-S2, TOPK_MERGE array, RGX lanes, HOME and QSOLO
module hfd_coll_q3 (
    input  wire ck, input wire rst,
    input  wire [967:0] f_hgi_rec, input wire [553:0] f_hgi_recx, input wire [39:0] f_hgi_cfg, output wire [2:0] t_hgi_ret,
    output wire [33:0] t_inj, output wire [159:0] t_inj_addr, output wire [79:0] t_vmaddr, input wire [1023:0] f_inj_d,
    output wire [2343:0] t_del, input wire [260:0] f_rc, output wire [260:0] t_rr,
    inout  wire [1119:0] llk0, inout wire [1119:0] llk1, inout wire [1119:0] llk2,
    input  wire [279:0] f_pr_cw, output wire [279:0] t_pr_cw, input wire [279:0] f_pr_ccw, output wire [279:0] t_pr_ccw,
    output wire [568:0] t_tkw, input wire f_tkw_cr,
    output wire [75:0] t_rgx_xq, input wire [513:0] f_rgx_xr, output wire [337:0] t_rgx_vmq, input wire [273:0] f_rgx_vmr,
    output wire [2212:0] t_rgx_t, input wire [4:0] f_rgx_t,
    output wire fault, output wire [31:0] t_stat);
    wire [2:0] tx_v, rx_credit, rx_v, sw_cr, lfault, locked;
    wire [3*545-1:0] tx_flit, rx_flit;
    wire [3*24-1:0] session;
    wire [5:0] lk_status_local;   // per-link status: read by the engine's stat logic only, no die consumer
    assign {llk2[546:0], llk1[546:0], llk0[546:0]} = {rx_credit[2], tx_flit[1090 +: 545], tx_v[2],
                                                      rx_credit[1], tx_flit[545 +: 545], tx_v[1],
                                                      rx_credit[0], tx_flit[0 +: 545], tx_v[0]};
    assign llk0[1117:1094] = session[0 +: 24]; assign llk1[1117:1094] = session[24 +: 24]; assign llk2[1117:1094] = session[48 +: 24];
    assign {sw_cr[0], rx_flit[0 +: 545], rx_v[0]} = llk0[1093:547];
    assign {sw_cr[1], rx_flit[545 +: 545], rx_v[1]} = llk1[1093:547];
    assign {sw_cr[2], rx_flit[1090 +: 545], rx_v[2]} = llk2[1093:547];
    assign {locked[0], lfault[0]} = llk0[1119:1118]; assign {locked[1], lfault[1]} = llk1[1119:1118];
    assign {locked[2], lfault[2]} = llk2[1119:1118];
    wire [1:0] inj_rd; wire [31:0] inj_idx; wire [3:0] del_valid; wire [2179:0] del_flit; wire [159:0] del_obase;
    wire rc_rdy, rr_v; wire [2:0] rr_tag; wire [255:0] rr_d;
    assign t_inj = {inj_rd, inj_idx};
    assign t_del = {del_obase, del_flit, del_valid};
    assign t_rr = {rc_rdy, rr_d, rr_tag, rr_v};
    wire tk_v; wire [567:0] tk_d;
    assign t_tkw = {tk_d, tk_v};
    wire [3:0] rg_v; wire [159:0] rg_a; wire [2047:0] rg_d; wire rg_vm;
    assign t_rgx_t = {rg_vm, rg_d, rg_a, rg_v};
    ot_hfd_coll_q3 u_q (.clk(ck), .rst_n(rst),
        .pr_clk_state({8{ck}}), .pr_clk_add({8{ck}}), .tkm_clk_core(ck), .tkm_clk_buffer(ck), .tkm_clk_packer(ck),
        .tkm_clk_lane({4{ck}}), .tkm_clk_tile({32{ck}}),
        .hgi_rec(f_hgi_rec), .hgi_recx(f_hgi_recx), .hgi_ret(t_hgi_ret), .hgi_cfg(f_hgi_cfg), .hgi_vmaddr(t_vmaddr),
        .hgi_inj_addr(t_inj_addr), .inj_idx(inj_idx), .inj_rd(inj_rd), .inj_d(f_inj_d),
        .del_valid(del_valid), .del_flit(del_flit), .hgi_del_obase(del_obase), .fault(fault), .stat_credit_stall(t_stat),
        .lk_tx_v(tx_v), .lk_tx_flit(tx_flit), .lk_rx_credit(rx_credit), .lk_rx_v(rx_v), .lk_rx_flit(rx_flit),
        .lk_sw_cr(sw_cr), .lk_session(session), .lk_fault(lfault), .lk_locked(locked), .lk_status(lk_status_local),
        .pr_cw_i(f_pr_cw), .pr_cw_o(t_pr_cw), .pr_ccw_i(f_pr_ccw), .pr_ccw_o(t_pr_ccw),
        .rc_v(f_rc[0]), .rc_rdy(rc_rdy), .rc_tag(f_rc[3:1]), .rc_mode(f_rc[4]), .rc_d(f_rc[260:5]),
        .rr_v(rr_v), .rr_tag(rr_tag), .rr_d(rr_d),
        .tkw_t_v(tk_v), .tkw_t_d(tk_d), .tkw_f_cr(f_tkw_cr),
        .rgx_xq(t_rgx_xq), .rgx_xr(f_rgx_xr), .rgx_vmq(t_rgx_vmq), .rgx_vmr(f_rgx_vmr),
        .rgx_t_v(rg_v), .rgx_t_addr(rg_a), .rgx_t_data(rg_d), .rgx_t_vm(rg_vm), .rgx_f_cr(f_rgx_t[3:0]), .rgx_f_fault(f_rgx_t[4]));
endmodule

// SE / NW / NE: two links each; no recx / ret / TKW / RGX ports (the real master ot_hfd_coll_q2 has none)
module hfd_coll_q2 (
    input  wire ck, input wire rst, input wire [1:0] qid,
    input  wire [967:0] f_hgi_rec, input wire [39:0] f_hgi_cfg,
    output wire [33:0] t_inj, output wire [159:0] t_inj_addr, output wire [79:0] t_vmaddr, input wire [1023:0] f_inj_d,
    output wire [2343:0] t_del, input wire [260:0] f_rc, output wire [260:0] t_rr,
    inout  wire [1119:0] llk0, inout wire [1119:0] llk1,
    input  wire [279:0] f_pr_cw, output wire [279:0] t_pr_cw, input wire [279:0] f_pr_ccw, output wire [279:0] t_pr_ccw,
    output wire fault, output wire [31:0] t_stat);
    wire [1:0] tx_v, rx_credit, rx_v, sw_cr, lfault, locked;
    wire [2*545-1:0] tx_flit, rx_flit;
    wire [2*24-1:0] session;
    wire [3:0] lk_status_local;
    assign {llk1[546:0], llk0[546:0]} = {rx_credit[1], tx_flit[545 +: 545], tx_v[1], rx_credit[0], tx_flit[0 +: 545], tx_v[0]};
    assign llk0[1117:1094] = session[0 +: 24]; assign llk1[1117:1094] = session[24 +: 24];
    assign {sw_cr[0], rx_flit[0 +: 545], rx_v[0]} = llk0[1093:547];
    assign {sw_cr[1], rx_flit[545 +: 545], rx_v[1]} = llk1[1093:547];
    assign {locked[0], lfault[0]} = llk0[1119:1118]; assign {locked[1], lfault[1]} = llk1[1119:1118];
    wire [1:0] inj_rd; wire [31:0] inj_idx; wire [3:0] del_valid; wire [2179:0] del_flit; wire [159:0] del_obase;
    wire rc_rdy, rr_v; wire [2:0] rr_tag; wire [255:0] rr_d;
    assign t_inj = {inj_rd, inj_idx};
    assign t_del = {del_obase, del_flit, del_valid};
    assign t_rr = {rc_rdy, rr_d, rr_tag, rr_v};
    ot_hfd_coll_q2 u_q (.clk(ck), .rst_n(rst), .pr_clk_state({8{ck}}), .pr_clk_add({8{ck}}), .qid(qid),
        .hgi_rec(f_hgi_rec), .hgi_cfg(f_hgi_cfg), .hgi_vmaddr(t_vmaddr),
        .hgi_inj_addr(t_inj_addr), .inj_idx(inj_idx), .inj_rd(inj_rd), .inj_d(f_inj_d),
        .del_valid(del_valid), .del_flit(del_flit), .hgi_del_obase(del_obase), .fault(fault), .stat_credit_stall(t_stat),
        .lk_tx_v(tx_v), .lk_tx_flit(tx_flit), .lk_rx_credit(rx_credit), .lk_rx_v(rx_v), .lk_rx_flit(rx_flit),
        .lk_sw_cr(sw_cr), .lk_session(session), .lk_fault(lfault), .lk_locked(locked), .lk_status(lk_status_local),
        .pr_cw_i(f_pr_cw), .pr_cw_o(t_pr_cw), .pr_ccw_i(f_pr_ccw), .pr_ccw_o(t_pr_ccw),
        .rc_v(f_rc[0]), .rc_rdy(rc_rdy), .rc_tag(f_rc[3:1]), .rc_mode(f_rc[4]), .rc_d(f_rc[260:5]),
        .rr_v(rr_v), .rr_tag(rr_tag), .rr_d(rr_d));
endmodule
`default_nettype wire
