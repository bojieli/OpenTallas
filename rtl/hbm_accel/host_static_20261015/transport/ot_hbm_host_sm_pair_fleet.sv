`timescale 1ns/1ps
`default_nettype none
// Initialization-only AXI host adapter joined to 32 actual native pair calendars.
// Native pair dependency: d3ef99f50; 64 actual1024x256 programme SRAMs.
module ot_hbm_host_sm_pair_fleet #(parameter integer MUT=0)(
 input wire clk,rst_n,
 input wire[11:0]s_awaddr,input wire s_awvalid,output wire s_awready,
 input wire[31:0]s_wdata,input wire[3:0]s_wstrb,input wire s_wvalid,output wire s_wready,
 output wire[1:0]s_bresp,output wire s_bvalid,input wire s_bready,
 input wire[11:0]s_araddr,input wire s_arvalid,output wire s_arready,
 output wire[31:0]s_rdata,output wire[1:0]s_rresp,output wire s_rvalid,input wire s_rready,
 output wire cfg_begin_v,cfg_commit_v,cfg_we,
 output wire[7:0]cfg_target,output wire[15:0]cfg_epoch,
 output wire[10:0]cfg_addr,output wire[255:0]cfg_data,
 output wire launch_v,output wire[15:0]launch_epoch,
 output wire[9:0]start_base,output wire[10:0]start_limit,
 output wire[15:0]start_loops,output wire fault,
 output wire[31:0][290:0]calendar,output wire[31:0]calendar_v,
 output wire[31:0][31:0]ordinal,output wire[31:0]done,
 output wire[31:0]target_ready,target_active,target_fault,
 output wire[31:0][15:0]target_ready_epoch
);
 wire cfg_ack_v;wire[1:0]cfg_ack_kind,cfg_ack_resp;wire[7:0]cfg_ack_target;wire[10:0]cfg_ack_addr;wire[15:0]cfg_ack_epoch;
 ot_hbm_host_sm_pair_install #(.MUT(MUT)) host(
 .clk(clk),
 .rst_n(rst_n),
 .s_awaddr(s_awaddr),
 .s_awvalid(s_awvalid),
 .s_awready(s_awready),
 .s_wdata(s_wdata),
 .s_wstrb(s_wstrb),
 .s_wvalid(s_wvalid),
 .s_wready(s_wready),
 .s_bresp(s_bresp),
 .s_bvalid(s_bvalid),
 .s_bready(s_bready),
 .s_araddr(s_araddr),
 .s_arvalid(s_arvalid),
 .s_arready(s_arready),
 .s_rdata(s_rdata),
 .s_rresp(s_rresp),
 .s_rvalid(s_rvalid),
 .s_rready(s_rready),
 .cfg_begin_v(cfg_begin_v),
 .cfg_commit_v(cfg_commit_v),
 .cfg_we(cfg_we),
 .cfg_target(cfg_target),
 .cfg_epoch(cfg_epoch),
 .cfg_addr(cfg_addr),
 .cfg_data(cfg_data),
 .cfg_ack_v(cfg_ack_v),
 .cfg_ack_kind(cfg_ack_kind),
 .cfg_ack_target(cfg_ack_target),
 .cfg_ack_addr(cfg_ack_addr),
 .cfg_ack_epoch(cfg_ack_epoch),
 .cfg_ack_resp(cfg_ack_resp),
 .target_ready(target_ready),
 .target_active(target_active),
 .target_fault(target_fault),
 .target_ready_epoch(target_ready_epoch),
 .launch_v(launch_v),
 .launch_epoch(launch_epoch),
 .start_base(start_base),
 .start_limit(start_limit),
 .start_loops(start_loops),
 .fault(fault));
 wire[31:0]av;wire[31:0][1:0]ak,ar;wire[31:0][7:0]at;wire[31:0][10:0]aa;wire[31:0][15:0]ae;
 for(genvar n=0;n<32;n++)begin:g_sm
 ot_smh_calendar_pair_static #(.W(291),.TARGET(128+n)) programme(
 .clk(clk),.rst_n(rst_n),.cfg_begin_v(cfg_begin_v&&cfg_target==128+n),
 .cfg_commit_v(cfg_commit_v&&cfg_target==128+n),.cfg_we(cfg_we&&cfg_target==128+n),
 .cfg_epoch(cfg_epoch),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .cfg_ack_v(av[n]),.cfg_ack_kind(ak[n]),.cfg_ack_target(at[n]),.cfg_ack_addr(aa[n]),.cfg_ack_epoch(ae[n]),.cfg_ack_resp(ar[n]),
 .ready(target_ready[n]),.ready_epoch(target_ready_epoch[n]),
 .start_v(launch_v),.start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),.start_epoch(launch_epoch),
 .calendar(calendar[n]),.calendar_v(calendar_v[n]),.ordinal(ordinal[n]),.active(target_active[n]),.done(done[n]),.fault(target_fault[n]));
 end
 assign cfg_ack_v=|av;
 reg[1:0]ack_kind,ack_resp;reg[7:0]ack_target;reg[10:0]ack_addr;reg[15:0]ack_epoch;
 always @*begin
 ack_kind=0;ack_resp=0;ack_target=0;ack_addr=0;ack_epoch=0;
 for(integer n=0;n<32;n++)if(av[n])begin
 ack_kind=ack_kind|ak[n];ack_resp=ack_resp|ar[n];ack_target=ack_target|at[n];ack_addr=ack_addr|aa[n];ack_epoch=ack_epoch|ae[n];
 end
 // A single host request is outstanding. Collision returns an explicit bad tag.
 if((av&(av-1'b1))!=0)begin ack_kind=3;ack_resp=2;end
 end
 assign cfg_ack_kind=ack_kind;assign cfg_ack_resp=ack_resp;assign cfg_ack_target=ack_target;assign cfg_ack_addr=ack_addr;assign cfg_ack_epoch=ack_epoch;
endmodule
`default_nettype wire
