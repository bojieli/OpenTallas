`timescale 1ns/1ps
`ifndef KVD_STMUT
`define KVD_STMUT 0
`endif
// RTL-BUILD-KV/ASTK 2026-10-18: the inline e-read leaf with the visibility check (see qkd_astk_strip_er_st.sv).
// KV-ERTAP 2026-10-18 (route qkd_astk_er_tap_st-v1-b18fa696b NEEDS_RTL: FF hold -6.7, 340 input->output combinational
// bits read_addr -> aso, esi -> response_data, and a 6-level com -> fault input cone; the route hold repair stalled on
// them): EVERY data pin is registered at the face (owner rule 2026-10-15).  No input reaches an output or a register
// through logic; every output is a flop.  Edges, with a read presented at the tap pin in cycle t:
//   t+1  ri_*  <= read_v / read_addr                           (input pin registers)
//   t+2  aso   <= request field of ri_*                        (output pin registers: the EP sees the request in t+2)
//   t+3  com_q / eso_q <= com / eso_v of cycle t+2 (input pin registers, every edge); d[2] = the request on aso in t+2
//   t+4  fault <= collide | unseen | legacy of that request against com / eso_v of the cycle the EP read it (t+2)
//   t+5  the EP's e_rdq of the request (ERL 3 = the EP's own three read stages after t+2) on esi
//   t+6  esi_q <= esi                                          (input pin registers, every edge)
//   t+7  response_v / addr / data <= tag d[5], esi_q[owner]    (output pin registers)
// => read pin -> response pin = ERL + 4 = 7 edges (was ERL 3, combinational on both faces); the EP read happens 2 edges
//    after the request (was 0); er_fault 1 edge later relative to the EP read.  Static-schedule cost: +4 edges on the
//    e quad (kv_static_die astk_eread erl 7).
module qkd_astk_er_tap_st #(parameter integer N = 4, ERL = 3) (
    input  wire            ck, rst_n,
    input  wire [N-1:0]    read_v,
    input  wire [11*N-1:0] read_addr,
    // owners 0..3 (strip rows 0, 1: S face) and 4..7 (rows 2, 3: N face)
    input  wire [3:0]      eso_v_lo, eso_v_hi,   // engine so[0] of each EP owner (legacy ECTL read valid: must stay 0)
    output wire [13*4-1:0] aso_lo, aso_hi,       // so[12:0] of each EP owner as the strip sees it
    input  wire [64*4-1:0] esi_lo, esi_hi,       // si[632:569] (e_rdq) of each EP owner
    input  wire [16*4-1:0] com_lo, com_hi,       // si[552:537] (exp_done, committed e groups) of each EP owner
    output reg  [N-1:0]    response_v,
    output reg  [11*N-1:0] response_addr,
    output reg  [64*N-1:0] response_data,
    output reg             fault
);
    localparam integer D = ERL + 3;               // tag stages d[0] (t+1) .. d[D-1] (t+ERL+3): the response source
    // ---- input pin registers --------------------------------------------------------------------------------------
    reg [N-1:0]     ri_v;  reg [11*N-1:0] ri_a;   // d[0]
    reg [7:0]       eso_q;
    reg [16*8-1:0]  com_q;
    reg [64*8-1:0]  esi_q;
    // ---- output pin registers -------------------------------------------------------------------------------------
    reg [13*8-1:0]  aso;
    assign aso_lo = aso[0 +: 52]; assign aso_hi = aso[52 +: 52];
    // ---- tag / valid stages -----------------------------------------------------------------------------------------
    reg [N-1:0]     dv[1:D-1];
    reg [11*N-1:0]  da[1:D-1];
    integer i, j, e;
    // request field of the registered request (d[0]) -> aso pin flops
    reg [13*8-1:0] aso_d;
    always @* begin
        aso_d = 104'd0;
        for (j = 0; j < N; j = j + 1)
            if (ri_v[j]) aso_d[13*ri_a[11*j+3 +: 3] +: 13] = {1'b0, ri_a[11*j +: 11], 1'b1};
    end
    // fault law on d[2] (the request the EP read in the previous cycle) against com / eso_v of that cycle
    reg collide, unseen, legacy;
    reg [15:0] vis;
    always @* begin
        collide = 1'b0; unseen = 1'b0;
        vis = 16'd0;
        for (e = 0; e < 8; e = e + 1) vis = vis | com_q[16*e +: 16];
        legacy = |eso_q;
        for (j = 0; j < N; j = j + 1)
            if (dv[2][j]) begin
                for (i = 0; i < j; i = i + 1)
                    if (dv[2][i] && da[2][11*i+3 +: 3] == da[2][11*j+3 +: 3]) collide = 1'b1;
                if (!vis[da[2][11*j+3 +: 4]]) unseen = 1'b1;
            end
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin
            ri_v <= 0; aso <= 0; eso_q <= 0; fault <= 0; response_v <= 0;
            for (i = 1; i < D; i = i + 1) dv[i] <= 0;
        end else begin
            ri_v <= read_v; eso_q <= {eso_v_hi, eso_v_lo};
            aso <= aso_d;
            dv[1] <= ri_v; for (i = 2; i < D; i = i + 1) dv[i] <= dv[i-1];
            response_v <= dv[D-1];
            if (collide) fault <= 1;
            if (unseen && (`KVD_STMUT != 4)) fault <= 1;
            if (legacy) fault <= 1;
        end
    always @(posedge ck) begin
        ri_a <= read_addr;
        com_q <= {com_hi, com_lo};
        esi_q <= {esi_hi, esi_lo};
        da[1] <= ri_a; for (i = 2; i < D; i = i + 1) da[i] <= da[i-1];
        response_addr <= da[D-1];
    end
    genvar g;
    generate for (g = 0; g < N; g = g + 1) begin : g_rsp
        wire [2:0] owner = (`KVD_STMUT == 5) ? da[D-2][11*g+3 +: 3] : da[D-1][11*g+3 +: 3];
        // decoded constant-index select (one-hot AND-OR; same function as esi_q[64*owner +: 64]) -> response pin flops
        // (`KVD_STMUT 6 = mutant: the e quad taken from the esi pins, bypassing the esi pin registers: one edge early)
        wire [64*8-1:0] esrc = (`KVD_STMUT == 6) ? {esi_hi, esi_lo} : esi_q;
        reg [63:0] sel;
        integer o;
        always @* begin sel = 64'd0; for (o = 0; o < 8; o = o + 1) sel = sel | ({64{owner == 3'(o)}} & esrc[64*o +: 64]); end
        always @(posedge ck) response_data[64*g +: 64] <= sel;
    end endgenerate
    initial if (ERL != 3 || N < 1 || N > 8) $fatal(1, "native EP ABI requires ERL3, 1<=N<=8");
endmodule
