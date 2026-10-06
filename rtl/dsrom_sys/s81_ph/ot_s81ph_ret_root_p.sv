`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_ret_root_p -- PIPELINED S81 region root (CLAUDE S81-PH gather, 2026-10-06).
//
// Same function as the W10 ot_v41_ret_root (rtl/v41rom/ot_v41_ret.sv; D-entry pairing buffer, QD-entry input queue,
// FP32 sibling adds, complete rows out) restructured for 1.2 GHz with margin.  The W10 root decides every candidate in
// ONE cycle (queue head mux -> norm -> D sibling compares -> priority chain -> parent / buffer update): root_m1
// -4.36 ns.  Measured on the way here (tile_m1 post-place, route SDC): two norm iterations per stage -388 ps, the
// prefix-OR priority decision loop -308 ps, D tag compares at S1 -249 ps, queue write gated by the pop -174 ps.
//   P   input: norm(i_t), ONE of norm's 5 iterations per registered stage (norm is idempotent: the W10 root applies it
//       at the queue head instead; same tag).  The parent tag is normalised the same way in the adder's delay line.
//   Q   input queue = QD-entry flop memory (every input word is written; a full queue is a fault) + registered head
//       (kept copies); the head mux is pointer-addressed only
//   S1  candidate = adder result (priority, as W10) else queue head (NC kept copies).  The buffer keeps, per slot,
//       the KEY of its partial = the tag its sibling must carry ({row, pos, lo ^ 2^k, k, nseg}), so a sibling test is
//       one 32-bit equality.  Match m = valid & key == candidate (a slot inserted by the previous decision is
//       compared through its pending write register); forward flag sp = key(previous candidate) == candidate.
//   S2  decision from registers only: hit = sp & previous inserted ? that slot : m (one-hot); free slot F = a
//       register (lowest free slot of the previous cycle's state, minus the slot it inserted).  Add (remove hit),
//       insert (at F), complete (row out) or fault (no free slot).  Valid bits update here; key/data one cycle later.
//   S3  add operands: one-hot AND-OR read of the hit slot's data, left = lower lo (W10 rule), parent tag (depends
//       only on the candidate: siblings differ in lo bit k), error OR.
//   ADD ot_fp32_add_rne_deep (SPLIT 7, bit-identical to the qualified ot_fp32_add_rne_pipe, LAT 8); tag and valid on a
//       local delay line (norm iterations in stages 0..4, last stage replicated: kept copies drive the S1 compares).
// Arithmetic and pairing are the W10 ones (siblings are unique; IEEE add commutes bit for bit): every row's value is
// identical, rows of a root may leave in another order.  Deviations, all in malformed streams only (a duplicate
// partial tag: two buffer entries or two candidates siblings of the same partial): W10 pairs with the lowest slot,
// this root raises fault (fail closed; checked one cycle later off the decision loop).  A slot freed by an add
// becomes allocatable one cycle later (W10: at once), so "buffer full" can fault one cycle early at D - 1 entries.
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_ret_root_p #(
    parameter integer D  = 128,
    parameter integer QD = 128,
    parameter integer NC = 16                // kept candidate / write-key copies (each serves D/NC slots)
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [31:0] i_t,
    input  wire [31:0] i_d,
    input  wire        i_e,
    output reg         r_v,
    output reg  [15:0] r_row,
    output reg  [2:0]  r_pos,
    output reg  [31:0] r_fp32,
    output reg  [15:0] r_bf16,
    output reg         r_e,
    output reg         fault
);
    // ot_v41_ret_pkg functions, local (yosys-native synthesis keeps the generator's [0:0] port names)
    function automatic complete(input [31:0] t);
        complete = t[12:8] == 5'd0 && (6'd1 << t[7:5]) >= {1'b0, t[4:0]};
    endfunction
    // sibling(a, b) of ot_v41_ret_pkg  <=>  key(a) == b
    function automatic [31:0] key(input [31:0] a);
        key = {a[31:13], a[12:8] ^ (5'd1 << a[7:5]), a[7:5], a[4:0]};
    endfunction
    // one iteration of ot_v41_ret_pkg::norm (which is exactly 5 of these in sequence)
    function automatic [31:0] norm_step(input [31:0] t);
        reg [18:0] row; reg [4:0] lo, n; reg [2:0] kk;
        begin
            {row, lo, kk, n} = t;
            if (!(lo == 5'd0 && (6'd1 << kk) >= {1'b0, n}) && lo[kk] == 1'b0 && ({1'b0, lo} + (6'd1 << kk)) >= {1'b0, n})
                kk = kk + 3'd1;
            norm_step = {row, lo, kk, n};
        end
    endfunction
    function automatic [D-1:0] lowest(input [D-1:0] x);   // lowest set bit, prefix-OR
        reg [D-1:0] p; integer s, j;
        begin
            p = x;
            for (s = 1; s < D; s = s * 2)
                for (j = D - 1; j >= s; j = j - 1) p[j] = p[j] | p[j - s];
            lowest = x & ~{p[D-2:0], 1'b0};
        end
    endfunction
    localparam integer QW = $clog2(QD);
    localparam integer LAT = 8;              // ot_fp32_add_rne_deep SPLIT 3'b111
    localparam integer SG = D / NC;          // slots per copy
    localparam integer NP = 5;               // input norm stages
    integer k, c;

    // ------------------------------------------------------------ P: normalised input (one norm iteration a stage)
    reg [NP-1:0] p_v; reg [31:0] p_t [0:NP-1]; reg [31:0] p_d [0:NP-1]; reg [NP-1:0] p_e;
    always @(posedge clk or negedge rst_n) if (!rst_n) p_v <= {NP{1'b0}}; else p_v <= {p_v[NP-2:0], i_v};
    always @(posedge clk) begin
        p_t[0] <= norm_step(i_t); p_d[0] <= i_d; p_e[0] <= i_e;
        for (c = 1; c < NP; c = c + 1) begin p_t[c] <= norm_step(p_t[c-1]); p_d[c] <= p_d[c-1]; p_e[c] <= p_e[c-1]; end
    end
    wire n_v = p_v[NP-1]; wire [31:0] n_t = p_t[NP-1], n_d = p_d[NP-1]; wire n_e = p_e[NP-1];

    // ------------------------------------------------------------ adder return (tag / valid delay line)
    reg [LAT-2:0] dv;
    reg [33*(LAT-1)-1:0] dtg;
    (* keep *) reg [NC-1:0] sv_c;
    (* keep *) reg [31:0] st_c [0:NC-1];
    reg st_e;
    reg sv;
    wire [31:0] sum; wire [1:0] err; wire sv_add;
    reg add; reg [31:0] add_a, add_b; reg [32:0] tag_in;

    // ------------------------------------------------------------ queue: memory + registered head
    localparam integer NQ = 5;
    reg [64:0] qm [0:QD-1];                  // {e, d32, t32}
    reg [QW-1:0] qw;
    (* keep *) reg [QW-1:0] qr_c [0:NQ-1];
    reg [QW:0] mc;
    reg hv; reg [31:0] h_d; reg h_e;
    (* keep *) reg [31:0] h_t_c [0:NC-1];
    wire pop = hv && !sv;                    // W10: use_q = !sv && queue not empty
    wire take = !hv || pop;
    wire from_mem = take && mc != 0;
    wire q_full = mc == QD;
    wire wr_mem = n_v && !q_full;            // every word goes through the memory (no pop-dependent bypass)
    reg [64:0] mw;
    always @* for (c = 0; c < NQ; c = c + 1) mw[13*c +: 13] = qm[qr_c[c]][13*c +: 13];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            qw <= 0; mc <= 0; hv <= 1'b0;
            for (c = 0; c < NQ; c = c + 1) qr_c[c] <= 0;
        end else begin
            if (wr_mem) qw <= qw + 1'b1;
            if (from_mem) for (c = 0; c < NQ; c = c + 1) qr_c[c] <= qr_c[c] + 1'b1;
            mc <= mc + (wr_mem ? 1'b1 : 1'b0) - (from_mem ? 1'b1 : 1'b0);
            if (take) hv <= from_mem;
        end
    always @(posedge clk) begin
        if (wr_mem) qm[qw] <= {n_e, n_d, n_t};
        if (from_mem) begin
            for (c = 0; c < NC; c = c + 1) h_t_c[c] <= mw[31:0];
            h_d <= mw[63:32]; h_e <= mw[64];
        end
    end

    // ------------------------------------------------------------ buffer: valid, key, data, error
    reg [D-1:0] bv;
    reg [31:0] bk [0:D-1];
    reg [31:0] bd [0:D-1];
    reg [D-1:0] be;

    // ------------------------------------------------------------ S1: candidate, compares
    wire        x_v = sv || hv;
    wire [31:0] x_d = sv ? sum : h_d;
    wire        x_e = sv ? (st_e | err != 2'd0) : h_e;
    wire [31:0] x_t0 = sv_c[0] ? st_c[0] : h_t_c[0];
    reg [D-1:0] ins_r;                       // slot inserted by the previous decision (one-hot)
    reg ins_any;
    (* keep *) reg [31:0] w_k_c [0:NC-1];   // its key / data / error, kept copies (written into the slot now)
    (* keep *) reg [31:0] w_d_c [0:NC-1];
    (* keep *) reg [NC-1:0] w_e_c;
    reg [D-1:0] m1;
    always @* begin
        for (k = 0; k < D; k = k + 1)
            m1[k] = bv[k] && ((ins_r[k] ? w_k_c[k / SG] : bk[k]) == (sv_c[k / SG] ? st_c[k / SG] : h_t_c[k / SG]));
    end
    reg s2_v, s2_cmp, s2_sp, s2_e; reg [31:0] s2_d, s2_t, s2_k;
    reg [D-1:0] s2_m;
    always @(posedge clk or negedge rst_n) if (!rst_n) s2_v <= 1'b0; else s2_v <= x_v;
    always @(posedge clk) begin
        s2_t <= x_t0; s2_k <= key(x_t0); s2_d <= x_d; s2_e <= x_e;
        s2_cmp <= complete(x_t0);
        s2_sp <= s2_v && s2_k == x_t0;       // the candidate is the sibling of the one now deciding
        s2_m <= m1;
    end

    // ------------------------------------------------------------ S2: decision (registers in, one-hot out)
    reg [D-1:0] fr_r; reg fr_any;            // free slot for this decision (one-hot)
`ifdef S81PH_MUT_NOFWD
    wire fwd = 1'b0;                                               // MUTANT: no forwarding of the previous insert
