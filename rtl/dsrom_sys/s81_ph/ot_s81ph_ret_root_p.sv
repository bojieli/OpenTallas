`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81ph_ret_root_p -- PIPELINED S81 region root (CLAUDE S81-PH gather, 2026-10-06).
//
// Same function as the W10 ot_v41_ret_root (rtl/v41rom/ot_v41_ret.sv; D-entry pairing buffer, QD-entry input queue,
// FP32 sibling adds, complete rows out) restructured for 1.2 GHz with margin: the W10 root decides every candidate
// in ONE cycle (queue head mux -> norm -> 128 sibling compares -> priority chain -> parent / buffer update), which
// routed at -4.36 ns (root_m1, PVE1, floorplan repair).  Here:
//   P0  input: norm(i_t) over three registered stages (2 + 2 + 1 of norm's 5 iterations; the W10 root applies norm at
//       the queue head instead: same tag, norm is idempotent).  The parent tag is normalised the same way, one
//       iteration per stage of the adder's tag delay line (root_m2 floorplan: one-stage norm = -1.2 ns)
//   Q   input queue = QD-entry flop memory + registered head (kept copies); the head mux is pointer-addressed only
//   S1  candidate = adder result (priority, as W10) else queue head; D sibling compares against the buffer, the
//       compare against the candidate now in S2 (forwarding), complete(); registered (kept copies of the candidate)
//   S2  decision: match = S1 match & current valid bits | (slot inserted by the previous candidate & forward
//       compare); lowest-index hit (prefix-OR one-hot, the W10 priority) -> remove + add, else lowest free slot ->
//       insert, else fault; complete -> row out.  Buffer valid/tag/data written here.
//   S3  add operands: one-hot AND-OR read of the hit slot's data (the slot is rewritten no earlier than the end
//       of this cycle), left = lower lo (W10 rule), parent tag (only depends on the candidate: siblings differ in lo
//       bit k only), error OR.
//   ADD ot_fp32_add_rne_deep (SPLIT 7, bit-identical to the qualified ot_fp32_add_rne_pipe, LAT 8); the tag and
//       valid travel on a local delay line whose last stage is replicated (kept copies drive the S1 compares).
// Arithmetic and pairing are the W10 ones (siblings are unique; IEEE add commutes bit for bit), so every row's
// value is identical; a root's rows can leave in a different order than W10 only when adds of different rows
// overlap differently (the exact bench compares per-root ordered (addr, data) streams vs the W10 root).
// ---------------------------------------------------------------------------------------------------------------
module ot_s81ph_ret_root_p #(
    parameter integer D  = 128,
    parameter integer QD = 128,
    parameter integer NC = 8                 // kept candidate / write-data copies (each drives D/NC slots)
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
    function automatic sibling(input [31:0] a, input [31:0] b);
        sibling = a[31:13] == b[31:13] && a[7:5] == b[7:5] && a[4:0] == b[4:0] &&
                  (a[12:8] ^ b[12:8]) == (5'd1 << a[7:5]);
    endfunction
    localparam integer QW = $clog2(QD);
    localparam integer LAT = 8;              // ot_fp32_add_rne_deep SPLIT 3'b111
    localparam integer SG = D / NC;          // slots per copy
    integer k, c;

    // ------------------------------------------------------------ P0: normalised input
    // one iteration of ot_v41_ret_pkg::norm (which is exactly 5 of these in sequence)
    function automatic [31:0] norm_step(input [31:0] t);
        reg [18:0] row; reg [4:0] lo, n; reg [2:0] k;
        begin
            {row, lo, k, n} = t;
            if (!(lo == 5'd0 && (6'd1 << k) >= {1'b0, n}) && lo[k] == 1'b0 && ({1'b0, lo} + (6'd1 << k)) >= {1'b0, n})
                k = k + 3'd1;
            norm_step = {row, lo, k, n};
        end
    endfunction
    reg n_v, p_v1, p_v2; reg [31:0] n_t, n_d, p_t1, p_d1, p_t2, p_d2; reg n_e, p_e1, p_e2;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin p_v1 <= 1'b0; p_v2 <= 1'b0; n_v <= 1'b0; end
        else begin p_v1 <= i_v; p_v2 <= p_v1; n_v <= p_v2; end
    always @(posedge clk) begin
        p_t1 <= norm_step(norm_step(i_t)); p_d1 <= i_d; p_e1 <= i_e;
        p_t2 <= norm_step(norm_step(p_t1)); p_d2 <= p_d1; p_e2 <= p_e1;
        n_t <= norm_step(p_t2); n_d <= p_d2; n_e <= p_e2;
    end

    // ------------------------------------------------------------ adder return (tag / valid delay line)
    reg [LAT-2:0] dv;                        // valid, stages 0..LAT-2
    reg [33*(LAT-1)-1:0] dtg;                // {tag32, e} stages 0..LAT-2
    (* keep *) reg [NC-1:0] sv_c;           // stage LAT-1 (aligned with the adder output), kept copies
    (* keep *) reg [31:0] st_c [0:NC-1];
    reg st_e;
    reg sv;                                  // = every sv_c (single copy for the queue / fault logic)
    wire [31:0] sum; wire [1:0] err; wire sv_add;
    reg add; reg [31:0] add_a, add_b; reg [32:0] tag_in;

    // ------------------------------------------------------------ queue: memory + registered head
    localparam integer NQ = 5;               // read pointer copies, 13 bits of the 65-b queue word each
    reg [64:0] qm [0:QD-1];                  // {e, d32, t32}
    reg [QW-1:0] qw;
    (* keep *) reg [QW-1:0] qr_c [0:NQ-1];  // read pointer copies (select fan-out of the head mux)
    reg [QW:0] mc;                           // entries in the memory (not counting the head)
    reg hv; reg [31:0] h_d; reg h_e;
    (* keep *) reg [31:0] h_t_c [0:NC-1];   // head tag, kept copies
    wire pop = hv && !sv;                    // W10: use_q = !sv && queue not empty
    wire take = !hv || pop;                  // head register (re)loads this cycle
    wire from_mem = take && mc != 0;
    wire bypass = take && mc == 0 && n_v;    // empty memory: the new word goes straight to the head
    wire wr_mem = n_v && !bypass;
    wire q_ovf = wr_mem && mc == QD && !from_mem;
    reg [64:0] mw;
    always @* for (c = 0; c < NQ; c = c + 1) mw[13*c +: 13] = qm[qr_c[c]][13*c +: 13];
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin
            qw <= 0; mc <= 0; hv <= 1'b0;
            for (c = 0; c < NQ; c = c + 1) qr_c[c] <= 0;
        end else begin
            if (wr_mem && !q_ovf) qw <= qw + 1'b1;
            if (from_mem) for (c = 0; c < NQ; c = c + 1) qr_c[c] <= qr_c[c] + 1'b1;
            mc <= mc + ((wr_mem && !q_ovf) ? 1'b1 : 1'b0) - (from_mem ? 1'b1 : 1'b0);
            if (take) hv <= from_mem || bypass;
        end
    always @(posedge clk) begin
        if (wr_mem && !q_ovf) qm[qw] <= {n_e, n_d, n_t};
        if (from_mem) begin
            for (c = 0; c < NC; c = c + 1) h_t_c[c] <= mw[31:0];
            h_d <= mw[63:32]; h_e <= mw[64];
        end else if (bypass) begin
            for (c = 0; c < NC; c = c + 1) h_t_c[c] <= n_t;
            h_d <= n_d; h_e <= n_e;
        end
    end

    // ------------------------------------------------------------ buffer
    reg [D-1:0] bv;
    reg [31:0] bt [0:D-1];
    reg [31:0] bd [0:D-1];
    reg [D-1:0] be;

    // ------------------------------------------------------------ S1: candidate, compares
    wire        x_v = sv || hv;
    wire [31:0] x_d = sv ? sum : h_d;
    wire        x_e = sv ? (st_e | err != 2'd0) : h_e;
    wire [31:0] x_t0 = sv_c[0] ? st_c[0] : h_t_c[0];
    reg [D-1:0] ins_r;                       // slot inserted by the previous decision (one-hot)
    (* keep *) reg [31:0] w_t_c [0:NC-1];   // its tag / data / error, kept copies (each writes D/NC slots)
    (* keep *) reg [31:0] w_d_c [0:NC-1];
    (* keep *) reg [NC-1:0] w_e_c;
    reg  [D-1:0] m1;
    always @* begin
        for (k = 0; k < D; k = k + 1)
            // a slot inserted by the previous decision holds its tag in w_t_c until the end of this cycle
            m1[k] = bv[k] && sibling(ins_r[k] ? w_t_c[k / SG] : bt[k], sv_c[k / SG] ? st_c[k / SG] : h_t_c[k / SG]);
    end
    reg s2_v, s2_cmp, s2_sp, s2_e; reg [31:0] s2_d;
    (* keep *) reg [31:0] s2_t_c [0:NC-1];
    reg [D-1:0] s2_m;
    always @(posedge clk or negedge rst_n) if (!rst_n) s2_v <= 1'b0; else s2_v <= x_v;
    always @(posedge clk) begin
        for (c = 0; c < NC; c = c + 1) s2_t_c[c] <= sv_c[c] ? st_c[c] : h_t_c[c];
        s2_d <= x_d; s2_e <= x_e;
        s2_cmp <= complete(x_t0);
        s2_sp <= s2_v && sibling(s2_t_c[0], x_t0);
        s2_m <= m1;
    end

    // ------------------------------------------------------------ S2: decision
`ifdef S81PH_MUT_NOFWD
    wire [D-1:0] mm = s2_m & bv;                                   // MUTANT: no forwarding of the previous insert
