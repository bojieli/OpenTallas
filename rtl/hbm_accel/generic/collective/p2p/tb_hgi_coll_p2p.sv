`timescale 1ns/1ps
// tb_hgi_coll_p2p (HBM peer-to-peer step 1, 2026-10-14): G real dies run the SAME normative COLL record sequence twice,
// on two fabrics simulated side by side:
//   CENTRAL  every die = ot_hfd_coll_r25gq (the central engine of the v13 die, NPT 9 links S0-S4 N0-N3);
//   P2P      every die = four ot_hfd_coll_q quadrant engines (SW NPT 3 = S0-S2, SE S3-S4, NW N0-N1, NE N2-N3) on a
//            2 x 2 registered peer ring (RLY relay registers a hop), records broadcast to the four engines with
//            different relay delays, ret from HOME (SW) only.
// The switch tier (behavioural, the established TU stub method: one labelled latency +LAT cycles flit-to-RX, ingress
// credits back after +CRED, egress paced at 3 flits / 4 cycles a link (the lk_ep line rate) against the receiver's
// 256-flit receive-buffer credits) routes a flit sent on die s link k to die t link k: by die AND rail (quadrant).
// Unicast partials go to their dst die, results / gathers (dst >= F0) are multicast to every other die.
// Each die has a VM image per fabric; the SU inject returns VM[hgi_inj_addr] in the same cycle, the deliveries write
// VM (lanes field > 16: 16 words at O + 16 gi; else `lanes` words at O + w).
// CHECKS (+CASE): every die, every record retires with no fault on both fabrics; the P2P VM image equals the CENTRAL
// image word for word over every address either fabric wrote, with identical write counts (bit-exact, exactly once);
// gathers also against an independent expected image (rank slices / rows).  Reports cycles first issue -> last done on
// both fabrics (die 0 per record and the whole sequence).  +RC=n also runs n RED_CARRY folds per mode on every die's
// ring and checks them against a C (IEEE binary32 RNE) golden of the B2 section 4 order.
// Mutants (defines, the run must print FAIL): MUT_Q (wrong quadrant quarter), MUT_CARRY (dropped carry), MUT_ORDER
// (reordered serial fold).
`ifndef G
`define G 8
`endif
`ifndef INJLAT
`define INJLAT 12
`endif
`ifndef INJSU
`define INJSU `INJLAT
`endif
`ifndef RLY
`define RLY 12
`endif
`define P2P_DUMP(E) $display("DUMP die=%0d q=%0d rq_n=%0d head=%b e_ret=%b ret=%b cr=%0d%0d%0d%0d dn=%0d/%0d/%0d/%0d e_fault=%b st=%0d p_open=%b p_next=%0d p_old=%0d iq=%0d/%0d npop=%0d ndone=%0d", \
    d, q, E.rq_n, E.head_v, E.e_ret, E.hgi_ret, E.cr[0], E.cr[1], E.cr[2], E.cr[3], E.dn[0], E.dn[1], E.dn[2], E.dn[3], E.e_fault, \
    E.u_ep.u_rec.st, E.u_ep.p_open, E.u_ep.p_next, E.u_ep.g_pipe.p_old, E.u_ring.iq_n[0], E.u_ring.iq_n[1], E.u_ring.n_pop, E.u_ring.n_done);
module tb_hgi_coll_p2p;
`ifdef SPMD
    // +define+SPMD: ONE real die (rank RR) of a 96-rank fabric; the 95 peers are replayed SPMD-lockstep by the switch
    // (the tb_hgi_coll_pipe method): when the die sends flit m of a gather on link k, every peer p sends ITS flit m of
    // the same gather on link k (LAT + p mod 5 later), its data read from p's A image through an independent model of
    // the quarter split.  Gathers and ARGMAX only (no partials).
    localparam integer NRK = 96, RR = 37;
`else
    localparam integer NRK = `G, RR = 0;
