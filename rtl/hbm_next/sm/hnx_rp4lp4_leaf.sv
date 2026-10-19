// HBM-NEXT-SM4: the P-lane leaf of hnx_rp4lp4 (lane fan-out, x-slot lane select, slot-major publish); see hnx_rp4lp4.sv
`timescale 1ns/1ps

// ---------------------------------------------------------------------------------------------------------------------
// per-lane registered fan-out of the row bundle and the x-write beat, lane-select decode (one leaf)
// MUT (bench negative controls only, default 0): 1 = lane P-1 takes lane 0's x target bit (lane alias);
//                                                2 = lane-select beats ignored (every lane takes every x beat).
module hnx_rp4lp4_lanefan #(parameter integer P = 4, parameter integer MUT = 0) (
    input  wire clk, input wire rst_n,
    input  wire [817:0] rl1, input wire [2068:0] bk1,
    output wire [P*818-1:0] rl_p, output wire [P*2069-1:0] bk_p, output wire [P-1:0] act
);
    wire sel = bk1[2068] && (bk1[2060:2048] == 13'd0);
    reg [P-1:0] tgt_q, act_q;
    always @(posedge clk)
        if (!rst_n) begin tgt_q <= {{(P-1){1'b0}}, 1'b1}; act_q <= {{(P-1){1'b0}}, 1'b1}; end
        else if (sel && MUT != 2) begin tgt_q <= bk1[P-1:0]; act_q <= bk1[8 +: P]; end
    assign act = act_q;
    genvar p;
    generate for (p = 0; p < P; p = p + 1) begin : g_ln
        localparam integer TB = (MUT == 1 && p == P - 1 && P > 1) ? 0 : p;
        wire take = (MUT == 2) ? 1'b1 : tgt_q[TB];
        (* keep *) reg [817:0] rq;
        (* keep *) reg bv;
        (* keep *) reg [2067:0] bd;
        always @(posedge clk) rq <= rl1;
        always @(posedge clk)
            if (!rst_n) bv <= 1'b0;
            else bv <= bk1[2068] && !sel && take;
        always @(posedge clk) bd <= bk1[2067:0];
        assign rl_p[p*818 +: 818] = rq;
        assign bk_p[p*2069 +: 2069] = {bv, bd};
    end endgenerate
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// slot-major publish: lane p delayed p*LSKEW, merged onto one gather word {gv, gf, gy[31:0], gt[15:0]}, registered.
// MUT 3 (bench only): lane 2 uses lane 1's slot (collides).
module hnx_rp4lp4_pub #(parameter integer P = 4, parameter integer LSKEW = 8, parameter integer MUT = 0) (
    input  wire clk, input wire rst_n,
    input  wire [P*50-1:0] g_p, input wire [P-1:0] act,
    output wire [49:0] g
);
    wire [P-1:0] v, f;
    wire [P*48-1:0] d;
    genvar p;
    generate for (p = 0; p < P; p = p + 1) begin : g_ln
        localparam integer DL = ((MUT == 3 && p == 2) ? 1 : p) * LSKEW;
        wire vi = g_p[p*50 + 49] && act[p];
        wire fi = g_p[p*50 + 48] && act[p];
        if (DL == 0) begin : g_d0
            assign v[p] = vi; assign f[p] = fi; assign d[p*48 +: 48] = g_p[p*50 +: 48];
        end else begin : g_dl
            // plain flop shift registers (flat vectors, no array: never a yosys memory)
            reg [DL-1:0] sv, sf;
            reg [DL*48-1:0] sd;
            always @(posedge clk)
                if (!rst_n) begin sv <= {DL{1'b0}}; sf <= {DL{1'b0}}; end
                else begin sv <= (sv << 1) | {{(DL-1){1'b0}}, vi}; sf <= (sf << 1) | {{(DL-1){1'b0}}, fi}; end
            always @(posedge clk) sd <= (sd << 48) | {{((DL-1)*48){1'b0}}, g_p[p*50 +: 48]};
            assign v[p] = sv[DL-1]; assign f[p] = sf[DL-1]; assign d[p*48 +: 48] = sd[(DL-1)*48 +: 48];
        end
    end endgenerate
    // merge: AND-OR of the valid lanes; two valid lanes in one cycle = schedule collision -> fault
    reg [47:0] m;
    reg multi;
    integer j, n;
    always @* begin
        m = 48'd0; n = 0;
        for (j = 0; j < P; j = j + 1) begin
            m = m | ({48{v[j]}} & d[j*48 +: 48]);
            n = n + (v[j] ? 1 : 0);
        end
        multi = (n > 1);
    end
    reg gv_q, gf_q;
    reg [47:0] gd_q;
    always @(posedge clk)
        if (!rst_n) begin gv_q <= 1'b0; gf_q <= 1'b0; end
        else begin gv_q <= |v; gf_q <= (|f) | multi; end
    always @(posedge clk) gd_q <= m;
    assign g = {gv_q, gf_q, gd_q};
endmodule

// ---------------------------------------------------------------------------------------------------------------------
// one P-lane leaf (soft child of the flat parent; holds 5 x P hard children): g = {gv, gf, gy, gt} as ot_rp4l_leaf
module hnx_rp4lp4_lf #(parameter integer P = 4, parameter integer LSKEW = 8, parameter integer MUT = 0) (
    input  wire clk, input wire rst_n, input wire [25:0] st, input wire [817:0] rl1,
    input  wire [2068:0] bk1, output wire [49:0] g
);
    wire [P*818-1:0] rl_p;
    wire [P*2069-1:0] bk_p;
    wire [P-1:0] act;
    wire [P*50-1:0] g_p;
    hnx_rp4lp4_lanefan #(.P(P), .MUT(MUT)) u_fan (.clk(clk), .rst_n(rst_n), .rl1(rl1), .bk1(bk1), .rl_p(rl_p), .bk_p(bk_p),
        .act(act));
    genvar p;
    generate for (p = 0; p < P; p = p + 1) begin : g_ln
        wire gv, gf; wire [31:0] gy; wire [15:0] gt;
        wire [2068:0] bk = bk_p[p*2069 +: 2069];
        hnx_rp4_leafh u_lh (.clk(clk), .clk_xb(clk), .clk_xf(clk), .clk_hard({5{clk}}), .rst_n(rst_n),
            .xs_a1(st[8:0]), .xs_g1(st[13:9]), .xs_a2(st[20:14]), .xs_g2(st[25:21]), .rl1(rl_p[p*818 +: 818]), .bk1(bk),
            .ohl1(bk[2060:2048]), .gv(gv), .gf(gf), .gy(gy), .gt(gt));
        assign g_p[p*50 +: 50] = {gv, gf, gy, gt};
    end endgenerate
    hnx_rp4lp4_pub #(.P(P), .LSKEW(LSKEW), .MUT(MUT)) u_pub (.clk(clk), .rst_n(rst_n), .g_p(g_p), .act(act), .g(g));
endmodule

