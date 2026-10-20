`timescale 1ns/1ps
`default_nettype none
// HBM-AGSM8 (10-20) bench: the DS expert-intermediate gather TRAIN -> w2 x-load static GO chain, production shape.
// Vehicle = tb_hgi_coll_gq (HBM-COLLQ / HBM-BANKLAT-COLL: four quadrant gather masters ot_hgi_coll_gq at VM_RT 74 on the
// GEN2-shaped read path LANES 1 / BANK_RT 72, both rings, real read / kq owner shares, 8-bank quadrant VM models with
// compiled-edge reservation checks), reprogrammed with ONE launch of 7 expert-intermediate rows (QBG R2 Bs 18 F 19,
// stride 24; t_start(k) = k * SP) and, per quadrant, the static GO calendar ot_hgi_coll_seg_go armed by the same
// launch broadcast (off(k) = t_start(k) + SPAN).  At every go_v the bench plays the slot-k w2 SM x-load: it reads the
// quadrant VM image of all 4 slices of segment k AT the GO edge and compares it bit-exact with the golden
// (hdc_golden_v41.quant_fp8 codes + UE8M0 exponent words, tools/hgi_sim/agsm8_chain_vectors_1020.py); destination
// words are poisoned before the run, so a word that has not landed by the GO edge fails.
// Reports launch -> last landing write per segment, the GO edges and the train launch -> last x-load edge.
// Mutants (each MUST FAIL): GOE=1 segment GOSEG's offset one edge early (x-load before the last landing write);
// SWAP=1 the w2 slots of segments 2 and 3 swapped (the slot-2 x-load reads segment 3 at segment 2's GO: wrong segment
// order vs the train's landing order); SP < SP_min (descriptor overlap: the gather master faults).
module tb_agsm8_chain;
    parameter integer MUT = 0, KQMUT = 0;
    parameter integer SP = 129, SPAN = 128, GOE = 0, GOSEG = 4, SWAP = 0;
    parameter integer LANES = 0, VM_RT = 0, BANK_RT = 6, SREG = 0, LT = 65, LG = 4;
    localparam integer PIN = LANES ? 1 : 0;
    function automatic integer DQ(input integer b); return LANES ? ((b * 23 + 5) % (LT + 1)) : 0; endfunction
    function automatic integer DR(input integer b); return LANES ? LT - DQ(b) : 0; endfunction
    localparam integer GL = LANES ? LG : 0;
    parameter string VEC = "vec";
    reg clk = 0, rst_n = 0; always #0.5 clk = ~clk;
    integer cyc = 0; always @(negedge clk) cyc <= cyc + 1;   // stable at every posedge
    integer scenario = 0, errors = 0, reads = 0, writes = 0, checked = 0;
    function automatic integer nextq(input integer q); case (q) 0: nextq = 1; 1: nextq = 3; 3: nextq = 2; default: nextq = 0; endcase endfunction
    function automatic integer prevq(input integer q); case (q) 0: prevq = 2; 1: prevq = 0; 3: prevq = 1; default: prevq = 3; endcase endfunction
    function automatic integer srcof(input integer q, input integer d, input integer h);
        integer s; s = q; for (integer j = 0; j < h; j = j + 1) s = d ? nextq(s) : prevq(s); return s;
    endfunction
    function automatic [255:0] payload(input integer q, input integer w);
        reg [255:0] v; for (integer l = 0; l < 8; l = l + 1) v[l*32 +: 32] = 32'h1b873593 ^ (32'(q) * 32'h9e3779b9) ^ (32'(w) * 32'h85ebca6b) ^ (32'(l) * 32'hc2b2ae35);
        return v;
    endfunction
    // ---------------------------------------------------------------- host frame (broadcast)
    reg cfg_v = 0, desc_v = 0, launch_v = 0; reg [7:0] cfg_target = 0; reg [11:0] cfg_addr = 0; reg [255:0] cfg_data = 0;
    reg [11:0] desc_base = 0; reg [12:0] desc_limit = 0; reg [15:0] desc_loops = 0;
    // fault 4: drop one ring-B transit (missing forward reservation at q1)
    integer drop_at = -1;
    function automatic [1:0] fault_drop(input integer q, input [1:0] f);
        return (scenario == 4 && q == 1 && cyc == drop_at) ? 2'b00 : f;
    endfunction
    // ---------------------------------------------------------------- rings, masters, shares, VM
    wire [279:0] aco [0:3], ano [0:3], bco [0:3], bno [0:3];
    wire [3:0] f_gq, f_ra, f_rb, f_rs, f_ks, conf;
    wire [3:0] f_ld;   // landing-leaf fault alone (NATIVE-SWEEP 10-18: fault 4 must reach the land fault face register)
    reg [57:0] isa [0:3]; reg [255:0] isa_d [0:3];
    wire [135:0] g_rq [0:3]; wire [2055:0] g_rr [0:3]; wire [2247:0] g_kq [0:3];
    wire [135:0] v_rq [0:3]; wire [2055:0] v_rr [0:3]; wire [2247:0] v_kq [0:3];
    reg [2247:0] a_kq [0:3];
    wire [2055:0] a_rr_unused [0:3];
    for (genvar q = 0; q < 4; q = q + 1) begin : g_q
        wire ra_lp_we, ra_srd_add, ra_srd_tx, ra_srd_rr, ra_srhs, ra_stx_acc, ra_add_v, ra_add_rhs, ra_res, ra_acc, ra_gath, ra_rrl;
        wire [2:0] ra_lp_tag, ra_sat, ra_stt, ra_srt, ra_add_tag, ra_tx_tag, ra_rrl_tag; wire [1:0] ra_sas, ra_add_src, ra_inj, ra_fwd, ra_dst, ra_rx;
        wire [255:0] ra_lp_d; wire [3:0] ra_ttl, ra_kind, ra_src; wire [5:0] ra_rtag;
        wire rb_lp_we, rb_rd; wire [2:0] rb_lp_tag, rb_rdt, rb_tag; wire [255:0] rb_lp_d; wire [1:0] rb_inj, rb_fwd, rb_rx;
        wire [3:0] rb_ttl, rb_kind, rb_src; wire [5:0] rb_rtag;
        wire [1:0] pa_v, pb_v; wire [3:0] pa_s, pb_s; wire [5:0] pa_t, pb_t; wire [511:0] pa_d, pb_d;
        wire act, dn, tf, fi, fl; assign f_gq[q] = fi | fl; assign f_ld[q] = fl;
        ot_hgi_coll_gq #(.MUT(MUT), .VM_RT(VM_RT)) gq(.clk_issue(clk), .clk_land(clk), .rst_n(rst_n), .qid(2'(q)), .tgt(8'hb0 + 8'(q)),
            .cfg_v(cfg_v), .cfg_target(cfg_target), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .desc_v(desc_v),
            .desc_base(desc_base), .desc_limit(desc_limit), .desc_loops(desc_loops), .launch_v(launch_v),
            .configured(conf[q]), .tgt_fault(tf), .active(act), .done(dn), .fault(fi), .land_fault(fl),
            .isa_ring(isa[q]), .isa_lp_data(isa_d[q]),
            .ra_lp_we(ra_lp_we), .ra_lp_tag(ra_lp_tag), .ra_lp_data(ra_lp_d), .ra_state_read_add(ra_srd_add),
            .ra_state_read_tx(ra_srd_tx), .ra_state_read_rr(ra_srd_rr), .ra_state_add_tag(ra_sat), .ra_state_tx_tag(ra_stt),
            .ra_state_rr_tag(ra_srt), .ra_state_add_src(ra_sas), .ra_state_add_rhs_acc(ra_srhs), .ra_state_tx_acc(ra_stx_acc),
            .ra_add_v(ra_add_v), .ra_add_tag(ra_add_tag), .ra_add_src(ra_add_src), .ra_add_rhs_acc(ra_add_rhs),
            .ra_tx_inject(ra_inj), .ra_tx_forward(ra_fwd), .ra_tx_tag(ra_tx_tag), .ra_tx_dst(ra_dst), .ra_tx_result(ra_res),
            .ra_tx_acc(ra_acc), .ra_tx_gather(ra_gath), .ra_tx_ttl(ra_ttl), .ra_rx_slot(ra_rx), .ra_rx_kind(ra_kind),
            .ra_rx_src(ra_src), .ra_rx_tag(ra_rtag), .ra_rr_local(ra_rrl), .ra_rr_local_tag(ra_rrl_tag),
            .rb_lp_we(rb_lp_we), .rb_lp_tag(rb_lp_tag), .rb_lp_data(rb_lp_d), .rb_state_read_tx(rb_rd), .rb_state_tx_tag(rb_rdt),
            .rb_tx_inject(rb_inj), .rb_tx_forward(rb_fwd), .rb_tx_tag(rb_tag), .rb_tx_ttl(rb_ttl), .rb_rx_slot(rb_rx),
            .rb_rx_kind(rb_kind), .rb_rx_src(rb_src), .rb_rx_tag(rb_rtag),
            .pa_v(pa_v), .pb_v(pb_v), .pa_src(pa_s), .pb_src(pb_s), .pa_tag(pa_t), .pb_tag(pb_t), .pa_d(pa_d), .pb_d(pb_d),
            .vm_rq(g_rq[q]), .vm_rr(g_rr[q]), .vm_kq(g_kq[q]));
        wire rr_v; wire [2:0] rr_tag; wire [255:0] rr_d;
        ot_hgi_coll_ring_ag #(.SPLIT_CLOCKS(1), .AG(1)) ra(
            .clk(clk), .rst_n(rst_n), .clk_ctl(clk), .clk_state({8{clk}}), .clk_add({8{clk}}), .qid(2'(q)),
            .cw_i(aco[prevq(q)]), .ccw_i(ano[nextq(q)]), .cw_o(aco[q]), .ccw_o(ano[q]),
            .lp_we(ra_lp_we), .lp_tag(ra_lp_tag), .lp_data(ra_lp_d),
            .state_read_add(ra_srd_add), .state_read_tx(ra_srd_tx), .state_read_rr(ra_srd_rr),
            .state_add_tag(ra_sat), .state_tx_tag(ra_stt), .state_rr_tag(ra_srt), .state_add_src(ra_sas),
            .state_add_rhs_acc(ra_srhs), .state_tx_acc(ra_stx_acc),
            .add_v(ra_add_v), .add_tag(ra_add_tag), .add_src(ra_add_src), .add_rhs_acc(ra_add_rhs),
            .tx_inject(ra_inj), .tx_forward(ra_fwd), .tx_tag(ra_tx_tag), .tx_dst(ra_dst), .tx_result(ra_res), .tx_acc(ra_acc),
            .tx_gather(ra_gath), .tx_ttl(ra_ttl), .rx_slot(ra_rx), .rx_kind(ra_kind), .rx_src(ra_src), .rx_tag(ra_rtag),
            .rr_local(ra_rrl), .rr_local_tag(ra_rrl_tag), .rr_v(rr_v), .rr_tag(rr_tag), .rr_d(rr_d),
            .ag_v(pa_v), .ag_src(pa_s), .ag_tag(pa_t), .ag_d(pa_d), .fault(f_ra[q]));
        ot_hgi_coll_ring_b_stop rb(.clk(clk), .rst_n(rst_n), .qid(2'(q)),
            .cw_i(bco[prevq(q)]), .ccw_i(bno[nextq(q)]), .cw_o(bco[q]), .ccw_o(bno[q]),
            .lp_we(rb_lp_we), .lp_tag(rb_lp_tag), .lp_data(rb_lp_d), .state_read_tx(rb_rd), .state_tx_tag(rb_rdt),
            .tx_inject(rb_inj), .tx_forward(fault_drop(q, rb_fwd)), .tx_tag(rb_tag), .tx_ttl(rb_ttl),
            .rx_slot(rb_rx), .rx_kind(rb_kind), .rx_src(rb_src), .rx_tag(rb_rtag),
            .ag_v(pb_v), .ag_src(pb_s), .ag_tag(pb_t), .ag_d(pb_d), .fault(f_rb[q]));
        // gq <-> share lanes (GL registered stations each way)
        wire [135:0] s_rq; wire [2055:0] s_rr;
        if (GL == 0) begin : g_nl assign s_rq = g_rq[q]; assign g_rr[q] = s_rr; end
        else begin : g_l
            reg [135:0] lq [0:GL-1]; reg [2055:0] lr [0:GL-1];
            always @(posedge clk) begin
                lq[0] <= rst_n ? g_rq[q] : '0; lr[0] <= rst_n ? s_rr : '0;
                for (integer d = 1; d < GL; d = d + 1) begin lq[d] <= lq[d-1]; lr[d] <= lr[d-1]; end
            end
            assign s_rq = lq[GL-1]; assign g_rr[q] = lr[GL-1];
        end
        ot_hbm_idx_vm_share2_static #(.REG(SREG), .BANK_RT(BANK_RT)) rs(.clk_pair({4{clk}}), .rst_n(rst_n), .a_rq(136'd0), .b_rq(s_rq), .vm_rq(v_rq[q]),
            .vm_rr(v_rr[q]), .a_rr(a_rr_unused[q]), .b_rr(s_rr), .fault(f_rs[q]));
        ot_hgi_coll_kq_share2 #(.MUT(KQMUT)) ks(.clk_pair({4{clk}}), .rst_n(rst_n), .a_kq(a_kq[q]), .b_kq(g_kq[q]),
            .vm_kq(v_kq[q]), .fault(f_ks[q]));
    end
    // ---------------------------------------------------------------- VM model (per quadrant, 8 banks)
    reg [255:0] mem [0:3][0:16383];
    reg [255:0] rpipe_d [0:3][0:7][0:5]; reg rpipe_v [0:3][0:7][0:5];
    reg [256:0] rr_reg [0:3][0:7];
    wire [16:0] m_rq [0:3][0:7];             // request as the bank model samples it (after rq lane DQ[b] + PIN)
    for (genvar q = 0; q < 4; q = q + 1) begin : g_vrr
        for (genvar b = 0; b < 8; b = b + 1) begin : g_b
            localparam integer NQ = DQ(b) + PIN, NRR = DR(b);
            if (NQ == 0) begin : g_q0 assign m_rq[q][b] = v_rq[q][b*17 +: 17]; end
            else begin : g_qd
                reg [16:0] d [0:NQ-1];
                always @(posedge clk) begin d[0] <= rst_n ? v_rq[q][b*17 +: 17] : '0; for (integer k = 1; k < NQ; k = k + 1) d[k] <= d[k-1]; end
                assign m_rq[q][b] = d[NQ-1];
            end
            if (NRR == 0) begin : g_r0 assign v_rr[q][b*257 +: 257] = rr_reg[q][b]; end
            else begin : g_rd
                reg [256:0] d [0:NRR-1];
                always @(posedge clk) begin d[0] <= rr_reg[q][b]; for (integer k = 1; k < NRR; k = k + 1) d[k] <= d[k-1]; end
                assign v_rr[q][b*257 +: 257] = d[NRR-1];
            end
        end
    end
    // compiled reservations: rres/wres[q][b] = list of edges (bitmap over cycles)
    localparam integer NC = 4096;
    bit rres [0:3][0:7][0:NC-1]; bit wres [0:3][0:7][0:NC-1]; reg [15:0] wsec [0:3][0:7][0:NC-1]; reg [15:0] rsec [0:3][0:7][0:NC-1];
    always @(posedge clk) begin
        for (integer q = 0; q < 4; q = q + 1) for (integer b = 0; b < 8; b = b + 1) begin
            reg [16:0] r; reg [280:0] k; reg [13:0] a;
            r = m_rq[q][b]; k = v_kq[q][b*281 +: 281];
            rr_reg[q][b] <= {rpipe_v[q][b][5], rpipe_d[q][b][5]};
            for (integer d = 5; d > 0; d = d - 1) begin rpipe_v[q][b][d] <= rpipe_v[q][b][d-1]; rpipe_d[q][b][d] <= rpipe_d[q][b][d-1]; end
            rpipe_v[q][b][0] <= 1'b0;
            if (rst_n && r[16]) begin
                a = {r[15], r[12:0]};
                if (r[2:0] != 3'(b) || (!r[15] && r[14:13] != 2'(q))) begin errors++; $display("AGSM8 VM q%0d b%0d bad read sector %h", q, b, r[15:0]); end
                if (!rres[q][b][cyc] || rsec[q][b][cyc] != r[15:0]) begin
                    if (errors < 20) $display("AGSM8 VM q%0d b%0d unreserved read cyc%0d sector %h (exp %0d %h)", q, b, cyc, r[15:0], rres[q][b][cyc], rsec[q][b][cyc]);
                    errors++;
                end
                rres[q][b][cyc] = 0; reads++;
                rpipe_v[q][b][0] <= 1'b1; rpipe_d[q][b][0] <= mem[q][a];
            end
            if (rst_n && k[280]) begin
                a = {k[279], k[276:264]};
                if (k[266:264] != 3'(b) || (!k[279] && k[278:277] != 2'(q)) || k[7:0] != 8'hff) begin errors++; $display("AGSM8 VM q%0d b%0d bad write %h", q, b, k[279:264]); end
                if (scenario == 0 && (!wres[q][b][cyc] || wsec[q][b][cyc] != k[279:264])) begin
                    if (errors < 20) $display("AGSM8 VM q%0d b%0d unreserved write cyc%0d sector %h (exp %0d %h)", q, b, cyc, k[279:264], wres[q][b][cyc], wsec[q][b][cyc]);
                    errors++;
                end
                wres[q][b][cyc] = 0; writes++;
                mem[q][a] <= k[263:8];
                for (integer row = 0; row < NR; row = row + 1)
                    if (a >= 14'(r_dst[row]) && a < 14'(r_dst[row] + 4 * r_str[row]) && cyc > last_w[row]) last_w[row] = cyc;
            end
        end
    end
    // ---------------------------------------------------------------- descriptors (7-row expert-intermediate train)
    localparam integer NR = 7, PERIOD = 7 * SP + SPAN + 64, LOOPS = 1;
    localparam integer KS = 2;   // HBM-NSFIX/KQS 10-18: registered kq share (pin flops + vm_kq flops): every COLL kq bank sample +2 edges
    localparam integer GO_LAT = 4;   // ot_hgi_coll_seg_go: go_v sampled L + 4 + off
    integer r_qbg [0:NR-1] = '{1, 1, 1, 1, 1, 1, 1};
    integer r_r2 [0:NR-1] = '{1, 1, 1, 1, 1, 1, 1};
    integer r_self [0:NR-1] = '{1, 1, 1, 1, 1, 1, 1};
    integer r_t [0:NR-1];
    integer r_f [0:NR-1] = '{19, 19, 19, 19, 19, 19, 19};
    integer r_bs [0:NR-1] = '{18, 18, 18, 18, 18, 18, 18};
    integer r_src [0:NR-1] = '{'h1000, 'h1080, 'h1100, 'h1180, 'h1200, 'h1280, 'h1300};
    integer r_dst [0:NR-1] = '{'h0400, 'h0480, 'h0500, 'h0580, 'h0600, 'h0680, 'h0700};
    integer r_str [0:NR-1] = '{24, 24, 24, 24, 24, 24, 24};
    integer last_w [0:NR-1];              // last landing write edge of each segment (any quadrant)
    integer go_e [0:3][0:NR-1];            // GO edge per quadrant / segment (as sampled)
    integer go_n [0:3];
    integer xl_ok = 0, xl_bad = 0;
    reg [255:0] srcw [0:NR-1][0:3][0:191]; reg [255:0] recw [0:NR-1][0:3][0:63];
    localparam [255:0] POISON = {8{32'hdeadbeef}};
    reg [255:0] srct [0:191]; reg [255:0] rect [0:63];
    function automatic [15:0] sec(input integer q, input integer w); return {1'b0, 2'(q), 13'(w)}; endfunction
    task automatic frame_cfg(input integer q, input integer row, input [223:0] payload);
        @(negedge clk); cfg_v = 1; cfg_target = 8'hb0 + 8'(q); cfg_addr = 12'(row); cfg_data = {16'hc7a1, 4'b0, 12'(row), payload};
        @(negedge clk); cfg_v = 0;
    endtask
    integer L = -1;        // launch sample edge
    task automatic at_edge(input integer t); @(posedge clk iff (cyc == t - 1)); #0.1; endtask
    task automatic compile(input integer row, input integer loop);
        integer fe, K, R;
        R = r_r2[row] ? 2 : 1; K = (r_f[row] + R - 1) / R;
        fe = L + 3 + loop * PERIOD + r_t[row];
        for (integer q = 0; q < 4; q = q + 1)
            for (integer i = 0; i < r_f[row]; i = i + 1) begin
                integer r, k, ie, d, a;
                r = i % R; k = i / R; d = k % 2; ie = fe + 1 + 3 * (k / 2) + (k % 2);
                if (r_qbg[row] && i < r_bs[row]) for (integer w = 0; w < 4; w = w + 1) begin
                    a = r_src[row] + 4 * i + w; rres[q][a%8][ie+1+GL+SREG+PIN+DQ(a%8)] = 1; rsec[q][a%8][ie+1+GL+SREG+PIN+DQ(a%8)] = sec(q, a);
                end
                if (!r_qbg[row]) begin a = r_src[row] + i; rres[q][a%8][ie+16+GL+SREG+PIN+DQ(a%8)] = 1; rsec[q][a%8][ie+16+GL+SREG+PIN+DQ(a%8)] = sec(q, a); end
                for (integer h = 1; h <= 3; h = h + 1) begin
                    integer s; s = srcof(q, d, h); a = r_dst[row] + s * r_str[row] + i;
                    wres[q][a%8][ie+32+KS+2*h+VM_RT] = 1; wsec[q][a%8][ie+32+KS+2*h+VM_RT] = sec(q, a);
                end
                if (r_self[row] || r_qbg[row]) begin a = r_dst[row] + q * r_str[row] + i; wres[q][a%8][ie+27+KS+VM_RT] = 1; wsec[q][a%8][ie+27+KS+VM_RT] = sec(q, a); end
            end
    endtask
    // ---------------------------------------------------------------- ISA pass-through master (not on a ring)
    reg [57:0] xi; reg [255:0] xd; wire [63:0] xo_ctl; wire [255:0] xo_d;
    reg [57:0] xi_h [0:3]; reg [255:0] xd_h [0:3]; integer xchk = 0;
    wire xa_lp_we, xa_srd_add, xa_srd_tx, xa_srd_rr, xa_srhs, xa_stx_acc, xa_add_v, xa_add_rhs, xa_res, xa_acc, xa_gath, xa_rrl;
    wire [2:0] xa_lp_tag, xa_sat, xa_stt, xa_srt, xa_add_tag, xa_tx_tag, xa_rrl_tag; wire [1:0] xa_sas, xa_add_src, xa_inj, xa_fwd, xa_dst, xa_rx;
    wire [3:0] xa_ttl, xa_kind, xa_src; wire [5:0] xa_rtag; wire xf, xc, xt, xact, xdn;
    ot_hgi_coll_gq_issue gx(.clk(clk), .rst_n(rst_n), .qid(2'd0), .tgt(8'hbf), .cfg_v(1'b0), .cfg_target(8'd0), .cfg_addr(12'd0),
        .cfg_data(256'd0), .desc_v(1'b0), .desc_base(12'd0), .desc_limit(13'd0), .desc_loops(16'd0), .launch_v(1'b0),
        .configured(xc), .tgt_fault(xt), .active(xact), .done(xdn), .fault(xf), .isa_ring(xi), .isa_lp_data(xd),
        .ra_lp_we(xa_lp_we), .ra_lp_tag(xa_lp_tag), .ra_lp_data(xo_d), .ra_state_read_add(xa_srd_add), .ra_state_read_tx(xa_srd_tx),
        .ra_state_read_rr(xa_srd_rr), .ra_state_add_tag(xa_sat), .ra_state_tx_tag(xa_stt), .ra_state_rr_tag(xa_srt),
        .ra_state_add_src(xa_sas), .ra_state_add_rhs_acc(xa_srhs), .ra_state_tx_acc(xa_stx_acc), .ra_add_v(xa_add_v),
        .ra_add_tag(xa_add_tag), .ra_add_src(xa_add_src), .ra_add_rhs_acc(xa_add_rhs), .ra_tx_inject(xa_inj), .ra_tx_forward(xa_fwd),
        .ra_tx_tag(xa_tx_tag), .ra_tx_dst(xa_dst), .ra_tx_result(xa_res), .ra_tx_acc(xa_acc), .ra_tx_gather(xa_gath), .ra_tx_ttl(xa_ttl),
        .ra_rx_slot(xa_rx), .ra_rx_kind(xa_kind), .ra_rx_src(xa_src), .ra_rx_tag(xa_rtag), .ra_rr_local(xa_rrl), .ra_rr_local_tag(xa_rrl_tag),
        .rb_lp_we(), .rb_lp_tag(), .rb_lp_data(), .rb_state_read_tx(), .rb_state_tx_tag(), .rb_tx_inject(), .rb_tx_forward(),
        .rb_tx_tag(), .rb_tx_ttl(), .rb_rx_slot(), .rb_rx_kind(), .rb_rx_src(), .rb_rx_tag(),
        .vm_rq_lo(), .vm_rq_hi(), .vm_rr_lo(1028'd0), .vm_rr_hi(1028'd0), .ld_fire(), .ld_desc(), .ld_ev_v(), .ld_ev_k(), .ld_p_v(), .ld_p_d());
    // v5 p_ring[57:0] order
    wire [57:0] xo = {xa_rrl_tag, xa_rrl, xa_rtag, xa_src, xa_kind, xa_rx, xa_acc, xa_res, xa_dst, xa_tx_tag, xa_fwd, xa_inj,
                      xa_add_rhs, xa_add_src, xa_add_tag, xa_add_v, xa_srt, xa_srd_rr, xa_stx_acc, xa_stt, xa_srd_tx, xa_srhs,
                      xa_sas, xa_sat, xa_srd_add, xa_lp_tag, xa_lp_we};
    // ---------------------------------------------------------------- static GO calendars (one a quadrant) + w2 x-load
    reg sg_we = 0; reg [2:0] sg_seg = 0; reg [15:0] sg_off = 0; reg [3:0] sg_n = 0;
    wire [3:0] sg_go, sg_arm, sg_flt; wire [2:0] sg_gs [0:3];
    for (genvar q = 0; q < 4; q = q + 1) begin : g_sg
        ot_hgi_coll_seg_go #(.NSEG(8)) sg(.clk(clk), .rst_n(rst_n), .cfg_we(sg_we), .cfg_seg(sg_seg), .cfg_off(sg_off),
            .cfg_n(sg_n), .launch_v(launch_v), .go_v(sg_go[q]), .go_seg(sg_gs[q]), .armed(sg_arm[q]), .fault(sg_flt[q]));
        always @(posedge clk) if (rst_n && sg_go[q]) begin : xl
            integer k, bad; bad = 0;
            k = sg_gs[q];
            if (SWAP && k == 2) k = 3; else if (SWAP && k == 3) k = 2;   // mutant: slot order != train landing order
            go_e[q][go_n[q]] = cyc; go_n[q] = go_n[q] + 1;
            // slot-k w2 x-load: every word of the gathered segment k (4 slices) from this quadrant's VM image at the GO edge
            for (integer s = 0; s < 4; s = s + 1) for (integer i = 0; i < r_f[k]; i = i + 1)
                if (mem[q][r_dst[k] + s * r_str[k] + i] !== recw[k][s][i]) bad = bad + 1;
            if (bad) begin xl_bad = xl_bad + 1; if (errors < 30) $display("AGSM8 XLOAD q%0d seg%0d GO cyc%0d (L+%0d): %0d words not landed / wrong", q, k, cyc, cyc - L, bad); errors++; end
            else xl_ok = xl_ok + 1;
        end
    end
    // ---------------------------------------------------------------- run
    integer last_edge = 0;
    initial begin
        if ($value$plusargs("fault=%d", scenario)) begin end
        for (integer q = 0; q < 4; q = q + 1) begin
            isa[q] = 0; isa_d[q] = 0; a_kq[q] = 0;
            for (integer a = 0; a < 16384; a = a + 1) mem[q][a] = 256'd0;
            for (integer b = 0; b < 8; b = b + 1) begin
                rr_reg[q][b] = 0; for (integer d = 0; d < 6; d = d + 1) rpipe_v[q][b][d] = 0;
                for (integer c = 0; c < NC; c = c + 1) begin rres[q][b][c] = 0; wres[q][b][c] = 0; end
            end
        end
        xi = 0; xd = 0;
        for (integer row = 0; row < NR; row = row + 1) begin r_t[row] = row * SP; last_w[row] = -1; end
        for (integer q = 0; q < 4; q = q + 1) go_n[q] = 0;
        // source data
        for (integer row = 0; row < NR; row = row + 1) for (integer q = 0; q < 4; q = q + 1) begin
            if (r_qbg[row]) begin
                // the closure daemon simulator (v5.050) refuses $readmemh into a sub-array: load 1-D temporaries, then copy
                $readmemh({VEC, "/seg", $sformatf("%0d", row), "_q", $sformatf("%0d", q), "_src.hex"}, srct, 0, 4 * r_bs[row] - 1);
                $readmemh({VEC, "/seg", $sformatf("%0d", row), "_q", $sformatf("%0d", q), "_rec.hex"}, rect, 0, r_f[row] - 1);
                for (integer w = 0; w < 4 * r_bs[row]; w = w + 1) srcw[row][q][w] = srct[w];
                for (integer w = 0; w < r_f[row]; w = w + 1) recw[row][q][w] = rect[w];
                for (integer w = 0; w < 4 * r_bs[row]; w = w + 1) mem[q][r_src[row] + w] = srcw[row][q][w];
            end else for (integer w = 0; w < r_f[row]; w = w + 1) mem[q][r_src[row] + w] = payload(q, 100 * row + w);
            for (integer w = 0; w < 4 * r_str[row]; w = w + 1) mem[q][r_dst[row] + w] = POISON;
        end
        repeat (5) @(negedge clk); rst_n = 1; repeat (6) @(negedge clk);
        // ISA pass-through: random words, compared 2 edges later (xo is the merge register)
        for (integer t = 0; t < 40; t = t + 1) begin
            @(negedge clk);
            if (t >= 2) begin
                if (xo !== xi_h[(t-2)%4] || xo_d !== (xi_h[(t-2)%4][0] ? xd_h[(t-2)%4] : xd_h[(t-2)%4])) begin
                    if (errors < 20) $display("AGSM8 ISA pass-through t%0d got %h exp %h", t, xo, xi_h[(t-2)%4]); errors++;
                end else xchk++;
            end
            xi = {$urandom, $urandom}; xi[28:27] = 0; xd = {8{$urandom}};   // no ISA inject (gather owns tx_gather)
            xi_h[t%4] = xi; xd_h[t%4] = xd;
        end
        @(negedge clk); xi = 0;
        // programme every quadrant
        for (integer q = 0; q < 4; q = q + 1) for (integer row = 0; row < NR; row = row + 1) begin
            reg [223:0] p; p = 0;
            p[0] = 1'(r_qbg[row]); p[1] = 1'(r_r2[row]); p[2] = 1'(r_self[row]); p[18:3] = 16'(r_t[row]);
            if (scenario == 2 && row == 1) p[18:3] = 16'(r_t[0] + 20);
            p[28:19] = 10'(r_f[row]); p[36:29] = 8'(r_bs[row]); p[52:37] = sec(q, r_src[row]); p[68:53] = sec(q, r_dst[row]);
            p[84:69] = 16'(r_str[row]); p[100:85] = 16'(PERIOD);
            frame_cfg(q, row, p);
        end
        for (integer q = 0; q < 4; q = q + 1) begin
            @(negedge clk); desc_v = 1; cfg_target = 8'hb0 + 8'(q); desc_base = 0; desc_limit = NR; desc_loops = LOOPS;
            @(negedge clk); desc_v = 0;
        end
        for (integer row = 0; row < NR; row = row + 1) begin
            integer o;
            o = r_t[row] + SPAN - ((GOE && row == GOSEG) ? 1 : 0);
            @(negedge clk); sg_we = 1; sg_seg = 3'(row); sg_off = 16'(o); sg_n = 4'(NR);
        end
        @(negedge clk); sg_we = 0;
        repeat (30) @(negedge clk);
        if (conf !== 4'hf) begin $display("AGSM8 FAIL targets not configured %b", conf); $finish; end
        launch_v = 1; @(posedge clk); L = cyc; @(negedge clk); launch_v = 0;
        for (integer l = 0; l < LOOPS; l = l + 1) for (integer row = 0; row < NR; row = row + 1) compile(row, l);
        last_edge = L + 3 + LOOPS * PERIOD + 100;
        // edges: IE(k=0) = L + 4; a value set by at_edge(T) is sampled at the posedge where cyc == T
        if (scenario == 1) fork begin at_edge(L + 4 + 27 + VM_RT); isa[2][28:27] = 2'b01; at_edge(L + 4 + 28 + VM_RT); isa[2] = 0; end join_none
        if (scenario == 3) fork begin at_edge(L + 4 + 34 + VM_RT); a_kq[1][((r_dst[0] + prevq(1) * r_str[0]) % 8) * 281 + 280] = 1'b1;
            at_edge(L + 4 + 35 + VM_RT); a_kq[1] = 0; end join_none
        drop_at = L + 4 + 30 + VM_RT;           // ring-B stop samples the first h=1 transit (k=0) here
        while (cyc < last_edge) @(negedge clk);
        // checks
        if (scenario != 0) begin
            if ((|f_gq || |f_ra || |f_rb || |f_ks) && (scenario != 4 || |f_ld))
                $display("AGSM8 FAULT PASS scenario=%0d gq%b ra%b rb%b ks%b ld%b", scenario, f_gq, f_ra, f_rb, f_ks, f_ld);
            else $display("AGSM8 FAULT ESCAPED scenario=%0d", scenario);
            $finish;
        end
        for (integer q = 0; q < 4; q = q + 1) if (go_n[q] != NR) begin $display("AGSM8 q%0d GO count %0d != %0d", q, go_n[q], NR); errors++; end
        if (|sg_flt) begin $display("AGSM8 seg_go fault %b", sg_flt); errors++; end
        for (integer row = 0; row < NR; row = row + 1)
            $display("AGSM8_SEG %0d fire L+%0d last_landing_write L+%0d go L+%0d (q0) lead %0d", row, 3 + r_t[row], last_w[row] - L,
                     go_e[0][row] - L, go_e[0][row] - last_w[row]);
        if (|f_gq || |f_ra || |f_rb || |f_rs || |f_ks) begin $display("AGSM8 unexpected fault gq%b ra%b rb%b rs%b ks%b", f_gq, f_ra, f_rb, f_rs, f_ks); errors++; end
        for (integer q = 0; q < 4; q = q + 1) for (integer b = 0; b < 8; b = b + 1) for (integer c = 0; c < NC; c = c + 1) begin
            if (rres[q][b][c]) begin if (errors < 30) $display("AGSM8 missing read q%0d b%0d cyc%0d", q, b, c); errors++; end
            if (wres[q][b][c]) begin if (errors < 30) $display("AGSM8 missing write q%0d b%0d cyc%0d", q, b, c); errors++; end
        end
        for (integer row = 0; row < NR; row = row + 1) for (integer q = 0; q < 4; q = q + 1) for (integer s = 0; s < 4; s = s + 1)
            for (integer i = 0; i < r_f[row]; i = i + 1) begin
                reg [255:0] e, g;
                if (s == q && !(r_self[row] || r_qbg[row])) continue;
                e = r_qbg[row] ? recw[row][s][i] : payload(s, 100 * row + i);
                g = mem[q][r_dst[row] + s * r_str[row] + i];
                if (g !== e) begin if (errors < 30) $display("AGSM8 DATA row%0d q%0d seg%0d word%0d got %h exp %h", row, q, s, i, g, e); errors++; end
                else checked++;
            end
        if (errors == 0) $display("AGSM8 PASS lanes=%0d vm_rt=%0d bank_rt=%0d sp=%0d span=%0d segs=%0d vm_words_checked=%0d xload_ok=%0d reads=%0d writes=%0d train_launch_to_last_landing=%0d launch_to_last_go=%0d",
            LANES, VM_RT, BANK_RT, SP, SPAN, NR, checked, xl_ok, reads, writes, last_w[NR-1] - L, go_e[0][NR-1] - L);
        else $display("AGSM8 FAIL errors=%0d", errors);
        $finish;
    end
endmodule
`default_nettype wire
