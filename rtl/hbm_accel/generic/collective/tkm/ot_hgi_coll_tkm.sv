`timescale 1ns/1ps
`default_nettype none
// ot_hgi_coll_tkm (hgi-1010/k 2026-10-10): the hardware COLL.TOPK_MERGE merge sink on the collective gather bypass.
//
// Semantics (tools/hgi_sim/machine.py u_coll_topk_merge, spec 6.7): every rank q of the group contributes n (value FP32,
// id U32) pairs; the result is the group's top k by descending value, -0 = +0, ties to the lower id (the golden
// lexsort((id, -value)), stable in concatenation order: rank q, then index j); O = those ids in ASCENDING id order
// (equal ids by the value order), R = their values (original bits, -0 kept).  k > G n takes all G n.  A NaN value faults.
//
// Transport (ot_hgi_coll_ep TKM = 1): flit f of rank q carries elements 8f .. 8f + 7: words 0..7 = values (the A sector
// f), words 8..15 = ids (the B sector f); pf = ceil(n / 8) flits a rank, multicast unchanged on the exact gather bypass.
// The sink takes the endpoint's delivery lanes behind per-lane credits (del_permit / del_reserve, as ot_hgi_coll_rgx_sink)
// so a busy merge back-pressures the switch instead of dropping.
//
// Element: E = {v, okey(value), ~id, ~q, ~j, nz} (84 bits).  The VALUE KEY {v, okey, ~id, ~q, ~j} (83 bits, larger is
// better) is a strict total order equal to the golden order; the ID KEY {v, ~id, okey, ~q, ~j} orders the output.
//
// Datapath:
//   decode (2 edges a lane): q = src - gbase, f = gi - q pf, j = 8 f + s, valid j < n, NaN check, E -> per-lane FIFO
//            (CAP 64, credits returned on pop);
//   filter / select: a lane head's elements are survivors iff key > tau; up to W = 4 survivors a cycle are taken over
//            the four lane heads (32 elements: a head whose survivors are all taken pops, so sparse survivors run at
//            the full 32 elements a cycle);
//   entry sort: the <= 4 survivors -> one block sorted by the value key (rank sort, 2 edges);
//   SYSTOLIC MERGE ARRAY: C = KMAX / 4 cells of 4 sorted elements.  A cell holding block X that receives a block Y
//            from above keeps the top 4 of X u Y and passes the bottom 4 down (merge path: 16 comparators); the last
//            cell drops its bottom.  Invariant: every element that passed cell c is <= every element cell c holds
//            then or later, so (a) position p = 4c + s holds an element with >= p + 1 elements >= it in the array
//            (tau = the element at position nout - 1 is an exact lower bound of the k-th key: anything below it can
//            never be selected), (b) a dropped element has KMAX >= k better elements, and (c) once no block is in
//            flight above cell ceil(nout / 4) the array's first nout positions are the exact top-nout, sorted.
//   ID PHASE: positions >= nout invalidated, every block rank-sorted by the id key, then ceil(nout / 4) rounds of
//            odd-even transposition (block merge-split between neighbours, the same merge network: the lower cell
//            keeps the bottom 4 and returns the top 4 to the upper cell) sort the selection by id;
//   OUTPUT: the array shifts up 4 cells an edge: 16 ids -> one O line (VM, 16 words), 16 values -> one R line.
// Fault (sticky until rst_n): NaN, a flit from outside the group / past pf, more than G pf flits, a credit underflow,
// a FIFO overflow.  MUT (bench mutants): 1 ties to the HIGHER id, 2 the 4th survivor of a select cycle is dropped,
// 3 a reservation does not consume a credit (FIFO overflow under back-pressure), 4 no id phase (O in value order).
module ot_hgi_coll_tkm #(
    parameter integer KMAX = 64,      // the die instance sets 2,048 (ot_hgi_coll_ep TKM_KMAX); a small default keeps read-time elaboration cheap
    parameter integer DEL  = 4,
    parameter integer FW   = 512,
    parameter integer PWT  = FW + 33,
    parameter integer CAP  = 64,
    parameter integer MUT  = 0
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,          // one edge: configuration below valid
    input  wire [11:0]          cfg_n,          // this rank's n (informational: validity is the sender's pad marker)
    input  wire [12:0]          cfg_k,          // k: O.n must equal min(k, elements received)
    input  wire [7:0]           cfg_g,          // group size
    input  wire [7:0]           cfg_gbase,      // the group's first rank (flit src - gbase = q)
    input  wire [15:0]          cfg_pf,         // ceil(n / 8)
    input  wire [12:0]          cfg_nout,       // O.n = min(k, the group's elements), 1 .. KMAX
    input  wire [39:0]          cfg_obase,      // O: VM word address (16-word aligned)
    input  wire [39:0]          cfg_rbase,      // R: VM word address (16-word aligned)
    input  wire                 cfg_has_r,
    input  wire [DEL-1:0]       del_reserve,
    output wire [DEL-1:0]       del_permit,
    input  wire [DEL-1:0]       del_valid,
    input  wire [DEL*PWT-1:0]   del_flit,
    output reg                  w_v,
    output reg  [39:0]          w_addr,
    output reg  [15:0]          w_mask,
    output reg  [FW-1:0]        w_data,
    input  wire                 w_rdy,
    output wire                 busy,
    output reg                  done,           // one edge: every output line accepted
    output reg                  fault,
    output reg  [31:0]          stat_cycles,    // start -> done
    output reg  [31:0]          stat_ins,       // blocks inserted
    output reg  [31:0]          stat_surv       // survivors taken
);
    localparam integer W  = 4;
    localparam integer C  = KMAX / W;
    localparam integer EW = 85;               // {region, valid, okey, ~id, ~q, ~j, nz}
    localparam integer KW = 83;
    localparam integer VB = 83;               // the valid bit (bit EW-1 is the region tag)
    localparam integer CB = $clog2(C + 1);
    localparam integer QW = 8 * EW;            // FIFO word: 8 elements
    // ---------------------------------------------------------------- element helpers
    function automatic [31:0] okey(input [31:0] x);
        reg [31:0] c;
        begin
            c = (x == 32'h8000_0000) ? 32'h0 : x;
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    function automatic [31:0] unkey(input [31:0] k, input nz);
        unkey = nz ? 32'h8000_0000 : (k[31] ? (k & 32'h7FFF_FFFF) : ~k);
    endfunction
    function automatic [KW-1:0] vkey(input [EW-1:0] e);
        vkey = e[VB:1];
    endfunction
    function automatic [KW-1:0] ikey(input [EW-1:0] e);
        ikey = {e[83], e[50:19], e[82:51], e[18:1]};
    endfunction
    // insertion key (84 bits): {valid, ~region, body}: region 0 = the value order (selection phase), region 1 = the id
    // order (re-insertion phase, always below region 0); an invalid element is 0 (the lowest)
    function automatic [KW:0] key2(input [EW-1:0] e);
        reg [KW-1:0] b_;
        begin
            b_ = e[84] ? ikey(e) : vkey(e);
            key2 = e[83] ? {1'b1, ~e[84], b_[KW-2:0]} : {(KW+1){1'b0}};
        end
    endfunction
    // KEY FORM (r3, the chain's storage format): T = {key2(e), nz} -- T[EW-1:1] is the 84-bit insertion key, so the
    // tiles compare stored bits with no key mux; tinv restores the element (an invalid element is 0 in both forms)
    function automatic [EW-1:0] tform(input [EW-1:0] e);
        tform = e[83] ? {key2(e), e[0]} : {EW{1'b0}};
    endfunction
    function automatic [EW-1:0] tinv(input [EW-1:0] t);
        reg [81:0] b_;
        begin
            b_ = t[82:1];
            tinv = !t[84] ? {EW{1'b0}} : (!t[83] ? {1'b1, 1'b1, b_[49:18], b_[81:50], b_[17:0], t[0]} : {1'b0, 1'b1, b_, t[0]});
        end
    endfunction
    // ---------------------------------------------------------------- configuration
    reg [11:0] n_q; reg [7:0] g_q, gb_q; reg [15:0] pf_q; reg [12:0] nout_q; reg [39:0] ob_q, rb_q; reg hr_q;
    reg [23:0] tot_q;                          // G pf flits expected
    reg [CB-1:0] cact_q;                       // ceil(nout / 4) active cells
    reg [CB-1:0] tc_q; reg [1:0] ts_q;         // tau position (nout - 1) -> cell, slot
    // ---------------------------------------------------------------- phases
    localparam [3:0] P_IDLE = 4'd0, P_INS = 4'd1, P_DRAIN = 4'd2, P_CONV1 = 4'd3, P_CLR2 = 4'd4, P_INS2 = 4'd5,
                     P_DRAIN2 = 4'd6, P_OUT = 4'd7, P_FLUSH = 4'd8, P_CLR0 = 4'd9;
    reg [3:0] ph;
    assign busy = (ph != P_IDLE);
    // ---------------------------------------------------------------- delivery credits + decode + FIFO
    reg [7:0] cr [0:DEL-1];
    reg [DEL-1:0] res_q;                       // del_reserve pin flop (debited one edge later)
    for (genvar l = 0; l < DEL; l = l + 1) begin : g_perm
        assign del_permit[l] = (cr[l] > 8'(res_q[l])) && (ph == P_INS);   // the registered reserve not yet debited     // flops only (no start -> permit path)
    end
    reg [DEL-1:0] d1_v, d2_v;
    // reset standard (ot_rst_relay): the port drives only the relay; FIFO l from region l, the control from region DEL
    wire [DEL:0] rr;
    ot_rst_relay #(.REGIONS(DEL + 1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rn = rr[DEL];
    reg [DEL-1:0] rfault;  // credit-underflow term from the del_reserve pin, registered
    // el1011-hbm-idx 10-11: pin-flop stage d0 on the delivery lanes and on start / cfg (rtl_boundary: the (src - gbase) x pf
    // decode was 85 gate levels from del_flit; start cleared the 2,048-entry array straight from the pin)
    reg [DEL-1:0] d0_v; reg [PWT-1:0] d0_f [0:DEL-1];
    reg start_p; reg [11:0] cfg_n_p; reg [12:0] cfg_k_p, cfg_nout_p; reg [7:0] cfg_g_p, cfg_gbase_p; reg [15:0] cfg_pf_p;
    reg [39:0] cfg_obase_p, cfg_rbase_p; reg cfg_has_r_p;
    always @(posedge clk) begin
        for (int l = 0; l < DEL; l = l + 1) d0_f[l] <= del_flit[l*PWT +: PWT];
        cfg_n_p <= cfg_n; cfg_k_p <= cfg_k; cfg_nout_p <= cfg_nout; cfg_g_p <= cfg_g; cfg_gbase_p <= cfg_gbase; cfg_pf_p <= cfg_pf;
        cfg_obase_p <= cfg_obase; cfg_rbase_p <= cfg_rbase; cfg_has_r_p <= cfg_has_r;
    end
    reg [7:0] d1_q [0:DEL-1]; reg [15:0] d1_gi [0:DEL-1]; reg [FW-1:0] d1_d [0:DEL-1];
    reg [23:0] d1_qpf [0:DEL-1];
    reg [QW-1:0] d2_e [0:DEL-1];
    wire [DEL-1:0] fe, fo; wire [QW-1:0] fd [0:DEL-1]; wire [6:0] fcnt [0:DEL-1];
    reg [DEL-1:0] fpop, fpop_q;
    for (genvar l = 0; l < DEL; l = l + 1) begin : g_fifo
        (* keep_hierarchy *) ot_hcoll_sfifo #(.W(QW), .AW(6)) u_q (.clk(clk), .rst_n(rr[l]), .push(d2_v[l]),
            .din(d2_e[l]), .pop(fpop[l]), .empty(fe[l]), .dout(fd[l]), .ovf(fo[l]), .count(fcnt[l]));
    end
    reg [23:0] rcv;                            // flits received (decoded)
    reg [18:0] nel;                            // valid (non-pad) elements received
    reg [12:0] k_q;
    reg [7:0]  occ [0:DEL-1];                  // FIFO occupancy (pushed - popped; the sfifo count misses its pipeline)
    // ---------------------------------------------------------------- tau
    reg [KW-1:0] tau;
    // ---------------------------------------------------------------- staging (3 a lane) + select
    reg [8*EW-1:0] st_e [0:DEL-1][0:2];          // packed 8-element words (yosys: no unpacked sub-array copies)
    reg [7:0]    st_m [0:DEL-1][0:2];
    reg [1:0]    st_n [0:DEL-1];
    reg [DEL-1:0] ld_v;
    reg [8*EW-1:0] ld_e [0:DEL-1];
    reg [7:0]    ld_m [0:DEL-1];
    reg [7:0]    dn [0:DEL-1];                 // survivors of the head already taken
    // entry pipeline
    reg          e1_v; reg [EW-1:0] e1 [0:3];
    reg          e2_v; reg [EW-1:0] e2 [0:3]; reg [5:0] e2_ge;   // pairwise compares for the rank sort
    // ---------------------------------------------------------------- the chain of hardened tiles (el1011-hbm-idx rebuild)
    // textbook audit (owner 10-11): the flat 2,048 x 85-b array (one clock root over 1,800 um, one entry bus to every
    // cell, 8,192 key compares in one edge) is now NT tiles of PT positions (ot_hgi_coll_tkm_tile, ~12k flops, own clock
    // tree): a tile keeps its best PT of what reached it and passes its bottom 4 down on a registered seam; an upward
    // conveyor (one presented-top register a seam) empties the chain from the top.  Two passes: value key, top nout ->
    // an SRAM cell buffer, chain cleared, id key, conveyed out as O / R lines.  Control reaches every tile at equal depth.
    localparam integer PT = (KMAX < 64) ? KMAX : 64;
    localparam integer NT = KMAX / PT;
    localparam integer NG2 = (NT + 3) / 4;
    localparam integer TW = 6, LW = 7;
    localparam integer BD = KMAX / 4;
    localparam integer BA = (BD <= 2) ? 1 : $clog2(BD);
    reg  [TW-1:0] tau_t; reg [LW-1:0] tau_l;
    reg  ctl_conv, ctl_clr;
    reg  [NG2-1:0] g_conv, g_clr; reg [TW-1:0] g_tt [0:NG2-1]; reg [LW-1:0] g_tl [0:NG2-1];
    reg  dconv1, dconv2, dconv3;
    reg  eb_v; reg [4*EW-1:0] eb;
    wire [4*EW-1:0] t_ovf [0:NT]; wire t_ovf_v [0:NT]; wire [4*EW-1:0] t_up [0:NT];
    wire [KW:0] t_tau [0:NT-1]; wire t_busy [0:NT-1];
    assign t_ovf[0] = eb; assign t_ovf_v[0] = eb_v; assign t_up[NT] = '0;
    for (genvar t = 0; t < NT; t = t + 1) begin : g_t
        ot_hgi_coll_tkm_tile #(.EW(EW), .PT(PT), .TW(TW), .LW(LW)) u_t (.clk(clk), .tid(TW'(t)),
            .clr(g_clr[t / 4]), .conv(g_conv[t / 4]), .tau_t(g_tt[t / 4]), .tau_l(g_tl[t / 4]),
            .ins_v(t_ovf_v[t]), .ins_b(t_ovf[t]), .ovf_v(t_ovf_v[t + 1]), .ovf_b(t_ovf[t + 1]),
            .up_in(t_up[t + 1]), .up_out(t_up[t]), .tau_o(t_tau[t]), .busy(t_busy[t]));
    end
    reg [NG2-1:0] gb_busy; reg [KW:0] g_tau [0:NG2-1]; reg any_busy; reg [KW:0] tau_b;
    always @(posedge clk) begin : trees
        reg [KW:0] o_; reg b_;
        for (integer g = 0; g < NG2; g = g + 1) begin
            g_conv[g] <= ctl_conv; g_clr[g] <= ctl_clr; g_tt[g] <= tau_t; g_tl[g] <= tau_l;
            o_ = '0; b_ = 1'b0;
            for (integer x = 0; x < 4; x = x + 1) if (g * 4 + x < NT) begin o_ = o_ | t_tau[g * 4 + x]; b_ = b_ | t_busy[g * 4 + x]; end
            g_tau[g] <= o_; gb_busy[g] <= b_;
        end
        o_ = '0; for (integer g = 0; g < NG2; g = g + 1) o_ = o_ | g_tau[g];
        tau_b <= o_; any_busy <= |gb_busy;
        dconv1 <= ctl_conv; dconv2 <= dconv1; dconv3 <= dconv2;   // r3: the tiles shift 3 edges after ctl_conv: capture t_up[0] then
    end
    // the SRAM cell buffer (pass 1 -> pass 2): BD cells of 4 elements, registered write port, captured read
    reg  bw_v; reg [BA-1:0] bw_a; reg [4*EW-1:0] bw_d;
    reg  br_v; reg [BA-1:0] br_a; reg br_q, rd2_v; reg [4*EW-1:0] rd2;
    wire [511:0] b_q;
    wire [511:0] bw_w = 512'(bw_d);
    for (genvar m = 0; m < 2; m = m + 1) begin : g_bm
        ot_sram_1r1w_1024x256_m2_r2c2 u_b (.clk(clk), .r_ce_in(br_v), .r_addr_in(10'(br_a)), .rd_out(b_q[256*m +: 256]),
            .w_ce_in(bw_v), .w_addr_in(10'(bw_a)), .wd_in(bw_w[256*m +: 256]), .w_mask_in({256{1'b1}}),
            .rr_en(2'b0), .rr_addr(18'd0), .cr_en(2'b0), .cr_sel(16'd0));
    end
    reg [BA:0] cnv, cap, rdn; reg [12:0] cneed; reg [3:0] qcnt; reg [3:0] wcnt;
    reg [EW-1:0] lb [0:15]; reg [9:0] lp;               // output line buffer, lines pushed
    integer c, s, a, b, l, i;
    // ---------------------------------------------------------------- output packer
    reg [12:0] outn;                           // elements shifted out
    reg [12:0] wrn;                            // elements written (O lines)
    reg [8:0]  line;                           // output line index
    // ---------------------------------------------------------------- main sequential
    // output step: one 16-element line an edge (the array shifts up 4 cells); O line (+ R line) into a 4-line queue that
    // the write port drains one line an edge; a step needs room for its lines
    reg [FW-1:0] lq_d [0:7]; reg [39:0] lq_a [0:7]; reg [15:0] lq_m [0:7]; reg [3:0] lq_n; reg [2:0] lq_h, lq_t;
    wire lq_pop = (lq_n != 4'd0) && (!w_v || w_rdy);
    // P_OUT conveyor: a cell (4 elements) an edge while the 8-line queue has room for every line issued and not yet
    // pushed (registered counts only; the cells reach the packer 2 edges after the decision)
    wire [10:0] lines_iss = 11'((cnv + 1 + 3) >> 2);
    wire [11:0] lq_need = 12'(lq_n) + 12'(lines_iss - 11'(lp)) * (hr_q ? 12'd2 : 12'd1);
    wire pgo = (ph == P_OUT) && (13'(cnv) < cneed) && (lq_need <= 12'd8);
    // select (combinational over the registered staging heads)
    reg [EW-1:0] sel_e [0:3]; reg [2:0] sel_n; reg [7:0] sel_take [0:DEL-1]; reg [DEL-1:0] sel_pop;
    always @* begin : selc
        integer r_, idx;
        reg [7:0] hm;
        r_ = 0;
        for (s = 0; s < 4; s = s + 1) sel_e[s] = {EW{1'b0}};
        for (l = 0; l < DEL; l = l + 1) begin
            sel_take[l] = 8'd0;
            hm = (st_n[l] != 2'd0) ? (st_m[l][0] & ~dn[l]) : 8'd0;
            for (i = 0; i < 8; i = i + 1) if (hm[i]) begin
                if (r_ < 4) begin if (!(MUT == 2 && r_ == 3)) sel_e[r_] = st_e[l][0][EW*i +: EW]; sel_take[l][i] = 1'b1; end
                r_ = r_ + 1;
            end
            sel_pop[l] = (st_n[l] != 2'd0) && ((hm & ~sel_take[l]) == 8'd0);
        end
        sel_n = (r_ > 4) ? 3'd4 : 3'(r_);
    end
    wire ins_live = (ph == P_INS);
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            ph <= P_IDLE; fault <= 1'b0; done <= 1'b0; w_v <= 1'b0; w_addr <= 40'd0; w_mask <= 16'd0; w_data <= '0;
            stat_cycles <= 32'd0; stat_ins <= 32'd0; stat_surv <= 32'd0;
            n_q <= 12'd1; k_q <= 13'd1; nel <= 19'd0; g_q <= 8'd1; gb_q <= 8'd0; pf_q <= 16'd1; nout_q <= 13'd1; ob_q <= 40'd0; rb_q <= 40'd0; hr_q <= 1'b0;
            tot_q <= 24'd0; cact_q <= '0; tc_q <= '0; ts_q <= 2'd0; rcv <= 24'd0; tau <= '0;
            rfault <= '0; res_q <= '0; d0_v <= '0; start_p <= 1'b0; d1_v <= '0; d2_v <= '0; fpop_q <= '0; ld_v <= '0; e1_v <= 1'b0; e2_v <= 1'b0;
            outn <= 13'd0; wrn <= 13'd0; line <= 9'd0; lq_n <= 4'd0; lq_h <= 3'd0; lq_t <= 3'd0;
            ctl_conv <= 1'b0; ctl_clr <= 1'b0; eb_v <= 1'b0; bw_v <= 1'b0; br_v <= 1'b0; br_q <= 1'b0; rd2_v <= 1'b0;
            cnv <= '0; cap <= '0; rdn <= '0; cneed <= 13'd0; qcnt <= 4'd0; wcnt <= 4'd0; lp <= 10'd0; tau_t <= '0; tau_l <= '0;
            for (l = 0; l < DEL; l = l + 1) begin cr[l] <= 8'(CAP); st_n[l] <= 2'd0; dn[l] <= 8'd0; occ[l] <= 8'd0; end
        end else begin
            done <= 1'b0;
            if (busy) stat_cycles <= stat_cycles + 32'd1;
            fpop_q <= fpop;
            start_p <= start; d0_v <= del_valid; res_q <= del_reserve;
            tot_q <= 24'(g_q) * 24'(pf_q);           // from the registered configuration (no input -> logic paths)
            cact_q <= CB'((nout_q + 13'd3) >> 2);
            tc_q <= CB'((nout_q - 13'd1) >> 2); ts_q <= 2'(nout_q - 13'd1);
            tau_t <= TW'((nout_q - 13'd1) / PT); tau_l <= LW'((nout_q - 13'd1) % PT);
            cneed <= (nout_q + 13'd3) >> 2;
            // ---- credits: reserve at dispatch, return one edge after a FIFO pop
            for (l = 0; l < DEL; l = l + 1) begin
                cr[l] <= cr[l] - ((MUT == 3) ? 8'd0 : 8'(res_q[l])) + 8'(fpop_q[l]);
                rfault[l] <= res_q[l] && cr[l] == 8'd0;
                if (rfault[l]) fault <= 1'b1;
                if (fo[l]) fault <= 1'b1;
                occ[l] <= occ[l] + 8'(d2_v[l]) - 8'(fpop[l]);
            end
            // ---- decode
            for (l = 0; l < DEL; l = l + 1) begin
                d1_v[l] <= d0_v[l];
                d1_q[l] <= d0_f[l][FW + 16 +: 8] - gb_q;
                d1_gi[l] <= d0_f[l][FW +: 16];
                d1_d[l] <= d0_f[l][FW-1:0];
                d1_qpf[l] <= 24'(8'(d0_f[l][FW + 16 +: 8] - gb_q)) * 24'(pf_q);
                if (d0_v[l] && !d0_f[l][PWT - 1]) fault <= 1'b1;
                d2_v[l] <= d1_v[l];
                begin : dec
                    reg [23:0] f_; reg [31:0] vv, id_; reg [23:0] j_; reg [EW-1:0] e_;
                    f_ = 24'(d1_gi[l]) - d1_qpf[l];
                    if (d1_v[l] && (d1_q[l] >= g_q || f_ >= 24'(pf_q))) fault <= 1'b1;
                    for (s = 0; s < 8; s = s + 1) begin
                        vv = d1_d[l][32*s +: 32]; id_ = d1_d[l][32*(8+s) +: 32];
                        j_ = {f_[20:0], 3'(s)};
                        e_ = {1'b1, okey(vv), (MUT == 1) ? id_ : ~id_, ~d1_q[l][6:0], ~j_[10:0], (vv == 32'h8000_0000)};
                        if (vv == 32'hFFFF_FFFF) e_ = {EW{1'b0}};                       // the sender's pad slot
                        else if (d1_v[l] && vv[30:23] == 8'hFF && vv[22:0] != 23'd0) fault <= 1'b1;
                        d2_e[l][EW*s +: EW] <= e_;
                    end
                end
            end
            if (ph == P_INS) begin : cnt
                reg [18:0] a_;
                a_ = nel;
                for (l = 0; l < DEL; l = l + 1) if (d2_v[l]) for (s = 0; s < 8; s = s + 1) a_ = a_ + 19'(d2_e[l][EW*s + VB]);
                nel <= a_;
            end
            if (ph == P_INS) rcv <= rcv + 24'(d2_v[0]) + 24'(d2_v[1]) + 24'(d2_v[2]) + 24'(d2_v[3]);
            if ((rcv + 24'(d2_v[0]) + 24'(d2_v[1]) + 24'(d2_v[2]) + 24'(d2_v[3])) > tot_q && ph == P_INS) fault <= 1'b1;
            // ---- tau (2 edges behind the array)
            tau <= vkey(tinv({tau_b, 1'b0}));
            // ---- staging: land (mask against tau), then slots; select consumes slot 0
            for (l = 0; l < DEL; l = l + 1) begin
                ld_v[l] <= fpop[l];
                for (s = 0; s < 8; s = s + 1) begin
                    ld_e[l][EW*s +: EW] <= fd[l][EW*s +: EW];
                    ld_m[l][s] <= fd[l][EW*s + VB] && (vkey(fd[l][EW*s +: EW]) > tau);
                end
                begin : stg
                    reg [1:0] n_;
                    n_ = st_n[l];
                    if (sel_pop[l] && ins_live) begin
                        st_e[l][0] <= st_e[l][1]; st_m[l][0] <= st_m[l][1];
                        st_e[l][1] <= st_e[l][2]; st_m[l][1] <= st_m[l][2];
                        n_ = n_ - 2'd1; dn[l] <= 8'd0;
                    end else if (ins_live) dn[l] <= dn[l] | sel_take[l];
                    if (ld_v[l]) begin
                        // the new entry lands at index n_ (after this edge's shift)
                        if (n_ == 2'd0) begin st_e[l][0] <= ld_e[l]; st_m[l][0] <= ld_m[l]; end
                        else if (n_ == 2'd1) begin st_e[l][1] <= ld_e[l]; st_m[l][1] <= ld_m[l]; end
                        else begin st_e[l][2] <= ld_e[l]; st_m[l][2] <= ld_m[l]; end
                        n_ = n_ + 2'd1;
                    end
                    st_n[l] <= n_;
                end
            end
            // ---- entry: select -> e1 -> (compares) e2 -> rank-sorted block -> broadcast insertion
            // (re-insertion: the top cell, tagged region 1 -- the id order)
            e1_v <= (ins_live && (sel_n != 3'd0)) || rd2_v;
            for (s = 0; s < 4; s = s + 1) e1[s] <= rd2_v ? rd2[EW*s +: EW] : sel_e[s];
            if (ins_live && sel_n != 3'd0) stat_surv <= stat_surv + 32'(sel_n);
            e2_v <= e1_v;
            for (s = 0; s < 4; s = s + 1) e2[s] <= e1[s];
            e2_ge[0] <= key2(e1[0]) >= key2(e1[1]); e2_ge[1] <= key2(e1[0]) >= key2(e1[2]); e2_ge[2] <= key2(e1[0]) >= key2(e1[3]);
            e2_ge[3] <= key2(e1[1]) >= key2(e1[2]); e2_ge[4] <= key2(e1[1]) >= key2(e1[3]); e2_ge[5] <= key2(e1[2]) >= key2(e1[3]);
            // ---- the array (X / bk: reset-free data flops in their own block below)
            begin : entry
                reg [1:0] r0, r1, r2, r3;
                r0 = 2'(!e2_ge[0]) + 2'(!e2_ge[1]) + 2'(!e2_ge[2]);
                r1 = 2'(e2_ge[0]) + 2'(!e2_ge[3]) + 2'(!e2_ge[4]);
                r2 = 2'(e2_ge[1]) + 2'(e2_ge[3]) + 2'(!e2_ge[5]);
                r3 = 2'(e2_ge[2]) + 2'(e2_ge[4]) + 2'(e2_ge[5]);
                eb_v <= e2_v;
                for (s = 0; s < 4; s = s + 1)
                    eb[EW*s +: EW] <= tform(((r0 == 2'(s)) ? e2[0] : {EW{1'b0}}) | ((r1 == 2'(s)) ? e2[1] : {EW{1'b0}}) |
                                            ((r2 == 2'(s)) ? e2[2] : {EW{1'b0}}) | ((r3 == 2'(s)) ? e2[3] : {EW{1'b0}}));
                if (e2_v && (ph == P_INS || ph == P_DRAIN)) stat_ins <= stat_ins + 32'd1;
            end
            // ---- the chain controls (one-edge pulses / levels; the tiles act 2 edges later)
            ctl_clr <= 1'b0; bw_v <= 1'b0;
            ctl_conv <= ((ph == P_CONV1) && (13'(cnv) < cneed)) || pgo;
            if (((ph == P_CONV1) && (13'(cnv) < cneed)) || pgo) cnv <= cnv + 1'b1;
            qcnt <= (!e1_v && !e2_v && !eb_v && !any_busy && !br_v && !br_q && !rd2_v) ? ((qcnt == 4'd15) ? qcnt : qcnt + 4'd1) : 4'd0;
            // pass-1 capture: the top cell leaving the chain -> the buffer, id order tag (region 1), positions >= nout dropped
            if (ph == P_CONV1 && dconv3) begin
                for (s = 0; s < 4; s = s + 1) begin : c1
                    reg [EW-1:0] e_;
                    e_ = tinv(t_up[0][EW*s +: EW]);
                    bw_d[EW*s +: EW] <= (13'({cap, 2'(s)}) < nout_q) ? (e_ | {e_[83], {(EW-1){1'b0}}}) : {EW{1'b0}};
                end
                bw_v <= 1'b1; bw_a <= BA'(cap); cap <= cap + 1'b1;
            end
            // pass-2 feed: buffer cells read one an edge, captured, then into the entry sorter
            br_v <= (ph == P_INS2) && (13'(rdn) < cneed);
            if ((ph == P_INS2) && (13'(rdn) < cneed)) begin br_a <= BA'(rdn); rdn <= rdn + 1'b1; end
            br_q <= br_v; rd2_v <= br_q; rd2 <= b_q[4*EW-1:0];
            // ---- output (P_OUT): conveyed cells -> a 16-element line every 4 cells -> O line (+ R line) into the queue
            begin : pk
                reg [3:0] n_; reg [2:0] t_; reg [12:0] cnt_; reg [FW-1:0] od_, rd_; reg [15:0] m_; reg [EW-1:0] e_;
                reg [EW-1:0] lx [0:15];
                n_ = lq_n; t_ = lq_t;
                if (lq_pop) begin
                    w_v <= 1'b1; w_addr <= lq_a[lq_h]; w_mask <= lq_m[lq_h]; w_data <= lq_d[lq_h];
                    lq_h <= lq_h + 3'd1; n_ = n_ - 4'd1;
                end else if (w_v && w_rdy) w_v <= 1'b0;
                if (ph == P_OUT && dconv3) begin
                    for (i = 0; i < 16; i = i + 1) lx[i] = lb[i];
                    for (s = 0; s < 4; s = s + 1) begin lx[4 * cap[1:0] + s] = tinv(t_up[0][EW*s +: EW]); lb[4 * cap[1:0] + s] <= tinv(t_up[0][EW*s +: EW]); end
                    cap <= cap + 1'b1;
                    if (cap[1:0] == 2'd3 || 13'(cap) + 13'd1 == cneed) begin
                        cnt_ = ((nout_q - outn) >= 13'd16) ? 13'd16 : (nout_q - outn);
                        m_ = (cnt_ == 13'd16) ? 16'hFFFF : 16'((17'd1 << cnt_[4:0]) - 17'd1);
                        for (i = 0; i < 16; i = i + 1) begin
                            e_ = lx[i];
                            od_[32*i +: 32] = (13'(i) < cnt_) ? ((MUT == 1) ? e_[50:19] : ~e_[50:19]) : 32'd0;
                            rd_[32*i +: 32] = (13'(i) < cnt_) ? unkey(e_[82:51], e_[0]) : 32'd0;
                        end
                        lq_d[t_] <= od_; lq_a[t_] <= ob_q + {27'd0, line, 4'd0}; lq_m[t_] <= m_; t_ = t_ + 3'd1; n_ = n_ + 4'd1;
                        if (hr_q) begin lq_d[t_] <= rd_; lq_a[t_] <= rb_q + {27'd0, line, 4'd0}; lq_m[t_] <= m_; t_ = t_ + 3'd1; n_ = n_ + 4'd1; end
                        line <= line + 9'd1; outn <= outn + cnt_; lp <= lp + 10'd1;
                        for (i = 0; i < 16; i = i + 1) lb[i] <= {EW{1'b0}};
                    end
                end
                lq_n <= n_; lq_t <= t_;
            end
            // ---- phase control
            case (ph)
                P_IDLE: if (start_p) begin
                    n_q <= cfg_n_p; k_q <= cfg_k_p; nel <= 19'd0; g_q <= cfg_g_p; gb_q <= cfg_gbase_p; pf_q <= cfg_pf_p; nout_q <= cfg_nout_p;
                    ob_q <= cfg_obase_p; rb_q <= cfg_rbase_p; hr_q <= cfg_has_r_p;
                    rcv <= 24'd0; tau <= '0;
                    stat_ins <= 32'd0; stat_surv <= 32'd0; stat_cycles <= 32'd0;
                    outn <= 13'd0; wrn <= 13'd0; line <= 9'd0; lp <= 10'd0;
                    ctl_clr <= 1'b1; wcnt <= 4'd0;
                    ph <= P_CLR0;
                end
                // the chain clears 2 edges after ctl_clr; the tau tree settles 3 more
                P_CLR0: begin wcnt <= wcnt + 4'd1; tau <= '0; if (wcnt == 4'd7) ph <= P_INS; end
                P_INS: if (rcv == tot_q && d0_v == '0 && d1_v == '0 && d2_v == '0 && occ[0] == 8'd0 && occ[1] == 8'd0 && occ[2] == 8'd0 && occ[3] == 8'd0 && ld_v == '0 &&
                           st_n[0] == 2'd0 && st_n[1] == 2'd0 && st_n[2] == 2'd0 && st_n[3] == 2'd0)
                    ph <= P_DRAIN;
                P_DRAIN: if (qcnt >= 4'd4) begin
                    // O.n must be min(k, the group's elements): a record whose O.n disagrees faults (E_RANGE)
                    if (19'(nout_q) != ((19'(k_q) < nel) ? 19'(k_q) : nel)) fault <= 1'b1;
                    cnv <= '0; cap <= '0;
                    ph <= (MUT == 4) ? P_OUT : P_CONV1;
                end
                P_CONV1: if (13'(cap) == cneed) begin ctl_clr <= 1'b1; wcnt <= 4'd0; ph <= P_CLR2; end
                P_CLR2: begin wcnt <= wcnt + 4'd1; if (wcnt == 4'd4) begin rdn <= '0; ph <= P_INS2; end end
                P_INS2: if (13'(rdn) == cneed) ph <= P_DRAIN2;
                P_DRAIN2: if (qcnt >= 4'd4) begin cnv <= '0; cap <= '0; ph <= P_OUT; end
                P_OUT: if (13'(cap) == cneed && lq_n == 4'd0 && !dconv1 && !dconv2 && !dconv3) ph <= P_FLUSH;
                P_FLUSH: if (!w_v) begin ph <= P_IDLE; done <= 1'b1; end
                default: ph <= P_IDLE;
            endcase
        end
    end
    // FIFO pop into the landing register: room counted on registered state (3 slots + landing)
    always @* for (integer l2 = 0; l2 < DEL; l2 = l2 + 1)
        fpop[l2] = !fe[l2] && (ph == P_INS) && ({1'b0, st_n[l2]} + 3'(ld_v[l2]) < 3'd3);
endmodule

// ot_tkm_lt: an explicit log-depth (lt, eq) key compare with kept levels (ABC otherwise maps wide compares as MAJ ripples).
module ot_tkm_lt #(parameter integer W = 85) (input wire [W-1:0] a, input wire [W-1:0] b, output wire lt);
 localparam integer L = $clog2(W), N = 1 << L;
 (* keep *) wire [N-1:0] tl [0:L];
 (* keep *) wire [N-1:0] te [0:L];
 genvar l, i;
 for (i = 0; i < N; i = i + 1) begin : g0
  if (i < W) begin : g_b assign tl[0][i] = ~a[i] & b[i]; assign te[0][i] = ~(a[i] ^ b[i]); end
  else begin : g_p assign tl[0][i] = 1'b0; assign te[0][i] = 1'b1; end
 end
 for (l = 0; l < L; l = l + 1) begin : g_l
  for (i = 0; i < (N >> (l + 1)); i = i + 1) begin : g_n
   assign tl[l + 1][i] = tl[l][2 * i + 1] | (te[l][2 * i + 1] & tl[l][2 * i]);
   assign te[l + 1][i] = te[l][2 * i + 1] & te[l][2 * i];
  end
  for (i = (N >> (l + 1)); i < N; i = i + 1) begin : g_z assign tl[l + 1][i] = 1'b0; assign te[l + 1][i] = 1'b1; end
 end
 assign lt = tl[L][0];
endmodule


// el1011-hbm-idx 2026-10-11: one HARDENED TILE of the TOPK_MERGE chain: PT positions sorted by the insertion key (larger
// first), reset-free, cleared by a pin.  Every input pin-flopped except the conveyor seam up_in (the tile below's
// up_out register drives only the bottom cell's D mux).
// r3 (tile route r2: TT -312 ps, 10,760 failing D pins, p_bg -> 85-b key compare -> count -> 9:1 insertion mux -> X in
// ONE edge; textbook class 5): the tile is a two-stage insertion pipeline at one block an edge.
//   stage C (compare): the pinned block B2 against the CURRENT array X (4 compares a position) and against the block B1
//     being inserted this edge (16 compares, replicated per position group); the 4-bit compare vectors are then moved
//     through the SAME insertion mux as B1's data (the vector travels with its element), so gt[] describes the array
//     B2 will meet.  Registered: gt[q] (4 bits a position), the block copy, the ops.
//   stage I (insert): count (popcount of gt[q]) -> neighbour decode -> the 9:1 insertion mux -> X / ovf / up_out.
// Elements arrive and live in KEY FORM (the parent's tform: T[EW-1:1] is the 84-bit insertion key, T[0] = nz), so no
// key mux sits in front of a compare.  Ops act at stage I, one edge behind the pins (clr > conv > insert); a block
// must not sit in stage C while stage I conveys (the parent drains the chain before conv; checked in simulation).
// The block pin flop is replicated per group of GP = 8 positions (no bit fans out to more than 8 positions x 4).
module ot_hgi_coll_tkm_tile #(parameter integer EW = 85, parameter integer PT = 64, parameter integer TW = 6,
                              parameter integer LW = 7, parameter integer CDUP = 0) (
    input  wire              clk,
    input  wire [TW-1:0]     tid,
    input  wire              clr, conv,
    input  wire [TW-1:0]     tau_t,
    input  wire [LW-1:0]     tau_l,
    input  wire              ins_v,
    input  wire [4*EW-1:0]   ins_b,
    output reg               ovf_v,
    output reg  [4*EW-1:0]   ovf_b,
    input  wire [4*EW-1:0]   up_in,
    output reg  [4*EW-1:0]   up_out,
    output reg  [EW-2:0]     tau_o,          // the KEY (T[EW-1:1]) at (tau_t, tau_l) when this tile holds it, else 0
    output reg               busy
);
    localparam integer KT = EW - 1;                          // key width (T[EW-1:1])
    localparam integer GP = 8;                               // positions a replicated block copy serves
    localparam integer NP = PT + 4;
    localparam integer NGR = (NP + GP - 1) / GP;
    reg p_clr, p_conv, p_v; reg [TW-1:0] p_tid, p_tt; reg [LW-1:0] p_tl;
    (* keep *) reg p_vg [0:NGR-1];
    (* keep *) reg [4*EW-1:0] p_bg [0:NGR-1];
    reg q_clr, q_conv, q_v;
    // CDUP=1 (TP192 e86 tile gate: q_conv 10,071 / q_clr 5,796 loads): the stage-C control flops are duplicated once per
    // position group (same D, same edge; kept), so each copy drives one group's X / gt registers. No added stage.
    (* keep *) reg q_clr_g [0:NGR-1];
    (* keep *) reg q_conv_g [0:NGR-1];
    (* keep *) reg q_v_g [0:NGR-1];
    (* keep *) reg q_vg [0:NGR-1];
    (* keep *) reg [4*EW-1:0] q_bg [0:NGR-1];
    reg [3:0] gt [0:NP-1];                                   // stage C -> I: block element j beats position q
    always @(posedge clk) begin
        p_clr <= clr; p_conv <= conv; p_v <= ins_v; p_tid <= tid; p_tt <= tau_t; p_tl <= tau_l;
        for (integer g = 0; g < NGR; g = g + 1) begin p_vg[g] <= ins_v; p_bg[g] <= ins_b; end
        q_clr <= p_clr; q_conv <= p_conv; q_v <= p_v;
        for (integer g = 0; g < NGR; g = g + 1) begin q_clr_g[g] <= p_clr; q_conv_g[g] <= p_conv; q_v_g[g] <= p_v; end
        for (integer g = 0; g < NGR; g = g + 1) begin q_vg[g] <= p_vg[g]; q_bg[g] <= p_bg[g]; end
    end
    reg [EW-1:0] X [0:PT-1];
    wire [EW-1:0] SX [0:NP-1];
    // flat packed vectors (yosys 0.68 asserts on unpacked wire arrays driven by parameterised instance ports)
    wire [4*NP-1:0]    g2f;                                  // g2f[4q +: 4]: B2 vs the current array position q
    wire [16*NGR-1:0]  gbf;                                  // gbf[16g + 4j + j2]: B2 element j2 beats B1 element j
    wire [2:0] cp [0:NP-1];                                  // stage I count (B1)
    genvar gp, gj, gk, gg;
    for (gp = 0; gp < NP; gp = gp + 1) begin : g_pos
        if (gp < PT) begin : g_x assign SX[gp] = X[gp]; end else begin : g_e assign SX[gp] = {EW{1'b0}}; end
        for (gj = 0; gj < 4; gj = gj + 1) begin : g_c
            wire [KT-1:0] ka = SX[gp][EW-1:1];               // operands as local wires (yosys 0.68: a memory-word
            wire [KT-1:0] kb = p_bg[gp / GP][EW*gj + 1 +: KT]; // part-select on a port re-derives the module and asserts)
            wire lt_;
            ot_tkm_lt #(.W(KT)) u_c (.a(ka), .b(kb), .lt(lt_));
            assign g2f[4*gp + gj] = lt_;
        end
        assign cp[gp] = q_vg[gp / GP] ? (3'(gt[gp][0]) + 3'(gt[gp][1]) + 3'(gt[gp][2]) + 3'(gt[gp][3])) : 3'd0;
    end
    for (gg = 0; gg < NGR; gg = gg + 1) begin : g_bb
        for (gj = 0; gj < 4; gj = gj + 1) begin : g_j
            for (gk = 0; gk < 4; gk = gk + 1) begin : g_k
                wire [KT-1:0] ka = q_bg[gg][EW*gj + 1 +: KT];
                wire [KT-1:0] kb = p_bg[gg][EW*gk + 1 +: KT];
                wire lt_;
                ot_tkm_lt #(.W(KT)) u_b (.a(ka), .b(kb), .lt(lt_));
                assign gbf[16*gg + 4*gj + gk] = lt_;
            end
        end
    end
    // the insertion mux (stage I selects), applied to the data (ins) and to the stage-C compare vectors (gn)
    reg [EW-1:0] ins [0:NP-1];
    reg [3:0]    gn  [0:NP-1];
    always @* begin : bcins
        for (integer q = 0; q < NP; q = q + 1) begin
            ins[q] = {EW{1'b0}}; gn[q] = 4'd0;
            for (integer i = 0; i <= 4; i = i + 1)
                if (q - i >= 0 && cp[(q - i >= 0) ? q - i : 0] == 3'(i)) begin
                    ins[q] = ins[q] | SX[(q - i >= 0) ? q - i : 0];
                    gn[q]  = gn[q]  | g2f[4*((q - i >= 0) ? q - i : 0) +: 4];
                end
            for (integer j = 0; j < 4; j = j + 1)
                if (q_vg[q / GP] && q - j >= 0 && cp[(q - j >= 0) ? q - j : 0] > 3'(j) && (q - j - 1 < 0 || cp[(q - j - 1 >= 0) ? q - j - 1 : 0] <= 3'(j))) begin
                    ins[q] = ins[q] | q_bg[q / GP][EW*j +: EW];
                    gn[q]  = gn[q]  | gbf[16*(q / GP) + 4*j +: 4];
                end
            // the overflow positions are empty again after the edge: B2 beats them with every valid element
            if (q >= PT) for (integer j = 0; j < 4; j = j + 1) gn[q][j] = p_bg[q / GP][EW*j + EW - 1];
        end
    end
    always @(posedge clk) begin : cmp
        for (integer q = 0; q < NP; q = q + 1)
            for (integer j = 0; j < 4; j = j + 1)
                gt[q][j] <= ((CDUP != 0) ? q_clr_g[q / GP] : q_clr) ? p_bg[q / GP][EW*j + EW - 1] : gn[q][j];
`ifndef SYNTHESIS
        if (q_conv && p_v) $error("ot_hgi_coll_tkm_tile: a block entered stage C while the tile conveys");
`endif
    end
    always @(posedge clk) begin : upd
        if (CDUP != 0) begin
            // per position: the group's own control copy (identical sequence to the shared form below)
            for (integer p_ = 0; p_ < PT; p_ = p_ + 1) begin
                if (q_clr_g[p_ / GP]) X[p_] <= {EW{1'b0}};
                else if (q_conv_g[p_ / GP]) X[p_] <= (p_ < PT - 4) ? X[(p_ < PT - 4) ? p_ + 4 : 0] : up_in[EW*((p_ >= PT - 4) ? p_ - (PT - 4) : 0) +: EW];
                else if (q_v_g[p_ / GP]) X[p_] <= ins[p_];
            end
            if (q_clr_g[NGR - 1]) begin up_out <= '0; ovf_v <= 1'b0; end
            else if (q_conv_g[NGR - 1]) begin
                for (integer s_ = 0; s_ < 4; s_ = s_ + 1) up_out[EW*s_ +: EW] <= X[4 + s_];
                ovf_v <= 1'b0;
            end else if (q_v_g[NGR - 1]) begin
                for (integer s_ = 0; s_ < 4; s_ = s_ + 1) begin ovf_b[EW*s_ +: EW] <= ins[PT + s_]; up_out[EW*s_ +: EW] <= ins[s_]; end
                ovf_v <= ins[PT][EW-1] | ins[PT + 1][EW-1] | ins[PT + 2][EW-1] | ins[PT + 3][EW-1];
            end else ovf_v <= 1'b0;
        end else begin
            if (q_clr) begin
                for (integer p_ = 0; p_ < PT; p_ = p_ + 1) X[p_] <= {EW{1'b0}};
                up_out <= '0; ovf_v <= 1'b0;
            end else if (q_conv) begin
                for (integer p_ = 0; p_ < PT - 4; p_ = p_ + 1) X[p_] <= X[p_ + 4];
                for (integer s_ = 0; s_ < 4; s_ = s_ + 1) begin X[PT - 4 + s_] <= up_in[EW*s_ +: EW]; up_out[EW*s_ +: EW] <= X[4 + s_]; end
                ovf_v <= 1'b0;
            end else if (q_v) begin
                for (integer p_ = 0; p_ < PT; p_ = p_ + 1) X[p_] <= ins[p_];
                for (integer s_ = 0; s_ < 4; s_ = s_ + 1) begin ovf_b[EW*s_ +: EW] <= ins[PT + s_]; up_out[EW*s_ +: EW] <= ins[s_]; end
                ovf_v <= ins[PT][EW-1] | ins[PT + 1][EW-1] | ins[PT + 2][EW-1] | ins[PT + 3][EW-1];
            end else ovf_v <= 1'b0;
        end
        busy <= p_v || q_v || ovf_v;
        tau_o <= (p_tid == p_tt) ? X[p_tl % PT][EW-1:1] : '0;
    end
endmodule

// ot_tkm_lt_live (TKM-2 2026-10-17): ot_tkm_lt with ONLY the live tree nodes kept.  ot_tkm_lt pads W to N = 2^L and
// keeps every [N-1:0] level, so each 85-bit compare carries 2 x 128 x 8 = 2,048 kept bits of which ~1,620 are
// constant padding; yosys insbuf turned those into 756,805 BUFx2 (55.2k um2) on the e86 tile (416 compares) that
// placement then removes (gate fab3f5eba: synth 85.3k um2, placed std 28.2k).  Same log-depth (lt, eq) tree, same
// msb-first combine, same kept cut points; an odd top node passes up unchanged (it stays the most significant node).
module ot_tkm_lt_live #(parameter integer W = 85) (input wire [W-1:0] a, input wire [W-1:0] b, output wire lt);
 localparam integer L = $clog2(W);
 function automatic integer nn(input integer l); nn = (W + (1 << l) - 1) >> l; endfunction
 function automatic integer off(input integer l); integer k; off = 0; for (k = 0; k < l; k = k + 1) off = off + nn(k); endfunction
 localparam integer TOT = off(L + 1);
 (* keep *) wire [TOT-1:0] tl;
 (* keep *) wire [TOT-1:0] te;
 genvar l, i;
 for (i = 0; i < W; i = i + 1) begin : g0 assign tl[i] = ~a[i] & b[i]; assign te[i] = ~(a[i] ^ b[i]); end
 for (l = 0; l < L; l = l + 1) begin : g_l
  for (i = 0; i < nn(l + 1); i = i + 1) begin : g_n
   if (2 * i + 1 < nn(l)) begin : g_c
    assign tl[off(l + 1) + i] = tl[off(l) + 2 * i + 1] | (te[off(l) + 2 * i + 1] & tl[off(l) + 2 * i]);
    assign te[off(l + 1) + i] = te[off(l) + 2 * i + 1] & te[off(l) + 2 * i];
   end else begin : g_p
    assign tl[off(l + 1) + i] = tl[off(l) + 2 * i];
    assign te[off(l + 1) + i] = te[off(l) + 2 * i];
   end
  end
 end
 assign lt = tl[off(L)];
endmodule


// ot_hgi_coll_tkm_tile_rg (TKM-2 2026-10-17, e86 successor of CDUP fab3f5eba): the same two-stage insertion tile,
// cycle-identical to ot_hgi_coll_tkm_tile CDUP=1, with
//  (1) ot_tkm_lt_live compares (no kept padding: removes the yosys insbuf storm), and
//  (2) the clock split by ROW GROUP into NRC = 4 related same-frequency regional roots plus the pin-stage root clk
//      (one CTS tree each; e86 single root measured TT 373.1 ps on 12,792 sinks):
//        clk    : pin stage p_* (p_bg / p_vg copies, controls), q_v, busy, tau_o   (inputs tid clr conv tau_* ins_*)
//        clk_r0 : position groups 0-1 (X[0..15], gt, q_bg/q_vg/control copies) + up_out
//        clk_r1 : groups 2-3;   clk_r2 : groups 4-5
//        clk_r3 : groups 6-7 + the overflow group 8 + ovf_v/ovf_b; captures up_in
//      Every flop keeps its edge; roots meet only register to register (ordinary related STA, no exception).
//      up_out / ovf use their own group's control copy (identical D and edge to the CDUP NGR-1 copy).
// PRE (HH-4 2026-10-18, default 0 = the lockstep-checked form above): PRE = 1 adds ONE input stage in front of the tile.
//   Route hcoll_v7_tkm_tile_e86-d4f2-21a3c7d78 (TT -166.81, 1,613 D pins; ORFS top paths and the pre-route gate all
//   u.p_bg[g][*] -> 85-b ot_tkm_lt_live tree -> gn insertion OR -> u.gt[q][j]): p_bg sat on the pin-stage root clk at the
//   N-face pins (~200 ps of buffered wire to the far row groups) and gt on the regional root, so the 10-level compare
//   cone crossed roots and paid the different-entry setup reserve (210 ps, clock.sdc pair rule) on top of 60 ps.  Not
//   fan-out (<= 12 loads a bit) and not a yosys ROM/merge (all 9 p_bg copies present).  With PRE = 1 the pin stage
//   s_* (clk, one copy at the pins) only registers the inputs; every p_bg / p_vg copy is clocked by ITS row group's root,
//   so the root crossing is flop -> wire -> flop and the whole compare cone p_bg -> gt is inside one regional tree.
//   Function = the PRE = 0 tile with clr / conv / ins_v / ins_b (and tid / tau_*) delayed one edge: 4 edges a chain hop
//   instead of 3; tkm_static's calendar takes TLAT = 4 for this shape (SETTLE = 4 NT + 8, up-chain capture tap +1).
// CREP (L2H-IDX e86s 2026-10-19, SAFE-DESIGN item 3; mapped census of the e86 gate: q_conv_g[1..7] each drove 2,064
//   loads, q_conv_g[0] 1,378 -- one control flop per row group steering all 8 x 86 X bits through a 3-level priority mux):
//   1 = the X / up_out / ovf_b update controls are SAME-EDGE KEPT COPIES, one per 29-bit slice of a position, holding the
//   registered ONE-HOT select {hold, ins, shift, clr} (decoded once per row group from that group's own kept copy of the
//   pin-stage p_clr / p_conv / p_v, clk root, D = the same i_* as p_*): X slice <= sh ? shift : in ? ins : hd ? X : 0.
//   Same edges, same function as CREP 0 (cycle-identity bench tb_hgi_coll_tkm_tile_rg_crep.sv); each select copy drives
//   one AND-OR leg per bit of its slice (<= 29 loads), each group decode feeds 24 copies.  q_*_g keep only gt / ovf_v.
//   CMUT (bench only, CREP 1): 1 = position 13 slice 1 takes hold where it should shift (must FAIL the lockstep).
module ot_hgi_coll_tkm_tile_rg #(parameter integer EW = 86, parameter integer PT = 64, parameter integer TW = 6,
                                 parameter integer LW = 7, parameter integer PRE = 0,
                                 parameter integer CREP = 0, parameter integer CMUT = 0) (
    input  wire              clk, clk_r0, clk_r1, clk_r2, clk_r3,
    input  wire [TW-1:0]     tid,
    input  wire              clr, conv,
    input  wire [TW-1:0]     tau_t,
    input  wire [LW-1:0]     tau_l,
    input  wire              ins_v,
    input  wire [4*EW-1:0]   ins_b,
    output reg               ovf_v,
    output reg  [4*EW-1:0]   ovf_b,
    input  wire [4*EW-1:0]   up_in,
    output reg  [4*EW-1:0]   up_out,
    output reg  [EW-2:0]     tau_o,
    output reg               busy
);
    localparam integer KT = EW - 1;
    localparam integer GP = 8;
    localparam integer NP = PT + 4;
    localparam integer NGR = (NP + GP - 1) / GP;
    localparam integer NRC = 4;
    function automatic integer rg(input integer g); rg = (g >= NGR - 1) ? NRC - 1 : (g * NRC) / (NGR - 1); endfunction
    wire [NRC-1:0] ckr = {clk_r3, clk_r2, clk_r1, clk_r0};
    reg p_clr, p_conv, p_v, q_v; reg [TW-1:0] p_tid, p_tt; reg [LW-1:0] p_tl;
    (* keep *) reg p_vg [0:NGR-1];
    (* keep *) reg [4*EW-1:0] p_bg [0:NGR-1];
    (* keep *) reg q_clr_g [0:NGR-1];
    (* keep *) reg q_conv_g [0:NGR-1];
    (* keep *) reg q_v_g [0:NGR-1];
    (* keep *) reg q_vg [0:NGR-1];
    (* keep *) reg [4*EW-1:0] q_bg [0:NGR-1];
    reg [3:0] gt [0:NP-1];
    wire i_clr, i_conv, i_v; wire [TW-1:0] i_tid, i_tt; wire [LW-1:0] i_tl; wire [4*EW-1:0] i_b;
    genvar gp, gj, gk, gg;
    if (PRE != 0) begin : g_pre
        reg s_clr, s_conv, s_v; reg [TW-1:0] s_tid, s_tt; reg [LW-1:0] s_tl; reg [4*EW-1:0] s_b;
        always @(posedge clk) begin
            s_clr <= clr; s_conv <= conv; s_v <= ins_v; s_tid <= tid; s_tt <= tau_t; s_tl <= tau_l; s_b <= ins_b;
        end
        assign i_clr = s_clr; assign i_conv = s_conv; assign i_v = s_v; assign i_tid = s_tid; assign i_tt = s_tt;
        assign i_tl = s_tl; assign i_b = s_b;
    end else begin : g_nopre
        assign i_clr = clr; assign i_conv = conv; assign i_v = ins_v; assign i_tid = tid; assign i_tt = tau_t;
        assign i_tl = tau_l; assign i_b = ins_b;
    end
    always @(posedge clk) begin
        p_clr <= i_clr; p_conv <= i_conv; p_v <= i_v; p_tid <= i_tid; p_tt <= i_tt; p_tl <= i_tl; q_v <= p_v;
    end
    for (gg = 0; gg < NGR; gg = gg + 1) begin : g_pbg
        if (PRE != 0) begin : g_r
            always @(posedge ckr[rg(gg)]) begin p_vg[gg] <= i_v; p_bg[gg] <= i_b; end
        end else begin : g_c
            always @(posedge clk) begin p_vg[gg] <= i_v; p_bg[gg] <= i_b; end
        end
    end
    for (gg = 0; gg < NGR; gg = gg + 1) begin : g_ctl
        always @(posedge ckr[rg(gg)]) begin
            q_clr_g[gg] <= p_clr; q_conv_g[gg] <= p_conv; q_v_g[gg] <= p_v; q_vg[gg] <= p_vg[gg]; q_bg[gg] <= p_bg[gg];
        end
    end
    reg [EW-1:0] X [0:PT-1];
    wire [EW-1:0] SX [0:NP-1];
    wire [4*NP-1:0]    g2f;
    wire [16*NGR-1:0]  gbf;
    wire [2:0] cp [0:NP-1];
    for (gp = 0; gp < NP; gp = gp + 1) begin : g_pos
        if (gp < PT) begin : g_x assign SX[gp] = X[gp]; end else begin : g_e assign SX[gp] = {EW{1'b0}}; end
        for (gj = 0; gj < 4; gj = gj + 1) begin : g_c
            wire [KT-1:0] ka = SX[gp][EW-1:1];
            wire [KT-1:0] kb = p_bg[gp / GP][EW*gj + 1 +: KT];
            wire lt_;
            ot_tkm_lt_live #(.W(KT)) u_c (.a(ka), .b(kb), .lt(lt_));
            assign g2f[4*gp + gj] = lt_;
        end
        assign cp[gp] = q_vg[gp / GP] ? (3'(gt[gp][0]) + 3'(gt[gp][1]) + 3'(gt[gp][2]) + 3'(gt[gp][3])) : 3'd0;
    end
    for (gg = 0; gg < NGR; gg = gg + 1) begin : g_bb
        for (gj = 0; gj < 4; gj = gj + 1) begin : g_j
            for (gk = 0; gk < 4; gk = gk + 1) begin : g_k
                wire [KT-1:0] ka = q_bg[gg][EW*gj + 1 +: KT];
                wire [KT-1:0] kb = p_bg[gg][EW*gk + 1 +: KT];
                wire lt_;
                ot_tkm_lt_live #(.W(KT)) u_b (.a(ka), .b(kb), .lt(lt_));
                assign gbf[16*gg + 4*gj + gk] = lt_;
            end
        end
    end
    reg [EW-1:0] ins [0:NP-1];
    reg [3:0]    gn  [0:NP-1];
    always @* begin : bcins
        for (integer q = 0; q < NP; q = q + 1) begin
            ins[q] = {EW{1'b0}}; gn[q] = 4'd0;
            for (integer i = 0; i <= 4; i = i + 1)
                if (q - i >= 0 && cp[(q - i >= 0) ? q - i : 0] == 3'(i)) begin
                    ins[q] = ins[q] | SX[(q - i >= 0) ? q - i : 0];
                    gn[q]  = gn[q]  | g2f[4*((q - i >= 0) ? q - i : 0) +: 4];
                end
            for (integer j = 0; j < 4; j = j + 1)
                if (q_vg[q / GP] && q - j >= 0 && cp[(q - j >= 0) ? q - j : 0] > 3'(j) && (q - j - 1 < 0 || cp[(q - j - 1 >= 0) ? q - j - 1 : 0] <= 3'(j))) begin
                    ins[q] = ins[q] | q_bg[q / GP][EW*j +: EW];
                    gn[q]  = gn[q]  | gbf[16*(q / GP) + 4*j +: 4];
                end
            if (q >= PT) for (integer j = 0; j < 4; j = j + 1) gn[q][j] = p_bg[q / GP][EW*j + EW - 1];
        end
    end
    for (gp = 0; gp < NP; gp = gp + 1) begin : g_gt
        always @(posedge ckr[rg(gp / GP)])
            for (integer j = 0; j < 4; j = j + 1)
                gt[gp][j] <= q_clr_g[gp / GP] ? p_bg[gp / GP][EW*j + EW - 1] : gn[gp][j];
    end
    if (CREP == 0) begin : g_upd
    for (gp = 0; gp < PT; gp = gp + 1) begin : g_xr
        always @(posedge ckr[rg(gp / GP)]) begin
            if (q_clr_g[gp / GP]) X[gp] <= {EW{1'b0}};
            else if (q_conv_g[gp / GP]) X[gp] <= (gp < PT - 4) ? X[(gp < PT - 4) ? gp + 4 : 0] : up_in[EW*((gp >= PT - 4) ? gp - (PT - 4) : 0) +: EW];
            else if (q_v_g[gp / GP]) X[gp] <= ins[gp];
        end
    end
    always @(posedge ckr[rg(0)]) begin : upo
        if (q_clr_g[0]) up_out <= '0;
        else if (q_conv_g[0]) for (integer s_ = 0; s_ < 4; s_ = s_ + 1) up_out[EW*s_ +: EW] <= X[4 + s_];
        else if (q_v_g[0]) for (integer s_ = 0; s_ < 4; s_ = s_ + 1) up_out[EW*s_ +: EW] <= ins[s_];
    end
    always @(posedge ckr[rg(NGR - 1)]) begin : ovo
        if (q_clr_g[NGR - 1] || q_conv_g[NGR - 1]) ovf_v <= 1'b0;
        else if (q_v_g[NGR - 1]) begin
            for (integer s_ = 0; s_ < 4; s_ = s_ + 1) ovf_b[EW*s_ +: EW] <= ins[PT + s_];
            ovf_v <= ins[PT][EW-1] | ins[PT + 1][EW-1] | ins[PT + 2][EW-1] | ins[PT + 3][EW-1];
        end else ovf_v <= 1'b0;
    end
    end else begin : g_crep
    // ---- CREP 1: per-group kept copies of the pin-stage controls, decoded once, registered as per-slice one-hot copies
    localparam integer XS = 29;                         // bits per control slice
    localparam integer NXS = (EW + XS - 1) / XS;        // slices per position
    localparam integer NUS = (4 * EW + XS - 1) / XS;    // slices of up_out / ovf_b
    (* keep *) reg pc_clr [0:NGR-1];
    (* keep *) reg pc_conv [0:NGR-1];
    (* keep *) reg pc_v [0:NGR-1];
    wire [3:0] dsel [0:NGR-1];                          // {hold, ins, shift, clr} of the NEXT edge, one-hot
    for (gg = 0; gg < NGR; gg = gg + 1) begin : g_pc
        always @(posedge clk) begin pc_clr[gg] <= i_clr; pc_conv[gg] <= i_conv; pc_v[gg] <= i_v; end
        assign dsel[gg] = {!pc_clr[gg] && !pc_conv[gg] && !pc_v[gg], !pc_clr[gg] && !pc_conv[gg] && pc_v[gg],
                           !pc_clr[gg] && pc_conv[gg], pc_clr[gg]};
    end
    for (gp = 0; gp < PT; gp = gp + 1) begin : g_xr
        wire [EW-1:0] xa = (gp < PT - 4) ? X[(gp < PT - 4) ? gp + 4 : 0] : up_in[EW*((gp >= PT - 4) ? gp - (PT - 4) : 0) +: EW];
        wire [EW-1:0] xn;
        always @(posedge ckr[rg(gp / GP)]) X[gp] <= xn;
        for (gj = 0; gj < NXS; gj = gj + 1) begin : g_s
            localparam integer LO = gj * XS;
            localparam integer W = (EW - LO < XS) ? EW - LO : XS;
            (* keep *) reg [3:0] m;                     // {hold, ins, shift, clr}
            always @(posedge ckr[rg(gp / GP)])
                m <= (CMUT == 1 && gp == 13 && gj == 1) ? {dsel[gp / GP][1] | dsel[gp / GP][3], dsel[gp / GP][2], 1'b0, dsel[gp / GP][0]}
                                                         : dsel[gp / GP];
            assign xn[LO +: W] = ({W{m[1]}} & xa[LO +: W]) | ({W{m[2]}} & ins[gp][LO +: W]) | ({W{m[3]}} & X[gp][LO +: W]);
        end
    end
    wire [4*EW-1:0] ua, ub, un, on;
    always @(posedge ckr[rg(0)]) up_out <= un;
    always @(posedge ckr[rg(NGR - 1)]) ovf_b <= on;
    wire [4*EW-1:0] oi;
    for (gk = 0; gk < 4; gk = gk + 1) begin : g_ua
        assign ua[EW*gk +: EW] = X[4 + gk]; assign ub[EW*gk +: EW] = ins[gk]; assign oi[EW*gk +: EW] = ins[PT + gk];
    end
    for (gj = 0; gj < NUS; gj = gj + 1) begin : g_us
        localparam integer LO = gj * XS;
        localparam integer W = (4 * EW - LO < XS) ? 4 * EW - LO : XS;
        (* keep *) reg [3:0] mu;                        // up_out: group 0 select
        (* keep *) reg mo;                              // ovf_b: last group's "ins" select (clr / conv / idle hold ovf_b)
        always @(posedge ckr[rg(0)]) mu <= dsel[0];
        always @(posedge ckr[rg(NGR - 1)]) mo <= dsel[NGR - 1][2];
        assign un[LO +: W] = ({W{mu[1]}} & ua[LO +: W]) | ({W{mu[2]}} & ub[LO +: W]) | ({W{mu[3]}} & up_out[LO +: W]);
        assign on[LO +: W] = mo ? oi[LO +: W] : ovf_b[LO +: W];
    end
    always @(posedge ckr[rg(NGR - 1)]) begin : ovo
        if (q_clr_g[NGR - 1] || q_conv_g[NGR - 1]) ovf_v <= 1'b0;
        else if (q_v_g[NGR - 1]) ovf_v <= ins[PT][EW-1] | ins[PT + 1][EW-1] | ins[PT + 2][EW-1] | ins[PT + 3][EW-1];
        else ovf_v <= 1'b0;
    end
    end
    always @(posedge clk) begin : cor
        busy <= p_v || q_v || ovf_v;
        tau_o <= (p_tid == p_tt) ? X[p_tl % PT][EW-1:1] : '0;
`ifndef SYNTHESIS
        if (q_conv_g[0] && p_v) $error("ot_hgi_coll_tkm_tile_rg: a block entered stage C while the tile conveys");
`endif
    end
endmodule
`default_nettype wire
