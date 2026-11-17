(* blackbox *) module ot_hdc_sfu_exp_t #(
    parameter integer LA = 4,
    parameter integer LM = 5
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output reg         vo,
    output reg         fault
);
endmodule

(* blackbox *) module qfd_dv_lane_h_su_mem9 #(parameter integer CONTROL_SAFE=1, MEMORY_ALIGNMENT=3, MEMORY_READ_EXTRA=4, KV_WR_PIPE=0, SEGMENTED_MEMORY_DELAY=0) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              emit0,
    input  wire              live,
    input  wire [17:0]       i,
    input  wire [18:0]       fin_th,
    input  wire              i_last_r,
    input  wire [23:0]       cura0, curb0, curc0, curd0, rrow,
    input  wire [23:0]       asi, bsi, csi, dsi,
    input  wire              asrc, bsrc, csrc, mc, md, redsq,
    input  wire [1:0]        ma, mb, dst, red,
    input  wire [2:0]        ad,
    input  wire [31:0]       imm1, imm2,
    input  wire [2:0]        cls,
    input  wire              accept,
    input  wire [2:0]        i_sfu,
    output wire              va_re,
    output wire [23:0]       va_addr,
    input  wire [31:0]       va_q,
    output wire              vb_re,
    output wire [23:0]       vb_addr,
    input  wire [31:0]       vb_q,
    output wire              vc_re,
    output wire [23:0]       vc_addr,
    input  wire [31:0]       vc_q,
    output wire              wrom_re,
    output wire [23:0]       wrom_addr,
    input  wire [255:0]      wrom_q,
    output wire              crom_re,
    output wire [23:0]       crom_addr,
    input  wire [63:0]       crom_q,
    output wire              vm_we,
    output wire [23:0]       vm_waddr,
    output wire [31:0]       vm_wdata,
    output wire              kv_we,
    output wire [23:0]       kv_waddr,
    output wire [31:0]       kv_wdata,
    output wire              l_ov,
    output wire [31:0]       l_out,
    output wire [1:0]        l_red,
    output wire              l_redsq,
    output wire [23:0]       l_raddr,
    output wire              l_last,
    output wire              retire,
    output wire              l_fault,
    output wire              sx_exp_v,
    output wire [31:0]       sx_exp_x,
    input  wire [31:0]       sy_exp_y,
    input  wire              sy_exp_vo,
    input  wire              sy_exp_f,
    output wire              sx_rcp_v,
    output wire [31:0]       sx_rcp_x,
    input  wire [31:0]       sy_rcp_y,
    input  wire              sy_rcp_f,
    output wire              sx_rsq_v,
    output wire [31:0]       sx_rsq_x,
    input  wire [31:0]       sy_rsq_y,
    input  wire              sy_rsq_f
);
endmodule

(* blackbox *) module qfd_dv_s5_lrly #(parameter integer MUT = 0) (
    input  wire           ck,
    input  wire           rst_n,
    
    input  wire [499:0]   gb,
    input  wire [2:0]     gv,
    input  wire           lv1,
    input  wire [95:0]    pd1,
    input  wire [31:0]    va_q, vb_q, vc_q,
    input  wire [63:0]    cr_q,
    
    output wire           h_rst_n,
    output wire           c_emit0, c_live, c_ilast, c_accept,
    output wire [17:0]    c_i,
    output wire [18:0]    c_fin_th,
    output wire [23:0]    c_cura, c_curb, c_curc, c_curd, c_rrow, c_asi, c_bsi, c_csi, c_dsi,
    output wire           c_asrc, c_bsrc, c_csrc, c_mc, c_md, c_redsq,
    output wire [1:0]     c_ma, c_mb, c_dst, c_red,
    output wire [2:0]     c_ad, c_cls, c_isfu,
    output wire [31:0]    c_imm1, c_imm2,
    output wire [31:0]    c_va, c_vb, c_vc,
    output wire [255:0]   c_wrom,
    output wire [63:0]    c_crom,
    
    input  wire           h_va_re, h_vb_re, h_vc_re, h_wrom_re, h_crom_re, h_vm_we, h_kv_we, h_l_ov, h_l_redsq, h_l_last,
                          h_retire, h_l_fault,
    input  wire [23:0]    h_va_addr, h_vb_addr, h_vc_addr, h_wrom_addr, h_crom_addr, h_vm_waddr, h_kv_waddr, h_l_raddr,
    input  wire [31:0]    h_vm_wdata, h_kv_wdata, h_l_out,
    input  wire [1:0]     h_l_red,
    
    output wire           va_re, vb_re, vc_re, wrom_re, crom_re, vm_we, kv_we, l_ov, l_last, retire, l_fault, l_redsq,
    output wire [23:0]    va_addr, vb_addr, vc_addr, wrom_addr, crom_addr, vm_waddr, kv_waddr, l_raddr,
    output wire [31:0]    vm_wdata, kv_wdata, l_out,
    output wire [1:0]     l_red
);
endmodule

(* blackbox *) module ot_hdc_sfu_rcp_t #(
    parameter integer LA = 4,
    parameter integer LM = 5
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output reg         vo,
    output reg         fault
);
endmodule

(* blackbox *) module ot_hdc_sfu_rsq_t #(
    parameter integer LA = 4,
    parameter integer LM = 5
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output reg         vo,
    output reg         fault
);
endmodule
