`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_qwen_d2d_chan: SIMULATION-ONLY channel of one die-to-die link direction
// for the Qwen ROM system bench: LAT cycles of flight (PHY + channel) and a
// deterministic error injector that inverts bit `flip_bit` of every flit
// whose index n satisfies n >= flip_start, (n - flip_start) % flip_period == 0
// (flip_period 0: no errors).  It stands for the analog PHY and channel no
// digital RTL can be; the link layer (ot_qwen_d2d_link) must recover every
// injected error by replay.
// ---------------------------------------------------------------------------
module ot_qwen_d2d_chan #(
    parameter integer FW  = 600,
    parameter integer LAT = 8
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [FW-1:0] in_flit,
    output wire          out_valid,
    output wire [FW-1:0] out_flit,
    input  integer       flip_period,
    input  integer       flip_start,
    input  integer       flip_bit,
    output integer       n_flipped
);
    reg [FW-1:0] d [0:LAT-1];
    reg [LAT-1:0] v;
    integer n, i;
    initial n_flipped = 0;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin v <= 0; n <= 0; end
        else begin
            v <= {v[LAT-2:0], 1'b1};
            n <= n + 1;
            if (flip_period > 0 && n >= flip_start && ((n - flip_start) % flip_period) == 0) begin
                d[0] <= in_flit ^ ({{(FW-1){1'b0}}, 1'b1} << (flip_bit % FW));
                n_flipped = n_flipped + 1;
            end else d[0] <= in_flit;
            for (i = 1; i < LAT; i = i + 1) d[i] <= d[i-1];
        end
    end
    assign out_valid = v[LAT-1];
    assign out_flit  = d[LAT-1];
endmodule
