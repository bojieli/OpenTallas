`timescale 1ns/1ps
// DIE-S81-85 svc census 11-10 (COORD loopgap-153x-1109): census-safe copy of ot_s81_su_smc
// (rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv, unchanged without the define), the box body under
// -DOT_S81_SVC_CS (the box keeps its name).  Same ports, same cycles.  Only drivers above 64 load pins change:
//   - rst_n: NRN kept copies of the reset relay's second flop (each = rr1), one per load group;
//   - the adders: ot_s81_svc_qadd_lat_cs (KEEP 1, LAT LA; = ot_dsrom_su_softmax_add ADD6 0 = ot_hdc_qadd_lat,
//     yosys EQ vs rtl/hdc).
// Lock-step bench against the original: tools/s81_dv/svc_cs/tb_smc_cs.sv.
module ot_s81_su_smc_cs #(
    parameter integer LPH = 16, LA = 4
) (
    input  wire               clk,
    input  wire               rst_in,
    input  wire               i_v,
    input  wire               i_l,
    input  wire [LPH*32-1:0]  i_e,
    output reg                o_v,
    output reg                o_l,
    output reg  [31:0]        o_s
);
    localparam integer CPV = LPH / 8, LVI = $clog2(CPV);
    // reset copies: 0 control + tree lines, 1 cv, 2 cl, 3.. one per adder (chain k*7+j-1, then the tree)
    localparam integer NAD = CPV * 7 + CPV - 1;
    localparam integer NRN = 3 + NAD;
    reg rr0, rr1;
    always @(posedge clk or negedge rst_in) if (!rst_in) begin rr0 <= 1'b0; rr1 <= 1'b0; end else begin rr0 <= 1'b1; rr1 <= rr0; end
    (* keep = 1 *) reg [NRN-1:0] rnk;
    always @(posedge clk or negedge rst_in) if (!rst_in) rnk <= {NRN{1'b0}}; else rnk <= {NRN{rr0}};
    wire rst_n = rnk[0];
    reg               e_at, e_last;
    reg [LPH*32-1:0]  be;
    always @(posedge clk) be <= i_e;
    always @(posedge clk or negedge rst_n) if (!rst_n) begin e_at <= 1'b0; e_last <= 1'b0; end
                                           else begin e_at <= i_v; e_last <= i_v && i_l; end
    wire [7*LA:0] cv, cl;
    ot_hdc_vline #(.D(7 * LA)) u_cv (.clk(clk), .rst_n(rnk[1]), .v(e_at), .vd(cv));
    ot_hdc_vline #(.D(7 * LA)) u_cl (.clk(clk), .rst_n(rnk[2]), .v(e_last), .vd(cl));
    wire [CPV*32-1:0] csum_o;
    genvar k, j, l;
    generate for (k = 0; k < CPV; k = k + 1) begin : g_ch
        wire [32*8-1:0] acc;
        wire [31:0] x0 = be[32*(8*k) +: 32];
        assign acc[31:0] = (x0 == 32'h80000000) ? 32'd0 : x0;
        for (j = 1; j < 8; j = j + 1) begin : g_j
            wire [31:0] xj;
            wire fa;
            ot_hdc_delay #(.W(32), .D(LA * (j - 1))) u_xd (.clk(clk), .rst_n(rst_n), .d(be[32*(8*k+j) +: 32]), .q(xj));
            ot_s81_svc_qadd_lat_cs #(.KEEP(1), .LAT(LA)) u_a
                (clk, rnk[3 + 7*k + j - 1], cv[LA*(j-1)], acc[32*(j-1) +: 32], xj, acc[32*j +: 32], fa);
        end
        assign csum_o[32*k +: 32] = acc[32*7 +: 32];
    end endgenerate
    wire [LA*LVI:0] vtv, vtl;
    ot_hdc_vline #(.D(LA * LVI)) u_vtv (.clk(clk), .rst_n(rst_n), .v(cv[7*LA]), .vd(vtv));
    ot_hdc_vline #(.D(LA * LVI)) u_vtl (.clk(clk), .rst_n(rst_n), .v(cl[7*LA]), .vd(vtl));
    generate for (k = 0; k <= LVI; k = k + 1) begin : g_vt
        wire [(CPV >> k)*32-1:0] x;
        if (k == 0) begin : g_0
            assign x = csum_o;
        end else begin : g_n
            for (l = 0; l < (CPV >> k); l = l + 1) begin : g_l
                wire fa;
                ot_s81_svc_qadd_lat_cs #(.KEEP(1), .LAT(LA)) u_a
                    (clk, rnk[3 + 7*CPV + (CPV - (CPV >> (k-1))) + l], vtv[LA*(k-1)],
                     g_vt[k-1].x[64*l +: 32], g_vt[k-1].x[64*l + 32 +: 32], x[32*l +: 32], fa);
            end
        end
    end endgenerate
    always @(posedge clk or negedge rst_n) if (!rst_n) begin o_v <= 1'b0; o_l <= 1'b0; end
                                           else begin o_v <= vtv[LA*LVI]; o_l <= vtl[LA*LVI]; end
    always @(posedge clk) o_s <= g_vt[LVI].x;
endmodule