`else
    wire fwd = s2_sp && ins_any;
`endif
    wire [D-1:0] hit_oh = fwd ? ins_r : s2_m;
    wire hit_any = fwd || (|s2_m);
    wire live = s2_v && !s2_cmp;
    wire dec_add = live && hit_any;
    wire dec_ins = live && !hit_any && fr_any;
    // next free slot: lowest free of the current state, minus the slot inserted now (removals count next cycle)
    wire [D-1:0] fr_a = lowest(~bv & ~fr_r), fr_b = lowest(~bv);
    wire fr_a_any = |(~bv & ~fr_r), fr_b_any = |(~bv);
    wire [2:0] s2_kk = s2_t[7:5];
    wire [4:0] s2_lo = s2_t[12:8];
    wire [31:0] s2_par = {s2_t[31:13], s2_lo & ~(5'd1 << s2_kk), s2_kk + 3'd1, s2_t[4:0]};   // normalised in the delay line
    wire s2_right = s2_lo[s2_kk];            // candidate is the right sibling: buffer word is the left operand
    reg a3_v, a3_right, a3_e; reg [31:0] a3_d, a3_t; reg [D-1:0] a3_oh;
    reg [D-1:0] rm_r, e_m; reg e_dup;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            bv <= {D{1'b0}}; ins_r <= {D{1'b0}}; ins_any <= 1'b0; fr_r <= {{(D-1){1'b0}}, 1'b1}; fr_any <= 1'b1;
            a3_v <= 1'b0; r_v <= 1'b0; fault <= 1'b0; rm_r <= {D{1'b0}}; e_m <= {D{1'b0}}; e_dup <= 1'b0;
        end else begin
            a3_v <= dec_add;
            ins_r <= dec_ins ? fr_r : {D{1'b0}};
            ins_any <= dec_ins;
            bv <= (bv & ~(dec_add ? hit_oh : {D{1'b0}})) | (dec_ins ? fr_r : {D{1'b0}});
            fr_r <= dec_ins ? fr_a : fr_b;
            fr_any <= dec_ins ? fr_a_any : fr_b_any;
            r_v <= s2_v && s2_cmp;
            rm_r <= dec_add ? hit_oh : {D{1'b0}};
            // malformed-stream checks, one cycle later: a match on the slot the previous add removed, forwarding and
            // a buffer match at once, more than one buffer match
            e_dup <= live && ((|(s2_m & rm_r)) || (fwd && (|s2_m)));
            e_m <= live ? s2_m : {D{1'b0}};
            if (n_v && q_full) fault <= 1'b1;
            if (live && !hit_any && !fr_any) fault <= 1'b1;
            if (e_dup || (|(e_m & ~lowest(e_m)))) fault <= 1'b1;
        end
    always @(posedge clk) begin
        for (k = 0; k < D; k = k + 1)
            if (ins_r[k]) begin bk[k] <= w_k_c[k / SG]; bd[k] <= w_d_c[k / SG]; be[k] <= w_e_c[k / SG]; end
        for (c = 0; c < NC; c = c + 1) begin w_k_c[c] <= s2_k; w_d_c[c] <= s2_d; w_e_c[c] <= s2_e; end
        a3_oh <= hit_oh; a3_d <= s2_d; a3_e <= s2_e; a3_t <= s2_par; a3_right <= s2_right;
        r_row <= s2_t[28:13]; r_pos <= s2_t[31:29]; r_fp32 <= s2_d; r_e <= s2_e;
        r_bf16 <= ({1'b0, s2_d} + 33'h7FFF + {32'd0, s2_d[16]}) >> 16;
    end

    // ------------------------------------------------------------ S3: operands
    reg [31:0] b_sel; reg e_sel;
    always @* begin
        b_sel = 32'd0; e_sel = 1'b0;
        for (k = 0; k < D; k = k + 1) begin
            b_sel = b_sel | ({32{a3_oh[k]}} & bd[k]);
            e_sel = e_sel | (a3_oh[k] & be[k]);
        end
    end
    always @(posedge clk or negedge rst_n) if (!rst_n) add <= 1'b0; else add <= a3_v;
    always @(posedge clk) begin
        if (a3_v) begin
            if (a3_right) begin add_a <= b_sel; add_b <= a3_d; end
            else begin add_a <= a3_d; add_b <= b_sel; end
        end
        tag_in <= {a3_t, e_sel | a3_e};
    end
    ot_fp32_add_rne_deep #(.SPLIT(3'b111)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(add), .a(add_a), .b(add_b),
        .y(sum), .err(err), .valid_out(sv_add));
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin dv <= 0; sv_c <= {NC{1'b0}}; sv <= 1'b0; end
        else begin
            dv <= {dv[LAT-3:0], add};
            sv_c <= {NC{dv[LAT-2]}}; sv <= dv[LAT-2];
        end
    always @(posedge clk) begin
        // delay line stage j < 5 applies norm iteration j to the parent tag (5 iterations = norm)
        for (c = 0; c < LAT - 1; c = c + 1)
            if (c < 5) dtg[33*c +: 33] <= {norm_step(c == 0 ? tag_in[32:1] : dtg[33*(c-1) + 1 +: 32]),
                                           (c == 0) ? tag_in[0] : dtg[33*(c-1)]};
            else dtg[33*c +: 33] <= dtg[33*(c-1) +: 33];
        for (c = 0; c < NC; c = c + 1) st_c[c] <= dtg[33*(LAT-2) + 1 +: 32];
        st_e <= dtg[33*(LAT-2)];
    end
`ifndef SYNTHESIS
    always @(posedge clk) if (rst_n && sv_add !== sv) $error("ot_s81ph_ret_root_p: adder latency != %0d", LAT);
    initial if (D % NC != 0 || D < 2) $fatal(1, "ot_s81ph_ret_root_p: D %% NC");
`endif
endmodule
