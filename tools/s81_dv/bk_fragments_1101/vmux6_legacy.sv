module dsdv_idx_vmux6_legacy #(
    parameter integer V = 276,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst,
    input  wire [V-1:0]  i_r,
    input  wire [V-1:0]  i_s,
    input  wire [V-1:0]  i_a,
    input  wire [V-1:0]  i_b,
    input  wire [V-1:0]  i_n,
    input  wire [V-1:0]  i_l,
    output reg  [V-1:0]  o,
    output reg           fault
);
    localparam integer NI = 6, NJ = (V - 1 + 23) / 24;
    reg rs0;
    always @(posedge ck or negedge rst) if (!rst) rs0 <= 1'b0; else rs0 <= 1'b1;
    wire [NI:0] rl;
    genvar k, c;
    generate for (k = 0; k <= NI; k = k + 1) begin : g_reset
        dsdv_vm_bit #(.ID(k)) u (.ck(ck), .rn(rst), .d(rs0), .q(rl[k]));
    end endgenerate
    wire [NI*V-1:0] iv = {i_l, i_n, i_b, i_a, i_s, i_r};
    reg  [NI*V-1:0] r;                     // input stage (data no reset)
    wire [NI*NJ-1:0] vk;                   // kept valid copies, one per 24-b data slice
    generate for (k = 0; k < NI; k = k + 1) begin : g_in
        localparam integer KS = (MUT == 1 && k == 4) ? 2 : k;
        for (c = 0; c < NJ; c = c + 1) begin : g_c
            dsdv_vm_bit #(.ID(100 * (k + 1) + c)) u (.ck(ck), .rn(rl[k]), .d(iv[KS*V]), .q(vk[k*NJ+c]));
        end
        always @(posedge ck or negedge rl[NI]) if (!rl[NI]) r[k*V] <= 1'b0; else r[k*V] <= iv[k*V];
        always @(posedge ck) r[k*V+1 +: V-1] <= iv[k*V+1 +: V-1];
    end endgenerate
    always @(posedge ck or negedge rl[NI])
        if (!rl[NI]) begin o[0] <= 1'b0; fault <= 1'b0; end
        else begin
            o[0] <= r[0] | r[V] | r[2*V] | r[3*V] | r[4*V] | ((MUT == 2) ? 1'b0 : r[5*V]);
            if ((3'(r[0]) + 3'(r[V]) + 3'(r[2*V]) + 3'(r[3*V]) + 3'(r[4*V]) + 3'(r[5*V])) > 3'd1) fault <= 1'b1;
        end
    generate for (c = 0; c < NJ; c = c + 1) begin : g_out
        localparam integer LO = 1 + 24 * c, SW = (V - LO < 24) ? V - LO : 24;
        always @(posedge ck)
            o[LO +: SW] <= (r[0*V+LO +: SW] & {SW{vk[0*NJ+c]}}) | (r[1*V+LO +: SW] & {SW{vk[1*NJ+c]}}) |
                           (r[2*V+LO +: SW] & {SW{vk[2*NJ+c]}}) | (r[3*V+LO +: SW] & {SW{vk[3*NJ+c]}}) |
                           (r[4*V+LO +: SW] & {SW{vk[4*NJ+c]}}) | (r[5*V+LO +: SW] & {SW{vk[5*NJ+c]}});
    end endgenerate
endmodule
