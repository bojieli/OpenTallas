// CLAUDE pq-rootcam ROUND 2 2026-10-08 (routes of round 1, 08f27dc4f: TT -555.9 / -551.4 / PAR1 -682.1, FF >= +2, DRC 0).
// Worst TT classes of those routes (path_summary, SS-scaled ranking, 2000 endpoints):
//   s_t -> norm() -> qk/head_k (44 levels: norm is 5 SERIAL increment-compare steps);  ct -> norm() -> c_pt (40);
//   u_add s2 -> s3 (35, behavioural add re-rippled by ABC);  match_vec -> hit_any/first1 -> in_mask -> bt/bd/be write
//   enables (28; 128 x 66 enables);  match_vec -> first1 -> rm_mask -> next_match_vec -> match_vec (24);  rst_n ->
//   128 async set/reset pins (recovery).
// Round-2 fixes (no change to the one-candidate-per-cycle throughput, no added cycle on the decision loop):
//   * norm_f(): the 5 serial steps in closed form.  The k increment condition C(k) depends on k only, so once C fails
//     k stays; norm = k + (number of leading true C(k), C(k+1) .. C(k+4)) with all five C evaluated in PARALLEL
//     (3-bit wrap and the out-of-range lo[k] -> "no increment" case kept bit for bit; exhaustively checked in the gate).
//   * parent tag / operand order computed in B from the registered candidate ct (not on the A mux output).
//   * buffer keeps KEYS (the tag its sibling must carry: lo bit k flipped), so a sibling test is one 32-bit equality.
//   * decision loop cut: A registers pm = matches against the CURRENT buffer only (entries with a pending write are
//     compared through the write register) and qn = key(ct) == candidate; B applies the removal of the previous
//     decision as a registered mask: match = (pm & ~rm_r) | (in_r & qn).  The loop is register -> first-one /
//     OR-reduce -> masks -> register.
//   * entry writes one cycle after the decision, from registers (in_r one-hot, w_*): no 128 x 66 enable fan-out from
//     the decision logic.  A read in C of an entry inserted by the previous decision sees the landed write.
//   * adder: ot_fp32_add_rne_deep (bit-identical to ot_fp32_add_rne_pipe) with kept Kogge-Stone adds (KS 1);
//     ASPLIT cuts more stages (LAT = 5 + popcount(ASPLIT)): ASPLIT 0 adds no cycle, ASPLIT 7 adds 3 per add level.
//   * reset: rst_n only on the input station; everything else on a registered reset (async assert, sync release one
//     cycle later; the input station keeps the first word after release).
// Round-1 header follows.
// CLAUDE pq-rootcam 2026-10-08: pipelined ROOTD128 sibling CAM (structural redesign of ot_s81_pq_ret_root_cam).
// Same ports and same pairing/arithmetic as ot_s81_pq_ret_root_cam (and therefore the native ot_v41_ret_root);
// opt-in by instantiation, the original module is unchanged.
//
// Why: the staged CAM failed TT by -1,168 ps (B: match_vec -> binary hit index -> 128:1 bt[hit] mux -> parent/norm
// -> tag_in, 1.87 ns) and C/CP by ~-800 ps (head_t -> norm -> 128 sibling compares -> binary hit/fr decode ->
// next_match_vec).  Restructured so that no stage holds more than one wide operation:
//   S  input station: every input pin lands on a flop (PAR 1: odd-parity check, bad word dropped).  The norm()
//      k-field is computed here and stored beside the raw queue word, so the head carries a normalised tag with
//      no norm on the A path (raw tag kept for the face parity).
//   Q  queue head register; the read pointer + 1 is a register (no incrementer before the 128:1 read).
//   A  candidate = adder result or head.  Per-entry sibling compare against the STORED tags (bv & sibling(bt[n],at)),
//      plus one scalar compare against B's candidate (sibling(ct, at)) for the same-edge insert forward; B's
//      removal/insert reach A only as one-hot masks from a log-depth prefix-OR first-one (no binary index).
//      The pair's parent tag and operand order are computed here from the candidate alone: for true siblings
//      the entry's tag equals ct except lo bit k, so parent(bt[hit], ct) = norm({ct.row, ct.lo & ~2^k, ct.k+1,
//      ct.nseg}) and (bt.lo < ct.lo) = ct.lo[k].  This removes the bt[hit] read from the add path entirely.
//   B  decision from the registered match/free vectors (first-one one-hot, OR-reduce); bv/bt/bd/be one-hot
//      writes; complete results registered straight to the output pins.
//   C  one-hot AND-OR read of bd/be (bt/bp too with PAR) with the registered hit one-hot; operand swap; issue.
//      Safe: a slot freed in B(t) can be rewritten only by an insert decided in B(t+1), whose write lands on the
//      same edge C(t+1) samples the old entry (as OPC 1 of the original).
//   D  (PAR 1 only) registered entry read, entry parity check (no add on a mismatch), then issue.
// Cost vs ot_s81_pq_ret_root_cam OPC 0: +1 input station (PAR 0; PAR 1 already had it), +1 on the add round trip
// (C), +1 more with PAR (D).  The bench measures the deltas against the native root.
// fault is a registered output (one cycle later than the internal sticky flags).
module ot_s81_pq_ret_root_cam_p #(
    parameter integer D = 128,
    parameter integer QD = 128,
    parameter integer PAR = 0,
    parameter integer ASPLIT = 0,        // ot_fp32_add_rne_deep SPLIT (0: 5-cycle adder, 7: 8-cycle)
    parameter integer AKS = 1            // kept Kogge-Stone adds in the adder
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [31:0] i_t,
    input  wire [31:0] i_d,
    input  wire        i_e,
    input  wire        i_p,
    input  wire        up_fault,
    output reg         r_v,
    output reg  [15:0] r_row,
    output reg  [2:0]  r_pos,
    output reg  [31:0] r_fp32,
    output reg  [15:0] r_bf16,
    output reg         r_e,
    output reg         r_p,
    output wire        fault
);
    import ot_v41_ret_pkg::*;
    localparam integer QW = $clog2(QD);
    localparam integer LAT = 5 + (ASPLIT & 1) + ((ASPLIT >> 1) & 1) + ((ASPLIT >> 2) & 1);

    // lowest set bit as a one-hot: log-depth prefix OR (no carry chain, no binary index)
    function automatic [D-1:0] first1(input [D-1:0] x);
        reg [D-1:0] p;
        integer s;
        begin
            p = x;
            for (s = 1; s < D; s = s * 2) p = p | (p << s);
            first1 = x & ~(p << 1);
        end
    endfunction
    // ot_v41_ret_pkg::norm in closed form (five parallel conditions, leading-run count)
    function automatic [31:0] norm_f(input [31:0] t);
        reg [18:0] row;
        reg [4:0] lo, n;
        reg [2:0] k, kj, inc;
        reg run, lb, cj;
        integer j;
        begin
            {row, lo, k, n} = t;
            run = 1'b1; inc = 3'd0;
            for (j = 0; j < 5; j = j + 1) begin
                kj = k + j[2:0];
                lb = (kj < 3'd5) ? lo[kj] : 1'b1;
                cj = !(lo == 5'd0 && (6'd1 << kj) >= {1'b0, n}) && lb == 1'b0 && ({1'b0, lo} + (6'd1 << kj)) >= {1'b0, n};
                run = run & cj;
                inc = inc + {2'd0, run};
            end
            norm_f = {row, lo, k + inc, n};
        end
    endfunction
    // the tag a partial's sibling carries (sibling(a, b) <=> key(a) == b); key is an involution
    function automatic [31:0] key(input [31:0] a);
        key = {a[31:13], a[12:8] ^ (5'd1 << a[7:5]), a[7:5], a[4:0]};
    endfunction

    // ---------------- reset: input station on rst_n, the rest on a registered reset
    reg rst_q;
    always @(posedge clk or negedge rst_n) if (!rst_n) rst_q <= 1'b0; else rst_q <= 1'b1;
    reg fault_c, pfault, fault_q;
    // ---------------- S: input station
    reg        s_v, s_uf;
    reg        s_e, s_p;
    reg [31:0] s_t, s_d;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin s_v <= 1'b0; s_uf <= 1'b0; end else begin s_v <= i_v; s_uf <= up_fault; end
    always @(posedge clk) begin s_t <= i_t; s_d <= i_d; s_e <= i_e; s_p <= i_p; end
    wire        s_bad = (PAR != 0) && s_v && !(^{s_e, s_d, s_t, s_p});
    wire        w_v = s_v && !s_bad;
    wire [31:0] w_n = norm_f(s_t);
    wire [2:0]  w_k = w_n[7:5];
    // ---------------- Q: input queue + registered head
    reg [31:0] qt [0:QD-1];
    reg [31:0] qd [0:QD-1];
    reg [2:0]  qk [0:QD-1];
    reg        qe [0:QD-1];
    reg        qp [0:QD-1];
    reg [QW-1:0] qr, qr1, qw;
    reg [QW:0]   qc;
    reg [31:0] head_t, head_d;
    reg [2:0]  head_k;
    reg        head_e, head_p;
    // ---------------- buffer (keys, data, error, face parity of the tag word)
    reg [D-1:0] bv, bv_s;
    reg [31:0] bk [0:D-1];
    reg [31:0] bd [0:D-1];
    reg        be [0:D-1];
    reg        bp [0:D-1];
    // ---------------- adder
    wire [31:0] sum;
    wire [1:0]  err;
    wire        sv;
    reg         add;
    reg [31:0]  add_a, add_b;
    reg [32:0]  tag_in;
    wire [32:0] st;
    ot_fp32_add_rne_deep #(.SPLIT(ASPLIT), .KS(AKS)) u_add (.clk(clk), .rst_n(rst_q), .valid_in(add), .a(add_a),
                                .b(add_b), .y(sum), .err(err), .valid_out(sv));
    ot_hdc_delay #(.W(33), .D(LAT)) u_t (.clk(clk), .rst_n(rst_q), .d(tag_in), .q(st));
    // ---------------- A: candidate, match against the current buffer (pending writes through w_k)
    wire        use_q = !sv && qc != 0;
    wire [31:0] head_n = {head_t[31:8], head_k, head_t[4:0]};
    wire [31:0] at = sv ? st[32:1] : head_n;
    wire [31:0] ad = sv ? sum : head_d;
    wire        ae = sv ? (st[0] | err != 2'd0) : head_e;
    wire        av = sv || qc != 0;
    wire        head_bad = (PAR != 0) && !sv && qc != 0 && !(^{head_e, head_d, head_t, head_p});
    // B registers
    reg         cv, ce, cp;
    reg [31:0]  ct, cd;
    reg [D-1:0] pm, frees, rm_r, in_r;
    reg         qn;
    // write registers (entry write lands one cycle after the decision)
    reg [31:0]  w_kk, w_d;
    reg         w_e, w_p;
    reg  [D-1:0] sib_old;
    integer n;
    always @* for (n = 0; n < D; n = n + 1) sib_old[n] = bk[n] == at;
    // sib_w: the entry with a pending write; sib_new: B's candidate (same-edge insert forward)
    wire        sib_w = w_kk == at;
    wire        sib_new = key(ct) == at;
    wire [D-1:0] next_pm = (bv & ~in_r & sib_old) | (in_r & {D{sib_w}});
    // ---------------- B: decision (registers -> first-one / OR-reduce -> masks -> registers)
    wire [D-1:0] match_vec = (pm & ~rm_r) | (in_r & {D{qn}});
    wire        hit_any = |match_vec;
    wire        fr_any = |frees;
    wire [D-1:0] hit_oh = first1(match_vec);
    wire [D-1:0] fr_oh = first1(frees);
    wire        cmp_b = cv && !complete(ct);
    wire        remove_b = cmp_b && hit_any;
    wire        insert_b = cmp_b && !hit_any && fr_any;
    wire [D-1:0] rm_mask = remove_b ? hit_oh : {D{1'b0}};
    wire [D-1:0] in_mask = insert_b ? fr_oh : {D{1'b0}};
    wire [D-1:0] bv_next = (bv & ~rm_mask) | in_mask;
    wire [D-1:0] next_frees = ~bv_next;
    wire        cand_bad = (PAR != 0) && cv && !(^{ce, cd, ct, cp});
    wire [32:0] rb = {1'b0, cd} + 33'h7FFF + {32'd0, cd[16]};
    // parent tag + operand order from the registered candidate (exact for siblings: entry = ct with lo bit k flipped)
    wire [4:0]  b_kb = 5'd1 << ct[7:5];
    wire        b_sw = |(ct[12:8] & b_kb);                           // entry is the left operand
    wire [31:0] b_pt = norm_f({ct[31:13], ct[12:8] & ~b_kb, ct[7:5] + 3'd1, ct[4:0]});
    // ---------------- C: one-hot entry read
    reg         c_add, c_e, c_swc;
    reg [D-1:0] c_oh;
    reg [31:0]  c_d, c_ptc;
    reg [31:0]  sel_d, sel_k;
    reg         sel_e, sel_p;
    always @* begin
        sel_d = 32'd0; sel_k = 32'd0; sel_e = 1'b0; sel_p = 1'b0;
        for (n = 0; n < D; n = n + 1) begin
            sel_d = sel_d | ({32{c_oh[n]}} & bd[n]);
            sel_e = sel_e | (c_oh[n] & be[n]);
            if (PAR != 0) begin
                sel_k = sel_k | ({32{c_oh[n]}} & bk[n]);
                sel_p = sel_p | (c_oh[n] & bp[n]);
            end
        end
    end
    // ---------------- D (PAR 1): registered entry, parity check
    reg         d_add, d_e, d_sw, d_ce, d_p;
    reg [31:0]  d_d, d_t, d_cd, d_pt;
    wire        dent_bad = (PAR != 0) && d_add && !(^{d_e, d_d, d_t, d_p});
    wire        bvs_bad = (PAR != 0) && (bv != bv_s);
    wire        qc_bad = (PAR != 0) && (((qw - qr) & (QD - 1)) != (qc & (QD - 1)));
    assign fault = fault_q;
    always @(posedge clk or negedge rst_q)
        if (!rst_q) begin pfault <= 1'b0; fault_q <= 1'b0; end
        else begin
            if (s_bad || head_bad || cand_bad || dent_bad || bvs_bad || qc_bad) pfault <= 1'b1;
            fault_q <= fault_c | pfault | ((PAR != 0) ? s_uf : 1'b0);
        end
    // ---------------- control state
    always @(posedge clk or negedge rst_q) begin
        if (!rst_q) begin
            qr <= 0; qr1 <= 1; qw <= 0; qc <= 0; cv <= 1'b0; pm <= 0; qn <= 1'b0; rm_r <= 0; in_r <= 0;
            frees <= {D{1'b1}}; bv <= 0; bv_s <= 0; r_v <= 1'b0; fault_c <= 1'b0; add <= 1'b0; c_add <= 1'b0;
            d_add <= 1'b0;
        end else begin
            // A -> B
            cv <= av && !head_bad;
            pm <= next_pm; qn <= sib_new;
            if (w_v) qw <= qw + 1'b1;
            if (use_q) begin qr <= qr1; qr1 <= qr1 + 1'b1; end
            qc <= qc + (w_v ? 1'b1 : 1'b0) - (use_q ? 1'b1 : 1'b0);
            if (w_v && qc == QD && !use_q) fault_c <= 1'b1;
            // B
            frees <= next_frees; rm_r <= rm_mask; in_r <= in_mask;
            bv <= bv_next; bv_s <= bv_next;
            r_v <= cv && complete(ct);
            if (cmp_b && !hit_any && !fr_any) fault_c <= 1'b1;
            c_add <= remove_b && !cand_bad;
            // C / D -> adder
            if (PAR != 0) begin d_add <= c_add; add <= d_add && !dent_bad; end
            else add <= c_add;
        end
    end
    // ---------------- entry write from registers, one write enable per entry
    genvar g;
    generate for (g = 0; g < D; g = g + 1) begin : g_ent
        always @(posedge clk) if (in_r[g]) begin bk[g] <= w_kk; bd[g] <= w_d; be[g] <= w_e; bp[g] <= w_p; end
    end endgenerate
    // ---------------- data path
    always @(posedge clk) begin
        // queue
        if (w_v) begin qt[qw] <= s_t; qd[qw] <= s_d; qk[qw] <= w_k; qe[qw] <= s_e; qp[qw] <= s_p; end
        if (use_q) begin
            if (qc == 1 && w_v) begin head_t <= s_t; head_k <= w_k; head_d <= s_d; head_e <= s_e; head_p <= s_p; end
            else if (qc > 1) begin
                head_t <= qt[qr1]; head_k <= qk[qr1]; head_d <= qd[qr1]; head_e <= qe[qr1]; head_p <= qp[qr1];
            end
        end else if (qc == 0 && w_v) begin head_t <= s_t; head_k <= w_k; head_d <= s_d; head_e <= s_e; head_p <= s_p; end
        // A -> B
        ct <= at; cd <= ad; ce <= ae; cp <= ~^{ae, ad, at};
        // B -> write registers (key of the candidate; cp is the parity of the tag word, key keeps the k field)
        w_kk <= key(ct); w_d <= cd; w_e <= ce; w_p <= cp;
        // B: result register
        r_row <= ct[28:13]; r_pos <= ct[31:29]; r_fp32 <= cd; r_bf16 <= rb[31:16]; r_e <= ce;
        r_p <= (PAR != 0) ? ~^{ct[28:13], ct[31:29], cd, rb[31:16], ce} : 1'b0;
        // B -> C
        c_oh <= hit_oh; c_d <= cd; c_e <= ce; c_swc <= b_sw; c_ptc <= b_pt;
        // C -> D (PAR) or C -> adder
        if (PAR != 0) begin
            d_d <= sel_d; d_t <= key(sel_k); d_e <= sel_e; d_p <= sel_p; d_cd <= c_d; d_ce <= c_e; d_sw <= c_swc; d_pt <= c_ptc;
            if (d_sw) begin add_a <= d_d; add_b <= d_cd; end else begin add_a <= d_cd; add_b <= d_d; end
            tag_in <= {d_pt, d_e | d_ce};
        end else begin
            if (c_swc) begin add_a <= sel_d; add_b <= c_d; end else begin add_a <= c_d; add_b <= sel_d; end
            tag_in <= {c_ptc, sel_e | c_e};
        end
    end
endmodule
