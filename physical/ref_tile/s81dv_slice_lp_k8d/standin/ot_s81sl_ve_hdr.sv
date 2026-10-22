// stand-in pin source: header of ot_s81sl_ve from rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv with default parameters {'LM': '5'}
module ot_s81sl_ve (
input  wire         clk,
    input  wire         rst_n,
    
    input  wire         r_v,
    input  wire [1:0]   r_c,
    input  wire [127:0] r_h, r_k, r_w,
    
    output reg          p_v,
    output reg  [1:0]   p_c,
    output reg  [31:0]  p_hh, p_kk, p_dd,
    
    input  wire         a_v,
    input  wire [1:0]   a_c,
    input  wire [255:0] a_h, a_val,
    input  wire [31:0]  a_g,
    output reg          o_v,
    output reg  [1:0]   o_c,
    output reg  [255:0] o_y,
    output reg          fault
);
endmodule
