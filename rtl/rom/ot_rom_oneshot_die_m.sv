`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// MARGIN form of ot_rom_oneshot_die (rtl/rom/ot_rom_oneshot_allreduce.sv), the Qwen ROM die's collective engine
// (r21 master qfd_io_collective), for the 2026-10-06/07 closure rules.  Same transactions, same rank-order binary32
// fold, same faults; latency is longer (transaction-level exactness, design simplification rule 1):
//   * every input is captured in a flop at its pin, every output leaves from a flop (register-to-register boundary);
//   * the local port is credit-based (rule 2: no same-cycle cross-block handshake): the sender holds IB credits and
//     in_cr returns one per word taken out of the IB-word input buffer;
//   * each source FIFO has a registered HEAD word (hd / hv): the pop decision reads only flops (hv, the head's mode
//     bit, g_busy, s0_v / s0_mode, inflight == 0), instead of the FIFO counts and the DEPTH:1 read mux;
//   * the adders are ot_hdc_fp32_add_lat at ADD_LAT 7 (the tile's 1.2 GHz-at-SS binary32 adder, same RNE results
//     and error encoding) instead of ot_fp32_add_rne_pipe at 5 (~1.09 GHz at SS);
//   * tx_ready / cr_in are taken from their pin registers (a cycle late): tx_ready is the link layer's registered
//     "may send" (the die link is credit-based end to end; a send against a deasserted tx_ready faults, code bit 2).
// Capacity per source: DEPTH FIFO words + the head register >= the DEPTH credits, so no FIFO can overflow; an
// overflow is still checked and faults.
// ---------------------------------------------------------------------------
module ot_rom_oneshot_die_m #(
    parameter integer N       = 4,
    parameter integer RANK    = 0,
    parameter integer LANES   = 16,
    parameter integer TAGW    = 32,
    parameter integer DEPTH   = 16,
    parameter integer ADD_LAT = 7,
    parameter integer IB      = 4,
    parameter integer FW      = 32 * LANES,
    parameter integer PW      = FW + 2 + TAGW,
    parameter integer RB      = (N > 1) ? $clog2(N) : 1,
    // PR = 1 (qwen-blocks 2026-10-07; 0 = original): the pop decision is replicated per (source, 128-bit slice) from
    // kept copies of its state flops (each registered from the same next-state as the original), so the head refill
    // and s0 capture enables of a slice come from a local pop; the local word enters its FIFO one edge after it is
    // sent (registered {data}, the occupancy check counts it); tx_rec is captured without an enable.  Transactions,
    // fold order, values and faults unchanged; the local word reaches the head one cycle later.
    // PR = 2 (safe-qwen S-A3, 2026-10-08): the pop / refill decision reaches every (source, 128-bit slice) through a
    // 2-level REGISTERED fanout tree of keep_hierarchy leaves (synthesis cannot merge them: the PR = 1 copies were
    // merged back into hv[0] by Yosys, so PR = 1 routed with one hv fanning out to every head bit, TT -340.7):
    // level 1 = per-source copies of the decision state registered from its next state (as PR = 1), level 2 = the
    // slice's {pop, refill, read index} registered per (source, slice).  The slice head / s0 registers therefore act
    // one edge after the decision, and the s0 consumers (fold input, gather stage, tag check) are re-timed by one
    // edge (+1 cycle per collective word).  The head's mode / last bits stay at control timing (hb_c).  rst_n reaches
    // only per-region reset synchronisers (control, one per source, one per adder stage; 2-edge release).
    // Transactions, fold order, values and faults unchanged.
    parameter integer PR      = 0,
    // OPQ = 1 (fill-9 2026-10-10, qfd_io_collective root cause): the rank-order fold's operand skew lines (stage g waits
    // (g-1)*ADD_LAT cycles for the running sum) are free-running FW*D-bit SHIFT registers (10,752 flops at N 4 that
    // shift every cycle: back-to-back Q->D hops with no logic, the FF-hold class g_stage.g_d.dl -> dl of every route,
    // and the CTS hold-repair floods).  OPQ = 1 replaces each with a per-128-bit-slice operand QUEUE (keep_hierarchy
    // leaf, QD = 2^ceil(log2(D+1)) entries): written only on red_in, read in order when the stage's adder takes its
    // valid (sv[g-1] = red_in delayed exactly D: the adders are fixed-latency), local per-slice write / read pointers
    // reset by the stage's own reset leaf.  Same operand at the same adder edge: values, fold order, faults, cycles
    // unchanged.
    parameter integer OPQ     = 0,
    // el1011-q-coll 2026-10-11 (qfd_io_collective pr2_pf-7f5522d03-f9a routed TT -63.6 / FF -18.0, structural boundary):
    //   TXK   = 1: tx_rec leaves from its OWN kept pin register (PR != 0 registered txrec_q and lpq from the same ib_head, so
    //               synthesis merged them into one flop per bit that also feeds the interior local-FIFO write: the
    //               "pin flop" could not sit at the right-face pins -> 141 tx_rec ports at -63.6 ps over 11 wire levels).
    //   FPIPE = 1: the reduce-error fault condition (red_out && serr[N-1], a 16-lane OR of spread adder flags) is
    //               registered one edge before it sets the sticky fault / fault_code[0] (-31.5 ps, 12 levels).  Fault is
    //               reported one edge later; data, out_err and every other output are unchanged.
    //   HDLO  = n: n HB4xp67 hold-delay cells (ot_hdly, dont_touch PRE_FLOORPLAN) on out_valid / out_data / out_last /
    //               out_rank / out_err (FF -18.0 ps over 318 out_data ports; TT setup on that class >= +60 ps).
    // All three 0 = the unchanged block.
    parameter integer TXK     = 0,
    parameter integer FPIPE   = 0,
    parameter integer HDLO    = 0,
    // MEMM = 1 (el1011-q-coll 2026-10-11, textbook class 1: N x DEPTH x PW = 4 x 32 x 546 receive-FIFO flops were ~70k of
    // the 119,632 clock sinks): each source FIFO body is a single-clock 1R1W macro (ot_sram_1r1w_32x546_m1).  PR = 2 only:
    // the macro is written at control timing from the registered push word / pointer and read with the level-1
    // registered {refill, index} copy, so its registered output lines up with the level-2 slice refill (the flop body
    // was read combinationally one edge later); a word pushed at e1 is counted in that cycle's mnz_n, read at e2.
    // Source 0's {mode, last} bits keep a 2 x DEPTH flop shadow for the control's head look-ahead (hb_c / hm_n).
    parameter integer MEMM    = 0,
    // FSL = 1 (el1011-q-coll 2026-10-11, textbook class 1 residual: the 3 x 16 LAT-7 adder lanes + skew lines kept ~50k
    // sinks on one root): the all-reduce fold is built from FW / 128 hardened lane-slice tiles (ot_coll_fold_slice: 4
    // lanes, its own skew lines, adders, valid chain from its lane 0, partial error OR and reset leaf) with registered
    // seams (pin flops in, flops out: +2 edges on the reduce path; ldl grows by 2).  serr[N-1] = OR of the slice
    // partials (OR is associative and every slice delays identically).  OPQ must be 0.
    parameter integer FSL     = 0,
    // IBH = 1 (el1011-q-coll 2026-10-11 22:40, pr2c TT -29.8: ir -> 4:1 ib_head mux -> ~400 ps of wire -> u_txk at the tx
    // face): the IB head is a REGISTER computed one edge ahead (hq <= ib[next ir], write-bypassed when the next head slot
    // is written this edge), so every consumer (u_txk / txrec_q / lpq) sees a flop and the long hop is wire only.
    // Same value every cycle as the combinational ib_head (cycle-exact; no latency).  FPIPE = 2 additionally registers
    // the tag-disagree and overflow fault conditions one edge (fault / fault_code[1..2] set one edge later).
    parameter integer IBH     = 0,
    // CT = 1 (qwen-tp8/coll4 2026-10-12, MARGIN 9): the column datapath (IB, receive pin registers, FIFO bodies, heads,
    // s0 operands, gather word, tx word) moves into five hardened ot_coll_col_tile leaves (rtl/rom/ot_coll_col_tile.sv),
    // each a one-cycle-delayed replica of its 128-bit column driven by registered control from this engine; the engine
    // keeps the control state machine, a 2-bit {mode, last} replica of source 0 for the pop decision, the fold slices and
    // the output registers.  Needs PR 2, MEMM 1, FSL 1, IBH 1, TXK 1, N 4, DEPTH 32, IB 4, LANES 16, TAGW 32.
    // +1 cycle on tx (tx_valid / tx_rec) and on the result path (out_*); the fault flags (agree) one edge later.
    parameter integer CT      = 0,
    // RSTRAP = 1 (qwen-coll-io r3 2026-10-14, one compute-die type for all 8 TP8 dies): the die's own source is the
    // one-hot STRAP self_s (static, from the die's package-rank bumps through the parent's pin flop) instead of the
    // RANK parameter, so one hardened cluster serves every package.  RSTRAP = 0: self_s is unused and every decision
    // below reduces to the RANK constant exactly as before.
    parameter integer RSTRAP  = 0,
    parameter integer CCLK = 0 // opt-in: independent phi-R clock at each hardened child
) (
    input  wire              clk,
    input wire [(PW+127)/128-1:0] clk_cols,
    input wire [FW/128-1:0] clk_folds,
    input  wire              rst_n,
    input  wire              in_valid,
    output wire              in_cr,
    input  wire [FW-1:0]     in_data,
    input  wire              in_last,
    input  wire              in_mode,
    input  wire [TAGW-1:0]   in_tag,
    output wire              tx_valid,
    output wire [PW-1:0]     tx_rec,
    input  wire [N-1:0]      tx_ready,
    input  wire [N-1:0]      cr_in,
    input  wire [N-1:0]      rx_valid,
    input  wire [N*PW-1:0]   rx_rec,
    output wire [N-1:0]      cr_out,
    output wire              out_valid,
    output wire [FW-1:0]     out_data,
    output wire              out_last,
    output wire [RB-1:0]     out_rank,
    output wire              out_err,
    output reg               fault,
    output reg  [2:0]        fault_code,
    input  wire [N-1:0]      self_s
);
    localparam integer DB = (DEPTH > 1) ? $clog2(DEPTH) : 1;
    localparam integer CB = $clog2(DEPTH + 1);
    localparam integer IA = (IB <= 2) ? 1 : $clog2(IB);
    localparam integer DL = (N - 1) * ADD_LAT + ((FSL != 0) ? 2 : 0) + ((CT != 0) ? 1 : 0);   // FSL: + the slice seams; CT: + the tile replica edge
    integer r;
    // ---- PR = 2: per-region reset synchronisers (rst_n reaches only these) ------------------------------------------
    wire          rst_i;                 // control region
    wire [N-1:0]  rst_k;                 // per source: its slice leaves
    wire [N-1:0]  rst_a;                 // per adder stage (index 1..N-1)
    genvar g;
    generate if (PR >= 2) begin : g_rsr
        (* keep_hierarchy *) ot_coll_rst_leaf u_rc (.clk(clk), .arst_n(rst_n), .q(rst_i));
        for (g = 0; g < N; g = g + 1) begin : g_rr
            (* keep_hierarchy *) ot_coll_rst_leaf u_rk (.clk(clk), .arst_n(rst_n), .q(rst_k[g]));
            (* keep_hierarchy *) ot_coll_rst_leaf u_ra (.clk(clk), .arst_n(rst_n), .q(rst_a[g]));
        end
    end else begin : g_rsd
        assign rst_i = rst_n; assign rst_k = {N{rst_n}}; assign rst_a = {N{rst_n}};
    end endgenerate
    // ---- pin registers -------------------------------------------------------------------------------------------
    reg              iv_q;
    reg [PW-1:0]     irec_q;
    reg [N-1:0]      txr_q, cri_q, rxv_q;
    reg [N*PW-1:0]   rxr_q;
    always @(posedge clk) begin irec_q <= {in_tag, in_mode, in_last, in_data}; rxr_q <= rx_rec; end
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin iv_q <= 1'b0; txr_q <= 0; cri_q <= 0; rxv_q <= 0; end
        else begin iv_q <= in_valid; txr_q <= tx_ready; cri_q <= cr_in; rxv_q <= rx_valid; end
    // ---- local input buffer (IB words, credit per word taken) ----------------------------------------------------
    reg [PW-1:0] ib [0:IB-1];
    reg [IA:0]   iw, ir;
    wire ib_empty = (iw == ir);
    wire ib_full  = (iw[IA-1:0] == ir[IA-1:0]) && (iw[IA] != ir[IA]);
    wire [PW-1:0] ib_head;
    always @(posedge clk) if (iv_q && !ib_full) ib[iw[IA-1:0]] <= irec_q;
    // ---- credits and transmit -------------------------------------------------------------------------------------
    localparam [N-1:0] SELF = {{(N-1){1'b0}}, 1'b1} << RANK;
    wire [N-1:0] SF = (RSTRAP != 0) ? self_s : SELF;      // the die's own source (one-hot)
    reg  [CB-1:0] cr [0:N-1];
    reg  [CB:0]   mcnt [0:N-1];          // words in the source FIFO (head register excluded)
    reg  [N-1:0]  hv;                    // head register valid
    reg  [N-1:0]  can_tx;
    reg           lpv;                   // PR: the local word sent last edge, entering its FIFO now
    reg  [PW-1:0] lpq;
    always @(*) for (r = 0; r < N; r = r + 1)
        can_tx[r] = SF[r] ? ((mcnt[r] + hv[r] + ((PR != 0) ? lpv : 1'b0)) < DEPTH) : (cr[r] != 0 && txr_q[r]);
    wire fire = !ib_empty && (&can_tx);
    generate if (IBH != 0) begin : g_ibh
        wire [IA:0] ir_nx = fire ? ir + 1'b1 : ir;
        reg  [PW-1:0] hq;
        always @(posedge clk)
`ifdef OT_ONESHOT_M_IBH_MUTANT
            if (1'b0) hq <= irec_q;                  // negative control: no write bypass of the look-ahead head
`else
            if (iv_q && !ib_full && (iw[IA-1:0] == ir_nx[IA-1:0])) hq <= irec_q;
`endif
            else hq <= ib[ir_nx[IA-1:0]];
        assign ib_head = hq;
    end else begin : g_ibc
        assign ib_head = ib[ir[IA-1:0]];
    end endgenerate
    wire         txv_q, icr_q;
    reg [PW-1:0] txrec_q;
    generate if (PR != 0) begin : g_txr
        always @(posedge clk) begin txrec_q <= ib_head; lpq <= ib_head; end   // tx_rec meaningful only with tx_valid
        if (CT != 0) begin : g_txct
            // CT: tx_rec comes from the column tiles (assigned in g_ct)
        end else if (TXK != 0) begin : g_txk
            // dedicated pin register in a keep_hierarchy leaf: synthesis cannot merge it with lpq
            (* keep_hierarchy *) ot_coll_pinreg #(.W(PW)) u_txk (.clk(clk), .d(ib_head), .q(tx_rec));
        end else begin : g_txm
            assign tx_rec = txrec_q;
        end
        always @(posedge clk or negedge rst_i) if (!rst_i) lpv <= 1'b0; else lpv <= fire;
    end else begin : g_txo
        always @(posedge clk) if (fire) txrec_q <= ib_head;
        assign tx_rec = txrec_q;
        always @(*) begin lpv = 1'b0; lpq = {PW{1'b0}}; end
    end endgenerate
    // tx_valid (tx face) and in_cr (in face) are logically the same register (<= fire), but their pins sit on
    // different faces ~870 um apart: a single merged flop cannot reach both within one 500-um stage.  Each is
    // its own pin register in a keep_hierarchy leaf (synthesis cannot merge them), placed at its own pin.
    (* keep_hierarchy *) ot_coll_pinreg_r u_txv (.clk(clk), .rst_n(rst_i), .d(fire), .q(txv_q));
    (* keep_hierarchy *) ot_coll_pinreg_r u_icr (.clk(clk), .rst_n(rst_i), .d(fire), .q(icr_q));
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin iw <= 0; ir <= 0; end
        else begin
            if (iv_q && !ib_full) iw <= iw + 1'b1;
            if (fire) ir <= ir + 1'b1;
        end
    generate if (CT != 0) begin : g_txvd
        // CT: the tiles' tx word is the engine's tx_rec one edge later; tx_valid follows it (own pin register leaf)
        (* keep_hierarchy *) ot_coll_pinreg_r u_txv2 (.clk(clk), .rst_n(rst_i), .d(txv_q), .q(tx_valid));
    end else begin : g_txvo
        assign tx_valid = txv_q;
    end endgenerate
    assign in_cr = icr_q;
    // ---- receive FIFOs with registered heads ----------------------------------------------------------------------
    reg [PW-1:0] mem [0:N*DEPTH-1];
    reg [DB-1:0] wp [0:N-1];
    reg [DB-1:0] rp [0:N-1];
    reg [PW-1:0] hd [0:N-1];
    wire [N-1:0] push;
    wire [N*PW-1:0] push_rec;
    reg [1:0] m0ml [0:DEPTH-1];          // MEMM: source 0's {mode, last} bits at control timing (the body is a macro)
    wire [1:0] ml0_rec;                  // source 0's {mode, last} at push timing (CT: from the 2-bit replica)
    always @(posedge clk) if (push[0]) m0ml[wp[0]] <= (CT != 0) ? ml0_rec : push_rec[FW +: 2];
    generate for (g = 0; g < N; g = g + 1) begin : g_src
        if (RSTRAP != 0) begin : g_sel
            assign push[g] = SF[g] ? ((PR != 0) ? lpv : fire) : rxv_q[g];
            assign push_rec[g*PW +: PW] = SF[g] ? ((PR != 0) ? lpq : ib_head) : rxr_q[g*PW +: PW];
        end else if (g == RANK) begin : g_loc
            assign push[g] = (PR != 0) ? lpv : fire;
            assign push_rec[g*PW +: PW] = (PR != 0) ? lpq : ib_head;
        end else begin : g_rem
            assign push[g] = rxv_q[g];
            assign push_rec[g*PW +: PW] = rxr_q[g*PW +: PW];
        end
    end endgenerate
    // ---- CT: 2-bit {mode, last} replica of the column datapath for source 0 (the pop decision reads it via m0ml) ----
    generate if (CT != 0) begin : g_mlr
        reg [1:0] irec_ml, hq_ml, lpq_ml, rxr0_ml;
        reg [1:0] ib_ml [0:IB-1];
        wire [IA:0] ir_nxm = fire ? ir + 1'b1 : ir;
        always @(posedge clk) begin
            irec_ml <= {in_mode, in_last};
            rxr0_ml <= rx_rec[FW +: 2];
            if (iv_q && !ib_full) ib_ml[iw[IA-1:0]] <= irec_ml;
            if (iv_q && !ib_full && (iw[IA-1:0] == ir_nxm[IA-1:0])) hq_ml <= irec_ml;
            else hq_ml <= ib_ml[ir_nxm[IA-1:0]];
            lpq_ml <= hq_ml;
        end
        assign ml0_rec = SF[0] ? lpq_ml : rxr0_ml;
    end else begin : g_mlo
        assign ml0_rec = push_rec[FW +: 2];
    end endgenerate
    // ---- pop: a word index leaves every head at once ----------------------------------------------------------------
    reg          g_busy;
    reg  [RB-1:0] g_cnt;
    reg  [15:0]  inflight;
    reg          s0_v, s0_mode, s0_last;
    reg  [FW-1:0] s0_d [0:N-1];
    wire [N*PW-1:0] hdf;                 // the head words (PR: assembled from the slice registers)
    reg  [1:0] hb_c;                     // PR = 2: source 0's head {mode, last} at control timing
    wire hmode = (PR >= 2) ? hb_c[1] : hdf[FW + 1];
    wire hlast = (PR >= 2) ? hb_c[0] : hdf[FW];
    wire all_hv = &hv;
    wire pop_red = all_hv && !g_busy && !(s0_v && s0_mode) && !hmode;
    wire pop_gat = all_hv && !g_busy && hmode && inflight == 16'd0 && !s0_v;
    wire pop = pop_red || pop_gat;
    reg [N-1:0] refill;
    always @(*) for (r = 0; r < N; r = r + 1) refill[r] = (mcnt[r] != 0) && (!hv[r] || pop);
    reg cro_q;
    always @(posedge clk or negedge rst_i) if (!rst_i) cro_q <= 1'b0; else cro_q <= pop;
    generate for (g = 0; g < N; g = g + 1) begin : g_cr
        assign cr_out[g] = SF[g] ? 1'b0 : cro_q;
    end endgenerate
    always @(posedge clk or negedge rst_i) begin
        if (!rst_i) begin
            for (r = 0; r < N; r = r + 1) begin cr[r] <= DEPTH; mcnt[r] <= 0; wp[r] <= 0; rp[r] <= 0; end
            hv <= 0;
        end else begin
            for (r = 0; r < N; r = r + 1) begin
                if (!SF[r]) cr[r] <= cr[r] - (fire ? 1'b1 : 1'b0) + (cri_q[r] ? 1'b1 : 1'b0);
                if (push[r]) begin
                    if (MEMM == 0) mem[r*DEPTH + wp[r]] <= push_rec[r*PW +: PW];
                    wp[r] <= wp[r] + 1'b1;
                end
                if (refill[r]) begin
                    if (PR == 0) hd[r] <= mem[r*DEPTH + rp[r]];
                    rp[r] <= rp[r] + 1'b1;
                end
                hv[r] <= refill[r] ? 1'b1 : (pop ? 1'b0 : hv[r]);
                mcnt[r] <= mcnt[r] + (push[r] ? 1'b1 : 1'b0) - (refill[r] ? 1'b1 : 1'b0);
            end
        end
    end
    // ---- head stage ----------------------------------------------------------------------------------------------------
    always @(posedge clk or negedge rst_i) begin
        if (!rst_i) begin s0_v <= 1'b0; s0_mode <= 1'b0; s0_last <= 1'b0; end
        else begin
            s0_v <= pop;
            if (pop) begin s0_mode <= hmode; s0_last <= hlast; end
        end
    end
    always @(posedge clk) if (refill[0]) hb_c <= (MEMM != 0) ? m0ml[rp[0]] : mem[rp[0]][FW +: 2];
    // PR = 2: the s0 registers are written one edge after the pop; s0_vl / s0_ml / s0_ll re-time their consumers
    reg s0_vl, s0_ml, s0_ll;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin s0_vl <= 1'b0; s0_ml <= 1'b0; s0_ll <= 1'b0; end
        else begin s0_vl <= s0_v; s0_ml <= s0_mode; s0_ll <= s0_last; end
    wire s0_vc = (PR >= 2) ? s0_vl : s0_v;           // consumer-timed s0 valid / mode / last
    wire s0_mc = (PR >= 2) ? s0_ml : s0_mode;
    wire s0_lc = (PR >= 2) ? s0_ll : s0_last;
    reg [TAGW:0] s0_t [0:N-1];
    generate if (PR == 0) begin : g_s0o
        for (g = 0; g < N; g = g + 1) begin : g_hdf
            assign hdf[g*PW +: PW] = hd[g];
        end
        always @(posedge clk) if (pop) for (r = 0; r < N; r = r + 1) begin
            s0_d[r] <= hd[r][FW-1:0];
            s0_t[r] <= hd[r][PW-1 -: TAGW + 1];
        end
    end endgenerate
    reg agree;
    always @(*) begin
        agree = 1'b1;
        for (r = 1; r < N; r = r + 1) if (s0_t[r] != s0_t[0]) agree = 1'b0;
    end
    // ---- all-reduce: ((p0 + p1) + p2) + ... in rank order ----------------------------------------------------------
    wire red_in = s0_vc && !s0_mc;
    wire [FW-1:0] sum  [0:N-1];
    wire [N-1:0]  sv;
    wire [N-1:0]  serr;
    // OT_ONESHOT_M_MUTANT (negative control only): ranks 1 and 2 swap places in the fold, ((p0 + p2) + p1) + p3
    wire [FW-1:0] fsrc [0:N-1];
    generate for (g = 0; g < N; g = g + 1) begin : g_fsrc
