// stand-in pin source: header of ot_s81sl_vp from rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv with default parameters {'ML': '7', 'AL': '6', 'HPL': '1'}
module ot_s81sl_vp (
input  wire          clk,
    input  wire          rst_n,
    input  wire          c_v,
    input  wire [159:0]  c_d,
    
    input  wire          sw_v,
    input  wire [9:0]    sw_a,
    input  wire [7:0]    sw_m,
    input  wire [255:0]  sw_d,
    
    input  wire [1:0]    cw_v,
    input  wire [23:0]   cw_a,
    input  wire [63:0]   cw_d,
    
    output reg           lo_v,
    output reg  [255:0]  lo_d,
    
    output reg           s_v,
    output reg  [159:0]  s_d,
    input  wire          x_rv,
    input  wire [9:0]    x_ra,
    output reg           x_qv,
    output reg  [255:0]  x_qd,
    input  wire          x_wv,
    input  wire [9:0]    x_wa,
    input  wire [7:0]    x_wm,
    input  wire [255:0]  x_wd,
    
    output reg           hw_v, output reg [2:0] hw_j, output reg hw_hf, output reg [255:0] hw_d,
    output reg           hr_v, output reg [2:0] hr_j, output reg hr_hf,
    input  wire          hq_v, input wire [255:0] hq_d,
    output reg           n_go, output reg [127:0] n_pre,
    output reg           m_v, output reg m_q, output reg m_b, output reg [7:0] m_i,
    output reg           wl_v, output reg [2:0] wl_i, output reg [255:0] wl_d,
    output reg           fault
);
endmodule
