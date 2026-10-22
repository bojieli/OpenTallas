`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// RTLGAP-SUKV 10-21 (G-L2-L20-HW, opt-in): ot_s81sl_cmp_pool -- the DeepSeek-V4.1 compressor gate-softmax POOL
// (attn.cmp.pool, kv-source layers with compress ratio 2: L2 / L8 / L14) on the KV leaf's 256-b VM extension port.
// Golden (tools/s81_dv/dv_layer_fixtures.py compressor(), hdc_golden_v41 chunk8), per feature d of D = 512, slots i =
// 0 (older, the open-group slot of position p-1) and 1 (position p):
//     m   = max(s0, s1)                     (first maximum; equal values select s0 -- the value is the same)
//     e_i = exp(s_i + (-m))                 (hdc_golden exp: the polynomial of ot_hdc_v41x_exp, as attention's)
//     den = e0 + e1                         (seqsum order)
//     p_i = e_i / den                       (IEEE binary32 RNE, canonical +0: ot_dsrom_su_fdiv_f12, as attention's)
//     y   = (kv0 * p0) + (kv1 * p1)         (seqsum of the products, kv * p operand order)
//     out = bf16(y) widened to FP32         (the CN job's operand: rms_parts(to_bf16(pooled)))
// Every arithmetic step is an existing qualified primitive: ot_dsrom_qadd #(LA) (the KVE adder), ot_hdc_qmul_lat #(LM)
// (the KVE multiplier), ot_hdc_v41x_exp #(LM, LA) and ot_dsrom_su_fdiv_f12 (the SU attention softmax's exp / divide).
// The only new combinational function is the binary32 max compare (sign-magnitude order).
//
// Static calendar (no ready / credit / data-dependent issue).  One job = 64 groups of 8 features (one 256-b VM row
// pair a group per operand).  Slot record s (base B_s, 4-aligned, 128-b VM rows): kv rows B_s + 4 r + 2 h (r = 0..31,
// h = 0..1), score rows B_s + 128 + 4 r + 2 h -- the operand layout compressor_kv / compressor_score (32 + 32 rows of
// 512 b).  Edge e = 4 g + j of the job issues ONE row-pair read:
//     j = 0: score slot 0 of group g      j = 1: score slot 1 of group g          (g < 64)
//     j = 2: kv slot 0 of group g - K     j = 3: kv slot 1 of group g - K         (0 <= g - K < 64)
// K = KLAG groups: the kv of group g is read so that it reaches the lanes 1..3 edges after the lanes' probability
// p0 / p1 of group g (the offset is independent of the VM read latency, since both reads take the same fixed path).
// The kv therefore never waits in a buffer: 4 (64 + K) issue edges, 256 reads, 64 row-pair writes
// (out base + 4 r + 2 h), out base = one slot's kv base (in place: kv of a group is read before its result is
// written) or a region disjoint from both slot records.
// Responses return in issue order at the VM's fixed latency; the role of each response is the head of a 2-bit tag
// queue written at issue (sequencing only: no flow control, an overflow / underflow is a sticky fault).
// Lanes: 8 x ot_s81sl_cmp_pool_lane (one FP32 feature each), every one with its own pin flops, reset relay and
// time-shared units (one adder for both subtractions, one exp, one divider, one multiplier for both items: a group's
// two items occupy two consecutive edges of a 4-edge group period, so no unit is ever asked twice in one edge).
// Faults (sticky): a malformed command, a tag-queue error, a lane arithmetic fault (exp / div / add / mul fault
// convention), a kv arriving when its probability is not held (calendar drift).
// MUT (bench negative controls only; 0 in every build): 1 den = e0 + e0; 2 y = kv1 * p0 + kv0 * p1 (slot swap);
// 3 no bf16 rounding (truncation); 4 max picks s0 always; 5 KLAG - 2 (the calendar drifts: kv before p).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_cmp_pool #(
    parameter integer LM = 5, LA = 4, MUT = 0
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         start,          // one-edge command pulse (decoded by the leaf)
    input  wire [9:0]   b0,             // slot 0 (older) record base, 128-b rows
    input  wire [9:0]   b1,             // slot 1 (newer) record base
    input  wire [9:0]   ob,             // output base
    output reg          busy,
    output reg          done,
    output reg          fault,
    output reg          x_rv,
    output reg  [9:0]   x_ra,
    input  wire         x_qv,
    input  wire [255:0] x_qd,
    output reg          x_wv,
    output reg  [9:0]   x_wa,
    output reg  [7:0]   x_wm,
    output reg  [255:0] x_wd,
    output wire [255:0] dbg_y32,        // bench probe: the 8 lanes' FP32 y of the group being written
    output wire [15:0]  dbg_age
);
    // lane latencies (all fixed): sub LA, exp DE, den LA, div DD; the kv lag in groups
    localparam integer DE = 7 * LM + 8 * LA + 4;
    localparam integer DD = 33;
    // p0 of group g is held from (sc0 response edge in the lane's pin flop) + TP0 + 1, see ot_s81sl_cmp_pool_lane
    localparam integer TP0 = 2 + LA + DE + 1 + LA + DD;
    localparam integer KLAG0 = (TP0 + 1 - 2 + 3) / 4;               // ceil((TP0 + 1 - 2) / 4)
    localparam integer KLAG = (MUT == 5) ? KLAG0 - 2 : KLAG0;
    localparam integer NG = 64;
    localparam integer NE = 4 * (NG + KLAG);                         // issue edges
`ifndef SYNTHESIS
    // kv0 of group g reaches the lane at r + 4 KLAG + 2: after p0 is held (r + TP0 + 1) and before the next group's p0
    // replaces it (r + TP0 + 4)
    initial if (MUT != 5 && (4 * KLAG + 2 < TP0 + 1 || 4 * KLAG + 2 > TP0 + 3))
        $fatal(1, "ot_s81sl_cmp_pool: no kv lag fits TP0 %0d", TP0);
