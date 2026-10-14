`timescale 1ns/1ps
`default_nettype none
// ot_hgi_qdq_q FRONT child (q8 re-partition, 2026-10-13: the cluster parent is wires only; q7 put 14.3k own flops on a
// cluster clock spine that diverged to 1.79 ns insertion).  rec pin flops -> record binding -> S1 -> span pipe -> S3.
// Every port registered here: rec lands in f_rec; s1_v (= the accept strobe one cycle late), s3_v, the S3 bundle and
// nfault are flops.  Own reset relay.  Function = lines of ot_hgi_qdq_q before the record queue, unchanged.
module ot_hgi_qdq_fr_one_s2 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [682:0]  rec,
    output reg           s1_v,        // a record was accepted (cmd valid, one cycle late)
    output reg           s2_v,
    output wire          one,
    output reg           one_s1,
    output wire [332:0]  s2,          // {el3, alo3, ahi3, olo3, ohi3, as3, os3, rs3, ws3, bpr3, nsl3, m3, hd3}
    output wire          nfault
);
    reg f_rst; reg [682:0] f_rec;
    always @(posedge clk) begin f_rst <= rst_n; f_rec <= rec; end
    wire [0:0] rr_n;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(f_rst), .rst_n(rr_n));
    wire [1408:0] cmd;
    ot_hgi_quant_record u_rec (.clk(clk), .rst_n(rr_n[0]), .rec(f_rec), .cmd(cmd), .nfault(nfault));

    reg [127:0] s1_h; reg [255:0] s1_a, s1_o;
    always @(posedge clk) begin
        s1_h <= cmd[128:1]; s1_a <= cmd[385 +: 256]; s1_o <= cmd[1153 +: 256];
        one_s1 <= cmd[453 +: 20] == 20'd1 && cmd[1221 +: 20] == 20'd1;
    end
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
    // Only classify equal one-row descriptors; everything else retains the closed general path.
    reg one2;
    always @(posedge clk) begin
        fld2 <= fld1; fast2 <= fast1; same2 <= ars1 == ors1; ab2 <= ab1; ob2 <= ob1; n2 <= an1; m2 <= am1;
        ars2 <= ars1; ors2 <= ors1; hd2 <= {s1_h[127:118], s1_h[71:64]};
        // 41-bit bounds include overflow above the VM address space; no product cone.
        aend2 <= 64'({1'b0, ab1} + 41'(an1) - 41'd1);
        oend2 <= 64'({1'b0, ob1} + 41'(on1) - 41'd1);
        one2 <= am1 == 20'd1 && om1 == 20'd1;
    end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin s1_v <= 0; s2_v <= 0; end
        else begin s1_v <= cmd[0]; s2_v <= s1_v; end
    assign one = one2;
    assign s2 = {fld2, fast2, same2, aend2, oend2, ab2, ob2, n2, m2, ars2, ors2, hd2};
endmodule
`default_nettype wire
