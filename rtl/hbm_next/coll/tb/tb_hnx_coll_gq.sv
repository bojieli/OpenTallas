`timescale 1ns/1ps
`default_nettype none
// HBM-COLLQ bench: four quadrant COLL gather masters (ot_hnx_coll_gq = issue leaf with 2 quantisers + landing leaf) driving the two
// cross-quadrant rings (ring A = ot_hgi_coll_ring_ag full stop, ring B = ot_hgi_coll_ring_b_stop die block, ring order
// q0 -> q1 -> q3 -> q2 -> q0), each landing into its own quadrant VM model (8 banks, real bank timing: rq/kq sampled one
// edge after the client register, registered read response 6 edges after the sample) through the real static owner
// splits (read: ot_hbm_idx_vm_share2_static, A = the COLL control reader, idle here; write: ot_hnx_coll_kq_share2,
// A = the COLL v6 writer, idle here). One F20 programme per quadrant (targets 0xB0+q), one broadcast launch, 2 periods.
// Rows: plain R2 F72 / plain R1 F19 (no self-land) / QBG R2 expert_intermediate (Bs 18) / QBG R1 o-group (Bs 8) /
// QBG R2 engram rows (Bs 48, 2 exponent words) / plain R2 F1.
// Checks (scenario 0): every VM read and write is at the compiled (bank, edge) of the compiler rule written here
// independently (tools/hgi_sim/collq_gather_1018.py), and no other; final VM images equal the reference gather
// (plain: the source quadrants' words; QBG: hdc_golden_v41.quant_fp8 codes + UE8M0 exponent bytes, files from the
// compiler model); no gq / ring / share fault. ISA pass-through: a fifth master with random ISA ring words must output
// them on the ring-A ports exactly 2 edges later. +fault=N must fault: 1 ISA ring-A inject collides with a gather inject,
// 2 descriptor overlap (fires while busy), 3 COLL writer double-books a landing bank (kq share), 4 a ring-B arrival dropped,
// HNX 5 (with +set=1) a train whose rs_O breaks the bank rule (rs_O != R K mod 8).
// HBM-NEXT-UNITS-COLL 10-19: fork of rtl/hbm_accel/generic/collective/p2p/tb_hgi_coll_gq.sv for the N-row message train
// (ot_hnx_coll_gq). +set=0 = the d4g rows exactly (N = 1); +set=1 = trains N 1..6 incl. a negative source stride; +set=2 =
// the cycles(N) scan (plain R2 F64 and QBG R2 F19 at N = 1, 2, 3, 4, 6). The compiler rule below books every train
// read / write at (bank, edge) from t = rr K + k (double booking = bench error); all bookings must be hit exactly, the
// VM images must equal the N single-row gathers, and COLLQ_TRAIN prints the per-row fire -> last-write span.
module tb_hnx_coll_gq;
    parameter integer MUT = 0, KQMUT = 0;
    parameter integer FFL = 3;        // launch sample -> fire of t_start 0 (HNX-GQ s3 registered descriptor read: 4)
    parameter string VEC = "vec";
    parameter string VECR = "vecr";   // HNX: per-row QBG vectors (tools/hbm_next/hnx_coll_gq_train.py vectors)
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
        wire act, dn, tf, fi, fl; assign f_gq[q] = fi | fl;
        ot_hnx_coll_gq #(.MUT(MUT)) gq(.clk_issue(clk), .clk_land(clk), .rst_n(rst_n), .qid(2'(q)), .tgt(8'hb0 + 8'(q)),
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
        ot_hbm_idx_vm_share2_static rs(.clk_pair({4{clk}}), .rst_n(rst_n), .a_rq(136'd0), .b_rq(g_rq[q]), .vm_rq(v_rq[q]),
            .vm_rr(v_rr[q]), .a_rr(a_rr_unused[q]), .b_rr(g_rr[q]), .fault(f_rs[q]));
        ot_hnx_coll_kq_share2 #(.MUT(KQMUT)) ks(.clk_pair({4{clk}}), .rst_n(rst_n), .a_kq(a_kq[q]), .b_kq(g_kq[q]),
            .vm_kq(v_kq[q]), .fault(f_ks[q]));
    end
    // ---------------------------------------------------------------- VM model (per quadrant, 8 banks)
    reg [255:0] mem [0:3][0:16383];
    reg [255:0] rpipe_d [0:3][0:7][0:5]; reg rpipe_v [0:3][0:7][0:5];
    reg [256:0] rr_reg [0:3][0:7];
    for (genvar q = 0; q < 4; q = q + 1) begin : g_vrr
        for (genvar b = 0; b < 8; b = b + 1) begin : g_b assign v_rr[q][b*257 +: 257] = rr_reg[q][b]; end
    end
    // compiled reservations: rres/wres[q][b] = list of edges (bitmap over cycles)
    localparam integer NC = 4096;
    bit wseen [0:NC-1];       // HNX: a VM bank write sampled at this edge (any quadrant)
    bit rres [0:3][0:7][0:NC-1]; bit wres [0:3][0:7][0:NC-1]; reg [15:0] wsec [0:3][0:7][0:NC-1]; reg [15:0] rsec [0:3][0:7][0:NC-1];
    always @(posedge clk) begin
        for (integer q = 0; q < 4; q = q + 1) for (integer b = 0; b < 8; b = b + 1) begin
            reg [16:0] r; reg [280:0] k; reg [13:0] a;
            r = v_rq[q][b*17 +: 17]; k = v_kq[q][b*281 +: 281];
            rr_reg[q][b] <= {rpipe_v[q][b][5], rpipe_d[q][b][5]};
            for (integer d = 5; d > 0; d = d - 1) begin rpipe_v[q][b][d] <= rpipe_v[q][b][d-1]; rpipe_d[q][b][d] <= rpipe_d[q][b][d-1]; end
            rpipe_v[q][b][0] <= 1'b0;
            if (rst_n && r[16]) begin
                a = {r[15], r[12:0]};
                if (r[2:0] != 3'(b) || (!r[15] && r[14:13] != 2'(q))) begin errors++; $display("COLLQ VM q%0d b%0d bad read sector %h", q, b, r[15:0]); end
                if (!rres[q][b][cyc] || rsec[q][b][cyc] != r[15:0]) begin
                    if (errors < 20) $display("COLLQ VM q%0d b%0d unreserved read cyc%0d sector %h (exp %0d %h)", q, b, cyc, r[15:0], rres[q][b][cyc], rsec[q][b][cyc]);
                    errors++;
                end
                rres[q][b][cyc] = 0; reads++;
                rpipe_v[q][b][0] <= 1'b1; rpipe_d[q][b][0] <= mem[q][a];
            end
            if (rst_n && k[280]) begin
                a = {k[279], k[276:264]};
                if (k[266:264] != 3'(b) || (!k[279] && k[278:277] != 2'(q)) || k[7:0] != 8'hff) begin errors++; $display("COLLQ VM q%0d b%0d bad write %h", q, b, k[279:264]); end
                if (scenario == 0 && (!wres[q][b][cyc] || wsec[q][b][cyc] != k[279:264])) begin
                    if (errors < 20) $display("COLLQ VM q%0d b%0d unreserved write cyc%0d sector %h (exp %0d %h)", q, b, cyc, k[279:264], wres[q][b][cyc], wsec[q][b][cyc]);
                    errors++;
                end
                wres[q][b][cyc] = 0; writes++; wseen[cyc] = 1;
                mem[q][a] <= k[263:8];
            end
        end
    end
    // ---------------------------------------------------------------- descriptors (HNX: +set=S picks the row table)
    //   set 0  the d4g bench rows exactly (N = 1, strides 0, d4g vectors): the fork reproduces ot_hgi_coll_gq
    //   set 1  N-row trains: plain R2 F72 N4 | plain R1 F19 N3 (negative rs_A, no self-land) | QBG R2 F19 N6 |
    //          QBG R1 F9 N2 | QBG R2 F50 N1 | plain R2 F1 N5 -- 2 periods
    //   set 2  cycles(N) scan: plain R2 F64 and QBG R2 F19 (expert_intermediate) at N = 1, 2, 3, 4, 6 -- 1 period
    localparam integer NRM = 16, NROW = 6;
    integer NR = 6, PERIOD = 900, LOOPS = 2, set = 0;
    localparam integer KS = 2;   // HBM-NSFIX/KQS 10-18: registered kq share (pin flops + vm_kq flops): every COLL kq bank sample +2 edges
    integer r_qbg [0:NRM-1], r_r2 [0:NRM-1], r_self [0:NRM-1], r_t [0:NRM-1], r_f [0:NRM-1], r_bs [0:NRM-1];
    integer r_src [0:NRM-1], r_dst [0:NRM-1], r_str [0:NRM-1], r_n [0:NRM-1], r_rsa [0:NRM-1], r_rso [0:NRM-1];
    string r_vec [0:NRM-1];
    reg [255:0] srcw [0:NRM-1][0:NROW-1][0:3][0:191]; reg [255:0] recw [0:NRM-1][0:NROW-1][0:3][0:63];
    reg [255:0] srct [0:191]; reg [255:0] rect [0:63];
    integer span_c [0:NRM-1];   // compiled fire -> last bank-write sample edge, per row (= RTL: every write is checked at its edge)
    integer fire_c [0:NRM-1];   // fire edge of loop 0
    task automatic defrow(input integer d, input integer qbg, r2, self_, t, f, bs, src, dst, str, n, rsa, rso, input string vec);
        r_qbg[d] = qbg; r_r2[d] = r2; r_self[d] = self_; r_t[d] = t; r_f[d] = f; r_bs[d] = bs; r_src[d] = src; r_dst[d] = dst;
        r_str[d] = str; r_n[d] = n; r_rsa[d] = rsa; r_rso[d] = rso; r_vec[d] = vec;
    endtask
    task automatic setup_rows();
        if (set == 0) begin
            NR = 6; PERIOD = 900; LOOPS = 2;
            defrow(0, 0, 1, 1,   0, 72,  0, 'h1000, 'h0000, 72, 1, 0, 0, "");
            defrow(1, 0, 0, 0, 150, 19,  0, 'h1100, 'h0200, 24, 1, 0, 0, "");
            defrow(2, 1, 1, 1, 300, 19, 18, 'h1200, 'h0400, 24, 1, 0, 0, "expert_intermediate");
            defrow(3, 1, 0, 1, 450,  9,  8, 'h1300, 'h0500, 16, 1, 0, 0, "o_group");
            defrow(4, 1, 1, 1, 600, 50, 48, 'h1400, 'h0600, 56, 1, 0, 0, "engram_rows");
            defrow(5, 0, 1, 1, 780,  1,  0, 'h1600, 'h0700,  8, 1, 0, 0, "");
        end else if (set == 1) begin
            NR = 6; PERIOD = 900; LOOPS = 2;
            defrow(0, 0, 1, 1,   0, 72,  0, 'h1000, 'h0000, 72, 4,  80, 288, "");
            defrow(1, 0, 0, 0, 300, 19,  0, 'h1300, 'h0500, 24, 3, -24,  99, "");
            defrow(2, 1, 1, 1, 450, 19, 18, 'h1400, 'h0680, 24, 6,  72, 100, "expert_intermediate");
            defrow(3, 1, 0, 1, 600,  9,  8, 'h1600, 'h0900, 16, 2,  40,  65, "o_group");
            defrow(4, 1, 1, 1, 700, 50, 48, 'h1700, 'h0A00, 56, 1,   0,   0, "engram_rows");
            defrow(5, 0, 1, 1, 800,  1,  0, 'h1800, 'h0B00,  8, 5,   1,  34, "");
        end else begin
            integer ns [0:4] = '{1, 2, 3, 4, 6}; integer pt [0:4] = '{0, 150, 350, 600, 900};
            integer qt [0:4] = '{1250, 1330, 1420, 1530, 1650};
            integer sp, dp, sq, dq;
            NR = 10; PERIOD = 1850; LOOPS = 1; sp = 'h1000; dp = 'h0000; dq = 'h1400; sq = 'h1A40;
            for (integer j = 0; j < 5; j = j + 1) begin
                defrow(j, 0, 1, 1, pt[j], 64, 0, sp, dp, 64, ns[j], 64, 256, ""); sp += 64 * ns[j]; dp += 256 * ns[j];
            end
            for (integer j = 0; j < 5; j = j + 1) begin
                defrow(5 + j, 1, 1, 1, qt[j], 19, 18, sq, dq, 24, ns[j], 72, 100, "expert_intermediate"); sq += 72 * ns[j]; dq += 100 * ns[j];
            end
        end
    endtask
    function automatic integer pbase(input integer row, input integer rr);   // plain payload seed (set 0 = the d4g bench's)
        return (set == 0) ? 100 * row : 4096 * row + 256 * rr;
    endfunction
    function automatic [15:0] sec(input integer q, input integer w); return {1'b0, 2'(q), 13'(w)}; endfunction
    task automatic frame_cfg(input integer q, input integer row, input [223:0] payload);
        @(negedge clk); cfg_v = 1; cfg_target = 8'hb0 + 8'(q); cfg_addr = 12'(row); cfg_data = {16'hc7a1, 4'b0, 12'(row), payload};
        @(negedge clk); cfg_v = 0;
    endtask
    integer L = -1;        // launch sample edge
    task automatic at_edge(input integer t); @(posedge clk iff (cyc == t - 1)); #0.1; endtask
    // the compiler rule, written here independently of the RTL: train index t = rr K + k drives the slot / direction /
    // tag schedule; addresses use the row-local flit i and the row strides. A double booking is a bench error.
    task automatic book(input integer w, input integer q, input integer a, input integer c);
        if (w) begin
            if (wres[q][a%8][c]) begin errors++; $display("COLLQ COMPILE write double-booked q%0d b%0d cyc%0d", q, a % 8, c); end
            wres[q][a%8][c] = 1; wsec[q][a%8][c] = sec(q, a);
        end else begin
            if (rres[q][a%8][c]) begin errors++; $display("COLLQ COMPILE read double-booked q%0d b%0d cyc%0d", q, a % 8, c); end
            rres[q][a%8][c] = 1; rsec[q][a%8][c] = sec(q, a);
        end
    endtask
    task automatic compile(input integer row, input integer loop);
        integer fe, K, R, last;
        R = r_r2[row] ? 2 : 1; K = (r_f[row] + R - 1) / R;
        fe = L + FFL + loop * PERIOD + r_t[row]; last = fe;
        for (integer rr = 0; rr < r_n[row]; rr = rr + 1)
        for (integer q = 0; q < 4; q = q + 1)
            for (integer i = 0; i < r_f[row]; i = i + 1) begin
                integer r, k, t, ie, d, a, so, dw;
                r = i % R; k = i / R; t = rr * K + k; d = t % 2; ie = fe + 1 + 3 * (t / 2) + (t % 2);
                so = r_src[row] + rr * r_rsa[row]; dw = r_dst[row] + rr * r_rso[row];
                if (r_qbg[row] && i < r_bs[row]) for (integer w = 0; w < 4; w = w + 1) book(0, q, so + 4 * i + w, ie + 1);
                if (!r_qbg[row]) book(0, q, so + i, ie + 16);
                for (integer h = 1; h <= 3; h = h + 1) begin
                    integer s; s = srcof(q, d, h); a = dw + s * r_str[row] + i;
                    book(1, q, a, ie + 32 + KS + 2 * h); if (ie + 32 + KS + 2 * h > last) last = ie + 32 + KS + 2 * h;
                end
                if (r_self[row] || r_qbg[row]) begin a = dw + q * r_str[row] + i; book(1, q, a, ie + 27 + KS); end
            end
        if (loop == 0) begin span_c[row] = last - fe; fire_c[row] = fe; end
    endtask
    // ---------------------------------------------------------------- ISA pass-through master (not on a ring)
    reg [57:0] xi; reg [255:0] xd; wire [63:0] xo_ctl; wire [255:0] xo_d;
    reg [57:0] xi_h [0:3]; reg [255:0] xd_h [0:3]; integer xchk = 0;
    wire xa_lp_we, xa_srd_add, xa_srd_tx, xa_srd_rr, xa_srhs, xa_stx_acc, xa_add_v, xa_add_rhs, xa_res, xa_acc, xa_gath, xa_rrl;
    wire [2:0] xa_lp_tag, xa_sat, xa_stt, xa_srt, xa_add_tag, xa_tx_tag, xa_rrl_tag; wire [1:0] xa_sas, xa_add_src, xa_inj, xa_fwd, xa_dst, xa_rx;
    wire [3:0] xa_ttl, xa_kind, xa_src; wire [5:0] xa_rtag; wire xf, xc, xt, xact, xdn;
    ot_hnx_coll_gq_issue gx(.clk(clk), .rst_n(rst_n), .qid(2'd0), .tgt(8'hbf), .cfg_v(1'b0), .cfg_target(8'd0), .cfg_addr(12'd0),
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
    // ---------------------------------------------------------------- run
    integer last_edge = 0;
    initial begin
        if ($value$plusargs("fault=%d", scenario)) begin end
        if ($value$plusargs("set=%d", set)) begin end
        setup_rows();
        for (integer q = 0; q < 4; q = q + 1) begin
            isa[q] = 0; isa_d[q] = 0; a_kq[q] = 0;
            for (integer a = 0; a < 16384; a = a + 1) mem[q][a] = 256'd0;
            for (integer b = 0; b < 8; b = b + 1) begin
                rr_reg[q][b] = 0; for (integer d = 0; d < 6; d = d + 1) rpipe_v[q][b][d] = 0;
                for (integer c = 0; c < NC; c = c + 1) begin rres[q][b][c] = 0; wres[q][b][c] = 0; end
            end
        end
        for (integer c = 0; c < NC; c = c + 1) wseen[c] = 0;
        xi = 0; xd = 0;
        // source data (set 0: the d4g vector files; sets 1/2: one vector file per train row rr, VECR)
        for (integer row = 0; row < NR; row = row + 1) for (integer rr = 0; rr < r_n[row]; rr = rr + 1) for (integer q = 0; q < 4; q = q + 1) begin
            integer so; so = r_src[row] + rr * r_rsa[row];
            if (r_qbg[row]) begin
                // the closure daemon simulator (v5.050) refuses $readmemh into a sub-array: load 1-D temporaries, then copy
                if (set == 0) begin
                    $readmemh({VEC, "/", r_vec[row], "_q", $sformatf("%0d", q), "_src.hex"}, srct, 0, 4 * r_bs[row] - 1);
                    $readmemh({VEC, "/", r_vec[row], "_q", $sformatf("%0d", q), "_rec.hex"}, rect, 0, r_f[row] - 1);
                end else begin
                    $readmemh({VECR, "/", r_vec[row], "_q", $sformatf("%0d_r%0d", q, rr), "_src.hex"}, srct, 0, 4 * r_bs[row] - 1);
                    $readmemh({VECR, "/", r_vec[row], "_q", $sformatf("%0d_r%0d", q, rr), "_rec.hex"}, rect, 0, r_f[row] - 1);
                end
                for (integer w = 0; w < 4 * r_bs[row]; w = w + 1) srcw[row][rr][q][w] = srct[w];
                for (integer w = 0; w < r_f[row]; w = w + 1) recw[row][rr][q][w] = rect[w];
                for (integer w = 0; w < 4 * r_bs[row]; w = w + 1) mem[q][so + w] = srcw[row][rr][q][w];
            end else for (integer w = 0; w < r_f[row]; w = w + 1) mem[q][so + w] = payload(q, pbase(row, rr) + w);
        end
        repeat (5) @(negedge clk); rst_n = 1; repeat (6) @(negedge clk);
        // ISA pass-through: random words, compared 2 edges later (xo is the merge register)
        for (integer t = 0; t < 40; t = t + 1) begin
            @(negedge clk);
            if (t >= 2) begin
                if (xo !== xi_h[(t-2)%4] || xo_d !== (xi_h[(t-2)%4][0] ? xd_h[(t-2)%4] : xd_h[(t-2)%4])) begin
                    if (errors < 20) $display("COLLQ ISA pass-through t%0d got %h exp %h", t, xo, xi_h[(t-2)%4]); errors++;
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
            p[104:101] = 4'(r_n[row] - 1); p[120:105] = 16'(r_rsa[row]); p[136:121] = 16'(r_rso[row]);
            if (scenario == 5 && row == 2) p[136:121] = 16'(r_rso[row] - 4);   // HNX: rs_O != R K (mod 8) -> descriptor fault
            frame_cfg(q, row, p);
        end
        for (integer q = 0; q < 4; q = q + 1) begin
            @(negedge clk); desc_v = 1; cfg_target = 8'hb0 + 8'(q); desc_base = 0; desc_limit = 13'(NR); desc_loops = 16'(LOOPS);
            @(negedge clk); desc_v = 0;
        end
        repeat (30) @(negedge clk);
        if (conf !== 4'hf) begin $display("COLLQ FAIL targets not configured %b", conf); $finish; end
        launch_v = 1; @(posedge clk); L = cyc; @(negedge clk); launch_v = 0;
        for (integer l = 0; l < LOOPS; l = l + 1) for (integer row = 0; row < NR; row = row + 1) compile(row, l);
        last_edge = L + FFL + LOOPS * PERIOD + 100;
        // edges: IE(k=0) = L + FFL + 1; a value set by at_edge(T) is sampled at the posedge where cyc == T
        if (scenario == 1) fork begin at_edge(L + FFL + 1 + 27); isa[2][28:27] = 2'b01; at_edge(L + FFL + 1 + 28); isa[2] = 0; end join_none
        if (scenario == 3) fork begin at_edge(L + FFL + 1 + 34); a_kq[1][((r_dst[0] + prevq(1) * r_str[0]) % 8) * 281 + 280] = 1'b1;
            at_edge(L + FFL + 1 + 35); a_kq[1] = 0; end join_none
        drop_at = L + FFL + 1 + 30;                   // ring-B stop samples the first h=1 transit (k=0) here
        while (cyc < last_edge) @(negedge clk);
        // checks
        if (scenario != 0) begin
            if (|f_gq || |f_ra || |f_rb || |f_ks) $display("COLLQ FAULT PASS scenario=%0d gq%b ra%b rb%b ks%b", scenario, f_gq, f_ra, f_rb, f_ks);
            else $display("COLLQ FAULT ESCAPED scenario=%0d", scenario);
            $finish;
        end
        if (|f_gq || |f_ra || |f_rb || |f_rs || |f_ks) begin $display("COLLQ unexpected fault gq%b ra%b rb%b rs%b ks%b", f_gq, f_ra, f_rb, f_rs, f_ks); errors++; end
        for (integer q = 0; q < 4; q = q + 1) for (integer b = 0; b < 8; b = b + 1) for (integer c = 0; c < NC; c = c + 1) begin
            if (rres[q][b][c]) begin if (errors < 30) $display("COLLQ missing read q%0d b%0d cyc%0d", q, b, c); errors++; end
            if (wres[q][b][c]) begin if (errors < 30) $display("COLLQ missing write q%0d b%0d cyc%0d", q, b, c); errors++; end
        end
        for (integer row = 0; row < NR; row = row + 1) for (integer rr = 0; rr < r_n[row]; rr = rr + 1)
            for (integer q = 0; q < 4; q = q + 1) for (integer s = 0; s < 4; s = s + 1)
            for (integer i = 0; i < r_f[row]; i = i + 1) begin
                reg [255:0] e, g;
                if (s == q && !(r_self[row] || r_qbg[row])) continue;
                e = r_qbg[row] ? recw[row][rr][s][i] : payload(s, pbase(row, rr) + i);
                g = mem[q][r_dst[row] + rr * r_rso[row] + s * r_str[row] + i];
                if (g !== e) begin if (errors < 30) $display("COLLQ DATA row%0d rr%0d q%0d seg%0d word%0d got %h exp %h", row, rr, q, s, i, g, e); errors++; end
                else checked++;
            end
        // cycles(N): compiled span (fire -> last kq bank-sample edge) and the observed last VM write in the row's window
        for (integer row = 0; row < NR; row = row + 1) begin
            integer R, K, ob;
            R = r_r2[row] ? 2 : 1; K = (r_f[row] + R - 1) / R; ob = -1;
            for (integer c = fire_c[row]; c <= fire_c[row] + span_c[row] + 20 && c < NC; c = c + 1) if (wseen[c]) ob = c;
            $display("COLLQ_TRAIN row=%0d qbg=%0d R=%0d F=%0d K=%0d N=%0d rsA=%0d rsO=%0d span_compiled=%0d span_observed=%0d",
                     row, r_qbg[row], R, r_f[row], K, r_n[row], r_rsa[row], r_rso[row], span_c[row], ob - fire_c[row]);
            if (ob - fire_c[row] != span_c[row]) begin errors++; $display("COLLQ SPAN mismatch row%0d", row); end
        end
        if (errors == 0) $display("COLLQ PASS set=%0d rows=%0d loops=%0d vm_words_checked=%0d reads=%0d writes=%0d isa_passthrough=%0d",
            set, NR, LOOPS, checked, reads, writes, xchk);
        else $display("COLLQ FAIL set=%0d errors=%0d", set, errors);
        $finish;
    end
endmodule
`default_nettype wire
