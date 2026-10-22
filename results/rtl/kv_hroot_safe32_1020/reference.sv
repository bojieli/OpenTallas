`timescale 1ns/1ps
module qkd_kv_es_fan_stack_b #(parameter integer MUT = 0) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [1:0]      stack,         // identity strap: WS 0, WN 1, ES 2, EN 3
    input  wire [783:0]    h,
    output reg  [779:0]    d
);
    localparam integer H_AV = 0, H_XV = 2, H_DST = 4, H_EST = 6, H_PA = 8, H_PB = 13, H_QA = 18, H_QB = 23, H_DA = 28,
                       H_DB = 284, H_AD = 540, H_SV = 569, H_CTX = 570, H_EID = 631, H_EAD = 692, H_SS = 721,
                       H_TOK = 722, H_EP = 740, H_CV = 756, H_CST = 757, H_CPC = 759, H_CRG = 764, H_CVL = 767,
                       H_BV = 783;
    // chain field map: qkd_kv_es_fan_root / qkd_kv_pc_chain_station
    localparam integer F_V = 0, F_PC0 = 2, F_PC1 = 7, F_D0 = 12, F_D1 = 268, F_AD = 524, F_SV = 553, F_CTX = 554,
                       F_EV = 615, F_EPC0 = 617, F_EPC1 = 622, F_EST = 627, F_EID = 629, F_EAD = 690,
                       F_SS = 719, F_TOK = 720, F_EP = 738, F_CV = 754, F_CPC = 755, F_CRG = 760, F_CVL = 763, F_BT = 779,
                       W = 780;
    (* keep *) reg rs_q;
    always @(posedge ck) rs_q <= rst_n;
    wire [1:0] s = (MUT == 1) ? (stack ^ 2'd1) : stack;
    function automatic [W-1:0] head(input [W-1:0] prev, input [783:0] x);
        reg [W-1:0] o; reg [1:0] v, e;
        begin
            o = prev;
            v = x[H_AV +: 2] & {2{x[H_DST +: 2] == s}};
            e = x[H_XV +: 2] & {2{x[H_EST +: 2] == s}};
            o[F_V +: 2] = v; o[F_EV +: 2] = e;
            if (|v) begin
                o[F_PC0 +: 5] = x[H_PA +: 5]; o[F_PC1 +: 5] = x[H_PB +: 5];
                o[F_D0 +: 256] = x[H_DA +: 256]; o[F_D1 +: 256] = x[H_DB +: 256];
                o[F_AD +: 29] = x[H_AD +: 29]; o[F_SV] = x[H_SV]; o[F_CTX +: 61] = x[H_CTX +: 61];
            end
            if (|e) begin
                o[F_EPC0 +: 5] = x[H_QA +: 5]; o[F_EPC1 +: 5] = x[H_QB +: 5]; o[F_EST +: 2] = x[H_EST +: 2];
                o[F_EID +: 61] = x[H_EID +: 61]; o[F_EAD +: 29] = x[H_EAD +: 29];
            end
            o[F_SS] = x[H_SS];
            if (x[H_SS]) begin o[F_TOK +: 18] = x[H_TOK +: 18]; o[F_EP +: 16] = x[H_EP +: 16]; end
            o[F_CV] = x[H_CV] && x[H_CST +: 2] == s;
            if (x[H_CV]) begin o[F_CPC +: 5] = x[H_CPC +: 5]; o[F_CRG +: 3] = x[H_CRG +: 3]; o[F_CVL +: 16] = x[H_CVL +: 16]; end
            // BOOT: the boot word for this stack takes lane 0's pc / data / address fields (lane valids stay 0)
            o[F_BT] = x[H_BV] && x[H_DST +: 2] == s;
            if (o[F_BT]) begin o[F_PC0 +: 5] = x[H_PA +: 5]; o[F_D0 +: 256] = x[H_DA +: 256]; o[F_AD +: 29] = x[H_AD +: 29]; end
            head = o;
        end
    endfunction
    always @(posedge ck or negedge rs_q)
        if (!rs_q) d <= {W{1'b0}};
        else d <= head(d, h);
endmodule


module qkd_kv_es_fan_stack_bl #(parameter integer MUT = 0) (
    input  wire            ck,
    input  wire            rst_n,
    input  wire [1:0]      stack,         // identity strap: WS 0, WN 1, ES 2, EN 3
    input  wire [783:0]    h,
    output wire [779:0]    d
);
    reg [783:0] h_c;        // capture registers (i_ctl pins)
    reg [1:0]   s_c;
    always @(posedge ck) begin
        h_c <= h;
        s_c <= stack;
    end
    qkd_kv_es_fan_stack_b #(.MUT(MUT == 1 ? 1 : 0)) u_st (.ck(ck), .rst_n(rst_n), .stack(s_c),
                                                          .h((MUT == 2) ? h : h_c), .d(d));
endmodule

module qkd_kv_stack_relays_l #(parameter integer HW = 783, FW = 1, GW = 1, RW = 1, MUT = 0) (
    input  wire            ck,
    input  wire [HW+FW-1:0] dn,
    input  wire [GW-1:0]   g_i,
    input  wire [RW-1:0]   r_i,
    output reg  [FW-1:0]   fan,
    output reg  [GW-1:0]   g,
    output reg  [RW-1:0]   r
);
    reg [FW-1:0] fan_c;     // capture registers (input pins)
    reg [GW-1:0] g_c;
    reg [RW-1:0] r_c;
    always @(posedge ck) begin
        fan_c <= dn[HW - ((MUT == 1) ? 1 : 0) +: FW];
        g_c <= g_i;
        r_c <= r_i;
        fan <= fan_c;       // launch registers (output pins)
        g <= g_c;
        r <= (MUT == 2) ? r_i : r_c;
    end
endmodule