`endif

    reg rr0, rr1;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rn = rr1;

    reg [9:0]  sb0, sb1, sob;
    reg [9:0]  ie;            // issue edge
    reg [15:0] age;
    reg        issuing;
    reg [6:0]  nout;
    reg        fin;
    assign dbg_age = age;
    // ---------------------------------------------------------------- issue calendar
    wire [7:0] ig = ie[9:2];
    wire [1:0] ij = ie[1:0];
    wire [7:0] kg = ig - KLAG[7:0];
    wire       sc_slot = (ij[1] == 1'b0) && (ig < NG);
    wire       kv_slot = (ij[1] == 1'b1) && (ig >= KLAG) && (kg < NG);
    wire [7:0] gg = sc_slot ? ig : kg;                               // group of this read
    wire [9:0] rofs = {3'd0, gg[5:1], 2'b00} + {8'd0, gg[0], 1'b0};  // 4 r + 2 h  (r = g >> 1, h = g & 1)
    wire [9:0] rbase = ij[0] ? sb1 : sb0;
    wire [9:0] raddr = rbase + (sc_slot ? 10'd128 : 10'd0) + rofs;
    // ---------------------------------------------------------------- tag queue (in-order responses)
    reg [1:0] tq [0:7];
    reg [2:0] tw, tr; reg [3:0] tn;
    wire      push = issuing && (sc_slot || kv_slot);
    wire      pop  = x_qv;
    // ---------------------------------------------------------------- command check
    wire [10:0] x0 = {1'b0, b0}, x1 = {1'b0, b1}, xo = {1'b0, ob};
    wire [10:0] e0 = x0 + 11'd256, e1 = x1 + 11'd256, eo = xo + 11'd128;
    wire bad_cmd = (b0[1:0] != 2'd0) || (b1[1:0] != 2'd0) || (ob[1:0] != 2'd0) || (b0 > 10'd768) || (b1 > 10'd768) ||
                   (ob > 10'd896) || (b0 == b1) ||
                   ((x0 < x1) ? (e0 > x1) : (e1 > x0)) ||                                     // slot records overlap
                   !((ob == b0) || (ob == b1) || (((eo <= x0) || (xo >= e0)) && ((eo <= x1) || (xo >= e1))));
    // ---------------------------------------------------------------- lanes
    reg        l_v; reg [1:0] l_role; reg [255:0] l_d;              // response register (fans out to 8 lanes)
    wire [7:0] lo_v, lf;
    wire [255:0] lo_y, lo_y32;
    genvar l;
    generate for (l = 0; l < 8; l = l + 1) begin : g_lane
        ot_s81sl_cmp_pool_lane #(.LM(LM), .LA(LA), .MUT(MUT)) u_l (
            .clk(clk), .rst_n(rst_n), .i_v(l_v), .i_role(l_role), .i_d(l_d[32 * l +: 32]),
            .o_v(lo_v[l]), .o_y(lo_y[32 * l +: 32]), .o_y32(lo_y32[32 * l +: 32]), .fault(lf[l]));
    end endgenerate
    assign dbg_y32 = lo_y32;
    integer i;
    always @(posedge clk) begin
        l_d <= x_qd; l_role <= tq[tr];
        if (push) tq[tw] <= {kv_slot, ij[0]};                        // role = {kv, slot}: 0 sc0, 1 sc1, 2 kv0, 3 kv1
        x_ra <= raddr;
        x_wd <= lo_y; x_wa <= sob + {nout[6:1], 2'b00} + {8'd0, nout[0], 1'b0}; x_wm <= 8'hFF;
    end
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            busy <= 1'b0; done <= 1'b0; fault <= 1'b0; x_rv <= 1'b0; x_wv <= 1'b0; issuing <= 1'b0; ie <= 10'd0;
            age <= 16'd0; nout <= 7'd0; tw <= 3'd0; tr <= 3'd0; tn <= 4'd0; l_v <= 1'b0; sb0 <= 10'd0; sb1 <= 10'd0;
            sob <= 10'd0; fin <= 1'b0;
        end else begin
            done <= 1'b0; x_rv <= 1'b0; x_wv <= 1'b0; l_v <= pop && busy;
            if (start) begin
                if (busy || bad_cmd) fault <= 1'b1;
                else begin
                    busy <= 1'b1; issuing <= 1'b1; ie <= 10'd0; age <= 16'd0; nout <= 7'd0;
                    sb0 <= b0; sb1 <= b1; sob <= ob; tw <= 3'd0; tr <= 3'd0; tn <= 4'd0;
                end
            end
            if (busy) begin
                age <= age + 16'd1;
                if (issuing) begin
                    x_rv <= sc_slot || kv_slot;
                    ie <= ie + 10'd1;
                    if (ie == NE - 1) issuing <= 1'b0;
                end
                if (push) tw <= tw + 3'd1;
                if (pop) tr <= tr + 3'd1;
                tn <= tn + {3'd0, push} - {3'd0, pop};
                if ((pop && tn == 0 && !push) || (tn == 4'd8 && push && !pop)) fault <= 1'b1;
                if (|lf) fault <= 1'b1;
                if (lo_v[0]) begin
                    if (lo_v != 8'hFF) fault <= 1'b1;                   // lanes are in lockstep
                    x_wv <= 1'b1;
                    nout <= nout + 7'd1;
                    if (nout == NG - 1) fin <= 1'b1;
                end
                // the last pair write leaves x_w* one edge after its lane result: busy (the leaf's port select) holds
                // through that edge
                if (fin) begin fin <= 1'b0; busy <= 1'b0; done <= 1'b1; end
            end else if (pop || (|lo_v)) fault <= 1'b1;
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// One feature lane.  Edge numbering relative to r = the edge the lane's pin flop holds score slot 0 (role 0):
//   r+1  pin flop holds s1 (role 1): m = max(s0, s1), s0h, s1h registered (valid av at r+2)
//   r+2  sub adder issue item 0: s0h + (-m);   r+3 item 1: s1h + (-m)
//   r+2+LA       exp issue item 0 (item 1 next edge)
//   r+2+LA+DE    exp out item 0 (e0), r+3+LA+DE e1 -> den adder issue add(e0, e1) at r+3+LA+DE
//   r+3+2LA+DE   den out; div issue item 0 (e0 delayed LA+1) at that edge, item 1 next edge
//   r+3+2LA+DE+DD = r + TP0: p0 out (captured, held from r + TP0 + 1); p1 one edge later
//   kv0 / kv1 (roles 2 / 3) in the pin flop at r + 4 KLAG + 2 / + 3: mul issue kv * p (held)
//   +LM  products m0 / m1;  fin adder add(m0, m1) at the m1 edge; +LA y (FP32) -> bf16 -> o_y (one edge)
// Item tags are the "second of a back-to-back pair" bit of each stage's valid (groups are >= 4 edges apart).
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_cmp_pool_lane #(
    parameter integer LM = 5, LA = 4, MUT = 0
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        i_v,
    input  wire [1:0]  i_role,
    input  wire [31:0] i_d,
    output reg         o_v,
    output reg  [31:0] o_y,
    output reg  [31:0] o_y32,
    output reg         fault
);
    localparam integer DE = 7 * LM + 8 * LA + 4;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rn = rr1;
    function automatic gt;                                          // binary32 a > b (sign-magnitude order)
        input [31:0] a, b;
        begin
            if (a[30:0] == 31'd0 && b[30:0] == 31'd0) gt = 1'b0;
            else if (a[31] != b[31]) gt = !a[31];
            else if (!a[31]) gt = a[30:0] > b[30:0];
            else gt = a[30:0] < b[30:0];
        end
    endfunction
    function automatic [31:0] bf16;
        input [31:0] x;
        reg [32:0] s;
        begin
            s = {1'b0, x} + 33'h7FFF + {32'd0, x[16]};
            bf16 = {s[31:16], 16'd0};
        end
    endfunction
    // pin flops
    reg v_q; reg [1:0] r_q; reg [31:0] d_q;
    always @(posedge clk) begin r_q <= i_role; d_q <= i_d; end
    always @(posedge clk or negedge rn) if (!rn) v_q <= 1'b0; else v_q <= i_v;
    wire sc0 = v_q && r_q == 2'd0, sc1 = v_q && r_q == 2'd1, kv0 = v_q && r_q == 2'd2, kv1 = v_q && r_q == 2'd3;
    // ---------------------------------------------------------------- max
    reg [31:0] s0, s0h, s1h, mx; reg av, av1;
    always @(posedge clk) begin
        if (sc0) s0 <= d_q;
        if (sc1) begin s0h <= s0; s1h <= d_q; mx <= (MUT != 4 && gt(d_q, s0)) ? d_q : s0; end
    end
    always @(posedge clk or negedge rn) if (!rn) begin av <= 1'b0; av1 <= 1'b0; end else begin av <= sc1; av1 <= av; end
    // ---------------------------------------------------------------- sub (one adder, two items)
    wire sv = av || av1;
    wire [31:0] sa = av ? s0h : s1h;
    wire [31:0] sd; wire sf;
    ot_dsrom_qadd #(.LAT(LA)) u_sub (clk, rn, sv, sa, {~mx[31], mx[30:0]}, sd, sf);
    wire [LA:0] svd;
    ot_hdc_vline #(.D(LA)) u_svd (.clk(clk), .rst_n(rn), .v(sv), .vd(svd));
    // ---------------------------------------------------------------- exp
    wire ev; wire [31:0] ey; wire ef;
    ot_hdc_v41x_exp #(.LM(LM), .LA(LA)) u_exp (.clk(clk), .rst_n(rn), .v(svd[LA]), .x(sd), .y(ey), .vo(ev), .fault(ef));
    reg ev_d; reg [31:0] e0h;
    always @(posedge clk or negedge rn) if (!rn) ev_d <= 1'b0; else ev_d <= ev;
    wire e_item1 = ev && ev_d;
    always @(posedge clk) if (ev && !ev_d) e0h <= ey;
    // ---------------------------------------------------------------- den = e0 + e1 (MUT 1: e0 + e0)
    wire [31:0] den; wire df;
    ot_dsrom_qadd #(.LAT(LA)) u_den (clk, rn, e_item1, e0h, (MUT == 1) ? e0h : ey, den, df);
    wire [LA:0] dvd;
    ot_hdc_vline #(.D(LA)) u_dvd (.clk(clk), .rst_n(rn), .v(e_item1), .vd(dvd));
    // e stream delayed LA + 1: item 0 meets den's output edge, item 1 the next
    wire [31:0] ed; wire edv;
    ot_hdc_delay #(.W(32), .D(LA + 1)) u_ed (.clk(clk), .rst_n(rn), .d(ey), .q(ed));
    ot_hdc_delay #(.W(1), .D(LA + 1), .RESET(1)) u_edv (.clk(clk), .rst_n(rn), .d(ev), .q(edv));
    reg [31:0] denh; reg dh_v;
    always @(posedge clk) if (dvd[LA]) denh <= den;
    always @(posedge clk or negedge rn) if (!rn) dh_v <= 1'b0; else dh_v <= dvd[LA];
    wire [31:0] dsel = dvd[LA] ? den : denh;
    // ---------------------------------------------------------------- p_i = e_i / den
    wire pv; wire [31:0] py; wire pf;
    ot_dsrom_su_fdiv_f12 #(.NR(0)) u_div (.clk(clk), .rst_n(rn), .v(edv), .a(ed), .b(dsel), .y(py), .vo(pv), .fault(pf));
    reg pv_d; reg [31:0] p0h, p1h; reg p0f, p1f;
    always @(posedge clk or negedge rn) if (!rn) pv_d <= 1'b0; else pv_d <= pv;
    always @(posedge clk) begin
        if (pv && !pv_d) p0h <= py;
        if (pv && pv_d) p1h <= py;
    end
    // ---------------------------------------------------------------- products kv_i * p_i (one multiplier), y = m0 + m1
    wire mv = kv0 || kv1;
    wire [31:0] mb = (MUT == 2) ? (kv0 ? p1h : p0h) : (kv0 ? p0h : p1h);
    wire [31:0] my; wire mf;
    ot_hdc_qmul_lat #(LM) u_mul (clk, rn, mv, d_q, mb, my, mf);
    wire [LM:0] mvd;
    ot_hdc_vline #(.D(LM)) u_mvd (.clk(clk), .rst_n(rn), .v(mv), .vd(mvd));
    reg mvd_d; reg [31:0] m0h;
    always @(posedge clk or negedge rn) if (!rn) mvd_d <= 1'b0; else mvd_d <= mvd[LM];
    wire m_item1 = mvd[LM] && mvd_d;
    always @(posedge clk) if (mvd[LM] && !mvd_d) m0h <= my;
    wire [31:0] yy; wire yf;
    ot_dsrom_qadd #(.LAT(LA)) u_fin (clk, rn, m_item1, m0h, my, yy, yf);
    wire [LA:0] yvd;
    ot_hdc_vline #(.D(LA)) u_yvd (.clk(clk), .rst_n(rn), .v(m_item1), .vd(yvd));
    always @(posedge clk) if (yvd[LA]) begin o_y <= (MUT == 3) ? {yy[31:16], 16'd0} : bf16(yy); o_y32 <= yy; end
    // ---------------------------------------------------------------- valid / fault
    always @(posedge clk or negedge rn) begin
        if (!rn) begin o_v <= 1'b0; fault <= 1'b0; p0f <= 1'b0; p1f <= 1'b0; end
        else begin
            o_v <= yvd[LA];
            // p held flags: set at capture, consumed by the matching kv; a kv without its p, or a p overwritten before
            // its kv, is calendar drift (sticky fault)
            if (pv && !pv_d) begin if (p0f) fault <= 1'b1; p0f <= 1'b1; end
            else if (kv0) begin if (!p0f) fault <= 1'b1; p0f <= 1'b0; end
            if (pv && pv_d) begin if (p1f) fault <= 1'b1; p1f <= 1'b1; end
            else if (kv1) begin if (!p1f) fault <= 1'b1; p1f <= 1'b0; end
            if ((pv && !pv_d && kv0) || (pv && pv_d && kv1)) fault <= 1'b1;
            if (sf || ef || df || pf || mf || yf) fault <= 1'b1;
        end
    end
endmodule
