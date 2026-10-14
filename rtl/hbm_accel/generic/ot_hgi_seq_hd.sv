// ot_hgi_seq_hd.sv -- hold-delay stage of the hgi_seq split children (el1013-hbm-seq-split, 2026-10-13).
// The same body as ot_hgi_seq_hdly (defined inside ot_hgi_seq.sv), in a file of its own under a name of its own, so the
// split builds by -y without the flat file and next to it: N kept HB4xp67 delay cells a bit under SYNTHESIS (dont_touch
// by instance name *u_hdly_*), a wire in simulation -- function is identity.
`default_nettype none
module ot_hgi_seq_hd #(parameter integer W = 1, parameter integer N = 0) (input wire [W-1:0] a, output wire [W-1:0] y);
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
`default_nettype wire