`endif
    localparam integer G = `G, NL = 9, INJ = 2, DEL = 4, LANES = 16, FW = 32 * LANES, PWT = FW + 33, RW = 280, RLY = `RLY, INJL = `INJLAT, INJS = `INJSU;   // +define+INJSU=<n> != INJLAT: SU latency mutant (must FAIL)
    localparam integer MQ = `ifdef MUT_Q 1 `else 0 `endif;
    localparam integer MC = `ifdef MUT_CARRY 1 `else 0 `endif;
    localparam integer MO = `ifdef MUT_ORDER 1 `else 0 `endif;
    localparam integer TKQ = `ifdef TKMQ3 1 `else 0 `endif;   // +define+TKMQ3: the SW master with its die TOPK sink (KMAX 2,048)
    import "DPI-C" function int unsigned f32add(input int unsigned a, input int unsigned b);
    reg clk = 0, rst_n = 0;
    always #0.4166665 clk = ~clk;
    integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
    integer lat, cred, seed, rcn;
    string  tcase;
    // ---------------------------------------------------------------------------------------------------------------
    // record list
    localparam integer MAXR = 32;
    integer nrec = 0;
    integer r_op [0:MAXR-1], r_n [0:MAXR-1], r_afmt [0:MAXR-1], r_ofmt [0:MAXR-1], r_sub [0:MAXR-1];
    longint r_a [0:MAXR-1], r_o [0:MAXR-1];
    function automatic [255:0] md(input [2:0] fmt, input [39:0] base_, input [19:0] n);
        begin md = 256'd0; md[1:0] = 2'd1; md[4:2] = fmt; md[47:8] = base_; md[67:48] = n; md[87:68] = 20'd1; end
    endfunction
    function automatic [967:0] mkrec(input integer k, input integer die);
        reg [127:0] h; integer no;
        begin
            h = 0; h[127:124] = 4'd6; h[123:118] = 6'(r_op[k]); h[99:93] = 7'b0010001; h[71:64] = 8'(r_sub[k]);
            no = (r_op[k] == 3) ? 1 : r_n[k];
            mkrec = {8'(die), 21'd0, 21'(no), 21'(r_n[k]), 256'd0, md(3'(r_ofmt[k]), 40'(r_o[k]), 20'(no)),
                     md(3'(r_afmt[k]), 40'(r_a[k]), 20'(r_n[k])), h, 1'b1};
        end
    endfunction
    task automatic addrec(input integer op, input integer n, input integer af, input integer of_, input integer sub);
        begin
            r_op[nrec] = op; r_n[nrec] = n; r_afmt[nrec] = af; r_ofmt[nrec] = of_; r_sub[nrec] = sub;
            r_a[nrec] = 40'h10_0000 + nrec * 40'h1_0000; r_o[nrec] = 40'h80_0000 + nrec * 40'h2_0000;
            nrec = nrec + 1;
        end
    endtask
    // ---------------------------------------------------------------------------------------------------------------
    // VM images (key = die << 40 | word address) and expected gather image
    bit [31:0] vmc [longint]; bit [31:0] vmp [longint]; int wcc [longint]; int wcp [longint];
    function automatic longint ky(input integer d, input longint a); ky = (longint'(d) << 40) | a; endfunction
    function automatic integer did(input integer d); did = RR + d; endfunction
    function automatic [31:0] special(input integer r);
        case (r % 9)
            0: special = 32'h80000000; 1: special = 32'h7FC12345; 2: special = 32'hFF812345; 3: special = 32'h00000001;
            4: special = 32'h807FFFFF; 5: special = 32'h7F800000; 6: special = 32'hFF800000; 7: special = 32'h00000000;
            default: special = 32'h3F800000;
        endcase
    endfunction
    function automatic [31:0] aval(input integer k, input integer d, input integer w);
        integer h; reg [31:0] x;
        begin
            h = k * 1000003 + d * 7919 + w * 104729 + seed;
            if (r_op[k] == 3) aval = (w == 0) ? ((d % 5 == 2) ? 32'h40A00000 : 32'(32'h3F000000 + (d * 37 % 11) * 32'h100000))
                                              : 32'((NRK - d) * 1000 + 7);
            else if ((r_op[k] == 0 || r_op[k] == 4) && (h % 23 != 0)) begin      // reductions: finite normals mostly
                x = 32'(h * 2654435761); x[30:23] = 8'(100 + (h % 50)); aval = x;
            end else aval = ((h % 3) == 0) ? special(h) : 32'(h * 2246822519);
        end
    endfunction
    // ---------------------------------------------------------------------------------------------------------------
    // DUTs
    reg  [39:0] cfgb = 0;
    // CENTRAL
    reg  [967:0]     c_rec  [0:G-1];
    wire [2:0]       c_ret  [0:G-1];
    wire [INJ*16-1:0] c_ii  [0:G-1]; wire [INJ-1:0] c_ir [0:G-1]; reg [4*INJ*FW-1:0] c_iq [0:G-1];
    wire [DEL-1:0]   c_dv   [0:G-1]; wire [DEL*PWT-1:0] c_df [0:G-1]; wire [DEL*40-1:0] c_dob [0:G-1];
    wire             c_flt  [0:G-1];
    wire [NL-1:0]    c_txv  [0:G-1]; wire [NL*PWT-1:0] c_txf [0:G-1]; wire [NL-1:0] c_rxc [0:G-1];
    reg  [NL-1:0]    c_rxv  [0:G-1]; reg [NL*PWT-1:0] c_rxf [0:G-1]; reg [NL-1:0] c_crr [0:G-1];
    wire [79:0]      c_vma  [0:G-1];
    // P2P
    reg  [967:0]     p_rec  [0:G-1][0:3];
    wire [2:0]       p_ret  [0:G-1][0:3];
    wire [INJ*16-1:0] p_ii  [0:G-1][0:3]; wire [INJ-1:0] p_ir [0:G-1][0:3]; reg [INJ*FW-1:0] p_iq [0:G-1][0:3];
    wire [INJ*80-1:0] p_ia  [0:G-1][0:3];
    wire [DEL-1:0]   p_dv   [0:G-1][0:3]; wire [DEL*PWT-1:0] p_df [0:G-1][0:3]; wire [DEL*40-1:0] p_dob [0:G-1][0:3];
    wire             p_flt  [0:G-1][0:3];
    wire [NL-1:0]    p_txv  [0:G-1]; wire [NL*PWT-1:0] p_txf [0:G-1]; wire [NL-1:0] p_rxc [0:G-1];
    reg  [NL-1:0]    p_rxv  [0:G-1]; reg [NL*PWT-1:0] p_rxf [0:G-1]; reg [NL-1:0] p_crr [0:G-1];
    wire [RW-1:0]    p_cwo  [0:G-1][0:3]; wire [RW-1:0] p_ccwo [0:G-1][0:3];
    wire [RW-1:0]    p_cwi  [0:G-1][0:3]; wire [RW-1:0] p_ccwi [0:G-1][0:3];
    reg              rc_v   [0:G-1][0:3]; reg [2:0] rc_tag [0:G-1][0:3]; reg rc_mode [0:G-1][0:3]; reg [255:0] rc_d [0:G-1][0:3];
    wire             rc_rdy [0:G-1][0:3]; wire rr_v [0:G-1][0:3]; wire [2:0] rr_tag [0:G-1][0:3]; wire [255:0] rr_d [0:G-1][0:3];
    // link k of the die -> (quadrant, port): SW 0-2, SE 3-4, NW 5-6, NE 7-8
    function automatic integer lq(input integer k); lq = (k < 3) ? 0 : (k < 5) ? 1 : (k < 7) ? 2 : 3; endfunction
    function automatic integer lb(input integer q); lb = (q == 0) ? 0 : (q == 1) ? 3 : (q == 2) ? 5 : 7; endfunction
    // ring: CW successor in SW -> SE -> NE -> NW -> SW
    function automatic integer cwn(input integer q); cwn = (q == 0) ? 1 : (q == 1) ? 3 : (q == 3) ? 2 : 0; endfunction
    function automatic integer cwp(input integer q); cwp = (q == 0) ? 2 : (q == 1) ? 0 : (q == 3) ? 1 : 3; endfunction
    for (genvar d = 0; d < G; d = d + 1) begin : g_die
        ot_hfd_coll_r25gq u_c (.clk(clk), .rst_n(rst_n), .rank(8'd0), .pf(16'd0), .go(1'b0),
            .inj_idx(c_ii[d]), .inj_rd(c_ir[d]), .inj_q(c_iq[d]), .del_valid(c_dv[d]), .del_flit(c_df[d]), .fault(c_flt[d]),
            .stat_credit_stall(), .hgi_rec(c_rec[d]), .hgi_ret(c_ret[d]), .hgi_cfg(cfgb), .hgi_rowfmt_o(), .hgi_rowfmt_i(3'b000),
            .hgi_vmaddr(c_vma[d]), .hgi_del_obase(c_dob[d]),
            .lk_tx_v(c_txv[d]), .lk_tx_flit(c_txf[d]), .lk_rx_credit(c_rxc[d]), .lk_rx_v(c_rxv[d]), .lk_rx_flit(c_rxf[d]),
            .lk_sw_cr(c_crr[d]), .lk_session(), .lk_fault({NL{1'b0}}), .lk_locked({NL{1'b1}}), .lk_status(),
            .rgx_xq(), .rgx_xr(514'd0), .rgx_vmq(), .rgx_vmr(274'd0), .rgx_c_req(), .rgx_c_gnt(1'b0), .rgx_c_q(), .rgx_c_cr(32'd0),
            .rgx_c_rsp(32'd0), .rgx_xw(), .rgx_xwa(2'd0));
        for (genvar q = 0; q < 4; q = q + 1) begin : g_q
            localparam integer NP = (q == 0) ? 3 : 2, B = (q == 0) ? 0 : (q == 1) ? 3 : (q == 2) ? 5 : 7;
            // the die masters: SW = ot_hfd_coll_q3 (HOME, QSOLO), SE / NW / NE = ot_hfd_coll_q2 (strap qid)
            if (q == 0) begin : g_m3
                ot_hfd_coll_q3 #(.INJLAT(INJL), .TKM(TKQ), .MUT_Q(MQ), .MUT_CARRY(MC), .MUT_ORDER(MO)) u_q (.clk(clk), .rst_n(rst_n),
                    .tkm_clk_core(clk), .tkm_clk_buffer(clk), .tkm_clk_packer(clk), .tkm_clk_lane({4{clk}}), .tkm_clk_tile({32{clk}}),
                    .hgi_rec(p_rec[d][q]), .hgi_recx(554'd0), .hgi_ret(p_ret[d][q]), .hgi_cfg(cfgb), .hgi_vmaddr(), .hgi_inj_addr(p_ia[d][q]),
                    .inj_idx(p_ii[d][q]), .inj_rd(p_ir[d][q]), .inj_d(p_iq[d][q]), .del_valid(p_dv[d][q]), .del_flit(p_df[d][q]),
                    .hgi_del_obase(p_dob[d][q]), .fault(p_flt[d][q]), .stat_credit_stall(),
                    .lk_tx_v(p_txv[d][B +: NP]), .lk_tx_flit(p_txf[d][B*PWT +: NP*PWT]), .lk_rx_credit(p_rxc[d][B +: NP]),
                    .lk_rx_v(p_rxv[d][B +: NP]), .lk_rx_flit(p_rxf[d][B*PWT +: NP*PWT]), .lk_sw_cr(p_crr[d][B +: NP]),
                    .lk_session(), .lk_fault({NP{1'b0}}), .lk_locked({NP{1'b1}}), .lk_status(),
                    .pr_cw_i(p_cwi[d][q]), .pr_cw_o(p_cwo[d][q]), .pr_ccw_i(p_ccwi[d][q]), .pr_ccw_o(p_ccwo[d][q]),
                    .rc_v(rc_v[d][q]), .rc_rdy(rc_rdy[d][q]), .rc_tag(rc_tag[d][q]), .rc_mode(rc_mode[d][q]), .rc_d(rc_d[d][q]),
                    .rr_v(rr_v[d][q]), .rr_tag(rr_tag[d][q]), .rr_d(rr_d[d][q]),
                    .tkw_t_v(), .tkw_t_d(), .tkw_f_cr(1'b0),   // TOPK_MERGE (op 2) is not in these cases
                    .rgx_xq(), .rgx_xr(514'd0), .rgx_vmq(), .rgx_vmr(274'd0), .rgx_t_v(), .rgx_t_addr(), .rgx_t_data(), .rgx_t_vm(),
                    .rgx_f_cr(4'd0), .rgx_f_fault(1'b0));   // ROW_GATHER (op 5) is not in these cases: tb_hgi_coll_rgx_wtx
                if (d < 4) begin : g_dump
                    always @(posedge clk) if (dump_req) `P2P_DUMP(u_q.u_q)
                end
            end else begin : g_m2
                ot_hfd_coll_q2 #(.INJLAT(INJL), .MUT_Q(MQ), .MUT_CARRY(MC), .MUT_ORDER(MO)) u_q (.clk(clk), .rst_n(rst_n), .qid(2'(q)),
                    .hgi_rec(p_rec[d][q]), .hgi_cfg(cfgb), .hgi_vmaddr(), .hgi_inj_addr(p_ia[d][q]),
                    .inj_idx(p_ii[d][q]), .inj_rd(p_ir[d][q]), .inj_d(p_iq[d][q]), .del_valid(p_dv[d][q]), .del_flit(p_df[d][q]),
                    .hgi_del_obase(p_dob[d][q]), .fault(p_flt[d][q]), .stat_credit_stall(),
                    .lk_tx_v(p_txv[d][B +: NP]), .lk_tx_flit(p_txf[d][B*PWT +: NP*PWT]), .lk_rx_credit(p_rxc[d][B +: NP]),
                    .lk_rx_v(p_rxv[d][B +: NP]), .lk_rx_flit(p_rxf[d][B*PWT +: NP*PWT]), .lk_sw_cr(p_crr[d][B +: NP]),
                    .lk_session(), .lk_fault({NP{1'b0}}), .lk_locked({NP{1'b1}}), .lk_status(),
                    .pr_cw_i(p_cwi[d][q]), .pr_cw_o(p_cwo[d][q]), .pr_ccw_i(p_ccwi[d][q]), .pr_ccw_o(p_ccwo[d][q]),
                    .rc_v(rc_v[d][q]), .rc_rdy(rc_rdy[d][q]), .rc_tag(rc_tag[d][q]), .rc_mode(rc_mode[d][q]), .rc_d(rc_d[d][q]),
                    .rr_v(rr_v[d][q]), .rr_tag(rr_tag[d][q]), .rr_d(rr_d[d][q]));
                assign p_ret[d][q] = 3'b000;
                if (d < 4) begin : g_dump
                    always @(posedge clk) if (dump_req) `P2P_DUMP(u_q.u_q)
                end
            end
            // ring hops q -> CW successor, q -> CW predecessor (CCW): RLY relay registers each
            reg [RW-1:0] dcw [0:RLY-1]; reg [RW-1:0] dccw [0:RLY-1];
            always @(posedge clk) begin
                dcw[0] <= p_cwo[d][q]; dccw[0] <= p_ccwo[d][q];
                for (integer i = 1; i < RLY; i = i + 1) begin dcw[i] <= dcw[i-1]; dccw[i] <= dccw[i-1]; end
            end
            assign p_cwi[d][cwn(q)] = dcw[RLY-1];
            assign p_ccwi[d][cwp(q)] = dccw[RLY-1];
        end
    end
    // ---------------------------------------------------------------------------------------------------------------
    // SU inject (same cycle, from the VM image)
    always @* for (integer d = 0; d < G; d = d + 1) begin
        c_iq[d] = '0;
        for (integer i = 0; i < INJ; i = i + 1) if (c_ir[d][i]) begin : ci
            longint a; a = (PIPE_A(c_vma[d], c_ii[d], i));
            for (integer j = 0; j < 16; j = j + 1) c_iq[d][i*FW + 32*j +: 32] = vmc.exists(ky(d, a + j)) ? vmc[ky(d, a + j)] : 32'd0;
        end
        for (integer q = 0; q < 4; q = q + 1) begin
            p_iqn[d][q] = '0;
            for (integer i = 0; i < INJ; i = i + 1) if (p_ir[d][q][i]) begin : pi
                longint a; a = longint'(p_ia[d][q][80*i +: 40]);
                for (integer j = 0; j < 16; j = j + 1) p_iqn[d][q][i*FW + 32*j +: 32] = vmp.exists(ky(d, a + j)) ? vmp[ky(d, a + j)] : 32'd0;
            end
        end
    end
    // P2P SU model: reads VM at the request it sees at the engine's (registered) pins and answers INJLAT - 1 edges later
    // (fixed latency: die relays + the SU's fixed VM read), the contract of ot_hbm_accel_tu_endpoint_qpsg
    reg [INJ*FW-1:0] p_iqn [0:G-1][0:3];
    reg [INJ*FW-1:0] p_iqd [0:G-1][0:3][0:31];
    always @(posedge clk) for (integer d = 0; d < G; d = d + 1) for (integer q = 0; q < 4; q = q + 1) begin
        p_iqd[d][q][0] <= p_iqn[d][q];
        for (integer j = 1; j < 32; j = j + 1) p_iqd[d][q][j] <= p_iqd[d][q][j-1];
    end
    always @* for (integer d = 0; d < G; d = d + 1) for (integer q = 0; q < 4; q = q + 1)
        p_iq[d][q] = (INJS <= 1) ? p_iqn[d][q] : p_iqd[d][q][INJS - 2];
    // the central r25gq wrapper does not export hgi_inj_addr: A base (PIPE: latched a_run, the vmaddr low half) + 16 f
    function automatic longint PIPE_A(input [79:0] vma, input [INJ*16-1:0] ii, input integer i);
        PIPE_A = longint'(vma[39:0]) + longint'(ii[16*i +: 16]) * 16;
    endfunction
    // ---------------------------------------------------------------------------------------------------------------
    // deliveries -> VM
    task automatic deliver(input integer fab, input integer d, input [PWT-1:0] x, input [39:0] ob);
        integer ln; longint a;
        begin
            ln = integer'(x[FW+24 +: 8]);
            if (ln > 16) begin a = longint'(ob) + longint'(x[FW +: 16]) * 16; ln = 16; end
            else a = longint'(ob) + longint'(x[FW +: 16]);
            for (integer j = 0; j < ln; j = j + 1)
                if (fab == 0) begin vmc[ky(d, a + j)] = x[32*j +: 32]; wcc[ky(d, a + j)] = (wcc.exists(ky(d, a + j)) ? wcc[ky(d, a + j)] : 0) + 1; end
                else begin vmp[ky(d, a + j)] = x[32*j +: 32]; wcp[ky(d, a + j)] = (wcp.exists(ky(d, a + j)) ? wcp[ky(d, a + j)] : 0) + 1; end
        end
    endtask
    always @(posedge clk) if (rst_n) for (integer d = 0; d < G; d = d + 1) begin
        for (integer l = 0; l < DEL; l = l + 1) if (c_dv[d][l]) deliver(0, d, c_df[d][l*PWT +: PWT], c_dob[d][l*40 +: 40]);
        for (integer q = 0; q < 4; q = q + 1)
            for (integer l = 0; l < DEL; l = l + 1) if (p_dv[d][q][l]) deliver(1, d, p_df[d][q][l*PWT +: PWT], p_dob[d][q][l*40 +: 40]);
    end
    // ---------------------------------------------------------------------------------------------------------------
    // switch tier: per fabric, per destination (die, link) an egress queue {ready cycle, flit}; ingress credits back
    typedef struct packed { int t; logic [PWT-1:0] f; } ent_t;
    ent_t eq [0:1][0:G-1][0:NL-1][$];
    integer egc [0:1][0:G-1][0:NL-1]; integer pace [0:1][0:G-1][0:NL-1];
    int cin [0:1][0:G-1][0:NL-1][$]; int ceg [0:1][0:G-1][0:NL-1][$];
    integer nflit [0:1];
    initial for (integer f = 0; f < 2; f = f + 1) begin nflit[f] = 0;
        for (integer d = 0; d < G; d = d + 1) for (integer k = 0; k < NL; k = k + 1) begin egc[f][d][k] = 256; pace[f][d][k] = 0; end end
    always @(posedge clk) if (rst_n) for (integer f = 0; f < 2; f = f + 1) for (integer d = 0; d < G; d = d + 1) begin : sw
        reg [NL-1:0] txv, rxc, rxv, crr; reg [NL*PWT-1:0] txf, rxf;
        txv = f ? p_txv[d] : c_txv[d]; txf = f ? p_txf[d] : c_txf[d]; rxc = f ? p_rxc[d] : c_rxc[d];
        rxv = '0; rxf = f ? p_rxf[d] : c_rxf[d]; crr = '0;
        for (integer k = 0; k < NL; k = k + 1) begin
            if (txv[k]) begin : dep
                reg [PWT-1:0] x; integer dst; ent_t e;
                x = txf[k*PWT +: PWT]; dst = integer'(x[FW+24 +: 8]); nflit[f] = nflit[f] + 1;
                e.t = cyc + lat; e.f = x;
                if (x[PWT-1] == 1'b0) begin                               // partial: unicast to its owner die
                    if (dst - RR >= G || dst < RR) $fatal(1, "SW_BAD_DST fab=%0d die=%0d dst=%0d", f, d, dst);
                    eq[f][dst - RR][k].push_back(e);
                end else begin
                    for (integer t = 0; t < G; t = t + 1) if (t != d) eq[f][t][k].push_back(e);   // multicast
`ifdef SPMD
                    mirror(f, k, x);
