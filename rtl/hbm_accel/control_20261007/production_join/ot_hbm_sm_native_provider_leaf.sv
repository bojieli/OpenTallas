// Candidate: real full-shape native SMH. No external peer is fabricated.
// North owner and south descriptor adapter have separate modeled bays.
module ot_hbm_sm_native_provider_leaf #(parameter ENABLE=0,PROTECT=0,MAX_RECORDS=256,DESC_HOPS=32)(
 input wire peer_fault,
 output wire native_arrive,native_compute_fault,
 input wire  clk,
 input wire  rst_n,
 input wire  run_valid,
 output wire  run_ready,
 input wire [31:0] program_base,
 input wire [32:0] program_limit,
 input wire [15:0] record_count,
 output wire  mem_req_valid,
 input wire  mem_req_ready,
 output wire [31:0] mem_req_addr,
 input wire  mem_rsp_valid,
 output wire  mem_rsp_ready,
 input wire [31:0] mem_rsp_addr,
 input wire [31:0] mem_rsp_data,
 input wire  mem_rsp_error,
 output wire  alloc_valid,
 input wire  alloc_ready,
 output wire [15:0] alloc_record,
 output wire [23:0] alloc_lines,
 input wire  alloc_rsp_valid,
 output wire  alloc_rsp_ready,
 input wire [15:0] alloc_rsp_record,
 input wire [31:0] alloc_rsp_base,
 input wire  alloc_rsp_error,
 output wire  x_req_valid,
 input wire  x_req_ready,
 output wire [15:0] x_req_record,
 output wire [6:0] x_req_base,
 output wire [7:0] x_req_extent,
 input wire  x_valid,
 output wire  x_ready,
 input wire [15:0] x_record,
 input wire [6:0] x_ordinal,
 input wire [3:0] x_group,
 input wire [2047:0] x_data,
 input wire  x_error,
 input wire  publication_valid,
 output wire  publication_ready,
 input wire [15:0] publication_record,
 output wire  done,
 input wire  done_ready,
 output wire  fault,
 output wire  req_v,
 input wire  req_ready,
 output wire [31:0] req_addr,
 output wire [9:0] req_tag,
 input wire  rsp_v,
 input wire [9:0] rsp_tag,
 input wire [1087:0] rsp_data,
 output wire  rv,
 output wire [11:0] rrow,
 output wire [255:0] rdata,
 input wire  release_in,
 output wire  released,
 output wire  busy
 );
 wire  xw_en;
 wire [6:0] xw_addr;
 wire [6:0] xw_grp;
 wire [2047:0] xw_data;
 wire  d_valid;
 wire  d_ready;
 wire [31:0] d_base;
 wire [23:0] d_lines;
 wire  start;
 wire  start_ready;
 wire [12:0] op_rows;
 wire [15:0] op_c;
 wire [7:0] op_g;
 wire  op_gs;
 wire [1:0] op_fmt;
 wire [6:0] op_xb;
 wire  arrive;
 wire  sm_fault;
 wire owner_fault,south_fault,bridge_fault;
 wire south_d_valid,south_d_ready;
 wire[31:0]south_d_base;wire[23:0]south_d_lines;
 wire sm_rst_n=rst_n && ENABLE;
 assign native_arrive=arrive;
 assign native_compute_fault=sm_fault;
 assign fault=owner_fault || sm_fault || peer_fault;
 ot_hbm_sm_serial_protected #(.ENABLE(ENABLE),.PROTECT(PROTECT),.MAX_RECORDS(MAX_RECORDS)) owner(
 .clk(clk),
 .rst_n(rst_n),
 .run_valid(run_valid),
 .run_ready(run_ready),
 .program_base(program_base),
 .program_limit(program_limit),
 .record_count(record_count),
 .mem_req_valid(mem_req_valid),
 .mem_req_ready(mem_req_ready),
 .mem_req_addr(mem_req_addr),
 .mem_rsp_valid(mem_rsp_valid),
 .mem_rsp_ready(mem_rsp_ready),
 .mem_rsp_addr(mem_rsp_addr),
 .mem_rsp_data(mem_rsp_data),
 .mem_rsp_error(mem_rsp_error),
 .alloc_valid(alloc_valid),
 .alloc_ready(alloc_ready),
 .alloc_record(alloc_record),
 .alloc_lines(alloc_lines),
 .alloc_rsp_valid(alloc_rsp_valid),
 .alloc_rsp_ready(alloc_rsp_ready),
 .alloc_rsp_record(alloc_rsp_record),
 .alloc_rsp_base(alloc_rsp_base),
 .alloc_rsp_error(alloc_rsp_error),
 .x_req_valid(x_req_valid),
 .x_req_ready(x_req_ready),
 .x_req_record(x_req_record),
 .x_req_base(x_req_base),
 .x_req_extent(x_req_extent),
 .x_valid(x_valid),
 .x_ready(x_ready),
 .x_record(x_record),
 .x_ordinal(x_ordinal),
 .x_group(x_group),
 .x_data(x_data),
 .x_error(x_error),
 .xw_en(xw_en),
 .xw_addr(xw_addr),
 .xw_grp(xw_grp),
 .xw_data(xw_data),
 .d_valid(d_valid),
 .d_ready(d_ready),
 .d_base(d_base),
 .d_lines(d_lines),
 .start(start),
 .start_ready(start_ready),
 .op_rows(op_rows),
 .op_c(op_c),
 .op_g(op_g),
 .op_gs(op_gs),
 .op_fmt(op_fmt),
 .op_xb(op_xb),
 .arrive(arrive),
 .sm_fault(sm_fault || peer_fault),
 .publication_valid(publication_valid),
 .publication_ready(publication_ready),
 .publication_record(publication_record),
 .done(done),
 .done_ready(done_ready),
 .fault(owner_fault)
 );
 ot_hbm_sm_descriptor_bridge #(.ENABLE(ENABLE),.HOPS(DESC_HOPS),.DEPTH(2)) descriptor(
 .clk(clk),.rst_n(rst_n),.s_valid(d_valid),.s_ready(d_ready),.s_base(d_base),.s_lines(d_lines),
 .d_valid(south_d_valid),.d_ready(south_d_ready),.d_base(south_d_base),.d_lines(south_d_lines),
 .south_fault(south_fault),.north_fault(sm_fault),.fault(bridge_fault));
 ot_hbm_accel_smh sm(
 .clk(clk),
 .rst_n(sm_rst_n),
 .start(start),
 .start_ready(start_ready),
 .op_rows(op_rows),
 .op_c(op_c),
 .op_g(op_g),
 .op_gs(op_gs),
 .op_fmt(op_fmt),
 .op_xb(op_xb),
 .busy(busy),
 .d_valid(south_d_valid),
 .d_ready(south_d_ready),
 .d_base(south_d_base),
 .d_lines(south_d_lines),
 .req_v(req_v),
 .req_ready(req_ready),
 .req_addr(req_addr),
 .req_tag(req_tag),
 .rsp_v(rsp_v),
 .rsp_tag(rsp_tag),
 .rsp_data(rsp_data),
 .xw_en(xw_en),
 .xw_addr(xw_addr),
 .xw_grp(xw_grp),
 .xw_data(xw_data),
 .rv(rv),
 .rrow(rrow),
 .rdata(rdata),
 .fault(south_fault),
 .arrive(arrive),
 .release_in(release_in),
 .released(released)
 );
endmodule
