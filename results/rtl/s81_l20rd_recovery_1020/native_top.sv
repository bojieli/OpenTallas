module idxrg_r32_native_top (
    input  wire          ck,
    input  wire          rst,
    input  wire [3:0]    sid,
    input  wire [512:0]  qi,            // query chain {d 512, v}
    output reg  [512:0]  qo,
    input  wire [275:0]  si,            // score chain (BK V beats)
    output reg  [275:0]  so,
    input  wire [681:0]  rqi,           // from dsdv_svc_rs
    output reg  [681:0]  rqo,           // to dsfd_ctrl_rg2
    input  wire [561:0]  rdi,           // from dsfd_ctrl_rg2
    output reg  [561:0]  rdo,           // to dsdv_svc_rs
    output reg  [9:0]    st             // {fault cause 8, busy, fault}
);
dsdv_idx_rg_r32 #(.SRAM_MACRO(1), .ENG(1), .SQD(256)) u (.*);
endmodule
