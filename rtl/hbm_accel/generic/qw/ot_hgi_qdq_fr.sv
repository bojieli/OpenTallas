`timescale 1ns/1ps
`default_nettype none
// ot_hgi_qdq_q FRONT child (q8 re-partition, 2026-10-13: the cluster parent is wires only; q7 put 14.3k own flops on a
// cluster clock spine that diverged to 1.79 ns insertion).  rec pin flops -> record binding -> S1 -> span pipe -> S3.
// Every port registered here: rec lands in f_rec; s1_v (= the accept strobe one cycle late), s3_v, the S3 bundle and
// nfault are flops.  Own reset relay.  Function = lines of ot_hgi_qdq_q before the record queue, unchanged.
module ot_hgi_qdq_fr #(
    parameter integer SPANPIPE = 1
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [682:0]  rec,
    output reg           s1_v,        // a record was accepted (cmd valid, one cycle late)
    output reg           s3_v,
    output wire [189:0]  s3,          // {el3, alo3, ahi3, olo3, ohi3, as3, os3, rs3, ws3, bpr3, nsl3, m3, hd3}
    output wire          nfault
);
    reg f_rst; reg [682:0] f_rec;
    always @(posedge clk) begin f_rst <= rst_n; f_rec <= rec; end
    wire [0:0] rr_n;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    wire [1408:0] cmd;
    ot_hgi_quant_record u_rec (.clk(clk), .rst_n(rr_n[0]), .rec(f_rec), .cmd(cmd), .nfault(nfault));
    reg s2_v;
    reg [127:0] s1_h; reg [255:0] s1_a, s1_o;
    always @(posedge clk) begin s1_h <= cmd[128:1]; s1_a <= cmd[385 +: 256]; s1_o <= cmd[1153 +: 256]; end
    // S2: field / fast flags and spans (the multiplies are this stage's only arithmetic)
    wire [5:0] op1 = s1_h[123:118];
    wire [19:0] an1 = s1_a[67:48], am1 = s1_a[87:68], on1 = s1_o[67:48], om1 = s1_o[87:68];
    wire [31:0] ars1 = s1_a[119:88], ors1 = s1_o[119:88];
    wire [39:0] ab1 = s1_a[47:8], ob1 = s1_o[47:8];
    wire fld1 = s1_h[127:124] == 4 && op1 >= 4 && op1 <= 6 && s1_h[99:93] == 7'b0010001 && !s1_h[92] &&
                (op1 != 6 || s1_h[71:64] == 16) && s1_a[1:0] == 1 && s1_o[1:0] == 1 && s1_a[4:2] == 0 &&
                (s1_o[4:2] == 0 || s1_o[4:2] == 1) && !s1_o[5] && am1 != 0 && am1 == om1 && an1 != 0 && an1 == on1 &&
                (op1 == 6 ? an1[3:0] == 0 : an1[4:0] == 0);
    wire fast1 = !s1_a[5] && s1_a[135:120] <= 16'd1 && s1_o[135:120] <= 16'd1 && ab1[2:0] == 0 && ob1[2:0] == 0 &&
                 an1[2:0] == 0 && (am1 == 20'd1 || (ars1[2:0] == 0 && ors1[2:0] == 0 && ars1 >= {12'd0, an1} && ors1 >= {12'd0, on1}));
    reg fld2, fast2, same2; reg [63:0] aend2, oend2; reg [39:0] ab2, ob2; reg [19:0] n2, m2; reg [31:0] ars2, ors2;
    reg [17:0] hd2;                                   // {unit 4, op 6, block 8}: the decode's only header fields
    generate if (SPANPIPE == 0) begin : g_span_legacy
    always @(posedge clk) begin
        fld2 <= fld1; fast2 <= fast1; same2 <= ars1 == ors1; ab2 <= ab1; ob2 <= ob1; n2 <= an1; m2 <= am1;
        ars2 <= ars1; ors2 <= ors1; hd2 <= {s1_h[127:118], s1_h[71:64]};
        aend2 <= {24'd0, ab1} + (64'(am1) - 64'd1) * 64'(ars1) + 64'(an1) - 64'd1;
        oend2 <= {24'd0, ob1} + (64'(om1) - 64'd1) * 64'(ors1) + 64'(on1) - 64'd1;
    end
    end else begin : g_span_pipe
        // Physical stages: row decrement -> ten 2x32 partial products -> adjacent pairs -> nibble pairs -> pair sum ->
        // final product -> one end-address add.  The maximum legal product is 52 bits (20x32), so no 64-bit
        // multiply or multiply-plus-add cone remains.  Invalid zero-row descriptors still fail fld1.
        reg [19:0] rows_a, rows_o;
        reg [31:0] stride_a, stride_o;
        reg [33:0] pa [0:9], po [0:9];
        reg [35:0] nibble_a [0:4], nibble_o [0:4];
        reg [39:0] pair_a [0:1], pair_o [0:1]; reg [35:0] last_a, last_o;
        reg [47:0] sum_a, sum_o; reg [35:0] last_a2, last_o2;
        reg [51:0] prod_a, prod_o;
        reg [40:0] base_n_a, base_n_o, offset_a [0:5], offset_o [0:5];
        reg [2:0] flags [0:6]; reg [39:0] bases_a [0:6], bases_o [0:6];
        reg [19:0] ns [0:6], ms [0:6]; reg [31:0] rss_a [0:6], rss_o [0:6]; reg [17:0] headers [0:6];
        integer k;
        always @(posedge clk) begin
            rows_a <= am1 - 20'd1; rows_o <= om1 - 20'd1; stride_a <= ars1; stride_o <= ors1;
            base_n_a <= {1'b0, ab1} + 41'(an1); base_n_o <= {1'b0, ob1} + 41'(on1);
            offset_a[0] <= base_n_a - 41'd1; offset_o[0] <= base_n_o - 41'd1;
            for (k = 1; k < 6; k = k + 1) begin offset_a[k] <= offset_a[k-1]; offset_o[k] <= offset_o[k-1]; end
            for (k = 0; k < 10; k = k + 1) begin
                pa[k] <= rows_a[k*2 +: 2] * stride_a; po[k] <= rows_o[k*2 +: 2] * stride_o;
            end
            for (k = 0; k < 5; k = k + 1) begin
                nibble_a[k] <= 36'(pa[k*2]) + (36'(pa[k*2+1]) << 2);
                nibble_o[k] <= 36'(po[k*2]) + (36'(po[k*2+1]) << 2);
            end
            pair_a[0] <= 40'(nibble_a[0]) + (40'(nibble_a[1]) << 4); pair_o[0] <= 40'(nibble_o[0]) + (40'(nibble_o[1]) << 4);
            pair_a[1] <= 40'(nibble_a[2]) + (40'(nibble_a[3]) << 4); pair_o[1] <= 40'(nibble_o[2]) + (40'(nibble_o[3]) << 4);
            last_a <= nibble_a[4]; last_o <= nibble_o[4];
            sum_a <= 48'(pair_a[0]) + (48'(pair_a[1]) << 8); sum_o <= 48'(pair_o[0]) + (48'(pair_o[1]) << 8);
            last_a2 <= last_a; last_o2 <= last_o;