`ifdef OT_ONESHOT_M_MUTANT
        assign fsrc[g] = (g == 1 && N > 2) ? s0_d[2] : (g == 2) ? s0_d[1] : s0_d[g];
`else
        assign fsrc[g] = s0_d[g];
`endif
    end endgenerate
    assign sum[0] = fsrc[0];
    assign sv[0] = red_in;
    assign serr[0] = 1'b0;
    generate if (FSL != 0) begin : g_fsl
        initial if (OPQ != 0 || FW % 128 != 0) $error("ot_rom_oneshot_die_m FSL: OPQ 0 and FW a multiple of 128");
        initial if (N != 4 || ADD_LAT != 7) $error("ot_rom_oneshot_die_m FSL: the hardened ot_coll_fold_slice is N 4, ADD_LAT 7");
        localparam integer NS = FW / 128;
        wire [NS-1:0] sl_v, sl_e;
        wire red_in_f;                   // CT: the tiles' s0 operands are one edge late; so is the fold's valid
        if (CT != 0) begin : g_rid
            reg rq;
            always @(posedge clk or negedge rst_i) if (!rst_i) rq <= 1'b0; else rq <= red_in;
            assign red_in_f = rq;
        end else begin : g_rin
            assign red_in_f = red_in;
        end
        wire [FW-1:0] fsum;
        wire [N*FW-1:0] fsrc_f;
        genvar gs, gq;
        for (gq = 0; gq < N; gq = gq + 1) begin : g_ff
            assign fsrc_f[gq*FW +: FW] = fsrc[gq];
        end
        for (gs = 0; gs < NS; gs = gs + 1) begin : g_sl
            wire [N*128-1:0] sd;
            for (gq = 0; gq < N; gq = gq + 1) begin : g_sd
                assign sd[gq*128 +: 128] = fsrc_f[gq*FW + gs*128 +: 128];
            end
            (* keep_hierarchy *) ot_coll_fold_slice u_fs (   // hardened defaults N 4 / ADD_LAT 7 / SEAM 1 (no override: the
                                                           // parent takes the hardened macro master by name)
                .clk(CCLK ? clk_folds[gs] : clk), .rst_n(rst_n), .red_in(red_in_f), .src(sd), .sum(fsum[gs*128 +: 128]),
                .v_out(sl_v[gs]), .e_out(sl_e[gs]));
        end
        assign sum[N-1] = fsum;
        assign sv[N-1] = sl_v[0];
        assign serr[N-1] = |sl_e;
    end else begin : g_flat
        for (g = 1; g < N; g = g + 1) begin : g_stage
            wire [FW-1:0] pg;
            if (g == 1) begin : g_nd
                assign pg = fsrc[1];
            end else if (OPQ != 0) begin : g_q
                localparam integer D  = (g - 1) * ADD_LAT;
                localparam integer QA = $clog2(D + 1);
                localparam integer SW = (FW >= 128) ? 128 : FW;
                genvar k;
                for (k = 0; k < FW / SW; k = k + 1) begin : g_s
                    (* keep_hierarchy *) ot_coll_opq_slice #(.W(SW), .QA(QA)) u_q (
                        .clk(clk), .arst_n(rst_a[g]), .push(red_in), .d(fsrc[g][SW*k +: SW]),
                        .pop(sv[g-1]), .q(pg[SW*k +: SW]));
                end
            end else begin : g_d
                localparam integer D = (g - 1) * ADD_LAT;
                reg [FW*D-1:0] dl;
                always @(posedge clk) dl <= {dl[FW*(D-1)-1:0], fsrc[g]};
                assign pg = dl[FW*D-1 -: FW];
            end
            reg [ADD_LAT-1:0] edl;
            always @(posedge clk or negedge rst_a[g])
                if (!rst_a[g]) edl <= 0;
                else edl <= {edl[ADD_LAT-2:0], serr[g-1]};
            wire [LANES-1:0] lv;
            wire [2*LANES-1:0] le;
            genvar l;
            for (l = 0; l < LANES; l = l + 1) begin : g_lane
                ot_hdc_fp32_add_lat #(.LAT(ADD_LAT)) u_add (
                    .clk(clk), .rst_n(rst_a[g]), .valid_in(sv[g-1]),
                    .a(sum[g-1][32*l +: 32]), .b(pg[32*l +: 32]),
                    .y(sum[g][32*l +: 32]), .err(le[2*l +: 2]), .valid_out(lv[l]));
            end
            assign sv[g] = lv[0];
            assign serr[g] = (|le) || edl[ADD_LAT-1];
        end
    end endgenerate
    reg [DL-1:0] ldl;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) ldl <= 0;
        else ldl <= {ldl[DL-2:0], s0_lc};
    wire red_out = sv[N-1];
    // ---- all-gather --------------------------------------------------------------------------------------------------
    reg          go_v, go_last;
    reg [FW-1:0] go_d;
    wire [FW-1:0] ct_go;                 // CT: the column tiles' gather word
    reg [RB-1:0] go_rank;
    reg          gc_v, gc_last;          // control-timed gather selection (PR = 2 reads s0_d one edge later)
    reg [RB-1:0] gc_idx;
    always @(posedge clk or negedge rst_i) begin
        if (!rst_i) begin
            g_busy <= 1'b0; g_cnt <= 0; gc_v <= 1'b0; gc_last <= 1'b0; gc_idx <= 0; inflight <= 0;
        end else begin
            gc_v <= 1'b0;
            if (s0_v && s0_mode) begin g_busy <= 1'b1; g_cnt <= 0; end
            if (g_busy || (s0_v && s0_mode)) begin
                gc_v <= 1'b1;
                gc_idx <= g_busy ? g_cnt : 0;
                gc_last <= s0_last && (g_busy ? g_cnt : 0) == N - 1;
                if (g_busy) begin
                    g_cnt <= g_cnt + 1'b1;
                    if (g_cnt == N - 1) g_busy <= 1'b0;
                end else begin
                    g_cnt <= 1;
                    if (N == 1) g_busy <= 1'b0;
                end
            end
            inflight <= inflight + (pop_red ? 1'b1 : 1'b0) - (red_out ? 1'b1 : 1'b0);
        end
    end
    generate if (PR >= 2) begin : g_go2
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin go_v <= 1'b0; go_last <= 1'b0; go_rank <= 0; end
            else begin go_v <= gc_v; go_last <= gc_last; go_rank <= gc_idx; end
        if (CT == 0) begin : g_god
            always @(posedge clk) go_d <= s0_d[gc_idx];
        end
    end else begin : g_go1
        // original timing: the selection and the data in the same edge
        reg [RB-1:0] gi;
        always @(*) gi = g_busy ? g_cnt : 0;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin go_v <= 1'b0; go_last <= 1'b0; go_rank <= 0; end
            else begin
                go_v <= 1'b0;
                if (g_busy || (s0_v && s0_mode)) begin
                    go_v <= 1'b1; go_d <= s0_d[gi]; go_rank <= gi; go_last <= s0_last && gi == N - 1;
                end
            end
    end endgenerate
    // ---- registered outputs --------------------------------------------------------------------------------------------
    reg          ov_q, ol_q, oe_q;
    reg [FW-1:0] od_q;
    reg [RB-1:0] ork_q;
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin ov_q <= 1'b0; oe_q <= 1'b0; end
        else begin ov_q <= red_out || gov_m; oe_q <= red_out && serr[N-1]; end
    // CT: the tiles' gather word (ct_go) is the engine's go_d one edge later; go_v / go_last / go_rank follow it
    wire          gov_m, gol_m;
    wire [FW-1:0] god_m;
    wire [RB-1:0] gor_m;
    generate if (CT != 0) begin : g_god2
        reg gv2, gl2; reg [RB-1:0] gr2;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin gv2 <= 1'b0; gl2 <= 1'b0; gr2 <= 0; end
            else begin gv2 <= go_v; gl2 <= go_last; gr2 <= go_rank; end
        assign gov_m = gv2; assign gol_m = gl2; assign gor_m = gr2; assign god_m = ct_go;
    end else begin : g_god1
        assign gov_m = go_v; assign gol_m = go_last; assign gor_m = go_rank; assign god_m = go_d;
    end endgenerate
    always @(posedge clk) begin
        od_q <= gov_m ? god_m : sum[N-1];
        ol_q <= gov_m ? gol_m : ldl[DL-1];
        ork_q <= gov_m ? gor_m : {RB{1'b0}};
    end
    ot_hdly #(.W(FW + RB + 3), .N(HDLO)) u_hdly_out (.a({ov_q, od_q, ol_q, ork_q, oe_q}),
        .y({out_valid, out_data, out_last, out_rank, out_err}));
    // ---- faults ------------------------------------------------------------------------------------------------------
    reg ovf;
    always @(*) begin
        ovf = iv_q && ib_full;                                   // the sender ignored its credits
        for (r = 0; r < N; r = r + 1) if (mcnt[r] > DEPTH) ovf = 1'b1;
    end
    reg txv_d, txbad;     // a send while a link said no (link-layer violation), judged from the pin registers
    always @(posedge clk or negedge rst_i)
        if (!rst_i) begin txv_d <= 1'b0; txbad <= 1'b0; end
        else begin txv_d <= txv_q; txbad <= txv_d && !(&(txr_q | SF)); end
    wire rerr_f;
    generate if (FPIPE != 0) begin : g_fp
        reg rerr_q;
        always @(posedge clk or negedge rst_i) if (!rst_i) rerr_q <= 1'b0; else rerr_q <= red_out && serr[N-1];
        assign rerr_f = rerr_q;
    end else begin : g_fc
        assign rerr_f = red_out && serr[N-1];
    end endgenerate
    wire agree_f, ovf_f;
    reg  s0_vcd;                         // CT: the tag column's s0 tags are one edge late
    always @(posedge clk or negedge rst_i) if (!rst_i) s0_vcd <= 1'b0; else s0_vcd <= s0_vc;
    wire s0_vt = (CT != 0) ? s0_vcd : s0_vc;
    generate if (FPIPE >= 2) begin : g_fp2
        reg agq, ovq;
        always @(posedge clk or negedge rst_i)
            if (!rst_i) begin agq <= 1'b0; ovq <= 1'b0; end else begin agq <= s0_vt && !agree; ovq <= ovf; end
        assign agree_f = agq; assign ovf_f = ovq;
    end else begin : g_fc2
        assign agree_f = s0_vt && !agree; assign ovf_f = ovf;
    end endgenerate
    always @(posedge clk or negedge rst_i) begin
        if (!rst_i) begin fault <= 1'b0; fault_code <= 3'b0; end
        else begin
            if (rerr_f) begin fault <= 1'b1; fault_code[0] <= 1'b1; end
            if (agree_f) begin fault <= 1'b1; fault_code[1] <= 1'b1; end
            if (ovf_f || txbad) begin fault <= 1'b1; fault_code[2] <= 1'b1; end
        end
    end
    // ---- PR: replicated pop -------------------------------------------------------------------------------------------
    generate if (PR == 1) begin : g_s0r
        reg  [N-1:0] hv_n, mnz_n;
        reg          gb_n, hm_n, iz_n;
        reg  [DB-1:0] rp_n [0:N-1];
        reg  [15:0]  inflight_n;
        always @(*) begin
            for (r = 0; r < N; r = r + 1) begin
                hv_n[r] = refill[r] ? 1'b1 : (pop ? 1'b0 : hv[r]);
                mnz_n[r] = (mcnt[r] + (push[r] ? 1'b1 : 1'b0) - (refill[r] ? 1'b1 : 1'b0)) != 0;
                rp_n[r] = rp[r] + (refill[r] ? 1'b1 : 1'b0);
            end
            gb_n = g_busy ? (g_cnt != N - 1) : ((s0_v && s0_mode) ? (N != 1) : 1'b0);
            hm_n = refill[0] ? mem[rp[0]][FW + 1] : hdf[FW + 1];
            inflight_n = inflight + (pop_red ? 1'b1 : 1'b0) - (red_out ? 1'b1 : 1'b0);
            iz_n = (inflight_n == 16'd0);
        end
        localparam integer SLW = 128, NSL = (PW + SLW - 1) / SLW;
        wire [N*PW-1:0] s0f;
        genvar gr, gk;
        for (gr = 0; gr < N; gr = gr + 1) begin : g_r
            for (gk = 0; gk < NSL; gk = gk + 1) begin : g_k
                localparam integer LO = gk * SLW;
                localparam integer SW = (PW - LO < SLW) ? (PW - LO) : SLW;
                (* keep *) reg [N-1:0] hvc;
                (* keep *) reg gbc, s0vc, s0mc, hmc, izc, mnzc;
                (* keep *) reg [DB-1:0] rpc;
                reg [SW-1:0] hdk, s0k;
                always @(posedge clk or negedge rst_i)
                    if (!rst_i) begin hvc <= 0; gbc <= 1'b0; s0vc <= 1'b0; s0mc <= 1'b0; hmc <= 1'b0; izc <= 1'b1;
                                      mnzc <= 1'b0; rpc <= 0; end
                    else begin hvc <= hv_n; gbc <= gb_n; s0vc <= pop; s0mc <= pop ? hmode : s0_mode; hmc <= hm_n;
                               izc <= iz_n; mnzc <= mnz_n[gr]; rpc <= rp_n[gr]; end
                wire popk = (&hvc) && !gbc && ((!(s0vc && s0mc) && !hmc) || (hmc && izc && !s0vc));
                wire refk = mnzc && (!hvc[gr] || popk);
                wire [PW-1:0] mrow = mem[gr*DEPTH + rpc];
                always @(posedge clk) begin
                    if (refk) hdk <= mrow[LO +: SW];
                    if (popk) s0k <= hdk;
                end
                assign hdf[gr*PW + LO +: SW] = hdk;
                assign s0f[gr*PW + LO +: SW] = s0k;
            end
        end
        always @(*) for (r = 0; r < N; r = r + 1) begin
            s0_d[r] = s0f[r*PW +: FW];
            s0_t[r] = s0f[r*PW + PW - 1 -: TAGW + 1];
        end
    end else if (PR >= 2) begin : g_s0r2
        // ---- PR = 2: 2-level registered fanout tree (keep_hierarchy leaves) ------------------------------------------
        initial if (N > 4 || DB > 6) $error("ot_rom_oneshot_die_m PR=2: N <= 4 and DEPTH <= 64 (fixed-width leaves)");
        initial if (MEMM != 0 && OPQ != 0) $error("ot_rom_oneshot_die_m MEMM: not combined with OPQ");
        reg  [N-1:0] hv_n, mnz_n;
        reg          gb_n, hm_n, iz_n;
        reg  [DB-1:0] rp_n [0:N-1];
        reg  [15:0]  inflight_n;
        always @(*) begin
            for (r = 0; r < N; r = r + 1) begin
                hv_n[r] = refill[r] ? 1'b1 : (pop ? 1'b0 : hv[r]);
                mnz_n[r] = (mcnt[r] + (push[r] ? 1'b1 : 1'b0) - (refill[r] ? 1'b1 : 1'b0)) != 0;
                rp_n[r] = rp[r] + (refill[r] ? 1'b1 : 1'b0);
            end
            gb_n = g_busy ? (g_cnt != N - 1) : ((s0_v && s0_mode) ? (N != 1) : 1'b0);
            hm_n = refill[0] ? ((MEMM != 0) ? m0ml[rp[0]][1] : mem[rp[0]][FW + 1]) : hb_c[1];
            inflight_n = inflight + (pop_red ? 1'b1 : 1'b0) - (red_out ? 1'b1 : 1'b0);
            iz_n = (inflight_n == 16'd0);
        end
        localparam integer SLW = 128, NSL = (PW + SLW - 1) / SLW;
        wire [N*PW-1:0] s0f;
        wire [N*16-1:0] l1all;           // CT: every source's level-1 image, to the column tiles
        genvar gr, gk;
        for (gr = 0; gr < N; gr = gr + 1) begin : g_r
            // level 1 (per source): the decision state, registered from its next state (same timing as hv)
            wire [15:0] l1d, l1q;
            wire [3:0]  hv4 = hv_n;
            wire [5:0]  rp6 = rp_n[gr];
            assign l1d = {hv4, gb_n, pop, (pop ? hmode : s0_mode), hm_n, !iz_n, mnz_n[gr], rp6};
            (* keep_hierarchy *) ot_coll_dup16 u_l1 (.clk(clk), .arst_n(rst_k[gr]), .d(l1d), .q(l1q));
            assign l1all[gr*16 +: 16] = l1q;
            wire [N-1:0] hvc = l1q[12 +: N];
            wire gbc = l1q[11], s0vc = l1q[10], s0mc = l1q[9], hmc = l1q[8], izc = !l1q[7], mnzc = l1q[6];
            wire [DB-1:0] rpc = l1q[DB-1:0];
            wire popk = (&hvc) && !gbc && ((!(s0vc && s0mc) && !hmc) || (hmc && izc && !s0vc));
            wire refk = mnzc && (!hvc[gr] || popk);
            wire [7:0] l2d = {popk, refk, l1q[5:0]};
            wire [PW-1:0] mrow_m;                         // MEMM: this source's FIFO body macro, read at level-1 timing
            if (CT != 0) begin : g_mct
                // CT: the FIFO bodies, heads and s0 operands live in the column tiles (g_ct below)
                assign mrow_m = {PW{1'b0}};
                assign hdf[gr*PW +: PW] = {PW{1'b0}};
            end else if (MEMM != 0) begin : g_mm
                initial if (DEPTH != 32 || PW != 546) $error("ot_rom_oneshot_die_m MEMM: macro is 32 x 546");
`ifdef OT_ONESHOT_M_MEMM_MUTANT
                wire [DB-1:0] mra = rpc + 1'b1;           // negative control: the macro reads the next slot
