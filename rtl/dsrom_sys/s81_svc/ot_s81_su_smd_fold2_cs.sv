`timescale 1ns/1ps
// DIE-S81-85 svc census 11-10 (COORD loopgap-153x-1109): census-safe copy of ot_s81_su_smd_fold2
// (rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_smd_fold2.sv, unchanged without the define), the box body under
// -DOT_S81_SVC_CS (the box keeps its name).  Same ports, same cycles.  Only drivers above 64 load pins change:
//   - rst_n: NRN kept copies of the reset relay's second flop (each = rr1), one per load group;
//   - the cos / sin read index {ctxd[D_DIV], u_q[1:0]} (u_q[0] 512 / u_q[1] 256 / ctxd 131 pins) -> two kept one-hot
//     registers (cos / sin), loaded from the lines' previous stage, so they equal the index cycle for cycle;
//   - pa: selected by kept copies of pending (hi loads every edge; the hold term is dropped: pa is consumed only with
//     piv).  The schedule leaves an idle edge after every two-lane vector (i_pv is never high on the edge after
//     i_pv), as the original's pending / ctx pairing already requires;
//   - the ctx tag line is DRST 0 (data, qualified by dv); its last stage and dv's last stage are kept x2 for the
//     output word enables;
//   - u_d / u_m1 / u_m2 / u_a: the census-safe f12 copies (ot_s81_svc_fdiv_f12_cs, ot_s81_svc_qmul_lat_cs,
//     ot_s81_svc_qadd_lat_cs; yosys EQ vs rtl/hdc).
// Lock-step bench against the original: tools/s81_dv/svc_cs/tb_smd_cs.sv.
module ot_s81_su_smd_fold2_cs #(
    parameter integer LPH = 16, TAIL = 64, LM = 5, LA = 4, STALEDEN = 0
) (
    input  wire        clk,
    input  wire        rst_in,
    input  wire [1:0]  cfg_p,
    input  wire        i_pv,
    input  wire [127:0] i_pa,
    input  wire        i_dv,
    input  wire [31:0] i_den,
    input  wire        i_csv,
    input  wire [4:0]  i_csi,
    input  wire [63:0] i_csd,
    output reg         o_ov,
    output reg  [63:0] o_o,
    output reg  [1:0]  o_f
);
    localparam integer NPV = 512 / LPH;
    localparam integer D_DIV = 33;
    localparam integer DR = D_DIV + 1 + LM + LA + 1;
    localparam integer UT = (512 - TAIL) / LPH;
    // reset copies: 0 control, 1 dv line, 2-3 u_d, 4-7 u_m1 / u_m2, 8-9 u_a
    localparam integer NRN = 10;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    (* keep = 1 *) reg [NRN-1:0] rnk;
    always @(posedge clk or negedge rst_in) if (!rst_in) rnk <= {NRN{1'b0}}; else rnk <= {NRN{rr0}};
    wire rst_n = rnk[0];
    // pin flops
    reg        piv, dvq, csv;
    reg [63:0] pa, csd;
    reg [31:0] dnq;
    reg [4:0]  csi;
    reg [1:0] p; reg pending, ctx; reg [63:0] hi;
    (* keep = 1 *) reg [3:0] pk;                           // pending copies: pa 16-bit quarter selects
    always @(posedge clk) begin
        hi<=i_pa[127:64];
        pa[15:0]<=pk[0]?hi[15:0]:i_pa[15:0];
        pa[31:16]<=pk[1]?hi[31:16]:i_pa[31:16];
        pa[47:32]<=pk[2]?hi[47:32]:i_pa[47:32];
        pa[63:48]<=pk[3]?hi[63:48]:i_pa[63:48];
        dnq<=i_den;csd<=i_csd;csi<=i_csi;p<=cfg_p;
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin pending<=0;pk<=0;ctx<=0;end
        else begin pending<=i_pv;pk<={4{i_pv}};ctx<=pending;end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin piv <= 1'b0; dvq <= 1'b0; csv <= 1'b0; end
                                           else begin piv <= i_pv||pending; dvq <= i_dv; csv <= i_csv; end
    reg [31:0] ccos [0:7];
    reg [31:0] csin [0:7];
    reg [2:0] csn[0:1];
    always @(posedge clk) if (csv && csi[1:0] == p) begin ccos[{csi[2],csi[4:3]}] <= csd[63:32]; csin[{csi[2],csi[4:3]}] <= csd[31:0]; end
    always @(posedge clk or negedge rst_n)
        if(!rst_n)begin csn[0]<=0;csn[1]<=0;end
        else if(csv&&csi==0)begin csn[0]<=(p==0)?3'd1:3'd0;csn[1]<=0;end
        else if(csv&&csi[1:0]==p)csn[csi[2]]<=csn[csi[2]]+3'd1;
    reg [31:0] denl;
    reg        den_seen;
    always @(posedge clk or negedge rst_n) if (!rst_n) den_seen <= 1'b0; else if (dvq) den_seen <= 1'b1;
    always @(posedge clk) if (dvq && !(STALEDEN != 0 && den_seen)) denl <= dnq;
    reg [6:0] ucnt[0:1];
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n)begin ucnt[0]<=0;ucnt[1]<=0;end
        else if(piv)ucnt[ctx]<=(ucnt[ctx]+7'd1==NPV)?7'd0:ucnt[ctx]+7'd1;
    end
    // dv: valid line (reset), last stage kept x2 (output word enables)
    wire [DR-1:0] dvl;
    ot_hdc_vline #(.D(DR-1)) u_dv (.clk(clk), .rst_n(rnk[1]), .v(piv), .vd(dvl));
    (* keep = 1 *) reg [1:0] dvk;
    always @(posedge clk or negedge rnk[1]) if (!rnk[1]) dvk <= 2'b0; else dvk <= {2{dvl[DR-1]}};
    wire [DR:0] dv = {dvk[0], dvl};
    // ctx tag line (data, DRST 0); last stage kept x2
    reg [DR-1:1] ctxl;
    (* keep = 1 *) reg [1:0] ctxk;
    always @(posedge clk) begin ctxl <= {ctxl[DR-2:1], ctx}; ctxk <= {2{ctxl[DR-1]}}; end
    wire [DR:0] ctxd = {ctxk[0], ctxl, ctx};
    // u_ul: ucnt[ctx] 33 edges late (u_q), plain flops as ot_hdc_delay RESET 0
    reg [6:0] ulq [1:D_DIV];
    integer ui;
    always @(posedge clk) begin
        ulq[1] <= ucnt[ctx];
        for (ui = 2; ui <= D_DIV; ui = ui + 1) ulq[ui] <= ulq[ui-1];
    end
    wire [6:0] u_q = ulq[D_DIV], u_r, u_rd;
    ot_hdc_delay #(.W(7), .D(1)) u_ul1 (.clk(clk), .rst_n(rst_n), .d(u_q), .q(u_r));
    ot_hdc_delay #(.W(7), .D(LM + LA)) u_urd (.clk(clk), .rst_n(rst_n), .d(u_r), .q(u_rd));
    // one-hot cos / sin read index = {ctxd[D_DIV], u_q[1:0]}, loaded from the previous stage
    (* keep = 1 *) reg [7:0] oh_c, oh_s;
    always @(posedge clk) begin
        oh_c <= 8'd1 << {ctxl[D_DIV-1], ulq[D_DIV-1][1:0]};
        oh_s <= 8'd1 << {ctxl[D_DIV-1], ulq[D_DIV-1][1:0]};
    end
    wire [63:0] qd;
    reg  [31:0] o0;
    genvar l;
    generate for (l = 0; l < 2; l = l + 1) begin : g_dv
        wire fd;
        ot_s81_svc_fdiv_f12_cs #(.NR(0)) u_d (.clk(clk), .rst_n(rnk[2 + l]), .v(piv), .a(pa[32*l +: 32]), .b(denl),
                                             .y(qd[32*l +: 32]), .vo(), .fault(fd));
        wire [15:0] qb;
        ot_hdc_kinc #(.W(16), .K(1)) u_bf (.a(qd[32*l + 16 +: 16]),
                                           .inc(qd[32*l + 15] & (qd[32*l + 16] | (|qd[32*l +: 15]))), .y(qb));
        always @(posedge clk) o0[16*l +: 16] <= qb;
    end endgenerate
    wire [31:0] o0_d;
    ot_hdc_delay #(.W(32), .D(LM + LA)) u_o0d (.clk(clk), .rst_n(rst_n), .d(o0), .q(o0_d));
    reg  [31:0] c, s, cr, sr;
    integer ki;
    always @* begin
        cr = 32'd0; sr = 32'd0;
        for (ki = 0; ki < 8; ki = ki + 1) begin cr = cr | ({32{oh_c[ki]}} & ccos[ki]); sr = sr | ({32{oh_s[ki]}} & csin[ki]); end
    end
    always @(posedge clk) begin c <= cr; s <= sr; end
    wire tail = (u_rd >= UT);
    reg  [31:0] ob;
    wire [31:0] a = {o0[15:0], 16'd0}, b = {o0[31:16], 16'd0};
    generate for (l = 0; l < 2; l = l + 1) begin : g_rp
        wire [31:0] m1, m2, ad;
        wire f1, f2, f3;
        wire [31:0] unused_x1, unused_x2;
        ot_s81_svc_qmul_lat_cs #(.LAT(LM)) u_m1 (clk, rnk[4 + 2*l], dv[D_DIV + 1], (l == 0) ? a : b, c, m1, f1, unused_x1);
        ot_s81_svc_qmul_lat_cs #(.LAT(LM)) u_m2 (clk, rnk[5 + 2*l], dv[D_DIV + 1], (l == 0) ? b : a, s, m2, f2, unused_x2);
        wire [31:0] m2s = (l == 0) ? m2 : {~m2[31], m2[30:0]};
        ot_s81_svc_qadd_lat_cs #(.KEEP(1), .LAT(LA)) u_a (clk, rnk[8 + l], dv[D_DIV + 1 + LM], m1, m2s, ad, f3);
        wire [15:0] adb;
        ot_hdc_kinc #(.W(16), .K(1)) u_bf (.a(ad[31:16]), .inc(ad[15] & (ad[16] | (|ad[14:0]))), .y(adb));
        always @(posedge clk) ob[16*l +: 16] <= tail ? adb : o0_d[16*l +: 16];
    end endgenerate
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin o_ov <= 1'b0; o_f <= 2'd0; end
        else begin
            o_ov <= dv[DR] && ctxd[DR];
            if (dv[D_DIV] && u_q >= UT && csn[ctxd[D_DIV]] < 3'd4) o_f[ctxd[D_DIV]] <= 1'b1;
        end
    end
    reg [31:0] olo;
    always @(posedge clk) begin
        if (dvk[0] && !ctxk[0]) olo <= ob;
        if (dvk[0] && ctxk[0]) o_o[31:0] <= olo;
        if (dvk[1] && ctxk[1]) o_o[63:32] <= ob;
    end
endmodule
