`timescale 1ns/1ps
// QW-H16V 10-20: log-depth helpers for the safe32 head (exact; Kogge-Stone levels as (* keep *) wires so the gate
// mapping's area rewriting does not fold them back into ripple chains, as it did with cycle+1 in h16t: 30-AND chain).
// a + 1 (W-bit wrap), Kogge-Stone prefix-AND carries; each level a (* keep *) wire.
module ot_hdc_inc_ks #(parameter integer W=18) (input wire [W-1:0] a, output wire [W-1:0] y);
    localparam integer L=(W>1) ? $clog2(W) : 1;
    (* keep *) wire [W*(L+1)-1:0] p;        // level l bit k = &a[k : max(0, k-2^l+1)]
    genvar l, k;
    generate
        assign p[W-1:0] = a;
        for (l = 0; l < L; l = l + 1) begin : g_l
            for (k = 0; k < W; k = k + 1) begin : g_k
                if (k >= (1 << l)) begin : g_and
                    assign p[W*(l+1) + k] = p[W*l + k] & p[W*l + k - (1 << l)];
                end else begin : g_pass
                    assign p[W*(l+1) + k] = p[W*l + k];
                end
            end
        end
        assign y[0] = ~a[0];
        for (k = 1; k < W; k = k + 1) begin : g_y
            assign y[k] = a[k] ^ p[W*L + k - 1];
        end
    endgenerate
endmodule

// a > b (unsigned), log-depth MSB-first (gt, eq) tree; each level a (* keep *) wire.
module ot_hdc_gt_ks #(parameter integer W=32) (input wire [W-1:0] a, input wire [W-1:0] b, output wire gt);
    localparam integer L=(W>1) ? $clog2(W) : 1;
    localparam integer N=1<<L;
    (* keep *) wire [2*N*(L+1)-1:0] t;      // level l node k: {gt, eq} of bits [k*2^l +: 2^l]
    genvar l, k;
    generate
        for (k = 0; k < N; k = k + 1) begin : g_leaf
            if (k < W) begin : g_b
                assign t[2*k +: 2] = {a[k] & ~b[k], ~(a[k] ^ b[k])};
            end else begin : g_pad
                assign t[2*k +: 2] = 2'b01;
            end
        end
        for (l = 0; l < L; l = l + 1) begin : g_l
            for (k = 0; k < (N >> (l + 1)); k = k + 1) begin : g_k
                wire [1:0] lo = t[2*N*l + 2*(2*k) +: 2], hi = t[2*N*l + 2*(2*k+1) +: 2];
                assign t[2*N*(l+1) + 2*k +: 2] = {hi[1] | (hi[0] & lo[1]), hi[0] & lo[0]};
            end
            for (k = (N >> (l + 1)); k < N; k = k + 1) begin : g_z
                assign t[2*N*(l+1) + 2*k +: 2] = 2'b00;
            end
        end
        assign gt = t[2*N*L + 1];
    endgenerate
endmodule

// s = a + b (W-bit) and the carry out, Kogge-Stone (g, p) prefix; each level a (* keep *) flat vector (the 2-D keep
// arrays of ot_hdc_ksadd_k are not kept per element by yosys: h16t mapped those adds as ripples).
module ot_hdc_add_ks #(parameter integer W=24) (input wire [W-1:0] a, input wire [W-1:0] b, output wire [W-1:0] s,
                                                 output wire cout);
    localparam integer L=(W>1) ? $clog2(W) : 1;
    (* keep *) wire [W*(L+1)-1:0] g;
    (* keep *) wire [W*(L+1)-1:0] p;
    genvar l, k;
    generate
        assign g[W-1:0] = a & b;
        assign p[W-1:0] = a ^ b;
        for (l = 0; l < L; l = l + 1) begin : g_l
            for (k = 0; k < W; k = k + 1) begin : g_k
                if (k >= (1 << l)) begin : g_c
                    assign g[W*(l+1) + k] = g[W*l + k] | (p[W*l + k] & g[W*l + k - (1 << l)]);
                    assign p[W*(l+1) + k] = p[W*l + k] & p[W*l + k - (1 << l)];
                end else begin : g_p
                    assign g[W*(l+1) + k] = g[W*l + k];
                    assign p[W*(l+1) + k] = p[W*l + k];
                end
            end
        end
        assign s[0] = p[0];
        for (k = 1; k < W; k = k + 1) begin : g_s
            assign s[k] = p[k] ^ g[W*L + k - 1];
        end
        assign cout = g[W*L + W - 1];
    endgenerate
endmodule
