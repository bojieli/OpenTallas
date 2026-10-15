module ot_s81_hc_ctfn #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2
) (
    input  wire               clk,
    input  wire               rst_in,
    input  wire [S_RD+4:0]    fv_in,
    input  wire [FDW-1:0]     fd_in,
    output wire               rst_c,                 // first reset stage, relayed to every tile of the slot
    output reg  [S_RD+4:0]    fvm,
    output reg  [FDW-1:0]     fdm
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32, GT = GS / 2;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FDW = O_D + FDD, FXW = O_D + S_RD * 512;
    reg [1:0] rr;
    always @(posedge clk) rr <= {rr[0], rst_in};
    wire rst_n = rr[1];
    assign rst_c = rr[0];
    reg [S_RD+4:0] fv;
    reg [FDW-1:0]  fd;
    // the y-beat select drives every y-field bit of fdm (~2.8k muxes across the 576 um strip): NYR replicated pin flops
    // of fv[S_RD], one per y-field slice (same input pin, same cycle), instead of one flop with > 5k loads
    localparam integer NYR = 16, YSL = (YW + NYR - 1) / NYR;
    (* keep *) reg [NYR-1:0] ysel;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fv <= 0; fvm <= 0; ysel <= 0; end
        else begin fv <= fv_in; fvm <= fv; ysel <= {NYR{fv_in[S_RD]}}; end
    wire [YW-1:0] ysh = fd[O_D +: YW] >> (GT * 32);                        // y beat: next tile's slice to 0
    integer yb;
    always @(posedge clk) begin
        fd <= fd_in;
        fdm <= fd;
        for (yb = 0; yb < YW; yb = yb + 1)
            if (ysel[yb / YSL]) fdm[O_D + yb] <= ysh[yb];
    end
endmodule
