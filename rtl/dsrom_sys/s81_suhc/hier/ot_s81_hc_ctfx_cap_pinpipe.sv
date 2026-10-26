// Held structural successor to ot_s81_hc_ctfx_cap. Adds ONE fixed data/valid edge.
// The input captures sit on N pins, while fdx/fv launch on S pins. This separates
// the original same-edge captures cloned at distant output pins (s26 fd1007:417um).
// No production use until the HC calendar and full slab exact proof include +1.
module ot_s81_hc_ctfx_cap_pinpipe #(parameter integer S_RD = 2) (
    input wire clk,
    input wire rst_in,
    input wire [S_RD+4:0] fv_in,
    input wire [FXW-1:0] fd_in,
    output reg [S_RD+4:0] fv,
    output reg [FXW-1:0] fdx,
    output reg [S_RD+4:0] fv_local,
    output reg [FXW-1:0] fdx_local
);
    localparam integer O_D = 5 + S_RD*16 + 20 + 6 + 8 + 32 + 1, FXW = O_D + S_RD*512;
    (* keep = 1 *) reg [FXW-1:0] n_fd;
    (* keep = 1 *) reg [S_RD+4:0] n_fv;
    reg rr;
    always @(posedge clk) rr <= rst_in;
    always @(posedge clk) n_fd <= fd_in;
    always @(posedge clk or negedge rr) if (!rr) n_fv <= 0; else n_fv <= fv_in;
    always @(posedge clk) fdx <= n_fd;
    always @(posedge clk or negedge rr) if (!rr) fv <= 0; else fv <= n_fv;
    always @(posedge clk) fdx_local <= fdx;
    always @(posedge clk or negedge rr) if (!rr) fv_local <= 0; else fv_local <= fv;
endmodule
