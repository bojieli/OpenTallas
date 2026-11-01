// Selected compact199 physical wrapper parameters retained; INSTANCE/MB simulation identity preserved.
(* blackbox *)
module ot_v41_bf_col #(
    parameter integer NSEG = 8,
    parameter integer NCH = 16,
    parameter integer XF = 4,
    parameter integer LV = 5,
    parameter integer BF16 = 0,       
    parameter integer NCHB = 8,
    parameter integer NB = 1,
    parameter integer MTP = 0,        
    parameter integer EARLY = 0,      
    parameter integer CG = 1,         
                                      
    parameter integer DRAIN = 127,
    
    
    
    parameter integer FAST = 0,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer PP = 0,
    
    
    parameter integer FRONT_PAR = 0,
    
    
    
    
    
    parameter integer BP = 0,
    parameter integer QTIMING_FIX = 0,  
    parameter integer HC = 3,           
    parameter integer QPIPE = 0,        
    parameter integer QP_XS = 1,        
                                        
    parameter integer QP_CAP = 0,       
    parameter integer QP_P1 = 1,        
    parameter integer QP_CSAM = 10,     
    parameter integer QZ = 0,           
    parameter integer QZ_NS = 8,        
    parameter integer QZ_NE = 4,        
    parameter integer QY = 0,           
    parameter integer QX = 0,           
    
    
    
    parameter integer QBF = 0,
    
    
    
    
    
    
    parameter integer QZE = 0,
    
    
    
    
    
    
    
    
    parameter integer TCG = 0,
    parameter integer BXST = 0,
    parameter integer FXST = 0,         
    parameter integer GRADUAL_RNE = 0,
    parameter INSTANCE = "",
    parameter integer HDLY = 0,       
    parameter integer MB = 0,         
    
    
    
    
    
    
    
    
    
    
    parameter integer RCG = 0,
    parameter integer TAG_GROUPS = 0, 
    parameter integer KEEP_XPOS = 0   
) (
    input  wire          clk,
    input  wire          rst_n_pin,
    input  wire          ze_d,          
    input  wire          issue,
    input  wire [13:0]   a_ctr,
    input  wire          i1_v,
    input  wire          i1_bk,
    input  wire          i1_bf,
    input  wire [$clog2(NCH)+3+$clog2(NSEG)+(MTP != 0 ? 1 : 0)+6-1:0] i1_t,
    input  wire [255:0]  i2x_q0,
    input  wire [9:0]    i2x_e0,
    input  wire [255:0]  i2x_q1,
    input  wire [9:0]    i2x_e1,
    input  wire [16*NSEG-1:0] so_row,   
    input  wire [5*NSEG-1:0]  so_idx,
    input  wire [5*NSEG-1:0]  so_n,
    output wire          pv,
    output wire [31:0]   pval,
    output wire [15:0]   prow,
    output wire [4:0]    pseg,
    output wire [4:0]    pnseg,
    output wire          perr,
    output wire [2:0]    ppos,
    output wire          qy_bkf
);
endmodule
