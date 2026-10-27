(* blackbox *)
module ot_hdc_v41x_attn_s #(parameter integer H=16, D=32, TD=32, NL=4, TROWS=640, SRAM_MACRO=0, PWORDS=2, ILV=1, REPL=2,
  NSTAGE=2, FPL=4, FML=6, NBANKP=0, TILE_S=1, NARROW=1, MFAN=1, TRX=1, F12=1, FPLX=5, SC_CRED=0, PV_CRED=0) (
  input clk, rst_n, job_v, input [15:0] job_t, output job_ready, input q_v, input [D*16-1:0] q_w, output q_ready,
  input kv_v, input [NL-1:0] kv_m, input [NL*265-1:0] kv_w, output kv_ready,
  output sc_v, output [15:0] sc_row, output [NL-1:0] sc_m, output [NL*H*32-1:0] sc_y, output [NL*H-1:0] sc_f, input sc_cr,
  input p_v, input [2*TD*16-1:0] p_w, output p_ready,
  output pv_v, output [7:0] pv_c, output [4*H*32-1:0] pv_y, output [4*H-1:0] pv_f, input pv_cr, output qk_iss, output pv_iss);
endmodule
