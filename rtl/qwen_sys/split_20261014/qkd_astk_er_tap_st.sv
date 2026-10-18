`timescale 1ns/1ps
`ifndef KVD_STMUT
`define KVD_STMUT 0
`endif
// RTL-BUILD-KV/ASTK 2026-10-18: the inline e-read leaf with the visibility check (see qkd_astk_strip_er_st.sv).
module qkd_astk_er_tap_st #(parameter integer N = 4, ERL = 3) (
    input  wire            ck, rst_n,
    input  wire [N-1:0]    read_v,
    input  wire [11*N-1:0] read_addr,
    // owners 0..3 (strip rows 0, 1: S face) and 4..7 (rows 2, 3: N face)
    input  wire [3:0]      eso_v_lo, eso_v_hi,   // engine so[0] of each EP owner (legacy ECTL read valid: must stay 0)
    output wire [13*4-1:0] aso_lo, aso_hi,       // so[12:0] of each EP owner as the strip sees it
    input  wire [64*4-1:0] esi_lo, esi_hi,       // si[632:569] (e_rdq) of each EP owner
    input  wire [16*4-1:0] com_lo, com_hi,       // si[552:537] (exp_done, committed e groups) of each EP owner
    output wire [N-1:0]    response_v,
    output wire [11*N-1:0] response_addr,
    output wire [64*N-1:0] response_data,
    output reg             fault
);
    wire [7:0] eso_v = {eso_v_hi, eso_v_lo};
    wire [64*8-1:0] esi = {esi_hi, esi_lo};
    wire [16*8-1:0] com = {com_hi, com_lo};
    reg  [13*8-1:0] aso;
    assign aso_lo = aso[0 +: 52]; assign aso_hi = aso[52 +: 52];
    reg [N-1:0] val[0:ERL-1];
    reg [10:0] tag[0:ERL-1][0:N-1];
    reg collide, unseen;
    reg [15:0] vis;
    integer i, j, e;
    always @* begin
        aso = 104'd0;
        collide = 1'b0;
        vis = 16'd0;
        for (e = 0; e < 8; e = e + 1) vis = vis | com[16*e +: 16];
        unseen = 1'b0;
        for (j = 0; j < N; j = j + 1)
            if (read_v[j]) begin
                for (i = 0; i < j; i = i + 1)
                    if (read_v[i] && read_addr[11*i+3 +: 3] == read_addr[11*j+3 +: 3]) collide = 1'b1;
                aso[13*read_addr[11*j+3 +: 3] +: 13] = {1'b0, read_addr[11*j +: 11], 1'b1};
                if (!vis[read_addr[11*j+3 +: 4]]) unseen = 1'b1;
            end
    end
    always @(posedge ck or negedge rst_n)
        if (!rst_n) begin for (i = 0; i < ERL; i = i + 1) val[i] <= 0; fault <= 0; end
        else begin
            val[0] <= read_v; for (i = 1; i < ERL; i = i + 1) val[i] <= val[i-1];
            if (collide) fault <= 1;
            if (unseen && (`KVD_STMUT != 4)) fault <= 1;
            for (e = 0; e < 8; e = e + 1) if (eso_v[e]) fault <= 1;
        end
    always @(posedge ck) begin
        for (j = 0; j < N; j = j + 1) begin tag[0][j] <= read_addr[11*j +: 11]; for (i = 1; i < ERL; i = i + 1) tag[i][j] <= tag[i-1][j]; end
    end
    genvar g;
    generate for (g = 0; g < N; g = g + 1) begin : g_rsp
        wire [2:0] owner = (`KVD_STMUT == 5) ? tag[ERL-2][g][5:3] : tag[ERL-1][g][5:3];
        assign response_v[g] = val[ERL-1][g];
        assign response_addr[11*g +: 11] = tag[ERL-1][g];
        // decoded constant-index select (one-hot AND-OR; same function as esi[64*owner +: 64], no runtime part-select)
        reg [63:0] sel;
        integer o;
        always @* begin sel = 64'd0; for (o = 0; o < 8; o = o + 1) sel = sel | ({64{owner == 3'(o)}} & esi[64*o +: 64]); end
        assign response_data[64*g +: 64] = sel;
    end endgenerate
    initial if (ERL != 3 || N < 1 || N > 8) $fatal(1, "native EP ABI requires ERL3, 1<=N<=8");
endmodule
