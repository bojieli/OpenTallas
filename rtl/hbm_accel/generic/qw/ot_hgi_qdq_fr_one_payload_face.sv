`timescale 1ns/1ps
`default_nettype none
// ot_hgi_qdq_q FRONT child (q8 re-partition, 2026-10-13: the cluster parent is wires only; q7 put 14.3k own flops on a
// cluster clock spine that diverged to 1.79 ns insertion).  rec pin flops -> record binding -> S1 -> span pipe -> S3.
// Every port registered here: rec lands in f_rec; s1_v (= the accept strobe one cycle late), s3_v, the S3 bundle and
// nfault are flops.  Own reset relay.  Function = lines of ot_hgi_qdq_q before the record queue, unchanged.
module ot_hgi_qdq_fr_one_payload_face #(parameter integer MUT_END=0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [682:0]  rec,
    output reg           s1_v,        // a record was accepted (cmd valid, one cycle late)
    output reg           one_s1,
    output wire [189:0]  payload,          // {el3, alo3, ahi3, olo3, ohi3, as3, os3, rs3, ws3, bpr3, nsl3, m3, hd3}
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
    wire [18:0] ae1 = {1'b0, ab1[17:0]} + {1'b0, an1[17:0]} - 19'd1;
    wire [18:0] oe1 = {1'b0, ob1[17:0]} + {1'b0, on1[17:0]} - 19'd1;
    wire eligible1 = fld1 && fast1 && ab1[39:18]==0 && ob1[39:18]==0 && an1[19:18]==0 && on1[19:18]==0 && !ae1[18] && !oe1[18] &&
                      (ae1 < {1'b0,ob1[17:0]} || oe1 < {1'b0,ab1[17:0]} || (ars1 == ors1 && ab1 == ob1));
    // Dedicated per-output FFs survive identical-bit merging via ot_keep_regs.tcl.
    // Actual closed predecessor payload[139] Q224.6 exceededQ220; olo/os aliases
    // need separate face anchors while retaining the same arithmetic and edge.
    (* keep = "true", dont_touch = "true" *) reg [189:0] payload_face;
    assign payload = payload_face;
    // Final payload is launched at S2. The retirement leaf only captures this payload.
    always @(posedge clk) begin
        payload_face <= {eligible1,ab1[17:0],(ae1[17:0] ^ 18'(MUT_END)),ob1[17:0],oe1[17:0],
                    ab1[17:3],ob1[17:3],ars1[17:3],ors1[17:3],16'((an1+20'd31)>>5),
                    ((an1[4:0]==0)?3'd4:{1'b0,an1[4:3]}),am1,{s1_h[127:118],s1_h[71:64]}};
    end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) s1_v <= 0;
        else s1_v <= cmd[0];
endmodule
`default_nettype wire
