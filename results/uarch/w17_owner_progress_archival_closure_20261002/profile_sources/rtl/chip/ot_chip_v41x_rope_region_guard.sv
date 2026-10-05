`timescale 1ns/1ps
// Runtime HBM placement contract for read-only plain/YaRN RoPE tables.
// reserved_end[s] is the first free sector after *all* deployed key, window,
// CKV and other state regions on stack s. Zero is invalid. Every enabled
// table occupies MAX_POS*2 sectors per stack, with a 0.9 usable-capacity cap.
module ot_chip_v41x_rope_region_guard #(
    parameter integer HAW=30,
    parameter integer K_MEM=703125000,
    parameter integer MAX_POS=1048576
) (
    input  wire [1:0]       present,
    input  wire [4*HAW-1:0] reserved_end,
    input  wire [4*HAW-1:0] plain_base,
    input  wire [4*HAW-1:0] yarn_base,
    output wire             valid,
    output wire [3:0]       bad_stack
);
    localparam [63:0] TABLE_SECTORS=64'(MAX_POS)*2;
    localparam [63:0] USABLE_SECTORS=64'(K_MEM)*9/10;
    genvar s;
    generate for(s=0;s<4;s=s+1) begin : g_s
        wire [63:0] rsv=64'(reserved_end[s*HAW +: HAW]);
        wire [63:0] p0=64'(plain_base[s*HAW +: HAW]);
        wire [63:0] y0=64'(yarn_base[s*HAW +: HAW]);
        wire [63:0] p1=p0+TABLE_SECTORS;
        wire [63:0] y1=y0+TABLE_SECTORS;
        wire p_bad=present[0] && (p0<rsv || p1>USABLE_SECTORS || p1>(64'(1)<<HAW));
        wire y_bad=present[1] && (y0<rsv || y1>USABLE_SECTORS || y1>(64'(1)<<HAW));
        wire overlap=present==2'b11 && p0<y1 && y0<p1;
        assign bad_stack[s]=(rsv==0 || p_bad || y_bad || overlap);
    end endgenerate
    assign valid=present!=0 && !(|bad_stack);
endmodule
