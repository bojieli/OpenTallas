`timescale 1ns/1ps
// One X_SU constant operand from the held HBM RoPE pair cache. Ordinary
// CROM reads are left to the tile. Address bits 29:28 (AW-1:AW-2) tag a
// production RoPE read: 10 plain, 11 YaRN; bits [AW-3:5] are position.
module ot_chip_v41x_rope_su_word #(
    parameter integer AW = 30,
    parameter integer PW = 21
) (
    input  wire [1:0]     src,
    input  wire [AW-1:0]  addr,
    input  wire           cache_valid,
    input  wire           cache_hold,
    input  wire           cache_kind,
    input  wire [PW-1:0]  cache_pos,
    input  wire [2047:0]  cache_pairs,
    output wire           is_rope,
    output wire           bad,
    output wire [31:0]    data
);
    assign is_rope = AW >= 28 && (src == 2'd1 || src == 2'd2) &&
                    addr[AW-1:AW-2] >= 2'b10;
    assign bad = is_rope && (!cache_valid || !cache_hold ||
                 cache_kind != addr[AW-2] || AW'(cache_pos) != AW'(addr[AW-3:5]));
    wire [63:0] pair = cache_pairs[64*addr[4:0] +: 64];
    assign data = bad ? '0 : (src == 2'd1 ? pair[31:0] : pair[63:32]);
endmodule
