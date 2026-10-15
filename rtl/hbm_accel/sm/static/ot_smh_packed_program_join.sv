`timescale 1ns/1ps
// Two real programme SRAMs drive the SMcommand and packedcache readplane.
// Readprogramme launches oneedge earlier than commandprogramme, compiled
// explicitly. Missingdata faults; no readiness signal changes execution.
module ot_smh_packed_program_join(
 input wire clk,rst_n,
 input wire command_cfg_we,read_cfg_we,input wire [9:0] cfg_addr,
 input wire [255:0] command_cfg_data,read_cfg_data,
 input wire command_start_v,read_start_v,input wire [9:0] start_base,
 input wire [10:0] start_limit,input wire [15:0] start_loops,
 input wire open_v,open_bank,input wire [15:0] open_epoch,
 input wire [6:0] open_count,input wire [9:0] open_tag_base,
 input wire [3:0] sector_v,input wire [95:0] sector_index,
 input wire [63:0] sector_epoch,input wire [1023:0] sector_data,
 input wire retire_v,retire_bank,input wire [15:0] retire_epoch,
 output wire [1:0] block_ready,bank_owned,
 output wire [82:0] command,output wire [1098:0] packet,
 output wire command_v,read_calendar_v,command_done,read_done,
 output wire [31:0] command_ordinal,read_ordinal,
 output wire [1081:0] lt0,lt1,output wire [569:0] lb0,lb1,
 output wire [11:0] fm,output wire [42:0] expected_request,
 output wire programme_fault,service_fault,feed_fault
);
 wire [33:0] read_calendar;
 wire command_fault,read_fault,command_active,read_active,busy;
 ot_smh_calendar_static #(.W(83)) u_command(
 .clk(clk),.rst_n(rst_n),.cfg_we(command_cfg_we),.cfg_addr(cfg_addr),.cfg_data(command_cfg_data),
 .start_v(command_start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
 .calendar(command),.calendar_v(command_v),.ordinal(command_ordinal),.active(command_active),.done(command_done),.fault(command_fault));
 ot_smh_calendar_static #(.W(34)) u_read(
 .clk(clk),.rst_n(rst_n),.cfg_we(read_cfg_we),.cfg_addr(cfg_addr),.cfg_data(read_cfg_data),
 .start_v(read_start_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
 .calendar(read_calendar),.calendar_v(read_calendar_v),.ordinal(read_ordinal),.active(read_active),.done(read_done),.fault(read_fault));
 ot_hbm_svc_static_sm_packed136 #(.PACKED136(1)) u_cache(
 .clk(clk),.rst_n(rst_n),.open_v(open_v),.open_bank(open_bank),.open_epoch(open_epoch),.open_count(open_count),.open_tag_base(open_tag_base),
 .sector_v(sector_v),.sector_index(sector_index),.sector_epoch(sector_epoch),.sector_data(sector_data),
 .read_v(read_calendar_v&&read_calendar[33]),.read_bank(read_calendar[32]),.read_epoch(read_calendar[31:16]),.read_row(read_calendar[15:10]),.read_tag(read_calendar[9:0]),
 .retire_v(retire_v),.retire_bank(retire_bank),.retire_epoch(retire_epoch),.block_ready(block_ready),.bank_owned(bank_owned),.busy(busy),.fault(service_fault),.out_packet(packet));
 ot_smh_static_feed u_feed(.clk(clk),.rst_n(rst_n),.command(command_v?command:83'd0),.packet(packet),
 .expected_request(expected_request),.fault(feed_fault),.lt0(lt0),.lt1(lt1),.lb0(lb0),.lb1(lb1),.fm(fm));
 assign programme_fault=command_fault|read_fault;
endmodule