`endif
                end
                cin[f][d][k].push_back(cyc + cred);
            end
            if (cin[f][d][k].size() != 0 && cin[f][d][k][0] <= cyc) begin void'(cin[f][d][k].pop_front()); crr[k] = 1'b1; end
            if (rxc[k]) ceg[f][d][k].push_back(cyc + 5);
            if (ceg[f][d][k].size() != 0 && ceg[f][d][k][0] <= cyc) begin void'(ceg[f][d][k].pop_front()); egc[f][d][k] = egc[f][d][k] + 1; end
            pace[f][d][k] = (pace[f][d][k] >= 4) ? 4 : pace[f][d][k] + 3;
            if (eq[f][d][k].size() != 0 && eq[f][d][k][0].t <= cyc && egc[f][d][k] > 0 && pace[f][d][k] >= 4) begin : arr
                ent_t e; e = eq[f][d][k].pop_front();
                rxv[k] = 1'b1; rxf[k*PWT +: PWT] = e.f; egc[f][d][k] = egc[f][d][k] - 1; pace[f][d][k] = pace[f][d][k] - 4;
            end
        end
        if (f) begin p_rxv[d] <= rxv; p_rxf[d] <= rxf; p_crr[d] <= crr; end
        else begin c_rxv[d] <= rxv; c_rxf[d] <= rxf; c_crr[d] <= crr; end
    end
`ifdef SPMD
    // ---- independent model of the quarter split (the stub's own arithmetic, not the RTL's) ----------------------
    function automatic integer flo(input integer a, input integer b); flo = a / b; endfunction
    function automatic integer sl_s(input integer n, input integer p); sl_s = flo(p * n, NRK); endfunction
    // engine e: 0 central, 1..4 quadrant e-1.  Words / flits of rank p's contribution to gather k.
    function automatic integer e_start(input integer k, input integer e, input integer p);   // first word sent (sliced)
        integer s0, ln; s0 = sl_s(r_n[k], p); ln = sl_s(r_n[k], p + 1) - s0;
        e_start = (e == 0) ? s0 : s0 + flo((e - 1) * ln, 4);
    endfunction
    function automatic integer e_pf(input integer k, input integer e);
        integer mx, rw;
        if (r_op[k] == 3) e_pf = 1;
        else if (r_afmt[k] == 0) begin
            mx = 0;
            for (integer p = 0; p < NRK; p = p + 1) begin : m_
                integer s0, ln, a, b; s0 = sl_s(r_n[k], p); ln = sl_s(r_n[k], p + 1) - s0;
                a = (e == 0) ? 0 : flo((e - 1) * ln, 4); b = (e == 0) ? ln : flo(e * ln, 4);
                if (b - a > mx) mx = b - a;
            end
            e_pf = (mx + 15) / 16;
        end else begin
            rw = r_n[k] / 32;
            e_pf = (e == 0) ? rw : flo(e * rw, 4) - flo((e - 1) * rw, 4);
        end
    endfunction
    function automatic bit e_runs(input integer k, input integer e);
        e_runs = (e == 0) || (r_op[k] == 3 ? e == 1 : e_pf(k, e) != 0);
    endfunction
    // per engine: the records it runs, flits sent of each (resolves a departure's gather by its epoch tag)
    integer sent [0:4][0:MAXR-1];
    initial for (integer e = 0; e < 5; e = e + 1) for (integer k = 0; k < MAXR; k = k + 1) sent[e][k] = 0;
    task automatic mirror(input integer f, input integer lk, input [PWT-1:0] x);
        integer e, k, gord, pf_, m, gi; bit pipe_; reg [PWT-1:0] y; ent_t en;
        begin
            e = f ? lq(lk) + 1 : 0; pipe_ = (x[FW+27 +: 5] == 5'b11110); k = -1; gord = 0;
            for (integer i = 0; i < nrec && k < 0; i = i + 1) if (e_runs(i, e)) begin
                if (r_op[i] == 1) begin
                    if (pipe_ && (gord % 8) == integer'(x[FW+24 +: 3]) && sent[e][i] < e_pf(i, e)) k = i;
                    gord = gord + 1;
                end else if (!pipe_ && sent[e][i] < 1) k = i;
            end
            if (k < 0) $fatal(1, "MIRROR_NO_RECORD e=%0d dst=%h", e, x[FW+24 +: 8]);
            pf_ = e_pf(k, e); gi = integer'(x[FW +: 16]); m = gi - RR * pf_; sent[e][k] = sent[e][k] + 1;
            if (m < 0 || m >= pf_ || integer'(x[FW+16 +: 8]) != RR) $fatal(1, "MIRROR_BAD_DEPARTURE e=%0d rec=%0d gi=%0d pf=%0d", e, k, gi, pf_);
            for (integer p = 0; p < NRK; p = p + 1) if (p != RR) begin
                y = x; y[FW+16 +: 8] = 8'(p); y[FW +: 16] = 16'(p * pf_ + m);
                for (integer j = 0; j < 16; j = j + 1) begin : wd
                    integer w;
                    if (r_op[k] == 3) w = j;
                    else if (r_afmt[k] == 0) w = e_start(k, e, p) + 16 * m + j;
                    else w = 16 * (((e == 0) ? 0 : flo((e - 1) * (r_n[k] / 32), 4)) + m) + j;
                    y[32*j +: 32] = (w < ((r_afmt[k] == 1) ? r_n[k] / 2 : r_n[k])) ? aval(k, p, w) : 32'd0;
                end
                en.t = cyc + lat + (p % 5); en.f = y; eq[f][0][lk].push_back(en);
            end
        end
    endtask
`endif
    // ---------------------------------------------------------------------------------------------------------------
    // record issue (pulse when ready) and completion
    localparam integer RDL0 = 3, RDL1 = 9, RDL2 = 6, RDL3 = 14;     // P2P record relay delay per quadrant
    integer ci [0:G-1], pi_ [0:G-1], cd [0:G-1], pd [0:G-1];
    integer c_t0 [0:MAXR-1], c_t1 [0:MAXR-1], p_t0 [0:MAXR-1], p_t1 [0:MAXR-1];
    integer c_first, c_last, p_first, p_last;
    reg go_rec = 0;
    reg [967:0] pdl [0:G-1][0:15];
    always @(posedge clk) if (rst_n) for (integer d = 0; d < G; d = d + 1) begin
        c_rec[d] <= '0;
        if (go_rec && ci[d] < nrec && c_ret[d][0] && c_rec[d][0] == 1'b0) begin
            c_rec[d] <= mkrec(ci[d], did(d)); if (d == 0) c_t0[ci[d]] = cyc; if (ci[d] == 0 && d == 0) c_first = cyc; ci[d] = ci[d] + 1;
        end
        if (c_ret[d][1]) begin if (d == 0) c_t1[cd[d]] = cyc; cd[d] = cd[d] + 1; c_last = cyc; end
        // P2P: the HOME engine's ret; the record reaches each quadrant RDLq edges later
        pdl[d][0] = '0;
        if (go_rec && pi_[d] < nrec && p_ret[d][0][0] && !rec_inflight(d)) begin
            pdl[d][0] = mkrec(pi_[d], did(d)); if (d == 0) p_t0[pi_[d]] = cyc; if (pi_[d] == 0 && d == 0) p_first = cyc; pi_[d] = pi_[d] + 1;
        end
        for (integer i = 15; i > 0; i = i - 1) pdl[d][i] = pdl[d][i-1];
        p_rec[d][0] <= pdl[d][RDL0]; p_rec[d][1] <= pdl[d][RDL1]; p_rec[d][2] <= pdl[d][RDL2]; p_rec[d][3] <= pdl[d][RDL3];
        if (p_ret[d][0][1]) begin if (d == 0) p_t1[pd[d]] = cyc; pd[d] = pd[d] + 1; p_last = cyc; end
    end
    // the HOME ready is registered and already accounts for a record in its own relay window only from the edge it
    // lands: hold the next record until the previous one reached HOME (the command processor sees ready at HOME's pins)
    function automatic bit rec_inflight(input integer d);
        rec_inflight = 0; for (integer i = 0; i <= RDL0; i = i + 1) if (pdl[d][i][0]) rec_inflight = 1;
    endfunction
    // ---------------------------------------------------------------------------------------------------------------
    // RED_CARRY folds
    integer rc_err = 0, rc_got = 0;
    reg [255:0] rc_p [0:G-1][0:3][0:7];
    reg         rc_mo [0:7];
    function automatic [255:0] rc_gold(input integer d, input integer t, input bit tree);
        reg [255:0] y;
        for (integer l = 0; l < 8; l = l + 1) begin : ln
            int unsigned p0, p1, p2, p3;
            p0 = rc_p[d][0][t][32*l +: 32]; p1 = rc_p[d][1][t][32*l +: 32]; p2 = rc_p[d][2][t][32*l +: 32]; p3 = rc_p[d][3][t][32*l +: 32];
            y[32*l +: 32] = tree ? f32add(f32add(p0, p1), f32add(p2, p3)) : f32add(f32add(f32add(p0, p1), p2), p3);
        end
        rc_gold = y;
    endfunction
    always @(posedge clk) if (rst_n) for (integer d = 0; d < G; d = d + 1) for (integer q = 0; q < 4; q = q + 1)
        if (rr_v[d][q]) begin
            rc_got = rc_got + 1;
            if (rr_d[d][q] !== rc_gold(d, rr_tag[d][q], rc_mo[rr_tag[d][q]])) begin
                rc_err = rc_err + 1;
                if (rc_err < 6) $display("RC_MISMATCH die=%0d q=%0d tag=%0d mode=%0d got=%h want=%h", d, q, rr_tag[d][q],
                    rc_mo[rr_tag[d][q]], rr_d[d][q][31:0], rc_gold(d, rr_tag[d][q], rc_mo[rr_tag[d][q]]) & 32'hFFFFFFFF);
            end
        end
    task automatic run_rc(input integer rounds);
        begin
            for (integer r = 0; r < rounds; r = r + 1) begin
                rc_got = 0;
                for (integer t = 0; t < 8; t = t + 1) rc_mo[t] = t[0];
                for (integer d = 0; d < G; d = d + 1) for (integer q = 0; q < 4; q = q + 1) for (integer t = 0; t < 8; t = t + 1)
                    for (integer l = 0; l < 8; l = l + 1) begin : gv
                        reg [31:0] x; x = $random(seed); x[30:23] = 8'(110 + ($unsigned($random(seed)) % 30)); rc_p[d][q][t][32*l +: 32] = x;
                    end
                // the four quadrants submit in a scrambled order and at different times (no barrier)
                for (integer t = 0; t < 8; t = t + 1) for (integer qq = 3; qq >= 0; qq = qq - 1) begin
                    @(negedge clk);
                    for (integer d = 0; d < G; d = d + 1) for (integer q = 0; q < 4; q = q + 1) rc_v[d][q] = 0;
                    // rc_rdy is per tag: present the tag first, let it settle, then check and submit
                    for (integer d = 0; d < G; d = d + 1) rc_tag[d][(qq + d + t) % 4] = 3'(t);
                    #0.05;
                    for (integer d = 0; d < G; d = d + 1) begin
                        integer q; q = (qq + d + t) % 4;
                        if (!rc_rdy[d][q]) $fatal(1, "RC_NOT_READY die=%0d q=%0d tag=%0d", d, q, t);
                        rc_v[d][q] = 1; rc_mode[d][q] = rc_mo[t]; rc_d[d][q] = rc_p[d][q][t];
                    end
                end
                @(negedge clk); for (integer d = 0; d < G; d = d + 1) for (integer q = 0; q < 4; q = q + 1) rc_v[d][q] = 0;
                begin : wt integer w; w = 0; while (rc_got < G * 4 * 8 && w < 2000) begin @(negedge clk); w = w + 1; end end
                if (rc_got != G * 4 * 8) begin rc_err = rc_err + 1; $display("RC_COUNT got=%0d want=%0d", rc_got, G * 32); end
            end
        end
    endtask
    // ---------------------------------------------------------------------------------------------------------------
    // ---- progress / stall detector: no delivery, no link departure and no completion on a fabric for STALL cycles
    // while it still has records outstanding -> dump every engine's state (dies 0-3) and fail
    integer stall_lim; integer c_prog = 0, p_prog = 0; reg dump_req = 0; bit stalled = 0;
    always @(posedge clk) if (rst_n && go_rec) begin
        for (integer d = 0; d < G; d = d + 1) begin
            if (c_dv[d] != 0 || c_txv[d] != 0 || c_ret[d][1] || c_rxv[d] != 0) c_prog = cyc;
            if (p_txv[d] != 0 || p_rxv[d] != 0 || p_ret[d][0][1]) p_prog = cyc;
            for (integer q = 0; q < 4; q = q + 1) if (p_dv[d][q] != 0) p_prog = cyc;
        end
        dump_req <= 1'b0;
        if (!stalled && ((cyc - p_prog > stall_lim && pd[0] < nrec) || (cyc - c_prog > stall_lim && cd[0] < nrec))) begin
            stalled = 1; dump_req <= 1'b1;
            $display("STALL cyc=%0d central done=%0d (last progress %0d) p2p done=%0d (last progress %0d)", cyc, cd[0], c_prog, pd[0], p_prog);
        end
        if (cyc % 200000 == 0) begin $display("PROG cyc=%0d central done=%0d p2p done=%0d", cyc, cd[0], pd[0]); $fflush; end
    end
    always @(posedge clk) if (dump_req) for (integer d = 0; d < G && d < 4; d = d + 1)
        $display("DUMP die=%0d central st=%0d ret=%b", d, (d == 0) ? g_die[0].u_c.u_ep.u_rec.st : 0, c_ret[d]);
    integer fails = 0;
    task automatic check_images;
        integer nw, ndiff, ncnt, nexp; longint k;
        begin
            nw = 0; ndiff = 0; ncnt = 0; nexp = 0;
            foreach (wcc[k_]) begin
                k = k_; nw = nw + 1;
                if (!wcp.exists(k) || wcp[k] != wcc[k]) begin ncnt = ncnt + 1; if (ncnt < 6) $display("WCOUNT die=%0d addr=%h central=%0d p2p=%0d", k >> 40, k & 40'hFF_FFFF_FFFF, wcc[k], wcp.exists(k) ? wcp[k] : 0); end
                else if (vmp[k] !== vmc[k]) begin ndiff = ndiff + 1; if (ndiff < 6) $display("WDIFF die=%0d addr=%h central=%h p2p=%h", k >> 40, k & 40'hFF_FFFF_FFFF, vmc[k], vmp[k]); end
            end
            foreach (wcp[k_]) if (!wcc.exists(k_)) begin ncnt = ncnt + 1; if (ncnt < 6) $display("WEXTRA die=%0d addr=%h", k_ >> 40, k_ & 40'hFF_FFFF_FFFF); end
            // independent gather expectation: O[k] = rank slices (sliced) / rows (whole row) of the senders' A
            for (integer r = 0; r < nrec; r = r + 1) if (r_op[r] == 1) for (integer d = 0; d < G; d = d + 1) begin
                if (r_afmt[r] == 0 || r_afmt[r] == 5) begin                       // sliced: s_q = floor(q n / G)
                    for (integer w = 0; w < r_n[r]; w = w + 1) begin : sl
                        integer src; longint kk; src = (w * NRK + NRK - 1) / r_n[r];
                        while (src > 0 && (src * r_n[r]) / NRK > w) src = src - 1;
                        while (src + 1 < NRK && ((src + 1) * r_n[r]) / NRK <= w) src = src + 1;
                        kk = ky(d, r_o[r] + w);
                        if (!vmp.exists(kk) || vmp[kk] !== aval(r, src, w)) begin nexp = nexp + 1;
                            if (nexp < 6) $display("GEXP die=%0d rec=%0d w=%0d src=%0d got=%h want=%h", d, r, w, src, vmp.exists(kk) ? vmp[kk] : 0, aval(r, src, w)); end
                    end
                end else begin
                    integer rw; rw = r_n[r] / 32 * 16;                               // BF16 row words
                    for (integer s = 0; s < NRK; s = s + 1) for (integer w = 0; w < rw; w = w + 1) begin : wr
                        longint kk; kk = ky(d, r_o[r] + s * rw + w);
                        if (!vmp.exists(kk) || vmp[kk] !== aval(r, s, w)) begin nexp = nexp + 1;
                            if (nexp < 6) $display("REXP die=%0d rec=%0d src=%0d w=%0d", d, r, s, w); end
                    end
                end
            end
            $display("IMAGES words=%0d diff=%0d count_mismatch=%0d gather_expect_mismatch=%0d", nw, ndiff, ncnt, nexp);
            if (ndiff != 0 || ncnt != 0 || nexp != 0 || nw == 0) fails = fails + 1;
        end
    endtask
    initial begin
        if (!$value$plusargs("LAT=%d", lat)) lat = 453;
        if (!$value$plusargs("CRED=%d", cred)) cred = 137;
        if (!$value$plusargs("SEED=%d", seed)) seed = 1;
        if (!$value$plusargs("RC=%d", rcn)) rcn = 0;
        if (!$value$plusargs("STALL=%d", stall_lim)) stall_lim = 40000;
        if (!$value$plusargs("CASE=%s", tcase)) tcase = "qwen";
        // record sequences (production shapes)
        if (tcase == "qwen") begin                     // Qwen3-8B TP8: hidden 4,096; G = 8
            addrec(0, 4096, 0, 1, 0);                  // ALL_REDUCE_SUM FP32 -> BF16 (attention out)
            addrec(0, 4096, 0, 0, 0);                  // ALL_REDUCE_SUM FP32 -> FP32 (ffn out)
            addrec(1, 4096, 0, 0, 0);                  // ALL_GATHER sliced FP32 (512 a rank)
            addrec(1, 4096, 1, 1, 0);                  // ALL_GATHER whole row BF16 (pf 128)
            addrec(3, 2, 0, 5, 0);                     // ARGMAX_MERGE (one flit a rank, quadrant SW whole)
            addrec(0, 1280, 0, 1, 0);                  // uneven quarters (pf 80: 16 / 16 / 16 / 32)
            addrec(1, 1000, 0, 0, 0);                  // uneven sliced gather
            addrec(1, 96, 1, 1, 0);                    // whole row pf 3: quadrant SW gets no flit (no-op quarter)
        end else if (tcase == "dsg") begin            // DS TP96 production gathers (SPMD single die)
            addrec(1, 1280, 0, 0, 0); addrec(1, 512, 0, 0, 0); addrec(1, 5120, 0, 0, 0); addrec(1, 384, 0, 0, 0);
            for (integer i = 0; i < 7; i = i + 1) addrec(1, 2304, 0, 0, 0);
            addrec(1, 5120, 0, 0, 0); addrec(1, 2304, 0, 0, 0);
            addrec(3, 2, 0, 5, 0);                     // ARGMAX_MERGE over the 96
        end else if (tcase == "grm") begin            // GROUP_REDUCE_MCAST on a G >= 4 fabric, several groups (s 4 / 2):
            // the endpoint's owner fraction pf / s <= PFMAX / NC = 64 flits bounds n at 1,024 s (s 4: 4,096; s 2: 2,048)
            addrec(4, 4096, 0, 1, 4); addrec(4, 2048, 0, 0, 2); addrec(0, 1024 * G, 0, 1, 0);
        end else if (tcase == "ds") begin             // DS TP96: the layer's sliced FP32 gathers + group-of-8 reduce-multicast
            // the layer's 13 FP32 gathers in tag order (tb_hgi_coll_pipe: qa 1,280, kvraw 512, y 5,120, gsc 384,
            // expert intermediates 7 x 2,304, yf 5,120, 2,304); priced (token_path_20261009 hbm_gen_ds) 3,991.2 cycles
            addrec(1, 1280, 0, 0, 0); addrec(1, 512, 0, 0, 0); addrec(1, 5120, 0, 0, 0); addrec(1, 384, 0, 0, 0);
            for (integer i = 0; i < 7; i = i + 1) addrec(1, 2304, 0, 0, 0);
            addrec(1, 5120, 0, 0, 0); addrec(1, 2304, 0, 0, 0);
            addrec(4, 5120, 0, 1, 8);                  // GROUP_REDUCE_MCAST s = 8 -> BF16, multicast to the 96
            addrec(4, 5120, 0, 0, 8);                  // the same, FP32 result
            addrec(3, 2, 0, 5, 0);                     // ARGMAX_MERGE over the 96
        end else $fatal(1, "unknown CASE");
        for (integer d = 0; d < G; d = d + 1) begin ci[d] = 0; pi_[d] = 0; cd[d] = 0; pd[d] = 0;
            for (integer q = 0; q < 4; q = q + 1) begin rc_v[d][q] = 0; rc_tag[d][q] = 0; rc_mode[d][q] = 0; rc_d[d][q] = 0; end
            for (integer i = 0; i < 16; i = i + 1) pdl[d][i] = '0; end
        for (integer r = 0; r < nrec; r = r + 1) for (integer d = 0; d < G; d = d + 1) begin
            integer nw; nw = (r_afmt[r] == 1) ? r_n[r] / 2 : r_n[r];
            for (integer w = 0; w < nw; w = w + 1) begin vmc[ky(d, r_a[r] + w)] = aval(r, did(d), w); vmp[ky(d, r_a[r] + w)] = aval(r, did(d), w); end
        end
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        cfgb = {1'b0, 1'b1, 6'd46, 32'(NRK)}; @(negedge clk); cfgb = {1'b1, 1'b0, 6'd0, 32'd0}; @(negedge clk); cfgb = 0;
        repeat (8) @(negedge clk);
        go_rec = 1;
        begin : wait_all
            integer t; bit fl; t = 0;
            while (t < 4000000) begin
                bit alldone; alldone = 1; fl = 0;
                for (integer d = 0; d < G; d = d + 1) begin
                    if (cd[d] < nrec || pd[d] < nrec) alldone = 0;
                    if (c_flt[d] || p_flt[d][0] || c_ret[d][2] || p_ret[d][0][2]) fl = 1;
                end
                if (alldone || fl || stalled) break;
                @(negedge clk); t = t + 1;
            end
            if (fl) begin
                for (integer d = 0; d < G && d < 4; d = d + 1)
                    $display("FAULT die=%0d central flt=%0d ret=%b done=%0d | p2p flt=%0d%0d%0d%0d ret=%b done=%0d", d, c_flt[d], c_ret[d], cd[d],
                             p_flt[d][0], p_flt[d][1], p_flt[d][2], p_flt[d][3], p_ret[d][0], pd[d]);
                fails = fails + 1;
            end
            if (stalled) begin repeat (4) @(negedge clk); fails = fails + 1; end
            if (t >= 4000000) begin $display("TIMEOUT central done=%0d p2p done=%0d of %0d", cd[0], pd[0], nrec); fails = fails + 1; end
        end
        $display("DIAG central ep=%b multi=%b pipe=%b rec=%b state=%d", g_die[0].u_c.u_ep.ep_fault, g_die[0].u_c.u_ep.multi_err, g_die[0].u_c.u_ep.p_flt, g_die[0].u_c.u_ep.rec_fault, g_die[0].u_c.u_ep.u_rec.st);
        repeat (600) @(negedge clk);     // nothing may arrive late
        for (integer r = 0; r < nrec; r = r + 1)
            $display("REC %0d op=%0d n=%0d afmt=%0d ofmt=%0d | die0 issue->done central %0d p2p %0d cycles", r, r_op[r], r_n[r], r_afmt[r],
                     r_ofmt[r], c_t1[r] - c_t0[r], p_t1[r] - p_t0[r]);
        $display("SEQ case=%s G=%0d records=%0d central %0d cycles, p2p %0d cycles (first issue -> last done, all dies); flits sent central %0d p2p %0d",
                 tcase, G, nrec, c_last - c_first, p_last - p_first, nflit[0], nflit[1]);
        check_images();
        if (rcn > 0) begin
            run_rc(rcn);
            $display("RED_CARRY rounds=%0d folds=%0d errors=%0d", rcn, G * 4 * 8 * rcn, rc_err);
            if (rc_err != 0) fails = fails + 1;
        end
        if (fails == 0) $display("PASS HGI_COLL_P2P case=%s G=%0d records=%0d rc=%0d", tcase, G, nrec, rcn);
        else $display("FAIL HGI_COLL_P2P case=%s fails=%0d", tcase, fails);
        $finish;
    end
endmodule
