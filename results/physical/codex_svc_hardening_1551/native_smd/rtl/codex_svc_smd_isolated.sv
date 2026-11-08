module codex_svc_smd_isolated #(
    parameter integer LPH = 16, TAIL = 64, LM = 5, LA = 4, STALEDEN = 0
) (
    input  wire        clk,
    input  wire        rst_in,
    input  wire [2:0]  cfg_p,                          // the pair: lanes 2 p, 2 p + 1 of the head
    input  wire        i_pv,                           // a PV vector's two lanes
    input  wire [63:0] i_pa,
    input  wire        i_dv,                           // den
    input  wire [31:0] i_den,
    input  wire        i_csv,                          // cos / sin pair i_csi
    input  wire [4:0]  i_csi,
    input  wire [63:0] i_csd,
    output reg         o_ov,
    output reg  [31:0] o_o,                            // {lane 2 p + 1, lane 2 p} BF16
    output wire        o_f                             // sticky: a tail vector before its cos / sin
);
    localparam integer NPV = 512 / LPH;
    localparam integer D_DIV = 33;
    localparam integer DR = D_DIV + 1 + LM + LA + 1;
    localparam integer UT = (512 - TAIL) / LPH;        // first tail vector (28)
    reg f_local;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    wire rst_n = rr1;
    // pin flops
    reg        piv, dvq, csv;
    reg [63:0] pa, csd;
    reg [31:0] dnq;
    reg [4:0]  csi;
    reg [2:0]  p;
    always @(posedge clk) begin pa <= i_pa; dnq <= i_den; csd <= i_csd; csi <= i_csi; p <= cfg_p; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin piv <= 1'b0; dvq <= 1'b0; csv <= 1'b0; end
                                           else begin piv <= i_pv; dvq <= i_dv; csv <= i_csv; end
    // the pair's cos / sin for the TAIL / LPH tail vectors (slot = vector - UT)
    reg [31:0] ccos [0:3];
    reg [31:0] csin [0:3];
    reg [2:0]  csn;                                    // pairs of the current set received
    always @(posedge clk) if (csv && csi[2:0] == p) begin ccos[csi[4:3]] <= csd[63:32]; csin[csi[4:3]] <= csd[31:0]; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) csn <= 3'd0;
        else if (csv && csi == 5'd0) csn <= (p == 3'd0) ? 3'd1 : 3'd0;
        else if (csv && csi[2:0] == p) csn <= csn + 3'd1;
    // den (STALEDEN: the bench's negative control loads it on the first den after reset only)
    reg [31:0] denl;
    reg        den_seen;
    always @(posedge clk or negedge rst_n) if (!rst_n) den_seen <= 1'b0; else if (dvq) den_seen <= 1'b1;
    always @(posedge clk) if (dvq && !(STALEDEN != 0 && den_seen)) denl <= dnq;
    // pv / den -> BF16
    reg [6:0] ucnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) ucnt <= 7'd0;
        else if (piv) ucnt <= (ucnt + 7'd1 == NPV) ? 7'd0 : ucnt + 7'd1;
    end
    wire [DR:0] dv;
    ot_hdc_vline #(.D(DR)) u_dv (.clk(clk), .rst_n(rst_n), .v(piv), .vd(dv));
    wire [6:0] u_q, u_r, u_rd;
    ot_hdc_delay #(.W(7), .D(D_DIV)) u_ul (.clk(clk), .rst_n(rst_n), .d(ucnt), .q(u_q));
    ot_hdc_delay #(.W(7), .D(1)) u_ul1 (.clk(clk), .rst_n(rst_n), .d(u_q), .q(u_r));
    ot_hdc_delay #(.W(7), .D(LM + LA)) u_urd (.clk(clk), .rst_n(rst_n), .d(u_r), .q(u_rd));
    wire [63:0] qd;
    reg  [31:0] o0;
    genvar l;
    generate for (l = 0; l < 2; l = l + 1) begin : g_dv
        wire fd;
        ot_dsrom_su_fdiv_f12 #(.NR(0)) u_d (.clk(clk), .rst_n(rst_n), .v(piv), .a(pa[32*l +: 32]), .b(denl),
                                            .y(qd[32*l +: 32]), .vo(), .fault(fd));
        wire [15:0] qb;
        ot_hdc_kinc #(.W(16), .K(1)) u_bf (.a(qd[32*l + 16 +: 16]),
                                           .inc(qd[32*l + 15] & (qd[32*l + 16] | (|qd[32*l +: 15]))), .y(qb));
        always @(posedge clk) o0[16*l +: 16] <= qb;
    end endgenerate
    // inverse RoPE of the pair on the tail: even lane a*c + b*s, odd lane b*c + -(a*s)
    wire [31:0] o0_d;
    ot_hdc_delay #(.W(32), .D(LM + LA)) u_o0d (.clk(clk), .rst_n(rst_n), .d(o0), .q(o0_d));
    reg  [31:0] c, s;
    always @(posedge clk) begin c <= ccos[u_q[1:0]]; s <= csin[u_q[1:0]]; end
    wire tail = (u_rd >= UT);
    reg  [31:0] ob;
    wire [31:0] a = {o0[15:0], 16'd0}, b = {o0[31:16], 16'd0};
    generate for (l = 0; l < 2; l = l + 1) begin : g_rp
        wire [31:0] m1, m2, ad;
        wire f1, f2, f3;
        ot_dsrom_su_softmax_mul #(LM) u_m1 (clk, rst_n, dv[D_DIV + 1], (l == 0) ? a : b, c, m1, f1);
        ot_dsrom_su_softmax_mul #(LM) u_m2 (clk, rst_n, dv[D_DIV + 1], (l == 0) ? b : a, s, m2, f2);
        wire [31:0] m2s = (l == 0) ? m2 : {~m2[31], m2[30:0]};
        ot_dsrom_su_softmax_add #(.ADD6(0), .LA(LA)) u_a (clk, rst_n, dv[D_DIV + 1 + LM], m1, m2s, ad, f3);
        wire [15:0] adb;
        ot_hdc_kinc #(.W(16), .K(1)) u_bf (.a(ad[31:16]), .inc(ad[15] & (ad[16] | (|ad[14:0]))), .y(adb));
        always @(posedge clk) ob[16*l +: 16] <= tail ? adb : o0_d[16*l +: 16];
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_ov <= 1'b0; f_local <= 1'b0; end
        else begin
            o_ov <= dv[DR];
            if (dv[D_DIV] && u_q >= UT && csn < 3'd4) f_local <= 1'b1;
        end
    end
    always @(posedge clk) o_o <= ob;
    wire fault_next = (dv[D_DIV] && u_q >= UT && csn < 3'd4) ? 1'b1 : f_local;
    (* keep=1, keep_hierarchy=1 *) codex_svc_smd_face_fault u_fcopy
        (.clk(clk),.rst_n(rst_n),.d(fault_next),.q(o_f));
endmodule
(* keep_hierarchy=1 *) module codex_svc_smd_face_fault(input clk,rst_n,d,output reg q);
 always @(posedge clk or negedge rst_n) if(!rst_n) q<=1'b0;else q<=d;
endmodule