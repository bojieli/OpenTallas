`timescale 1ns/1ps
// BENCH-ONLY mutant child for tools/qwen_cluster/bench_reg1.sh M1: the reg1 ring-pair reader with read epoch K 3
// instead of the contract K 2 (bound only by the M1 sed copy of qfd_c_b16_reg1.sv; unused otherwise).
module qfd_c_land_r257_narrow_k3 (input wire ck, rsi, output wire [256:0] o, input wire [513:0] bank_w, bank_e,
                                  input wire [43:0] vld);
  wire [1027:0] b;
  assign b = {bank_e, bank_w};
  qfd_c_land_safe_r #(.W(257), .K(3)) u (.ck(ck), .rsi(rsi), .bank(b), .vld(vld), .o(o));
endmodule
