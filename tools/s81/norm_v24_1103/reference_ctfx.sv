// Immutable baseline eb9cfa044 original body, module renamed only.
module norm_reference_ctfx #(
    parameter integer NG = 256, D = 5120, S_RD = 2, ML = 5, AL = 4, CHAIN_STEP = AL, LOCAL_EPOCH = 1
) (
    input  wire               clk,
    input  wire               rst_in,
    input  wire [S_RD+4:0]    fv_in,
    input  wire [FXW-1:0]     fd_in,
    output reg  [S_RD+4:0]    fv,
    output reg  [FXW-1:0]     fdx,
    output wire [S_RD+4:0]    fv_local,
    output wire [FXW-1:0]     fdx_local,
    input  wire [7:0]         tid,
    input  wire [63:0]        cs_n,          // chunk sums of banks 0 / 1 (ctnl rows above the band: lanes 3, 7)
    input  wire [63:0]        cs_s,          // banks 2 / 3 (rows below: lanes 11, 15)
    input  wire [DLW-1:0]     dl_in,
    output reg  [DLW-1:0]     dl_out,
    input  wire [32:0]        ul_in,
    output reg  [32:0]        ul_out
);
    localparam integer O_RK = 0, O_RS = 2, O_RG = 3, O_RC = 5, O_PB = O_RC + S_RD * 16, O_NG = O_PB + 20,
                       O_NV = O_NG + 6, O_R = O_NV + 8, O_HS = O_R + 32, O_D = O_HS + 1, FXW = O_D + S_RD * 512;
    localparam integer SW = 137, DLW = 2 * SW + 1, DS = ML + 7 * CHAIN_STEP;
    reg rr;
    always @(posedge clk) rr <= rst_in;
    wire rst_n = rr;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fv <= 0; ul_out <= 0; end
        else begin fv <= {fv_in[S_RD+4], ul_out[32], fv_in[S_RD+2:0]}; ul_out <= ul_in; end
    always @(posedge clk) begin
        fdx <= fd_in;
        if (ul_out[32]) fdx[O_R +: 32] <= ul_out[31:0];
    end
    // Own the local broadcast capture physically; the cth region wrapper must contain no state.
    // Its reset is the incoming rst_c epoch, exactly the former region register's reset (not rr).
    generate if (LOCAL_EPOCH) begin : g_local_capture
        reg [S_RD+4:0] v;
        reg [FXW-1:0] d;
        // reset by the pin capture rr (rst_in's only load; cycle-identical epoch, see ot_s81_hc_ctfx_cap)
        always @(posedge clk or negedge rst_n)
            if (!rst_n) v <= 0; else v <= fv;
        always @(posedge clk) d <= fdx;
        assign fv_local = v;
        assign fdx_local = d;
    end else begin : g_no_local_capture
        assign fv_local = fv;
        assign fdx_local = fdx;
    end endgenerate
    // ctq replica on ctra's epoch (cth CNL_PIN: one local register after the broadcast flops)
    wire [S_RD+4:0] fvl;
    wire [O_D-1:0]  fcl;
    generate if (LOCAL_EPOCH) begin : g_le
        reg [S_RD+4:0] v;
        reg [O_D-1:0]  c;
        always @(posedge clk or negedge rst_n) if (!rst_n) v <= 0; else v <= fv;
        always @(posedge clk) c <= fdx[O_D-1:0];
        assign fvl = v; assign fcl = c;
    end else begin : g_nle
        assign fvl = fv; assign fcl = fdx[O_D-1:0];
    end endgenerate
    wire n_hs, n_cs, mx_v, x_v, b_v;
    wire [1:0] n_gs;
    wire [7:0] xi, si, sc_i, wi, yi;
    wire [DS:0] vs;
    wire [2*ML+1:0] vy;
    wire [31:0] rh;
    ot_s81_hc_ctq #(.NG(NG), .D(D), .S_RD(S_RD), .ML(ML), .AL(AL), .CHAIN_STEP(CHAIN_STEP)) u_q (.clk(clk), .rst_n(rst_n),
        .fv(fvl), .fdx({{(FXW - O_D){1'b0}}, fcl}), .n_hs(n_hs), .n_cs(n_cs), .n_gs(n_gs), .mx_v(mx_v), .x_v(x_v),
        .xi(xi), .vs(vs), .si(si), .rh(rh), .sc_i(sc_i), .b_v(b_v), .vy(vy), .wi(wi), .yi(yi));
    wire [127:0] cs = {cs_s, cs_n};
    reg       farq;
    reg [4:0] oct;
    always @(posedge clk) begin farq <= tid[0]; oct <= tid[5:1]; end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) dl_out <= 0;
        else begin : mrg
            reg [DLW-1:0] o;
            o = dl_in;
            if (vs[DS] && farq) begin
                if (o[SW * oct[0]]) o[DLW-1] = 1'b1;
                o[SW * oct[0] +: SW] = {cs, si[2:0], oct, 1'b1};
            end
            dl_out <= o;
        end
endmodule
