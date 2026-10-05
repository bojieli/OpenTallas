`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_gpu_coll_fabric: the R die links and the NVLink-switch tier with in-switch
// reduction (NVLS) of the GPU-organised HBM comparator, in clk_link.
//
//   up link    port r: LINK_PIPE register stages die r -> switch (the die's
//              NVLink port, package/board wire and the switch's ingress, as a
//              fixed-latency pipe; no PHY model in the system simulation).
//   switch     rtl/link/ot_link_nvls_switch.sv REUSED UNMODIFIED, P = R:
//              mode 0 ALL-REDUCE pops the R ports' records of one word index
//              together and adds them in its fixed pairwise tree over the port
//              index (binary32 RNE, ot_hdc_fp32_add_fast, canonical +0);
//              mode 1 ALL-GATHER forwards every record; the result is
//              multicast to every port.  SW_PIPE output stages stand for the
//              rest of the switch's cut-through latency: the W15 priced value
//              is ~250 ns (tools/w15_collectives.py HBM_SWITCH switch_core_ns
//              -> SW_PIPE = round(250 / T) - (2 + 3L)); the default here (4)
//              is the REDUCED setting for the end-to-end token simulation.
//   down link  port r: LINK_PIPE register stages switch -> die r.
//
// Reduction order.  The golden all-reduce is rank order ((r0 + r1) + r2) + ...
// The switch's pairwise tree equals it only for R = 2 (r0 + r1), so R != 2 is
// refused at elaboration (the switch is not edited; an R > 2 rank-order mode
// would be a separate module).
//
// Flow control.  The switch input FIFOs have no ready.  With one collective
// outstanding per rank, at most NREC_MAX = ceil(NL / LANES) records per port
// are in the switch; DEPTH >= NREC_MAX + 2 is checked at elaboration, and an
// overflow raises the switch's sticky fault (also an arithmetic error: a
// nonfinite operand or an overflowing sum fails closed).
//
// ENABLE = 0 (default): inert, every output 0, no switch instance.
// ---------------------------------------------------------------------------
module ot_gpu_coll_fabric #(
    parameter integer ENABLE    = 0,
    parameter integer R         = 2,
    parameter integer NL        = 128,
    parameter integer LANES     = 16,
    parameter integer TAGW      = 32,
    parameter integer DEPTH     = 16,
    parameter integer SW_PIPE   = 4,
    parameter integer LINK_PIPE = 2,
    parameter integer FW        = 32 * LANES,
    parameter integer PW        = FW + 2 + TAGW
) (
    input  wire              clk_link,
    input  wire              rst_link_n,
    input  wire [R-1:0]      up_v,          // die r -> switch
    input  wire [R*PW-1:0]   up_rec,
    output wire [R-1:0]      dn_v,          // switch -> die r
    output wire [R*PW-1:0]   dn_rec,
    output wire              fault          // sticky: switch FIFO overflow / arithmetic error
);
    generate if (ENABLE != 0) begin : g_on
        if (R != 2) begin : g_bad_r
            $error("ot_gpu_coll_fabric: R must be 2 (the reused switch's pairwise tree is the golden rank order only for R = 2)");
        end
        if (DEPTH < (NL + LANES - 1) / LANES + 2 || (DEPTH & (DEPTH - 1)) != 0) begin : g_bad_depth
            $error("ot_gpu_coll_fabric: DEPTH must be a power of two >= ceil(NL/LANES) + 2");
        end
        if (LINK_PIPE < 1 || SW_PIPE < 1) begin : g_bad_pipe
            $error("ot_gpu_coll_fabric: LINK_PIPE and SW_PIPE must be >= 1");
        end
        wire [R-1:0]    sw_iv;
        wire [R*PW-1:0] sw_ir;
        wire            sw_ov;
        wire [PW-1:0]   sw_or;
        genvar p;
        for (p = 0; p < R; p = p + 1) begin : g_port
            reg [LINK_PIPE-1:0] uv, dv;
            reg [PW-1:0]        ud [0:LINK_PIPE-1];
            reg [PW-1:0]        dd [0:LINK_PIPE-1];
            integer s;
            always @(posedge clk_link or negedge rst_link_n)
                if (!rst_link_n) begin uv <= {LINK_PIPE{1'b0}}; dv <= {LINK_PIPE{1'b0}}; end
                else begin
                    uv <= {uv[LINK_PIPE-2:0], up_v[p]};
                    dv <= {dv[LINK_PIPE-2:0], sw_ov};
                end
            always @(posedge clk_link) begin
                ud[0] <= up_rec[p*PW +: PW];
                dd[0] <= sw_or;
                for (s = 1; s < LINK_PIPE; s = s + 1) begin ud[s] <= ud[s-1]; dd[s] <= dd[s-1]; end
            end
            assign sw_iv[p] = uv[LINK_PIPE-1];
            assign sw_ir[p*PW +: PW] = ud[LINK_PIPE-1];
            assign dn_v[p] = dv[LINK_PIPE-1];
            assign dn_rec[p*PW +: PW] = dd[LINK_PIPE-1];
        end
        ot_link_nvls_switch #(.P(R), .LANES(LANES), .TAGW(TAGW), .DEPTH(DEPTH), .SW_PIPE(SW_PIPE)) u_sw (
            .clk(clk_link), .rst_n(rst_link_n), .in_valid(sw_iv), .in_rec(sw_ir),
            .out_valid(sw_ov), .out_rec(sw_or), .fault(fault));
    end else begin : g_off
        assign dn_v   = {R{1'b0}};
        assign dn_rec = {R*PW{1'b0}};
        assign fault  = 1'b0;
        /* verilator lint_off UNUSED */
        wire unused_off = &{1'b0, clk_link, rst_link_n, up_v, up_rec};
        /* verilator lint_on UNUSED */
    end endgenerate
endmodule
