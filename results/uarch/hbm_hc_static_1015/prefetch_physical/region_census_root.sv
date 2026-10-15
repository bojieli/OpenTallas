`default_nettype none
module hc_prefetch_region_census_root(
 input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,
 input wire reserve_v,output wire reserve_ready,input wire [31:0] reserve_base,
 input wire [11:0] reserve_total,input wire [2:0] reserve_bank,input wire [15:0] reserve_epoch,
 output wire [7:0] block_ready,output wire block_ready_v,output wire [2:0] block_ready_bank,
 output wire [15:0] block_ready_epoch,
 input wire start_v,input wire [2:0] start_bank,input wire [15:0] start_epoch,
 output wire out_v,output wire [7:0] out_mask,output wire [2047:0] out_data,
 output wire [10:0] out_ordinal,output wire [2:0] out_bank,output wire [15:0] out_epoch,
 output wire out_last,output wire fault,
 output wire [31:0] k_v,input wire [31:0] k_rdy,output wire [959:0] k_addr,
 output wire [127:0] k_len,output wire [543:0] k_tag,output wire [31:0] k_we,
 output wire [8191:0] k_wdata,output wire [1023:0] k_wstrb,input wire [31:0] k_wr_done,
 input wire [31:0] kr_v,output wire [31:0] kr_rdy,input wire [543:0] kr_tag,
 input wire [127:0] kr_beat,input wire [8191:0] kr_data
);
 ot_hbm_svc_prefetch_region_cdc #(.STACK(0),.DELIVERY_II(8),.ISSUE_INTERLEAVE(1),.MAX_OUTSTANDING(8),.ISSUE_WIDTH(4)) u_actual(.*);
endmodule
`default_nettype wire
