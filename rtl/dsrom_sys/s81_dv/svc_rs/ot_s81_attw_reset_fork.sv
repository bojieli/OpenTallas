`timescale 1ns/1ps
// Explicit reset distribution only. Every arc is combinational and non-inverting.
// The asynchronous assertion and existing two-edge release remain unchanged.
// Binary forks bound each internal source to two primitive gate inputs.
(* keep_hierarchy = 1 *)
module ot_s81_attw_reset_fork #(parameter integer N=1)(input wire d, output wire [N-1:0] q);
`ifdef SYNTHESIS
    if (N == 1) begin : g_leaf
        wire dn;
        (* keep = 1, dont_touch = 1 *) INVx1_ASAP7_75t_R u_n (.A(d), .Y(dn));
        (* keep = 1, dont_touch = 1 *) INVx1_ASAP7_75t_R u_p (.A(dn), .Y(q[0]));
    end else begin : g_split
        localparam integer L=N/2;
        wire dl, dr, nl, nr;
        (* keep = 1, dont_touch = 1 *) INVx1_ASAP7_75t_R u_ln (.A(d), .Y(nl));
        (* keep = 1, dont_touch = 1 *) INVx1_ASAP7_75t_R u_lp (.A(nl), .Y(dl));
        (* keep = 1, dont_touch = 1 *) INVx1_ASAP7_75t_R u_rn (.A(d), .Y(nr));
        (* keep = 1, dont_touch = 1 *) INVx1_ASAP7_75t_R u_rp (.A(nr), .Y(dr));
        ot_s81_attw_reset_fork #(.N(L)) u_l (.d(dl), .q(q[L-1:0]));
        ot_s81_attw_reset_fork #(.N(N-L)) u_r (.d(dr), .q(q[N-1:L]));
    end
`else
    assign q={N{d}};
`endif
endmodule
