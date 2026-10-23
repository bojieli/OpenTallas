// HBMc/TILES4 10-22 (HIERWRAP for the TP192 benches): Verilator 5.050 never substitutes a PARAMETERISED hier block in
// the top pass (HBMc/TOKEN2 9ba20e88b).  ot_hgi_coll_tkm_tile_e86 gained FAN32 / SEAM, so tkm_tp192_hier.vlt's hier
// block stopped being substituted and the TP192 top elaborated all 32 tiles flat (daemon peaks 210.8 / 271.2 GB).
// One parameter-free wrapper per FAN32 value (SEAM 0, as ot_hgi_coll_tkm_static instantiates it); same master, same
// parameters, ports by name.  Compiled only with -DOT_TKM_HIERWRAP (run_tp192_*.sh HIERWRAP=1).
module ot_hgi_coll_tkm_tile_e86_hw0(input wire clk,clk_r0,clk_r1,clk_r2,clk_r3,input wire clr,conv,
 input wire ins_v,input wire [343:0] ins_b,output wire ovf_v,output wire [343:0] ovf_b,
 input wire [343:0] up_in,output wire [343:0] up_out,output wire busy);
 ot_hgi_coll_tkm_tile_e86 #(.FAN32(0)) u(.*);
endmodule
module ot_hgi_coll_tkm_tile_e86_hw1(input wire clk,clk_r0,clk_r1,clk_r2,clk_r3,input wire clr,conv,
 input wire ins_v,input wire [343:0] ins_b,output wire ovf_v,output wire [343:0] ovf_b,
 input wire [343:0] up_in,output wire [343:0] up_out,output wire busy);
 ot_hgi_coll_tkm_tile_e86 #(.FAN32(1)) u(.*);
endmodule
module ot_hgi_coll_tkm_tile_e86_hw2(input wire clk,clk_r0,clk_r1,clk_r2,clk_r3,input wire clr,conv,
 input wire ins_v,input wire [343:0] ins_b,output wire ovf_v,output wire [343:0] ovf_b,
 input wire [343:0] up_in,output wire [343:0] up_out,output wire busy);
 ot_hgi_coll_tkm_tile_e86 #(.FAN32(2)) u(.*);
endmodule
