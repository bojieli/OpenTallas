`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_hbm3e_phy_v41x_aw30_e8p5_k (BIND/mu4 2026-10-19): the S81 die's HBM3E macro, K-ONLY variant -- same K port, same
// controller RTL (ot_s81_hbm_pcc) over the same behavioural PHY + device as ot_hbm3e_phy_v41x_aw30_e8p5, with the W port
// (the QE weight region, unused on S81: weights are in the ROM field) and the model counters (refreshes / w_reads) removed
// at the source instead of tied / left open on the die (strict bind OUTPUT_OPEN).  Abstract: physical/asap7_memory_macros_v2/
// ot_hbm3e_phy_v41x_aw30_e8p5_k/ (tools/s81_dv/phy_k_variant.py).  k_oor (sticky K request past the 2^30-sector stack) is a
// real status output: the binder wires it to a die status pin.  n_refreshes is an internal net for benches (hierarchical).
// Derived from ot_hbm3e_phy_v41x_aw30_e8p5.sv (K generate loop and k_oor logic byte-identical).
// ---------------------------------------------------------------------------------------------------------------
module ot_hbm3e_phy_v41x_aw30_e8p5_k #(parameter integer MUT = 0, parameter integer TREFI_PB = 240) (
    input  wire clk,
    input  wire rst_n,
    input  wire [31:0] k_v,
    output wire [31:0] k_rdy,
    input  wire [959:0] k_addr,
    input  wire [127:0] k_len,
    input  wire [543:0] k_tag,
    input  wire [31:0] k_we,
    input  wire [8191:0] k_wdata,
    input  wire [1023:0] k_wstrb,
    output wire [31:0] k_wr_done,
    output wire [31:0] kr_v,
    input  wire [31:0] kr_rdy,
    output wire [543:0] kr_tag,
    output wire [127:0] kr_beat,
    output wire [8191:0] kr_data,
    output reg  k_oor
);
    wire [31:0] kref [0:31]; wire [31:0] krd [0:31];
    wire [31:0] kviol;
    genvar p;
    generate for (p = 0; p < 32; p = p + 1) begin : g_k
        wire [2:0] c; wire [3:0] b; wire [20:0] r; wire [4:0] col; wire [255:0] wd, rd; wire [31:0] ws; wire rv; wire [3:0] vc;
        ot_s81_hbm_pcc #(.AW(30), .LENW(4), .TAGW(17), .BEATW(4), .TREFI_PB(TREFI_PB), .MUT(MUT)) u_c (.clk(clk), .rst_n(rst_n),
            .q_v(k_v[p]), .q_rdy(k_rdy[p]), .q_addr(k_addr[30*p +: 30]), .q_len(k_len[4*p +: 4]), .q_tag(k_tag[17*p +: 17]),
            .q_we(k_we[p]), .q_wdata(k_wdata[256*p +: 256]), .q_wstrb(k_wstrb[32*p +: 32]), .wr_done(k_wr_done[p]),
            .r_v(kr_v[p]), .r_rdy(kr_rdy[p]), .r_tag(kr_tag[17*p +: 17]), .r_beat(kr_beat[4*p +: 4]), .r_data(kr_data[256*p +: 256]),
            .d_cmd(c), .d_bank(b), .d_row(r), .d_col(col), .d_wdata(wd), .d_wstrb(ws), .d_rv(rv), .d_rdata(rd),
            .n_ref(kref[p]), .n_rd(krd[p]));
        ot_s81_hbm3e_dev_bm #(.AW(30)) u_d (.clk(clk), .rst_n(rst_n), .d_cmd(c), .d_bank(b), .d_row(r), .d_col(col),
            .d_wdata(wd), .d_wstrb(ws), .d_rv(rv), .d_rdata(rd), .viol(kviol[p]), .viol_code(vc));
    end endgenerate
    integer i;
`ifndef SYNTHESIS
    reg [63:0] n_refreshes;                     // bench observability only (tb_s81_hbm PHY_K reads dut.n_refreshes)
    always @* begin n_refreshes = 64'd0; for (i = 0; i < 32; i = i + 1) n_refreshes = n_refreshes + kref[i]; end
`endif
    always @(posedge clk or negedge rst_n)
        if (!rst_n) k_oor <= 1'b0;
        else
            for (i = 0; i < 32; i = i + 1)
                if (k_v[i] && k_rdy[i] && ({1'b0, k_addr[30*i +: 30]} + k_len[4*i +: 4] > 31'h40000000)) k_oor <= 1'b1;
endmodule
