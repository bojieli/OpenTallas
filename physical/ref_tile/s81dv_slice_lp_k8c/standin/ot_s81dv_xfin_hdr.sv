// stand-in pin source: header of ot_s81dv_xfin from rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv with default parameters {'NS': '16', 'NVL': '5', 'LM': '5', 'LA': '6'}
module ot_s81dv_xfin (
input  wire               clk,
    input  wire               rst_n,
    input  wire               go,
    input  wire               mode,         
    input  wire [3:0]         sid,          
    input  wire [31:0]        eps,
    input  wire               s_v,          
    input  wire [7:0]         s_i,
    input  wire [31:0]        s,
    input  wire               wi_v, input wire [3:0] wi_h, input wire [7:0] wi_b, input wire [5*32-1:0] wi_d,
    input  wire               ei_v, input wire [3:0] ei_h, input wire [7:0] ei_b, input wire [5*32-1:0] ei_d,
    output wire               eo_v, output wire [3:0] eo_h, output wire [7:0] eo_b, output wire [5*32-1:0] eo_d,
    output wire               wo_v, output wire [3:0] wo_h, output wire [7:0] wo_b, output wire [5*32-1:0] wo_d,
    output reg                rb_v,         
    output reg  [31:0]        rb_d,
    output reg                e_v,          
    output reg  [1:0]         e_c,
    output reg  [31:0]        e_hh, e_kk, e_dd,
    output wire               fault
);
endmodule