`ifdef OT_QDQ_SPAN_MUT   // bench mutant only (tb_hgi_qdq_span_equiv must FAIL): rows[19:16] partial dropped
            prod_a <= 52'(sum_a); prod_o <= 52'(sum_o);
`else
            prod_a <= 52'(sum_a) + (52'(last_a2) << 16); prod_o <= 52'(sum_o) + (52'(last_o2) << 16);
`endif
            aend2 <= 64'(prod_a) + 64'(offset_a[4]); oend2 <= 64'(prod_o) + 64'(offset_o[4]);
            flags[0] <= {fld1, fast1, ars1 == ors1}; bases_a[0] <= ab1; bases_o[0] <= ob1;
            ns[0] <= an1; ms[0] <= am1; rss_a[0] <= ars1; rss_o[0] <= ors1; headers[0] <= {s1_h[127:118], s1_h[71:64]};
            for (k = 1; k < 7; k = k + 1) begin
                flags[k] <= flags[k-1]; bases_a[k] <= bases_a[k-1]; bases_o[k] <= bases_o[k-1];
                ns[k] <= ns[k-1]; ms[k] <= ms[k-1]; rss_a[k] <= rss_a[k-1]; rss_o[k] <= rss_o[k-1]; headers[k] <= headers[k-1];
            end
        end
        always @* begin
            {fld2, fast2, same2} = flags[6]; ab2 = bases_a[6]; ob2 = bases_o[6]; n2 = ns[6]; m2 = ms[6];
            ars2 = rss_a[6]; ors2 = rss_o[6]; hd2 = headers[6];
        end
    end endgenerate
    // S3: eligibility; everything an entry needs, narrowed to the slice address space
    reg el3; reg [17:0] alo3, ahi3, olo3, ohi3; reg [14:0] as3, os3, rs3, ws3; reg [15:0] bpr3; reg [2:0] nsl3;
    reg [19:0] m3; reg [17:0] hd3;
    always @(posedge clk) begin
        el3 <= fld2 && fast2 && aend2 < 64'd262144 && oend2 < 64'd262144 &&
               ((aend2 < {24'd0, ob2}) || (oend2 < {24'd0, ab2}) || (same2 && ab2 == ob2));
        alo3 <= ab2[17:0]; ahi3 <= aend2[17:0]; olo3 <= ob2[17:0]; ohi3 <= oend2[17:0];
        as3 <= ab2[17:3]; os3 <= ob2[17:3]; rs3 <= ars2[17:3]; ws3 <= ors2[17:3];
        bpr3 <= 16'((n2 + 20'd31) >> 5); nsl3 <= (n2[4:0] == 5'd0) ? 3'd4 : {1'b0, n2[4:3]};
        m3 <= m2; hd3 <= hd2;
    end
    generate if (SPANPIPE == 0) begin : g_valid_legacy
        always @(posedge clk or negedge rr_n[0])
            if (!rr_n[0]) begin s1_v <= 0; s2_v <= 0; s3_v <= 0; end
            else begin s1_v <= cmd[0]; s2_v <= s1_v; s3_v <= s2_v; end
    end else begin : g_valid_pipe
        reg [5:0] span_v;
        always @(posedge clk or negedge rr_n[0])
            if (!rr_n[0]) begin s1_v <= 0; span_v <= 0; s2_v <= 0; s3_v <= 0; end
            else begin s1_v <= cmd[0]; span_v <= {span_v[4:0], s1_v}; s2_v <= span_v[5]; s3_v <= s2_v; end
    end endgenerate
    assign s3 = {el3, alo3, ahi3, olo3, ohi3, as3, os3, rs3, ws3, bpr3, nsl3, m3, hd3};
endmodule
`default_nettype wire
