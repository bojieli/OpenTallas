(* blackbox *) module qfd_syscal16_n32(
  input wire ck,
  input wire [4:0] rst_n,
  input wire cfg_we,
  input wire [4:0] cfg_addr,
  input wire [31:0] cfg_data_k,
  input wire [15:0] cfg_seg_k,
  input wire [7:0] start_k,
  input wire [7:0] halt_k,
  input wire [4:0] seg_k,
  output wire ev_v,
  output wire [2:0] ev_port,
  output wire [3:0] ev_kind,
  output wire [4:0] ev_beat,
  output wire running,
  output wire fault
);
endmodule

(* blackbox *) module qfd_syscal32_n32(
  input wire ck,
  input wire [6:0] rst_n,
  input wire cfg_we,
  input wire [5:0] cfg_addr,
  input wire [31:0] cfg_data_k,
  input wire [34:0] cfg_seg_k,
  input wire [9:0] start_k,
  input wire [9:0] halt_k,
  input wire [5:0] seg_k,
  output wire ev_v,
  output wire [2:0] ev_port,
  output wire [3:0] ev_kind,
  output wire [4:0] ev_beat,
  output wire running,
  output wire fault
);
endmodule

(* blackbox *) module qfd_syscal64_n32(
  input wire ck,
  input wire [10:0] rst_n,
  input wire cfg_we,
  input wire [6:0] cfg_addr,
  input wire [63:0] cfg_data_k,
  input wire [77:0] cfg_seg_k,
  input wire [13:0] start_k,
  input wire [13:0] halt_k,
  input wire [7:0] seg_k,
  output wire ev_v,
  output wire [2:0] ev_port,
  output wire [3:0] ev_kind,
  output wire [4:0] ev_beat,
  output wire running,
  output wire fault
);
endmodule
