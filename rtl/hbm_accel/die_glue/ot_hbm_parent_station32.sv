`timescale 1ns/1ps
`default_nettype none
// Isolated, UNBOUND source option. MODEL: results/arch/hbm_parent_station_1020/MODEL.md.
// One positive-edge identity hop; no existing top instantiates this module.
module ot_hbm_parent_station32 #(
    parameter integer W = 328
) (
    input wire ck,
    input wire rst_n,
    input wire [W-1:0] i,
    output wire [W-1:0] o,
    output wire [(W+23)/24-1:0] ready,
    output wire ck_o
);
    localparam integer BANK = 24;
    localparam integer G = (W + BANK - 1) / BANK;
    (* keep = 1, dont_touch = 1 *) reg face1;
    always @(posedge ck or negedge rst_n)
        if (!rst_n) face1 <= 1'b0;
        else face1 <= 1'b1;
`ifdef OT_HBM_PARENT_STATION_MUT_CLOCK
    assign ck_o = 1'b0;
`else
    ot_hbm_parent_station_buf u_ck (.a(ck), .y(ck_o));
`endif
    genvar g, b;
    generate for (g = 0; g < G; g = g + 1) begin : g_bank
        localparam integer LO = g * BANK;
        localparam integer N = (W - LO > BANK) ? BANK : W - LO;
        (* keep = 1, dont_touch = 1 *) reg face2;
        (* keep = 1, dont_touch = 1 *) reg [N-1:0] data_q;
        (* keep = 1, dont_touch = 1 *) reg ready_q;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) face2 <= 1'b0;
`ifdef OT_HBM_PARENT_STATION_MUT_RESET
            else face2 <= 1'b1;
`else
            else face2 <= face1;
`endif
        always @(posedge ck or negedge face2) begin
            if (!face2) begin
                data_q <= {N{1'b0}};
                ready_q <= 1'b0;
            end else begin
`ifdef OT_HBM_PARENT_STATION_MUT_DATA
                data_q <= i[LO +: N] ^ {{(N-1){1'b0}},1'b1};
`else
                data_q <= i[LO +: N];
`endif
                ready_q <= 1'b1;
            end
        end
        for (b = 0; b < N; b = b + 1) begin : g_out
            ot_hbm_parent_station_buf u_ob (.a(data_q[b]), .y(o[LO+b]));
        end
        ot_hbm_parent_station_buf u_rb (.a(ready_q), .y(ready[g]));
    end endgenerate
endmodule

module ot_hbm_parent_station_buf(input wire a, output wire y);
`ifdef SYNTHESIS
    (* keep = 1, dont_touch = 1 *) BUFx12f_ASAP7_75t_R u_cell (.A(a), .Y(y));
`else
    assign y = a;
`endif
endmodule
`default_nettype wire
