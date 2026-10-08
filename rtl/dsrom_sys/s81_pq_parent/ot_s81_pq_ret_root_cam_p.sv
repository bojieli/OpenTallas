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
    parameter integer PAR = 0
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
    wire [31:0] w_n = norm(s_t);
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
    // ---------------- buffer
    reg [D-1:0] bv, bv_s;
    reg [31:0] bt [0:D-1];
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
    ot_fp32_add_rne_pipe u_add (.clk(clk), .rst_n(rst_n), .valid_in(add), .a(add_a), .b(add_b),
                                .y(sum), .err(err), .valid_out(sv));
    ot_hdc_delay #(.W(33), .D(5)) u_t (.clk(clk), .rst_n(rst_n), .d(tag_in), .q(st));
    // ---------------- A: candidate, match against the post-B buffer state
    wire        use_q = !sv && qc != 0;
    wire [31:0] head_n = {head_t[31:8], head_k, head_t[4:0]};
    wire [31:0] at = sv ? st[32:1] : head_n;
    wire [31:0] ad = sv ? sum : head_d;
    wire        ae = sv ? (st[0] | err != 2'd0) : head_e;
    wire        av = sv || qc != 0;
    wire        head_bad = (PAR != 0) && !sv && qc != 0 && !(^{head_e, head_d, head_t, head_p});
    wire [4:0]  a_kb = 5'd1 << at[7:5];
    wire        a_sw = |(at[12:8] & a_kb);                       // entry is the left operand
    wire [31:0] a_pt = norm({at[31:13], at[12:8] & ~a_kb, at[7:5] + 3'd1, at[4:0]});
    // B registers
    reg         cv, ce, cp, c_sw;
    reg [31:0]  ct, cd, c_pt;
    reg [D-1:0] match_vec, frees;
    // ---------------- B: decision
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
    reg  [D-1:0] sib_old;
    integer n;
    always @* for (n = 0; n < D; n = n + 1) sib_old[n] = sibling(bt[n], at);
    wire        sib_new = sibling(ct, at);
    wire [D-1:0] next_match_vec = (bv & ~rm_mask & sib_old) | (in_mask & {D{sib_new}});
    wire [D-1:0] next_frees = ~bv_next;
    wire        cand_bad = (PAR != 0) && cv && !(^{ce, cd, ct, cp});
    wire [32:0] rb = {1'b0, cd} + 33'h7FFF + {32'd0, cd[16]};
    // ---------------- C: one-hot entry read
    reg         c_add, c_e, c_swc;
    reg [D-1:0] c_oh;
    reg [31:0]  c_d, c_ptc;
    reg [31:0]  sel_d, sel_t;
    reg         sel_e, sel_p;
    always @* begin
        sel_d = 32'd0; sel_t = 32'd0; sel_e = 1'b0; sel_p = 1'b0;
        for (n = 0; n < D; n = n + 1) begin
            sel_d = sel_d | ({32{c_oh[n]}} & bd[n]);
            sel_e = sel_e | (c_oh[n] & be[n]);
            if (PAR != 0) begin
                sel_t = sel_t | ({32{c_oh[n]}} & bt[n]);
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
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pfault <= 1'b0; fault_q <= 1'b0; end
        else begin
            if (s_bad || head_bad || cand_bad || dent_bad || bvs_bad || qc_bad) pfault <= 1'b1;
            fault_q <= fault_c | pfault | ((PAR != 0) ? s_uf : 1'b0);
        end
    // ---------------- control state
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            qr <= 0; qr1 <= 1; qw <= 0; qc <= 0; cv <= 1'b0; match_vec <= 0; frees <= {D{1'b1}};
            bv <= 0; bv_s <= 0; r_v <= 1'b0; fault_c <= 1'b0; add <= 1'b0; c_add <= 1'b0; d_add <= 1'b0;
        end else begin
            // A -> B
            cv <= av && !head_bad;
            match_vec <= next_match_vec; frees <= next_frees;
            if (w_v) qw <= qw + 1'b1;
            if (use_q) begin qr <= qr1; qr1 <= qr1 + 1'b1; end
            qc <= qc + (w_v ? 1'b1 : 1'b0) - (use_q ? 1'b1 : 1'b0);
            if (w_v && qc == QD && !use_q) fault_c <= 1'b1;
            // B
            bv <= bv_next; bv_s <= bv_next;
            r_v <= cv && complete(ct);
            if (cmp_b && !hit_any && !fr_any) fault_c <= 1'b1;
            c_add <= remove_b && !cand_bad;
            // C / D -> adder
            if (PAR != 0) begin d_add <= c_add; add <= d_add && !dent_bad; end
            else add <= c_add;
        end
    end
    // ---------------- B: one-hot insert write, one write enable per entry
    genvar g;
    generate for (g = 0; g < D; g = g + 1) begin : g_ent
        always @(posedge clk) if (in_mask[g]) begin bt[g] <= ct; bd[g] <= cd; be[g] <= ce; bp[g] <= cp; end
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
        ct <= at; cd <= ad; ce <= ae; cp <= ~^{ae, ad, at}; c_pt <= a_pt; c_sw <= a_sw;
        // B: result register (one-hot insert write: generate below)
        r_row <= ct[28:13]; r_pos <= ct[31:29]; r_fp32 <= cd; r_bf16 <= rb[31:16]; r_e <= ce;
        r_p <= (PAR != 0) ? ~^{ct[28:13], ct[31:29], cd, rb[31:16], ce} : 1'b0;
        // B -> C
        c_oh <= hit_oh; c_d <= cd; c_e <= ce; c_swc <= c_sw; c_ptc <= c_pt;
        // C -> D (PAR) or C -> adder
        if (PAR != 0) begin
            d_d <= sel_d; d_t <= sel_t; d_e <= sel_e; d_p <= sel_p; d_cd <= c_d; d_ce <= c_e; d_sw <= c_swc; d_pt <= c_ptc;
            if (d_sw) begin add_a <= d_d; add_b <= d_cd; end else begin add_a <= d_cd; add_b <= d_d; end
            tag_in <= {d_pt, d_e | d_ce};
        end else begin
            if (c_swc) begin add_a <= sel_d; add_b <= c_d; end else begin add_a <= c_d; add_b <= sel_d; end
            tag_in <= {c_ptc, sel_e | c_e};
        end
    end
endmodule
