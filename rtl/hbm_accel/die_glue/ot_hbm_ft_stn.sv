// HBM feedthrough station (FT-HBM-SU 2026-10-23): one register stage of a die lane carried THROUGH a block (FT-PLAN
// pushdown).  Function = the die relay ot_hbm_rly: r <= i on posedge ck, asynchronous active-low clear.  Difference:
// the clear comes in already relayed, one rn bit per group of <= 32 flops (native census <= 32 loads a dynamic net),
// from the kit-level reset tree (tools/hbm_ft/su_ft_kit.py: rs_ft -> ot_rst_relay levels -> rn groups), so the
// station holds no reset logic of its own.
`default_nettype none
module ot_hbm_ft_stn #(
    parameter int W = 64,
    parameter int GB = 32               // flops per reset group
) (
    input  wire                     ck,
    input  wire [(W+GB-1)/GB-1:0]   rn,
    input  wire [W-1:0]             i,
    output wire [W-1:0]             o
);
    localparam int G = (W + GB - 1) / GB;
    genvar g;
    generate
        for (g = 0; g < G; g = g + 1) begin : g_grp
            localparam int LO = g * GB;
            localparam int N  = (W - LO > GB) ? GB : W - LO;
            reg [N-1:0] r;
            always @(posedge ck or negedge rn[g])
                if (!rn[g]) r <= {N{1'b0}};
                else        r <= i[LO +: N];
            assign o[LO +: N] = r;
        end
    endgenerate
endmodule
`default_nettype wire
