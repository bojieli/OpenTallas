`timescale 1ns/1ps
// KV-PARAMS4 10-20 (K.STA.PARAMS / K.STA.ECTL): native-32 structurally safe successor of the K-tree tile, default-off.
//   ot_qkh_ktree_nc32c    = ot_qkh_ktree_nc (every register its own routed flop, no twin-value power-up) with
//     - reset: ot_rst_relay_bounded32 #(54) (leaves <= 32 endpoints; release 3 edges as ot_rst_relay SYNC2/TREE1),
//       replacing the 17-region ot_rst_relay whose scale-multiply copy drove 369 resets (lkp HOLD reset369);
//     - adders: ot_hdc_fp32_add_lat_ncr (native-32 kept-copy LAT-7 adder of ot_qkh_lane8_nc32c; split rst_n / rst_y);
//     - scale multiply: ot_hdc_fp32_mul_lat_ncr (LAT 6, constant SCALE operand, reset on 21 bounded leaves, kept select
//       copies, one-hot normalise fed from a kept copy of the root adder's y register).
//   ot_qkh_ktree_lk_nc32c = ot_qkh_ktree_lk (lockstep lane-valid check + 2-stage face reset landing) around it.
// Same ports, parameters, latency and outputs every cycle (bench tb_qkh_nc +mode=ktree / +mode=ktreelk).  0 added cycles.
module ot_qkh_ktree_nc32c #(
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter [31:0]  SCALE = 32'h3DB504F3
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [511:0]  kp_in,
    input  wire          kpv_in,
    input  wire [15:0]   gf_in,
    output reg  [31:0]   sc_d,
    output reg           sc_f,
    output reg           g_f
);
    generate if (ADD_LAT != 7 || MUL_LAT != 6) begin : g_bad_shape
        ot_qkh_ktree_nc32c_requires_7_6 u_trap ();
    end endgenerate
    // leaves: adder i -> rr[2i] (control) / rr[2i+1] (y); multiply -> rr[48:30] + rr[53:52]; tile control -> rr[49]; root y copies -> rr[51:50]
    wire [53:0] rr;
    ot_rst_relay_bounded32 #(.REGIONS(54)) u_rr (.clk(clk), .rst_n_in(rst_n), .rst_n(rr));
    wire rc = rr[49];
    reg  [511:0] kp_r;
    reg          kv_r;
    reg  [15:0]  gf_r;
    always @(posedge clk) kp_r <= kp_in;
    always @(posedge clk or negedge rc)
        if (!rc) begin kv_r <= 1'b0; gf_r <= 16'd0; end
        else begin kv_r <= kpv_in; gf_r <= gf_in; end
    wire [15*32-1:0] n;
    wire [14:0]      nvo, nf;
    wire [63:0]      root_y2;          // 2 kept copies of the root adder's y (feed the multiply's normalise)
`ifdef KVD_HSMUT
    reg  [511:0] kp_m;
    always @(posedge clk) kp_m <= kp_r;
    wire [511:0] lv3 = kp_m;            // bench mutant (must FAIL): level-4 adders see the partials one edge late
`else
    wire [511:0] lv3 = kp_r;
`endif
    genvar i;
    generate for (i = 0; i < 15; i = i + 1) begin : g_n
        localparam integer LEV = (i < 8) ? 4 : ((i < 12) ? 5 : ((i < 14) ? 6 : 7));
        localparam integer IX  = (i < 8) ? i : ((i < 12) ? i - 8 : ((i < 14) ? i - 12 : 0));
        localparam integer CB  = (LEV == 5) ? 0 : ((LEV == 6) ? 8 : 12);
        wire [31:0] a, b;
        wire        vin;
        if (LEV == 4) begin : g_l4
            assign a = lv3[32*(2*IX) +: 32];
            assign b = lv3[32*(2*IX + 1) +: 32];
            assign vin = kv_r;
        end else begin : g_lh
            assign a = n[32*(CB + 2*IX) +: 32];
            assign b = n[32*(CB + 2*IX + 1) +: 32];
            assign vin = nvo[CB + 2*IX];
        end
        wire [1:0] err;
        wire [63:0] y2;
        (* keep_hierarchy *) ot_hdc_fp32_add_lat_ncr #(.LAT(ADD_LAT), .YCOPY((i == 14) ? 2 : 0)) u_a (.clk(clk), .rst_n(rr[2*i]), .rst_y(rr[2*i+1]),
            .rst_y2(rr[51:50]), .valid_in(vin), .a(a), .b(b), .y(n[32*i +: 32]), .y2(y2), .err(err), .valid_out(nvo[i]));
        if (i == 14) begin : g_root
            assign root_y2 = y2;
        end
        assign nf[i] = nvo[i] && (err != 2'd0);
    end endgenerate
    wire [31:0] scd0;
    wire [1:0]  merr;
    wire        sv;
    (* keep_hierarchy *) ot_hdc_fp32_mul_lat_ncr #(.LAT(MUL_LAT), .BCONST_EN(1), .BCONST(SCALE)) u_scale (
        .clk(clk), .rst_v({rr[53:52], rr[48:30]}), .valid_in(nvo[14]), .a(n[32*14 +: 32]), .a_nrm(root_y2), .b(SCALE), .y(scd0), .err(merr), .valid_out(sv));
    reg kf;
    always @(posedge clk) sc_d <= scd0;
    always @(posedge clk or negedge rc)
        if (!rc) begin sc_f <= 1'b0; g_f <= 1'b0; kf <= 1'b0; end
        else begin sc_f <= sv && (merr != 2'd0); kf <= |nf; g_f <= (|gf_r) || kf; end
endmodule

module ot_qkh_ktree_lk_nc32c #(
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter [31:0]  SCALE = 32'h3DB504F3,
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [511:0]  kp_in,
    input  wire [15:0]   kpv_in,
    input  wire [15:0]   gf_in,
    output wire [31:0]   sc_d,
    output wire          sc_f,
    output wire          g_f
);
    wire [15:0] lk = (MUT == 1) ? 16'd0 : ({16{kpv_in[0]}} ^ kpv_in);
    (* keep *) reg rst_l0, rst_l1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rst_l0 <= 1'b0; rst_l1 <= 1'b0; end
        else begin rst_l0 <= 1'b1; rst_l1 <= rst_l0; end
    ot_qkh_ktree_nc32c #(.ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .SCALE(SCALE)) u_kt (
        .clk(clk), .rst_n(rst_l1), .kp_in(kp_in), .kpv_in(kpv_in[0]), .gf_in(gf_in | lk),
        .sc_d(sc_d), .sc_f(sc_f), .g_f(g_f));
endmodule
