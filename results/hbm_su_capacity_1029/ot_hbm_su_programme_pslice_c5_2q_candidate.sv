// Explicit candidate profile only; requires new physical qualification. Original master unchanged.
module ot_hbm_su_programme_pslice_c5_2q_candidate (
 input logic clk,rst_n,cfg_we,input logic [15:0] cfg_bank,input logic [6:0] cfg_row,
 input logic [255:0] cfg_data,input logic start,input logic [15:0] length,
 output logic busy,valid,done,fault,output logic [15:0] edge_index,output logic [2469:0] command);
 ot_hbm_su_programme_pslice_c5 #(.SB(2470),.NC(10),.DICT_CAP({32'd1,32'd1,32'd1,32'd1,32'd1,32'd3,32'd3,32'd5,32'd9,32'd5})) u_c5 (.*);
endmodule
