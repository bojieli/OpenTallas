module qkd_ahub_static_dw_safe_gen7 #(
    parameter [63:0] AP_OFS = 64'hffd9ffdaffd8ffd8,
    parameter integer FR_OFS = -7,
    parameter integer Z_IN_STRIDE = 4,
    parameter integer ZW_RLY = 0,
    parameter integer ZR_RLY = 0,
    parameter integer RX_RLY = 1,
    parameter integer RY_RLY = 2,
    parameter integer RS_RLY = 1,
    parameter integer WF_RLY = 1,
    parameter integer MUT = 0
) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire          hs_start,
    input  wire [15:0]   hs_ep,
    input  wire [5:0]    hs_layer,
    input  wire [13:0]   hs_ctx,
    input  wire [111:0]  hs_cal_lo,
    input  wire [15:0]   hs_cal_r,
    input  wire [42:0]   ap0,
    input  wire [42:0]   ap1,
    input  wire [42:0]   ap2,
    input  wire [42:0]   ap3,
    output wire [35:0]   am0,
    output wire [35:0]   am1,
    output wire [35:0]   am2,
    output wire [35:0]   am3,
    output wire          fr_valid,
    output wire [15:0]   fr_epoch,
    output wire [127:0]  fr_rz,
    output wire          hf
);
    // Fixed-profile emitted source fails closed on any unsupported geometry.
    initial if(AP_OFS!=64'hffd9ffdaffd8ffd8 || FR_OFS!=-7 || Z_IN_STRIDE!=4 ||
        ZW_RLY!=0 || ZR_RLY!=0 || RX_RLY!=1 || RY_RLY!=2 || RS_RLY!=1 || WF_RLY!=1 || MUT!=0)
        $fatal(1,"unsupported AHUB native parameter profile");
    qkd_ahub_static_dw_safe_native u_native (
        .ck(ck),
        .rst_n(rst_n),
        .hs_start(hs_start),
        .hs_ep(hs_ep),
        .hs_layer(hs_layer),
        .hs_ctx(hs_ctx),
        .hs_cal_lo(hs_cal_lo),
        .hs_cal_r(hs_cal_r),
        .ap0(ap0),
        .ap1(ap1),
        .ap2(ap2),
        .ap3(ap3),
        .am0(am0),
        .am1(am1),
        .am2(am2),
        .am3(am3),
        .fr_valid(fr_valid),
        .fr_epoch(fr_epoch),
        .fr_rz(fr_rz),
        .hf(hf));
endmodule
