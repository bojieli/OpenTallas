`default_nettype none
(* blackbox *) module ot_hbm_svc_static_sm_packed136_native_safe #(parameter integer PACKED136=0, MUT=0)(
 input wire clk,rst_n,
 input wire open_v,open_bank,input wire [15:0] open_epoch,input wire [6:0] open_count,input wire [9:0] open_tag_base,
 input wire [3:0] sector_v,input wire [95:0] sector_index,input wire [63:0] sector_epoch,input wire [1023:0] sector_data,
 input wire read_v,read_bank,input wire [15:0] read_epoch,input wire [5:0] read_row,input wire [9:0] read_tag,
 input wire retire_v,retire_bank,input wire [15:0] retire_epoch,
 output wire [1:0] block_ready,bank_owned,output wire busy,fault,output wire [1098:0] out_packet
);
endmodule

(* blackbox *) module ot_smh_calendar_static_x #(
    parameter integer W=135,
    parameter integer AW=11,
    parameter integer XW=1,
    parameter integer MUT=0 // 1 wrong wrap PC, 2 extra cycle at loop boundary, 3 context not captured (stale)
)(
    input wire clk,rst_n,
    input wire cfg_we,
    input wire [AW-1:0] cfg_addr,
    input wire [255:0] cfg_data,
    input wire start_v,
    input wire [AW-1:0] start_base,
    input wire [AW:0] start_limit,
    input wire [15:0] start_loops,
    input wire [XW-1:0] start_ctx,
    output reg [W-1:0] calendar,
    output reg [XW-1:0] calendar_ctx,
    output reg [15:0] calendar_iter,
    output reg calendar_lastit,
    output reg calendar_v,
    output reg [31:0] ordinal,
    output reg active,done,fault
);
endmodule

(* blackbox *) module ot_hbm_svg_landing_pair_native #(parameter integer J=0,MUT=0,FIFOMUT=0)(
 input wire pair_hbm_clk,pair_hbm_rst_n,pair_clk,pair_rst_n,return_clk,return_rst_n,
 input wire [1:0] in_v,input wire [569:0] in_data,output wire [1:0] in_ready,overflow,
 input wire reserve_v,input wire [1:0] reserve_bank,input wire [15:0] reserve_epoch,
 input wire [11:0] reserve_total,input wire stop,
 input wire [1:0] read_v,input wire [3:0] read_bank,input wire [11:0] read_row,
 input wire [2:0] ordinal,input wire group_valid,
 output wire [1:0] complete_v,output wire [3:0] complete_bank,output wire [1:0] bank_fault,
 output wire [255:0] out_data,output wire [2:0] out_ordinal,output wire out_valid,phase_fault
);
endmodule


// Unselected default alternative: must vanish from selected native configuration.
(* blackbox *) module ot_hbm_svc_sm8_landing_bank_sram285 #(
 parameter [2:0] BANK=0,parameter integer RESPONSE_DEPTH=8,parameter integer LBANKS=4,parameter integer FMUT=0,
 parameter integer LB=(LBANKS>2)?2:1,parameter integer IW=283+LB
)(
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire in_v,output wire in_ready,input wire [IW-1:0] in_data,
 output wire overflow,
 input wire reserve_v,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,
 input wire [11:0] reserve_total,input wire stop,
 output wire complete_v,output wire [LB-1:0] complete_bank,output wire fault,
 input wire read_v,input wire [LB-1:0] read_bank,input wire [5:0] read_row,
 output wire [255:0] read_data
);
endmodule

// Unselected default alternative: must vanish from selected native configuration.
(* blackbox *) module ot_hbm_svc_sm8_landing_boundary #(
 parameter [2:0] BANK=0, parameter integer RESPONSE_DEPTH=8,LBANKS=4,FMUT=0,
 parameter integer BMUT=0,LB=(LBANKS>2)?2:1,IW=283+LB
)(
 input wire hbm_clk,hbm_rst_n,stream_clk,stream_rst_n,
 input wire in_v,output reg in_ready,input wire [IW-1:0] in_data,output reg overflow,
 input wire reserve_v,input wire [LB-1:0] reserve_bank,input wire [15:0] reserve_epoch,
 input wire [11:0] reserve_total,input wire stop,
 output reg complete_v,output reg [LB-1:0] complete_bank,output reg fault,
 input wire read_v,input wire [LB-1:0] read_bank,input wire [5:0] read_row,
 output reg [255:0] read_data
);
endmodule

// Unselected default alternative: must vanish from selected native configuration.
(* blackbox *) module ot_hbm_svc_static_sm_packed136_native8 #(parameter integer PACKED136=0, MUT=0)(
 input wire clk,rst_n,
 input wire open_v,open_bank,input wire [15:0] open_epoch,input wire [6:0] open_count,input wire [9:0] open_tag_base,
 input wire [3:0] sector_v,input wire [95:0] sector_index,input wire [63:0] sector_epoch,input wire [1023:0] sector_data,
 input wire read_v,read_bank,input wire [15:0] read_epoch,input wire [5:0] read_row,input wire [9:0] read_tag,
 input wire retire_v,retire_bank,input wire [15:0] retire_epoch,
 output wire [1:0] block_ready,bank_owned,output wire busy,fault,output wire [1098:0] out_packet
);
endmodule
`default_nettype wire
