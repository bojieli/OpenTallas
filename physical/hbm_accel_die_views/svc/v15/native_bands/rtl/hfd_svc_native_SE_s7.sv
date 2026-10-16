`default_nettype none
// Native logical bank id is ordinal%32, not the DRAM PC hash.
// Separate real clock/reset ports remain visible for every actual leaf.
module hfd_svc_native_SE_s7 (
 input wire [1:0] owner_clk,
 input wire [1:0] owner_rst_n,
 input wire [1:0] owner_descriptor_v,
 input wire [59:0] owner_descriptor_base,
 input wire [23:0] owner_descriptor_total,
 input wire [1:0] owner_descriptor_bank,
 input wire [31:0] owner_descriptor_epoch,
 input wire [1:0] owner_block_active,
 input wire [59:0] owner_block_base,
 input wire [23:0] owner_block_total,
 input wire [1:0] owner_block_bank,
 input wire [31:0] owner_block_epoch,
 input wire [1:0] owner_stop,
 input wire [1:0] owner_k_ready,
 input wire [1:0] owner_kr_v,
 input wire [33:0] owner_kr_tag,
 input wire [7:0] owner_kr_beat,
 input wire [1:0] owner_response_take,
 output wire [1:0] owner_k_v,
 output wire [59:0] owner_k_addr,
 output wire [7:0] owner_k_len,
 output wire [33:0] owner_k_tag,
 output wire [1:0] owner_response_ok,
 output wire [21:0] owner_response_ordinal,
 output wire [31:0] owner_response_epoch,
 output wire [1:0] owner_response_bank,
 output wire [1:0] owner_fault,
 input wire [1:0] bank_hbm_clk,
 input wire [1:0] bank_hbm_rst_n,
 input wire [1:0] bank_stream_clk,
 input wire [1:0] bank_stream_rst_n,
 input wire [1:0] bank_in_v,
 output wire [1:0] bank_in_ready,
 input wire [567:0] bank_in_data,
 output wire [1:0] bank_overflow,
 input wire [1:0] bank_reserve_v,
 input wire [1:0] bank_reserve_bank,
 input wire [31:0] bank_reserve_epoch,
 input wire [23:0] bank_reserve_total,
 input wire [1:0] bank_stop,
 output wire [1:0] bank_complete_v,
 output wire [1:0] bank_complete_bank,
 output wire [1:0] bank_fault,
 input wire [1:0] bank_read_v,
 input wire [1:0] bank_read_bank,
 input wire [11:0] bank_read_row,
 output wire [511:0] bank_read_data
);
 ot_hbm_svc_prefetch_burst_owner #(.PC(5'd29),.OWNER_AW(5)) u_owner29 (.clk(owner_clk[0+:1]),.rst_n(owner_rst_n[0+:1]),.descriptor_v(owner_descriptor_v[0+:1]),.descriptor_base(owner_descriptor_base[0+:30]),.descriptor_total(owner_descriptor_total[0+:12]),.descriptor_bank(owner_descriptor_bank[0+:1]),.descriptor_epoch(owner_descriptor_epoch[0+:16]),.block_active(owner_block_active[0+:1]),.block_base(owner_block_base[0+:30]),.block_total(owner_block_total[0+:12]),.block_bank(owner_block_bank[0+:1]),.block_epoch(owner_block_epoch[0+:16]),.stop(owner_stop[0+:1]),.k_ready(owner_k_ready[0+:1]),.kr_v(owner_kr_v[0+:1]),.kr_tag(owner_kr_tag[0+:17]),.kr_beat(owner_kr_beat[0+:4]),.response_take(owner_response_take[0+:1]),.k_v(owner_k_v[0+:1]),.k_addr(owner_k_addr[0+:30]),.k_len(owner_k_len[0+:4]),.k_tag(owner_k_tag[0+:17]),.response_ok(owner_response_ok[0+:1]),.response_ordinal(owner_response_ordinal[0+:11]),.response_epoch(owner_response_epoch[0+:16]),.response_bank(owner_response_bank[0+:1]),.fault(owner_fault[0+:1]));
 ot_hbm_svc_prefetch_burst_bank #(.BANK(5'd29),.RESPONSE_DEPTH(8)) u_bank29 (.hbm_clk(bank_hbm_clk[0+:1]),.hbm_rst_n(bank_hbm_rst_n[0+:1]),.stream_clk(bank_stream_clk[0+:1]),.stream_rst_n(bank_stream_rst_n[0+:1]),.in_v(bank_in_v[0+:1]),.in_ready(bank_in_ready[0+:1]),.in_data(bank_in_data[0+:284]),.overflow(bank_overflow[0+:1]),.reserve_v(bank_reserve_v[0+:1]),.reserve_bank(bank_reserve_bank[0+:1]),.reserve_epoch(bank_reserve_epoch[0+:16]),.reserve_total(bank_reserve_total[0+:12]),.stop(bank_stop[0+:1]),.complete_v(bank_complete_v[0+:1]),.complete_bank(bank_complete_bank[0+:1]),.fault(bank_fault[0+:1]),.read_v(bank_read_v[0+:1]),.read_bank(bank_read_bank[0+:1]),.read_row(bank_read_row[0+:6]),.read_data(bank_read_data[0+:256]));
 ot_hbm_svc_prefetch_burst_owner #(.PC(5'd30),.OWNER_AW(5)) u_owner30 (.clk(owner_clk[1+:1]),.rst_n(owner_rst_n[1+:1]),.descriptor_v(owner_descriptor_v[1+:1]),.descriptor_base(owner_descriptor_base[30+:30]),.descriptor_total(owner_descriptor_total[12+:12]),.descriptor_bank(owner_descriptor_bank[1+:1]),.descriptor_epoch(owner_descriptor_epoch[16+:16]),.block_active(owner_block_active[1+:1]),.block_base(owner_block_base[30+:30]),.block_total(owner_block_total[12+:12]),.block_bank(owner_block_bank[1+:1]),.block_epoch(owner_block_epoch[16+:16]),.stop(owner_stop[1+:1]),.k_ready(owner_k_ready[1+:1]),.kr_v(owner_kr_v[1+:1]),.kr_tag(owner_kr_tag[17+:17]),.kr_beat(owner_kr_beat[4+:4]),.response_take(owner_response_take[1+:1]),.k_v(owner_k_v[1+:1]),.k_addr(owner_k_addr[30+:30]),.k_len(owner_k_len[4+:4]),.k_tag(owner_k_tag[17+:17]),.response_ok(owner_response_ok[1+:1]),.response_ordinal(owner_response_ordinal[11+:11]),.response_epoch(owner_response_epoch[16+:16]),.response_bank(owner_response_bank[1+:1]),.fault(owner_fault[1+:1]));
 ot_hbm_svc_prefetch_burst_bank #(.BANK(5'd30),.RESPONSE_DEPTH(8)) u_bank30 (.hbm_clk(bank_hbm_clk[1+:1]),.hbm_rst_n(bank_hbm_rst_n[1+:1]),.stream_clk(bank_stream_clk[1+:1]),.stream_rst_n(bank_stream_rst_n[1+:1]),.in_v(bank_in_v[1+:1]),.in_ready(bank_in_ready[1+:1]),.in_data(bank_in_data[284+:284]),.overflow(bank_overflow[1+:1]),.reserve_v(bank_reserve_v[1+:1]),.reserve_bank(bank_reserve_bank[1+:1]),.reserve_epoch(bank_reserve_epoch[16+:16]),.reserve_total(bank_reserve_total[12+:12]),.stop(bank_stop[1+:1]),.complete_v(bank_complete_v[1+:1]),.complete_bank(bank_complete_bank[1+:1]),.fault(bank_fault[1+:1]),.read_v(bank_read_v[1+:1]),.read_bank(bank_read_bank[1+:1]),.read_row(bank_read_row[6+:6]),.read_data(bank_read_data[256+:256]));
endmodule
`default_nettype wire