`else
                wire [DB-1:0] mra = rpc;
`endif
                ot_sram_1r1w_32x546_m1 u_m (.clk(clk), .r_ce_in(refk), .r_addr_in(mra), .rd_out(mrow_m),
                    .w_ce_in(push[gr]), .w_addr_in(wp[gr]), .wd_in(push_rec[gr*PW +: PW]), .w_mask_in({PW{1'b1}}));
            end else begin : g_mf
                assign mrow_m = {PW{1'b0}};
            end
            if (CT == 0) for (gk = 0; gk < NSL; gk = gk + 1) begin : g_k
                localparam integer LO = gk * SLW;
                localparam integer SW = (PW - LO < SLW) ? (PW - LO) : SLW;
                // level 2 (per source, slice): {pop, refill, read index} one edge later
                wire [7:0] l2q;
                (* keep_hierarchy *) ot_coll_dup8 u_l2 (.clk(clk), .arst_n(rst_k[gr]), .d(l2d), .q(l2q));
                wire popq = l2q[7], refq = l2q[6];
                wire [DB-1:0] rpq = l2q[DB-1:0];
                reg [SW-1:0] hdk, s0k;
                wire [PW-1:0] mrow = (MEMM != 0) ? mrow_m : mem[gr*DEPTH + rpq];
                always @(posedge clk) begin
                    if (refq) hdk <= mrow[LO +: SW];
                    if (popq) s0k <= hdk;
                end
                assign hdf[gr*PW + LO +: SW] = hdk;
                assign s0f[gr*PW + LO +: SW] = s0k;
            end
        end
        if (CT != 0) begin : g_ct
            initial if (N != 4 || (DEPTH != 32 && DEPTH != 64) || IB != 4 || FW != 512 || PW != 546 || MEMM == 0 || FSL == 0 || IBH == 0 || TXK == 0)
                $error("ot_rom_oneshot_die_m CT: N 4, DEPTH 32 | 64 (ot_coll_col_tile_d64), IB 4, LANES 16, TAGW 32, MEMM 1, FSL 1, IBH 1, TXK 1");
            localparam integer WB = (DEPTH == 64) ? 6 : 5;
            localparam integer NC = (PW + 127) / 128;   // 5 columns: 4 data + 1 {tag, mode, last}
            wire [PW-1:0] inrec = {in_tag, in_mode, in_last, in_data};
            wire [N*WB-1:0] wpall;
            for (gr = 0; gr < N; gr = gr + 1) begin : g_wp
                assign wpall[gr*WB +: WB] = wp[gr];
            end
            for (gk = 0; gk < NC; gk = gk + 1) begin : g_c
                localparam integer LO = gk * 128;
                localparam integer SW = (PW - LO < 128) ? (PW - LO) : 128;
                wire [127:0] ind;
                wire [511:0] rxd, s0o;
                wire [127:0] goo, txo;
                if (SW < 128) begin : g_pad
                    assign ind = {{(128 - SW){1'b0}}, inrec[LO +: SW]};
                end else begin : g_full
                    assign ind = inrec[LO +: 128];
                end
                for (gr = 0; gr < N; gr = gr + 1) begin : g_x
                    if (SW < 128) begin : g_px
                        assign rxd[gr*128 +: 128] = {{(128 - SW){1'b0}}, rx_rec[gr*PW + LO +: SW]};
                    end else begin : g_fx
                        assign rxd[gr*128 +: 128] = rx_rec[gr*PW + LO +: 128];
                    end
                    assign s0f[gr*PW + LO +: SW] = s0o[gr*128 +: SW];
                end
                if (DEPTH == 64) begin : g_d64
                (* keep_hierarchy *) ot_coll_col_tile_d64 u_ct (.clk(CCLK ? clk_cols[gk] : clk), .rst_n(rst_n), .rank_oh(SF),
                    .in_d(ind), .rx_d(rxd), .c_ibw(iv_q && !ib_full), .c_iw(iw[1:0]), .c_fire(fire), .c_ir(ir[1:0]),
                    .c_push(push), .c_wp(wpall), .c_l1(l1all), .c_gidx(gc_idx), .s0(s0o), .go(goo), .tx(txo));
                end else begin : g_d32
                (* keep_hierarchy *) ot_coll_col_tile u_ct (.clk(CCLK ? clk_cols[gk] : clk), .rst_n(rst_n), .rank_oh(SF),
                    .in_d(ind), .rx_d(rxd), .c_ibw(iv_q && !ib_full), .c_iw(iw[1:0]), .c_fire(fire), .c_ir(ir[1:0]),
                    .c_push(push), .c_wp(wpall), .c_l1(l1all), .c_gidx(gc_idx), .s0(s0o), .go(goo), .tx(txo));
                end
                assign tx_rec[LO +: SW] = txo[SW-1:0];
                if (gk < FW / 128) begin : g_go
                    assign ct_go[LO +: 128] = goo;
                end
            end
        end
        always @(*) for (r = 0; r < N; r = r + 1) begin
            s0_d[r] = s0f[r*PW +: FW];
            s0_t[r] = s0f[r*PW + PW - 1 -: TAGW + 1];
        end
    end endgenerate
    generate if (CT == 0) begin : g_nct
        assign ct_go = {FW{1'b0}};
    end endgenerate
endmodule

// PR = 2 leaves: fixed widths and no parameters (Yosys 0.68 asserts re-elaborating a parameterised keep_hierarchy
// module), instantiated with keep_hierarchy so synthesis keeps every copy.
// OPQ operand queue slice (see OPQ above): in-order, written on push, read combinationally at the read pointer and
// advanced on pop; 2^QA entries > the stage's D outstanding operands, so the write never meets the unread head.
module ot_coll_opq_slice #(parameter integer W = 128, parameter integer QA = 3) (
    input wire clk, input wire arst_n, input wire push, input wire [W-1:0] d, input wire pop, output wire [W-1:0] q);
    reg [QA-1:0] wp, rp;
    reg [W-1:0]  mem [0:(1 << QA) - 1];
    always @(posedge clk or negedge arst_n)
        if (!arst_n) begin wp <= 0; rp <= 0; end
        else begin if (push) wp <= wp + 1'b1; if (pop) rp <= rp + 1'b1; end
    always @(posedge clk) if (push) mem[wp] <= d;
`ifdef OT_ONESHOT_M_OPQ_MUTANT
    wire [QA-1:0] rq = rp + 1'b1;          // negative control only: reads the operand one word ahead
    assign q = mem[rq];
`else
    assign q = mem[rp];
`endif
endmodule
module ot_coll_dup16 (input wire clk, input wire arst_n, input wire [15:0] d, output reg [15:0] q);
    always @(posedge clk or negedge arst_n) if (!arst_n) q <= 16'd0; else q <= d;
endmodule
module ot_coll_dup8 (input wire clk, input wire arst_n, input wire [7:0] d, output reg [7:0] q);
    always @(posedge clk or negedge arst_n) if (!arst_n) q <= 8'd0; else q <= d;
endmodule
// el1011-q-coll 2026-10-11: enable-free pin register leaf (TXK): kept as its own hierarchy so it is never merged with an
// identical interior register and the pin-anchoring hook can place it at its port.
module ot_coll_pinreg #(parameter integer W = 1) (input wire clk, input wire [W-1:0] d, output reg [W-1:0] q);
    always @(posedge clk) q <= d;
endmodule
// single-bit control pin register with async reset (kept as its own leaf so it is never merged with a twin)
module ot_coll_pinreg_r (input wire clk, input wire rst_n, input wire d, output reg q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 1'b0; else q <= d;
endmodule
