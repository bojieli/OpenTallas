`timescale 1ns/1fs
// tb_xdie_hbm_coll (TOKEN-XDIE-HBM2 2026-10-18): two HBM d4g GEN2 dies, each with its REAL COLL quadrant parent and its
// REAL endpoint calendar, running a compiled F20 cross-die ALL_REDUCE programme (golden-order FP32 fold) at compiler
// cycles.  Per die (die-level instance names of the d4g GEN2 netlist, quadrant NE, link N2):
//   hb_coll_NE  ot_hfd_coll_q2_hard_v8g #(NLINK 1, TP 192)   issuer_m (static_issuer_v6 + 3 programme SRAMs) programmed by
//                                                             host F20 frames (target 52+QID), ctl_v5, qslots, link_e rail,
//                                                             reduce_static (16 x LAT8 FP32 add lanes), ring_ag, writer v6
//   hcollgi_NE  ot_hgi_coll_gq_issue                         ring-A merge register (gather master, not launched: +2 edges)
//   cp_ep_NE    ot_static_program_target #(TARGET 135, PCW10) F20 collar of the endpoint calendar
//   epcal_NE    hfd_hgi_vm_calendar                          universal calendar; ep_N2 RX controls = calendar[18:0]
//   (lanes)     RLY registered relays each way                (GEN2 hb_coll -> ep lane relays, COLL_EP 9.6)
//   ep_N2       hfd_ep_static                                elastic RX pingpong = the only flow-control point
//   lk_N2       ot_pdie_serdes                               KP4 RS(544,514) enc/dec + rate match; behavioural PMA
// Modelled only: the SU vector source (declared INJLAT-12 boundary, the inputs), the VM read boundary (unused here), ring-A
// neighbours (idle), the off-chip flight (switch 250 + cable 27.6 ns = SWD 333 words for DS; package trace SWD 4 for Qwen),
// die B 300 ppm slow, pad bit errors inside FEC t=15.
// The host loads both programmes (F20 frames), installs the descriptors and launches each die at its endpoint calendar
// phase (pre-edge TX gearbox phase 0) after the common start time T0.  From then on nothing is dynamic on-die: every
// COLL row and every endpoint arm / release / drain word is a fixed compiler cycle (tools/xdie_hbm_coll_compile.py).
// block_ready is CHECKED at the static release edge (never waited for); the published AR result is checked bit-exact
// against the Python golden fold ((x0 + x1) + x2) + x3 on both dies, and every link frame against its source vector.
// Plusargs: +DIR=<compiled dir> +NR0/+NR1 (COLL rows) +NC0/+NC1 (calendar words) +SWD=<flight words> +T0=<ns> +NEND=<cycles>
// Prints XDIE2_* events (edges relative to each die's launch edge L) and one line "XDIE2 ... PASS|FAIL".
module tb_xdie2_rly #(parameter integer W = 613, parameter integer N = 10) (input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
    reg [W-1:0] s [1:N];
    always @(posedge clk) s[1] <= d;
    for (genvar i = 2; i <= N; i = i + 1) begin : g
        always @(posedge clk) s[i] <= s[i-1];
    end
    assign q = s[N];
endmodule

module tb_xdie2_chan #(parameter integer DMAX = 1024) (input wire ck, input wire [543:0] d, output reg [543:0] q,
                                                       input wire ber, input integer D);
    reg [543:0] m [0:DMAX-1];
    integer w = 0, b;
    reg e;
    always @(posedge ck) begin
        e = ber && (($urandom % 2) == 0); b = $urandom % 544;
        q <= m[w];
        m[w] <= e ? (d ^ (544'd1 << b)) : d;
        w = (w >= D - 1) ? 0 : w + 1;
    end
endmodule

module tb_xdie2_die #(parameter integer D = 0, parameter integer RLY = 10, parameter integer IDLE_K = 204) (
    input wire clk, input wire rst_n,
    input wire cfg_v, input wire [7:0] cfg_target, input wire [11:0] cfg_addr, input wire [255:0] cfg_data,
    input wire desc_v, input wire [11:0] desc_base, input wire [12:0] desc_limit, input wire [15:0] desc_loops,
    input wire launch_v,
    output wire [511:0] sd_tx, input wire [511:0] sd_rx, input wire [1:0] sd_st,
    output wire up, output wire coll_conf, output wire cal_conf, output wire anyfault
);
    localparam [1:0] QID = 2'd3;
    // ---------------- hb_coll_NE ----------------
    wire c_conf, c_init, c_pf, c_busy, c_done, c_hf, c_fault, c_done2, rr_v;
    wire [15:0] c_cause; wire [31:0] c_cyc;
    wire [1:0] inj_rd; wire [31:0] inj_idx; wire [159:0] inj_addr; wire [1023:0] inj_d;
    wire [3:0] del_valid; wire [2179:0] del_flit; wire [159:0] del_obase;
    wire [2:0] rr_tag; wire [255:0] rr_d;
    wire [0:0] tx_pin_v, rx_pin_v, retry, phy_up; wire [611:0] tx_pin_flit, rx_pin_flit;
    wire [279:0] cw_o, ccw_o;
    wire [57:0] isa_ring; wire [255:0] isa_lp_data;
    wire ra_lp_we; wire [2:0] ra_lp_tag; wire [255:0] ra_lp_data;
    wire ra_state_read_add, ra_state_read_tx, ra_state_read_rr; wire [2:0] ra_state_add_tag, ra_state_tx_tag, ra_state_rr_tag;
    wire [1:0] ra_state_add_src; wire ra_state_add_rhs_acc, ra_state_tx_acc, ra_add_v; wire [2:0] ra_add_tag;
    wire [1:0] ra_add_src; wire ra_add_rhs_acc; wire [1:0] ra_tx_inject, ra_tx_forward; wire [2:0] ra_tx_tag;
    wire [1:0] ra_tx_dst; wire ra_tx_result, ra_tx_acc, ra_tx_gather; wire [3:0] ra_tx_ttl;
    wire [1:0] ra_rx_slot; wire [3:0] ra_rx_kind, ra_rx_src; wire [5:0] ra_rx_tag; wire ra_rr_local; wire [2:0] ra_rr_local_tag;
    wire [1:0] ag_v; wire [3:0] ag_src; wire [5:0] ag_tag; wire [511:0] ag_d;
    wire [135:0] vm_rq; wire [2055:0] vm_rr; wire [2247:0] vm_kq;
    ot_hfd_coll_q2_hard_v8g #(.NLINK(1), .TP(192)) hb (.rst_n(rst_n), .qid(QID), .clk_program(clk), .clk_control(clk),
        .clk_vmasm({16{clk}}), .clk_upipe({16{clk}}), .clk_issue(clk), .clk_qslots({26{clk}}), .clk_ring({17{clk}}),
        .clk_reduce({33{clk}}), .clk_vmwrite({16{clk}}), .clk_link({5{clk}}),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .program_configured(c_conf), .program_init_busy(c_init), .program_fault(c_pf), .hgi_busy(c_busy), .hgi_done(c_done),
        .hgi_fault(c_hf), .inj_rd(inj_rd), .inj_idx(inj_idx), .hgi_inj_addr(inj_addr), .inj_d(inj_d),
        .del_valid(del_valid), .del_flit(del_flit), .hgi_del_obase(del_obase), .rc_v(1'b0), .rc_tag(3'd0), .rc_d(256'd0),
        .rr_v(rr_v), .rr_tag(rr_tag), .rr_d(rr_d), .phy_up(phy_up), .tx_pin_v(tx_pin_v), .tx_pin_flit(tx_pin_flit),
        .rx_pin_v(rx_pin_v), .rx_pin_flit(rx_pin_flit), .retry_requested(retry),
        .pr_cw_i(280'd0), .pr_ccw_i(280'd0), .pr_cw_o(cw_o), .pr_ccw_o(ccw_o),
        .isa_ring(isa_ring), .isa_lp_data(isa_lp_data),
        .ra_lp_we(ra_lp_we), .ra_lp_tag(ra_lp_tag), .ra_lp_data(ra_lp_data),
        .ra_state_read_add(ra_state_read_add), .ra_state_read_tx(ra_state_read_tx), .ra_state_read_rr(ra_state_read_rr),
        .ra_state_add_tag(ra_state_add_tag), .ra_state_tx_tag(ra_state_tx_tag), .ra_state_rr_tag(ra_state_rr_tag),
        .ra_state_add_src(ra_state_add_src), .ra_state_add_rhs_acc(ra_state_add_rhs_acc), .ra_state_tx_acc(ra_state_tx_acc),
        .ra_add_v(ra_add_v), .ra_add_tag(ra_add_tag), .ra_add_src(ra_add_src), .ra_add_rhs_acc(ra_add_rhs_acc),
        .ra_tx_inject(ra_tx_inject), .ra_tx_forward(ra_tx_forward), .ra_tx_tag(ra_tx_tag), .ra_tx_dst(ra_tx_dst),
        .ra_tx_result(ra_tx_result), .ra_tx_acc(ra_tx_acc), .ra_tx_gather(ra_tx_gather), .ra_tx_ttl(ra_tx_ttl),
        .ra_rx_slot(ra_rx_slot), .ra_rx_kind(ra_rx_kind), .ra_rx_src(ra_rx_src), .ra_rx_tag(ra_rx_tag),
        .ra_rr_local(ra_rr_local), .ra_rr_local_tag(ra_rr_local_tag),
        .ag_v(ag_v), .ag_src(ag_src), .ag_tag(ag_tag), .ag_d(ag_d),
        .vm_rq(vm_rq), .vm_rr(vm_rr), .vm_kq(vm_kq), .fault(c_fault), .fault_cause(c_cause), .done(c_done2), .stat_cycles(c_cyc));
    // ---------------- hcollgi_NE (ring-A merge register; gather programme not installed, never launched) ----------------
    wire gi_conf, gi_tf, gi_act, gi_done, gi_fault;
    wire rb_lp_we; wire [2:0] rb_lp_tag; wire [255:0] rb_lp_data; wire rb_state_read_tx; wire [2:0] rb_state_tx_tag;
    wire [1:0] rb_tx_inject, rb_tx_forward; wire [2:0] rb_tx_tag; wire [3:0] rb_tx_ttl; wire [1:0] rb_rx_slot;
    wire [3:0] rb_rx_kind, rb_rx_src; wire [5:0] rb_rx_tag;
    wire [67:0] gi_rq_lo, gi_rq_hi; wire ld_fire; wire [52:0] ld_desc; wire ld_ev_v; wire [9:0] ld_ev_k;
    wire [1:0] ld_p_v; wire [511:0] ld_p_d;
    ot_hgi_coll_gq_issue gi (.clk(clk), .rst_n(rst_n), .qid(QID), .tgt(8'd179),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .configured(gi_conf), .tgt_fault(gi_tf), .active(gi_act), .done(gi_done), .fault(gi_fault),
        .isa_ring(isa_ring), .isa_lp_data(isa_lp_data),
        .ra_lp_we(ra_lp_we), .ra_lp_tag(ra_lp_tag), .ra_lp_data(ra_lp_data),
        .ra_state_read_add(ra_state_read_add), .ra_state_read_tx(ra_state_read_tx), .ra_state_read_rr(ra_state_read_rr),
        .ra_state_add_tag(ra_state_add_tag), .ra_state_tx_tag(ra_state_tx_tag), .ra_state_rr_tag(ra_state_rr_tag),
        .ra_state_add_src(ra_state_add_src), .ra_state_add_rhs_acc(ra_state_add_rhs_acc), .ra_state_tx_acc(ra_state_tx_acc),
        .ra_add_v(ra_add_v), .ra_add_tag(ra_add_tag), .ra_add_src(ra_add_src), .ra_add_rhs_acc(ra_add_rhs_acc),
        .ra_tx_inject(ra_tx_inject), .ra_tx_forward(ra_tx_forward), .ra_tx_tag(ra_tx_tag), .ra_tx_dst(ra_tx_dst),
        .ra_tx_result(ra_tx_result), .ra_tx_acc(ra_tx_acc), .ra_tx_gather(ra_tx_gather), .ra_tx_ttl(ra_tx_ttl),
        .ra_rx_slot(ra_rx_slot), .ra_rx_kind(ra_rx_kind), .ra_rx_src(ra_rx_src), .ra_rx_tag(ra_rx_tag),
        .ra_rr_local(ra_rr_local), .ra_rr_local_tag(ra_rr_local_tag),
        .rb_lp_we(rb_lp_we), .rb_lp_tag(rb_lp_tag), .rb_lp_data(rb_lp_data), .rb_state_read_tx(rb_state_read_tx),
        .rb_state_tx_tag(rb_state_tx_tag), .rb_tx_inject(rb_tx_inject), .rb_tx_forward(rb_tx_forward), .rb_tx_tag(rb_tx_tag),
        .rb_tx_ttl(rb_tx_ttl), .rb_rx_slot(rb_rx_slot), .rb_rx_kind(rb_rx_kind), .rb_rx_src(rb_rx_src), .rb_rx_tag(rb_rx_tag),
        .vm_rq_lo(gi_rq_lo), .vm_rq_hi(gi_rq_hi), .vm_rr_lo(1028'd0), .vm_rr_hi(1028'd0),
        .ld_fire(ld_fire), .ld_desc(ld_desc), .ld_ev_v(ld_ev_v), .ld_ev_k(ld_ev_k), .ld_p_v(ld_p_v), .ld_p_d(ld_p_d));
    // ---------------- cp_ep_NE + epcal_NE ----------------
    wire p_we, p_start, cp_fault; wire [9:0] p_addr, p_base; wire [255:0] p_data; wire [10:0] p_limit; wire [15:0] p_loops;
    wire cal_v, cal_active, cal_done, cal_fault; wire [31:0] ordinal;
    wire [9:0] client_seq, response_seq; wire [4:0] response_enable; wire [7:0] bank_enable, rslot_v, wslot_v;
    wire [23:0] bank_client, rslot, wslot, lg_local_read, lg_local_write; wire [1:0] hub_ring_enable, ring_tx_enable;
    wire [5:0] hub_ring_client, ring_tx_source; wire replay_enable, replay_source;
    ot_static_program_target #(.TARGET(8'd135), .PCW(10)) cp (.clk(clk), .rst_n(rst_n), .clk_cap(clk), .tgt(8'd0),
        .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data),
        .desc_v(desc_v), .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
        .program_active(cal_active), .program_cfg_we(p_we), .program_cfg_addr(p_addr), .program_cfg_data(p_data),
        .program_start_v(p_start), .program_start_base(p_base), .program_start_limit(p_limit),
        .program_start_loops(p_loops), .configured(cal_conf), .fault(cp_fault));
    hfd_hgi_vm_calendar epcal (.clk(clk), .clk_cap(clk), .clk_mem(clk), .rst_n(rst_n), .cfg_we(p_we), .cfg_addr(p_addr),
        .cfg_data(p_data), .start_v(p_start), .start_base(p_base), .start_limit(p_limit), .start_loops(p_loops),
        .calendar_v(cal_v), .ordinal(ordinal), .active(cal_active), .done(cal_done), .fault(cal_fault),
        .client_seq(client_seq), .response_seq(response_seq), .response_enable(response_enable),
        .bank_enable(bank_enable), .bank_client(bank_client), .hub_ring_enable(hub_ring_enable), .hub_ring_client(hub_ring_client),
        .rslot_v(rslot_v), .wslot_v(wslot_v), .rslot(rslot), .wslot(wslot), .ring_tx_enable(ring_tx_enable),
        .ring_tx_source(ring_tx_source), .replay_enable(replay_enable), .replay_source(replay_source),
        .lg_local_read(lg_local_read), .lg_local_write(lg_local_write));
    wire [186:0] calendar = {lg_local_write, lg_local_read, replay_source, replay_enable, ring_tx_source, ring_tx_enable, wslot,
                             rslot, wslot_v, rslot_v, hub_ring_client, hub_ring_enable, bank_client, bank_enable, response_seq,
                             response_enable, client_seq};
    // ep_N2 RX controls: the low 19 calendar bits (host_completion.json: j = 0, rx_arm_v .. rx_slot_index)
    wire arm_v = calendar[0], arm_b = calendar[1]; wire [6:0] words = calendar[8:2];
    wire rel_v = calendar[9], rel_b = calendar[10], slot_v = calendar[11], slot_b = calendar[12]; wire [5:0] slot_i = calendar[18:13];
    // ---------------- lanes + ep_N2 ----------------
    wire e_tx_v; wire [611:0] e_tx_f; wire e_rx_v; wire [611:0] e_rx_f; wire e_up; wire [1:0] bready;
    wire ep_fault; wire [10:0] ep_cause;
    tb_xdie2_rly #(.W(613), .N(RLY)) u_rt (.clk(clk), .d({tx_pin_v[0], tx_pin_flit}), .q({e_tx_v, e_tx_f}));
    tb_xdie2_rly #(.W(614), .N(RLY)) u_rr (.clk(clk), .d({e_up, e_rx_v, e_rx_f}), .q({phy_up[0], rx_pin_v[0], rx_pin_flit}));
    hfd_ep_static #(.IDLE_K(IDLE_K), .MUT(0)) u_ep (.clk(clk), .rst_n(rst_n),
        .tx_v(e_tx_v), .tx_frame(e_tx_f), .rx_arm_v(arm_v), .rx_arm_bank(arm_b), .rx_block_words(words),
        .rx_release_v(rel_v), .rx_release_bank(rel_b), .rx_slot_v(slot_v), .rx_slot_bank(slot_b),
        .rx_slot_index(slot_i), .rx_pin_v(e_rx_v), .rx_pin_flit(e_rx_f), .rx_block_ready(bready),
        .phy_up(e_up), .fault(ep_fault), .fault_cause(ep_cause), .sd_tx(sd_tx), .sd_rx(sd_rx), .sd_st(sd_st));
    assign up = e_up; assign coll_conf = c_conf;
    // ---------------- declared boundaries: SU vector source (INJLAT 12) + VM read port (7-edge return) ----------------
    reg [511:0] su_mem [0:15];
    localparam integer SUL = 11;
    reg [15:0] s_idx [0:SUL-1]; reg s_rd [0:SUL-1];
    always @(posedge clk) begin
        s_idx[0] <= inj_idx[15:0]; s_rd[0] <= inj_rd[0];
        for (int p = 1; p < SUL; p++) begin s_idx[p] <= s_idx[p-1]; s_rd[p] <= s_rd[p-1]; end
    end
    assign inj_d = {512'd0, s_rd[SUL-1] ? su_mem[s_idx[SUL-1][3:0]] : 512'd0};
    reg [7:0] vm_valid [0:6];
    initial for (int t = 0; t < 7; t++) vm_valid[t] = 0;
    always @(posedge clk) begin
        for (int b = 0; b < 8; b++) vm_valid[0][b] <= vm_rq[b*17+16];
        for (int t = 1; t < 7; t++) vm_valid[t] <= vm_valid[t-1];
    end
    for (genvar b = 0; b < 8; b = b + 1) begin : g_vm
        assign vm_rr[b*257 +: 257] = {vm_valid[6][b], {8{32'h564d0000 + 32'(b)}}};
    end
    // ---------------- observation (edges relative to the launch edge L of this die) ----------------
    reg [511:0] xk [0:3]; reg [511:0] gold; reg [32:0] gmeta;
    string dir;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "missing +DIR");
        for (int i = 0; i < 16; i++) su_mem[i] = 0;
        $readmemh($sformatf("%s/su_d%0d.hex", dir, D), su_mem);
        $readmemh($sformatf("%s/xk.hex", dir), xk);
    end
    reg [544:0] gl [0:1];
    initial begin $readmemh($sformatf("%s/golden.hex", dir), gl); gold = gl[D][511:0]; gmeta = gl[D][544:512]; end
    integer cyc = 0, L = -1, nfault = 0, nrx = 0, npub = 0, pub_ok = 0, sched_fail = 0, rx_bad = 0, pub_edge = -1;
    integer coll_done_seen = 0, cal_done_seen = 0, first_wr = -1, last_rx = -1;
    integer first_fault = -1; reg [15:0] cause_seen = 0; reg [10:0] ep_seen = 0; reg [1:0] br_prev = 0;
    wire [2:0] g_ph = u_ep.u_tx.ph; wire [12:0] g_gc = u_ep.u_tx.gc;
    wire l_wr = hb.u_body.g_link[0].u_link.wr_v, l_rd = hb.u_body.g_link[0].u_link.rd_v;
    wire l_ex = hb.u_body.g_link[0].u_link.rx_expect_v, l_rxv = hb.u_body.g_link[0].u_link.rx_v;
    wire [544:0] l_rxf = hb.u_body.g_link[0].u_link.rx_flit; wire [10:0] l_cause = hb.u_body.g_link[0].u_link.fault_cause;
    wire l_abort = hb.u_body.g_link[0].u_link.epoch_abort;
    wire fault_now = c_fault | gi_fault | gi_tf | cp_fault | cal_fault | ep_fault | (|l_cause) | l_abort;
    assign anyfault = (nfault != 0) | (sched_fail != 0) | (rx_bad != 0);
    function automatic integer rel(); return (L < 0) ? -1 : cyc - L; endfunction
    always @(posedge clk) begin
        // every check below reads the PRE-edge values: the values the flops sample at this edge
        if (launch_v && L < 0) begin L = cyc; $display("XDIE2_L d=%0d edge=%0d ph=%0d gc=%0d", D, cyc, g_ph, g_gc); end
        if (L >= 0) begin
            if (l_wr) begin $display("XDIE2_WR d=%0d rel=%0d", D, rel()); if (first_wr < 0) first_wr = rel(); end
            if (c_done) begin coll_done_seen = 1; $display("XDIE2_DONE d=%0d coll rel=%0d", D, rel()); end
            if (cal_done) begin cal_done_seen = 1; $display("XDIE2_DONE d=%0d cal rel=%0d", D, rel()); end
            if (l_rd) $display("XDIE2_RD d=%0d rel=%0d", D, rel());
            if (l_ex) $display("XDIE2_EX d=%0d rel=%0d pin=%0d", D, rel(), rx_pin_v[0]);
            if (rx_pin_v[0]) $display("XDIE2_RXPIN d=%0d rel=%0d", D, rel());
            if (e_tx_v) $display("XDIE2_TXEP d=%0d rel=%0d ph=%0d gc=%0d", D, rel(), g_ph, g_gc);
            if (u_ep.f_v) $display("XDIE2_LAND d=%0d rel=%0d", D, rel());
            if (arm_v) $display("XDIE2_ARM d=%0d rel=%0d bank=%0d words=%0d", D, rel(), arm_b, words);
            if (slot_v) $display("XDIE2_SLOT d=%0d rel=%0d bank=%0d idx=%0d", D, rel(), slot_b, slot_i);
            if (rel_v) begin
                $display("XDIE2_REL d=%0d rel=%0d bank=%0d ready=%b", D, rel(), rel_b, bready);
                if (!bready[rel_b]) begin
                    sched_fail = sched_fail + 1;
                    $display("XDIE2_SCHED_FAIL d=%0d block bank%0d NOT READY at its static release rel=%0d", D, rel_b, rel());
                end
            end
            for (int b = 0; b < 2; b++) if (bready[b] && !br_prev[b]) $display("XDIE2_RDY d=%0d bank=%0d rel=%0d", D, b, rel());
            br_prev = bready;
            // link frame: bit-exact vs the peer's source vector (frame f of the peer = operand 2*(1-D)+f)
            if (l_rxv) begin
                if (l_rxf !== {1'b1, 8'hff, 8'(1 - D), 16'(2 * (1 - D) + nrx), xk[2 * (1 - D) + nrx]}) begin
                    rx_bad = rx_bad + 1; $display("XDIE2_ERR d=%0d link frame %0d mismatch", D, nrx);
                end
                $display("XDIE2_RXV d=%0d rel=%0d frame=%0d", D, rel(), nrx); last_rx = rel();
                nrx = nrx + 1;
            end
            if (del_valid[0]) begin
                npub = npub + 1; pub_edge = rel();
                if (del_flit[511:0] === gold && del_flit[544:512] === gmeta) pub_ok = pub_ok + 1;
                else begin
                    $display("XDIE2_ERR d=%0d AR payload mismatch (golden-order fold) meta %h/%h", D, del_flit[544:512], gmeta);
                    for (int l = 0; l < 16; l++) if (del_flit[l*32 +: 32] !== gold[l*32 +: 32])
                        $display("XDIE2_ERR d=%0d lane %0d got %h golden %h", D, l, del_flit[l*32 +: 32], gold[l*32 +: 32]);
                end
                $display("XDIE2_PUB d=%0d rel=%0d", D, rel());
            end
            if (|del_valid[3:1]) begin nfault = nfault + 1; $display("XDIE2_ERR d=%0d unexpected delivery %b", D, del_valid); end
        end
        if (fault_now) begin
            if (first_fault < 0) begin
                first_fault = cyc;
                $display("XDIE2_FAULT d=%0d rel=%0d coll=%b cause=%h gq=%b/%b cp=%b cal=%b ep=%b epcause=%h link=%h abort=%b",
                         D, rel(), c_fault, c_cause, gi_fault, gi_tf, cp_fault, cal_fault, ep_fault, ep_cause, l_cause, l_abort);
            end
            nfault = nfault + 1;
        end
        cyc <= cyc + 1;
    end
endmodule

module tb_xdie_hbm_coll;
    parameter integer RLY = 10, IDLE_K = 204;
    localparam real TA = 0.833333, TB = 0.833333 * 1.0003;       // die B 300 ppm slow (plesiochronous dies)
    integer SWD = 333, T0 = 9000, NEND = 2600, NR [0:1], NC [0:1];
    reg ca = 0, cb = 0, rst = 0, ber = 1;
    always #(TA / 2) ca = ~ca;
    always #(TB / 2) cb = ~cb;
    wire ck [0:1]; assign ck[0] = ca; assign ck[1] = cb;
    wire [511:0] txa, txb, rxa, rxb; wire [1:0] sta, stb; wire [543:0] pa, pb, pa_c, pb_c; wire tca, tcb;
    ot_pdie_serdes u_sa (.clk(ca), .rst(rst), .tx(txa), .rx(rxa), .st(sta), .pma_tx(pa), .pma_tck(tca), .pma_rx(pb_c), .pma_rck(tcb));
    ot_pdie_serdes u_sb (.clk(cb), .rst(rst), .tx(txb), .rx(rxb), .st(stb), .pma_tx(pb), .pma_tck(tcb), .pma_rx(pa_c), .pma_rck(tca));
    tb_xdie2_chan u_ab (.ck(tca), .d(pa), .q(pa_c), .ber(ber), .D(SWD));
    tb_xdie2_chan u_ba (.ck(tcb), .d(pb), .q(pb_c), .ber(ber), .D(SWD));
    // host F20 ingress per die (each on its die clock)
    reg cv [0:1]; reg [7:0] tg [0:1]; reg [11:0] ad [0:1]; reg [255:0] dt [0:1]; reg dv [0:1]; reg [11:0] db [0:1];
    reg [12:0] dl [0:1]; reg [15:0] dlp [0:1]; reg lv [0:1];
    wire up [0:1]; wire cconf [0:1]; wire kconf [0:1]; wire af [0:1];
    initial for (int s = 0; s < 2; s++) begin cv[s] = 0; tg[s] = 0; ad[s] = 0; dt[s] = 0; dv[s] = 0; db[s] = 0; dl[s] = 0; dlp[s] = 0; lv[s] = 0; end
    tb_xdie2_die #(.D(0), .RLY(RLY), .IDLE_K(IDLE_K)) dA (.clk(ca), .rst_n(rst), .cfg_v(cv[0]), .cfg_target(tg[0]),
        .cfg_addr(ad[0]), .cfg_data(dt[0]), .desc_v(dv[0]), .desc_base(db[0]), .desc_limit(dl[0]), .desc_loops(dlp[0]),
        .launch_v(lv[0]), .sd_tx(txa), .sd_rx(rxa), .sd_st(sta), .up(up[0]), .coll_conf(cconf[0]), .cal_conf(kconf[0]), .anyfault(af[0]));
    tb_xdie2_die #(.D(1), .RLY(RLY), .IDLE_K(IDLE_K)) dB (.clk(cb), .rst_n(rst), .cfg_v(cv[1]), .cfg_target(tg[1]),
        .cfg_addr(ad[1]), .cfg_data(dt[1]), .desc_v(dv[1]), .desc_base(db[1]), .desc_limit(dl[1]), .desc_loops(dlp[1]),
        .launch_v(lv[1]), .sd_tx(txb), .sd_rx(rxb), .sd_st(stb), .up(up[1]), .coll_conf(cconf[1]), .cal_conf(kconf[1]), .anyfault(af[1]));
    wire [2:0] gph [0:1]; wire [12:0] ggc [0:1];
    assign gph[0] = dA.u_ep.u_tx.ph; assign ggc[0] = dA.u_ep.u_tx.gc; assign gph[1] = dB.u_ep.u_tx.ph; assign ggc[1] = dB.u_ep.u_tx.gc;
    string dir;
    reg [255:0] coll0 [0:447]; reg [255:0] coll1 [0:447]; reg [186:0] cal0 [0:1023]; reg [186:0] cal1 [0:1023];
    integer loaded [0:1], launched [0:1];
    localparam [7:0] TGT_COLL = 8'd55, TGT_CAL = 8'd135;       // 52 + QID(3); 132 + k(NE = 3)
    for (genvar s = 0; s < 2; s = s + 1) begin : g_host
        initial begin
            loaded[s] = 0; launched[s] = 0;
            wait (rst);
            repeat (8) @(negedge ck[s]);
            // COLL programme: per row 6 x 256-b word segments + the 64-b row metadata (F20 frames, 55-edge row drain)
            for (int row = 0; row < NR[s]; row++) begin
                for (int seg = 0; seg < 7; seg++) begin
                    @(negedge ck[s]); cv[s] = 1; tg[s] = TGT_COLL; ad[s] = 12'(row * 8 + seg); dt[s] = (s == 0) ? coll0[row * 7 + seg] : coll1[row * 7 + seg];
                end
                @(negedge ck[s]); cv[s] = 0;
                repeat (55) @(negedge ck[s]);
            end
            // endpoint calendar programme: one protected word per F20 frame
            for (int w = 0; w < NC[s]; w++) begin
                @(negedge ck[s]); cv[s] = 1; tg[s] = TGT_CAL; ad[s] = 12'(w);
                dt[s] = {16'hc7a1, 6'd0, 10'(w), 37'd0, (s == 0) ? cal0[w] : cal1[w]};
            end
            @(negedge ck[s]); cv[s] = 0; repeat (8) @(negedge ck[s]);
            @(negedge ck[s]); dv[s] = 1; tg[s] = TGT_COLL; db[s] = 0; dl[s] = 13'(NR[s]); dlp[s] = 1;
            @(negedge ck[s]); dv[s] = 0; repeat (66) @(negedge ck[s]);
            @(negedge ck[s]); dv[s] = 1; tg[s] = TGT_CAL; db[s] = 0; dl[s] = 13'(NC[s]); dlp[s] = 1;
            @(negedge ck[s]); dv[s] = 0; repeat (NC[s] + 16) @(negedge ck[s]);
            if (!cconf[s] || !kconf[s]) begin $display("XDIE2 FAIL die%0d descriptors not configured coll=%b cal=%b", s, cconf[s], kconf[s]); $finish; end
            loaded[s] = 1;
            // launch at the common start time T0, on the die's first edge whose pre-edge TX gearbox phase is 0
            if ($realtime > T0) begin $display("XDIE2 FAIL die%0d not loaded/up before T0=%0d ns (%0.1f)", s, T0, $realtime); $finish; end
            wait ($realtime >= T0);
            @(negedge ck[s]);
            while (!(gph[s] == 0 && ggc[s] != 13'(IDLE_K))) @(negedge ck[s]);
            if (!up[s]) begin $display("XDIE2 FAIL die%0d link not up at launch", s); $finish; end
            lv[s] = 1; @(negedge ck[s]); lv[s] = 0; launched[s] = 1;
        end
    end
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) $fatal(1, "missing +DIR");
        void'($value$plusargs("SWD=%d", SWD)); void'($value$plusargs("T0=%d", T0)); void'($value$plusargs("NEND=%d", NEND));
        if (!$value$plusargs("NR0=%d", NR[0]) || !$value$plusargs("NR1=%d", NR[1]) ||
            !$value$plusargs("NC0=%d", NC[0]) || !$value$plusargs("NC1=%d", NC[1])) $fatal(1, "missing +NR0/1 +NC0/1");
        if ($test$plusargs("NOBER")) ber = 0;
        $readmemh($sformatf("%s/coll_d0.hex", dir), coll0); $readmemh($sformatf("%s/coll_d1.hex", dir), coll1);
        $readmemh($sformatf("%s/cal_d0.hex", dir), cal0); $readmemh($sformatf("%s/cal_d1.hex", dir), cal1);
        repeat (8) @(posedge ca); rst = 1;
        wait (launched[0] == 1 && launched[1] == 1);
        repeat (NEND) @(posedge ca);
        begin
            reg ok; integer e0, e1;
            e0 = dA.pub_edge; e1 = dB.pub_edge;
            ok = dA.npub == 1 && dB.npub == 1 && dA.pub_ok == 1 && dB.pub_ok == 1 && dA.nrx == 2 && dB.nrx == 2 &&
                 !af[0] && !af[1] && dA.cal_done_seen && dB.cal_done_seen && dA.coll_done_seen && dB.coll_done_seen;
            $display("XDIE2_AR d0 launch->publication %0d cycles | d1 %0d cycles (1.2 GHz; edges from each die's launch)", e0, e1);
            $display("XDIE2_XLINK d0 first_wr=%0d last_rx=%0d | d1 first_wr=%0d last_rx=%0d", dA.first_wr, dA.last_rx, dB.first_wr, dB.last_rx);
            $display("XDIE2 SWD=%0d pub=%0d/%0d ok=%0d/%0d rx=%0d/%0d faults=%0d/%0d sched_fail=%0d/%0d rx_bad=%0d/%0d done=%0d%0d/%0d%0d %s",
                     SWD, dA.npub, dB.npub, dA.pub_ok, dB.pub_ok, dA.nrx, dB.nrx, dA.nfault, dB.nfault, dA.sched_fail, dB.sched_fail,
                     dA.rx_bad, dB.rx_bad, dA.coll_done_seen, dA.cal_done_seen, dB.coll_done_seen, dB.cal_done_seen, ok ? "PASS" : "FAIL");
        end
        $finish;
    end
endmodule
