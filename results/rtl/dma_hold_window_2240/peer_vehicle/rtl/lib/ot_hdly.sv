`timescale 1ns/1ps
// ot_hdly (from bf-hier-1011 ot_bf_hdly, el1011-q-coll 2026-10-11): hold-delay stage on a block IO bit (owner: deterministic hold fix at a hardened
// block boundary).  N HB4xp67 delay cells per bit (~38 ps each at FF, ASAP7 RVT), kept and dont_touch'ed by the flow
// (physical/qwen_die_masters/hdly_dont_touch.tcl, PRE_FLOORPLAN) so remove_buffers / repair passes leave them.  In
// simulation (and for N = 0) it is a wire: function is identity, so exactness is unchanged.
module ot_hdly #(parameter integer W = 1, parameter integer N = 0) (input wire [W-1:0] a, output wire [W-1:0] y);
`ifdef SYNTHESIS
    if (N == 0) begin : g_w
        assign y = a;
    end else begin : g_d
        genvar b, k;
        for (b = 0; b < W; b = b + 1) begin : g_b
            wire [N:0] c;
            assign c[0] = a[b];
            for (k = 0; k < N; k = k + 1) begin : g_k
                (* keep *) HB4xp67_ASAP7_75t_R u_hb (.A(c[k]), .Y(c[k+1]));
            end
            assign y[b] = c[N];
        end
    end
`else
    assign y = a;
`endif
endmodule