`else
    wire [D-1:0] mm = (s2_m & bv) | (ins_r & {D{s2_sp}});
`endif
    wire [D-1:0] fr = ~bv;
    // lowest set bit, prefix-OR (log depth)
    function automatic [D-1:0] lowest(input [D-1:0] x);
        reg [D-1:0] p; integer s, j;
        begin
            p = x;
            for (s = 1; s < D; s = s * 2)
                for (j = D - 1; j >= s; j = j - 1) p[j] = p[j] | p[j - s];
            lowest = x & ~{p[D-2:0], 1'b0};
        end
    endfunction
    wire [D-1:0] hit_oh = lowest(mm);
    wire [D-1:0] fr_oh = lowest(fr);
    wire hit_any = |mm, fr_any = |fr;
    wire dec_add = s2_v && !s2_cmp && hit_any;
    wire dec_ins = s2_v && !s2_cmp && !hit_any && fr_any;
    wire [31:0] s2_t0 = s2_t_c[0];
    // parent tag: lo with bit k cleared, k + 1 (siblings share row/pos/nseg/k and differ in lo bit k)
    wire [2:0] s2_k = s2_t0[7:5];
    wire [4:0] s2_lo = s2_t0[12:8];
    wire [31:0] s2_par = {s2_t0[31:13], s2_lo & ~(5'd1 << s2_k), s2_k + 3'd1, s2_t0[4:0]};   // normalised in the delay line
    wire s2_right = s2_lo[s2_k];             // candidate is the right sibling: buffer word is the left operand
    reg a3_v, a3_right, a3_e; reg [31:0] a3_d, a3_t; reg [D-1:0] a3_oh;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin bv <= {D{1'b0}}; ins_r <= {D{1'b0}}; a3_v <= 1'b0; r_v <= 1'b0; fault <= 1'b0; end
        else begin
            a3_v <= dec_add;
            ins_r <= dec_ins ? fr_oh : {D{1'b0}};
            if (dec_add) bv <= bv & ~hit_oh;
            else if (dec_ins) bv <= bv | fr_oh;
            r_v <= s2_v && s2_cmp;
            if (q_ovf || (s2_v && !s2_cmp && !hit_any && !fr_any)) fault <= 1'b1;
        end
    always @(posedge clk) begin
        for (k = 0; k < D; k = k + 1)
            // buffer data written one cycle after the decision (root_m3 floorplan: decision -> 128 x 66 write
            // enables = -319 ps); valid bits (bv) still update at the decision
            if (ins_r[k]) begin bt[k] <= w_t_c[k / SG]; bd[k] <= w_d_c[k / SG]; be[k] <= w_e_c[k / SG]; end
        for (c = 0; c < NC; c = c + 1) begin w_t_c[c] <= s2_t_c[c]; w_d_c[c] <= s2_d; w_e_c[c] <= s2_e; end
        a3_oh <= hit_oh; a3_d <= s2_d; a3_e <= s2_e; a3_t <= s2_par; a3_right <= s2_right;
        r_row <= s2_t0[28:13]; r_pos <= s2_t0[31:29]; r_fp32 <= s2_d; r_e <= s2_e;
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
