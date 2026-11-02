// PREP functional ports only; physical FT roles remain HOLD. Not a registered macro.
module qkd_kvs_pc (
    input wire [779:0] i_next,
    output wire [327:0] pc__po,
    input wire [0:0] ck,
    input wire [0:0] hrst_n,
    input wire [127:0] i_grp,
    output wire [304:0] o_grp,
    input wire [1:0] pc__cfg_stack,
    output wire [0:0] pc__hcompletion_v,
    output wire [0:0] pc__hcompletion_we,
    output wire [260:0] pc__her,
    input wire [287:0] pc__hes,
    input wire [0:0] pc__land_er,
    input wire [260:259] pc__land_er_259,
    output wire [287:0] pc__land_es,
    input wire [4:0] pc__pc,
    input wire [288:0] pc__pi,
    input wire [0:0] rst_n,
    input wire [298:0] i_prev,
    output wire [298:0] o_next,
    output wire [779:0] o_prev,
    input wire [0:0] pc__fi,
    output wire [0:0] pc__fo,
    input wire [32:0] pc__ki,
    output wire [32:0] pc__ko,
    input wire [0:0] x__est__0_1
);
endmodule
