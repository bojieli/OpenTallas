module ot_s81_hc_ctfn_nt_reference #(
    parameter integer NG = 256, D = 5120, NCOL = 3, GS = 8, S_RD = 2
) (
    input  wire               clk,
    input  wire               rst_in,
    input  wire [S_RD+4:0]    fv_in,
    input  wire [FDW-1:0]     fd_in,
    output wire               rst_c,
    output reg  [S_RD+4:0]    fvm,
    output reg  [FDW-1:0]     fdm
);
    localparam integer NS = NG / GS, NP = (NS + NCOL - 1) / NCOL, YW = NP * GS * 32;
    localparam integer FDD = (S_RD * 512 > YW) ? S_RD * 512 : YW;
    localparam integer O_D = 5 + S_RD * 16 + 20 + 6 + 8 + 32 + 1, FDW = O_D + FDD;
    reg [1:0] rr;
    always @(posedge clk) rr <= {rr[0], rst_in};
    wire rst_n = rr[1];
    assign rst_c = rr[0];
    reg [S_RD+4:0] fv;
    reg [FDW-1:0]  fd;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fv <= 0; fvm <= 0; end
        else begin fv <= fv_in; fvm <= fv; end
    always @(posedge clk) begin fd <= fd_in; fdm <= fd; end
endmodule
