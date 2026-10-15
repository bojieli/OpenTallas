`default_nettype none
// Structural successor, not a replacement identity for the CLOSED PC leaf.
// Compiler pulses enter through one physical FF stage; out_v/out_data leave
// through one physical FF stage. Scheduled read latency is three sampling
// edges (old leaf one): +2 cycles. No ready or retry on compiler ports.
// Request and KR one-entry queues are exclusively at the HBM PHY boundary.
// The core observes request acceptance when queued; external service occurs
// only on k_v && k_rdy. Parent calendars must price that transport explicitly.
// A KR beat takes one extra edge to reach the core; done/status take another.
// Clock spread and all timing remain unqualified until a new native route.
module ot_hbm_svc_static_pc_boundary (
 input wire clk,core_clk,rst_n,
 input wire open_v,open_bank,input wire [15:0] open_epoch,input wire [6:0] open_count,
 input wire fill_v,fill_bank,input wire [15:0] fill_epoch,input wire [5:0] fill_slot,
 input wire [255:0] fill_data,
 input wire read_v,read_bank,input wire [15:0] read_epoch,input wire [5:0] read_slot,
 output reg out_v,output reg [255:0] out_data,
 input wire retire_v,retire_bank,input wire [15:0] retire_epoch,
 // cmd_write=0 prefetches into an empty open bank. cmd_write=1 writes a
 // complete staged bank and retires it only after every real k_wr_done.
 input wire cmd_v,cmd_write,cmd_bank,input wire [15:0] cmd_epoch,
 input wire [29:0] cmd_addr,cmd_step,
 output reg [1:0] block_ready,output reg [1:0] bank_owned,output reg busy,output reg done,output reg fault,
 output reg k_v,input wire k_rdy,output reg [29:0] k_addr,
 output reg [3:0] k_len,output reg [16:0] k_tag,output reg k_we,
 output reg [255:0] k_wdata,output reg [31:0] k_wstrb,input wire k_wr_done,
 input wire kr_v,output reg kr_rdy,input wire [16:0] kr_tag,
 input wire [3:0] kr_beat,input wire [255:0] kr_data
);
 reg open_v_q;
 reg open_bank_q;
 reg [15:0] open_epoch_q;
 reg [6:0] open_count_q;
 reg fill_v_q;
 reg fill_bank_q;
 reg [15:0] fill_epoch_q;
 reg [5:0] fill_slot_q;
 reg [255:0] fill_data_q;
 reg read_v_q;
 reg read_bank_q;
 reg [15:0] read_epoch_q;
 reg [5:0] read_slot_q;
 reg retire_v_q;
 reg retire_bank_q;
 reg [15:0] retire_epoch_q;
 reg cmd_v_q;
 reg cmd_write_q;
 reg cmd_bank_q;
 reg [15:0] cmd_epoch_q;
 reg [29:0] cmd_addr_q;
 reg [29:0] cmd_step_q;
 wire c_out_v;
 wire [255:0] c_out_data;
 wire [1:0] c_block_ready;
 wire [1:0] c_bank_owned;
 wire c_busy;
 wire c_done;
 wire c_fault;
 wire [29:0] c_k_addr;
 wire [3:0] c_k_len;
 wire [16:0] c_k_tag;
 wire c_k_we;
 wire [255:0] c_k_wdata;
 wire [31:0] c_k_wstrb;
 reg [16:0] kr_tag_q;
 reg [3:0] kr_beat_q;
 reg [255:0] kr_data_q;
 reg kr_valid_q,ack_q;
 // A queued request is not an external transaction. ACK/data are legal only
 // after actual PHY acceptance, including a zero-wait same-edge response.
 reg read_outstanding,write_outstanding,protocol_fault;
 wire accept_read = k_v && k_rdy && !k_we;
 wire accept_write = k_v && k_rdy && k_we;
 wire read_response_ok = read_outstanding || accept_read;
 wire write_response_ok = write_outstanding || accept_write;
 wire c_k_v,c_kr_rdy;
 wire c_k_rdy = !k_v;
 always @* kr_rdy = !kr_valid_q && !fault;
 always @(posedge clk or negedge rst_n) begin
  if (!rst_n) begin
   open_v_q <= 0;
   open_bank_q <= 0;
   open_epoch_q <= 0;
   open_count_q <= 0;
   fill_v_q <= 0;
   fill_bank_q <= 0;
   fill_epoch_q <= 0;
   fill_slot_q <= 0;
   fill_data_q <= 0;
   read_v_q <= 0;
   read_bank_q <= 0;
   read_epoch_q <= 0;
   read_slot_q <= 0;
   retire_v_q <= 0;
   retire_bank_q <= 0;
   retire_epoch_q <= 0;
   cmd_v_q <= 0;
   cmd_write_q <= 0;
   cmd_bank_q <= 0;
   cmd_epoch_q <= 0;
   cmd_addr_q <= 0;
   cmd_step_q <= 0;
   out_v <= 0;
   out_data <= 0;
   block_ready <= 0;
   bank_owned <= 0;
   busy <= 0;
   done <= 0;
   fault <= 0;
   k_addr <= 0;
   k_len <= 0;
   k_tag <= 0;
   k_we <= 0;
   k_wdata <= 0;
   k_wstrb <= 0;
   kr_tag_q <= 0;
   kr_beat_q <= 0;
   kr_data_q <= 0;
   k_v <= 0; kr_valid_q <= 0; ack_q <= 0;
   read_outstanding <= 0; write_outstanding <= 0; protocol_fault <= 0;
  end else begin
   open_v_q <= open_v;
   open_bank_q <= open_bank;
   open_epoch_q <= open_epoch;
   open_count_q <= open_count;
   fill_v_q <= fill_v;
   fill_bank_q <= fill_bank;
   fill_epoch_q <= fill_epoch;
   fill_slot_q <= fill_slot;
   fill_data_q <= fill_data;
   read_v_q <= read_v;
   read_bank_q <= read_bank;
   read_epoch_q <= read_epoch;
   read_slot_q <= read_slot;
   retire_v_q <= retire_v;
   retire_bank_q <= retire_bank;
   retire_epoch_q <= retire_epoch;
   cmd_v_q <= cmd_v;
   cmd_write_q <= cmd_write;
   cmd_bank_q <= cmd_bank;
   cmd_epoch_q <= cmd_epoch;
   cmd_addr_q <= cmd_addr;
   cmd_step_q <= cmd_step;
   out_v <= c_out_v;
   out_data <= c_out_data;
   block_ready <= c_block_ready;
   bank_owned <= c_bank_owned;
   busy <= c_busy;
   done <= c_done;
   fault <= c_fault || protocol_fault;
   ack_q <= k_wr_done && write_response_ok;
   if (accept_read) read_outstanding <= 1;
   if (accept_write) write_outstanding <= 1;
   if (kr_v && kr_rdy) begin
    if (!read_response_ok) protocol_fault <= 1;
    else read_outstanding <= 0;
   end
   if (k_wr_done) begin
    if (!write_response_ok) protocol_fault <= 1;
    else write_outstanding <= 0;
   end
   if (k_v && k_rdy) k_v <= 0;
   if (c_k_v && c_k_rdy) begin
    k_v <= 1;
    k_addr <= c_k_addr;
    k_len <= c_k_len;
    k_tag <= c_k_tag;
    k_we <= c_k_we;
    k_wdata <= c_k_wdata;
    k_wstrb <= c_k_wstrb;
   end
   if (kr_valid_q && c_kr_rdy) kr_valid_q <= 0;
   if (kr_v && kr_rdy && read_response_ok) begin
    kr_valid_q <= 1;
    kr_tag_q <= kr_tag;
    kr_beat_q <= kr_beat;
    kr_data_q <= kr_data;
   end
   if (c_fault || protocol_fault) k_v <= 0;
  end
 end
 ot_hbm_svc_static_pc u_core (
 .clk(core_clk), .rst_n(rst_n),
 .open_v(open_v_q),
 .open_bank(open_bank_q),
 .open_epoch(open_epoch_q),
 .open_count(open_count_q),
 .fill_v(fill_v_q),
 .fill_bank(fill_bank_q),
 .fill_epoch(fill_epoch_q),
 .fill_slot(fill_slot_q),
 .fill_data(fill_data_q),
 .read_v(read_v_q),
 .read_bank(read_bank_q),
 .read_epoch(read_epoch_q),
 .read_slot(read_slot_q),
 .retire_v(retire_v_q),
 .retire_bank(retire_bank_q),
 .retire_epoch(retire_epoch_q),
 .cmd_v(cmd_v_q),
 .cmd_write(cmd_write_q),
 .cmd_bank(cmd_bank_q),
 .cmd_epoch(cmd_epoch_q),
 .cmd_addr(cmd_addr_q),
 .cmd_step(cmd_step_q),
 .out_v(c_out_v),
 .out_data(c_out_data),
 .block_ready(c_block_ready),
 .bank_owned(c_bank_owned),
 .busy(c_busy),
 .done(c_done),
 .fault(c_fault),
 .k_addr(c_k_addr),
 .k_len(c_k_len),
 .k_tag(c_k_tag),
 .k_we(c_k_we),
 .k_wdata(c_k_wdata),
 .k_wstrb(c_k_wstrb),
 .k_v(c_k_v),
 .k_rdy(c_k_rdy),
 .k_wr_done(ack_q),
 .kr_v(kr_valid_q),
 .kr_rdy(c_kr_rdy),
 .kr_tag(kr_tag_q),
 .kr_beat(kr_beat_q),
 .kr_data(kr_data_q)
 );
endmodule
`default_nettype wire
