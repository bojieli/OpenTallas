module ot_hnx_fused_host_program #(parameter [7:0] TARGET=0,parameter integer DELIVERED_RESET=1)(
 input wire clk,rst_n,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,
 output wire ready,active,done,fault,
 output wire job_v,output wire [216:0] job,output wire [7:0] wsc,output wire [5:0] pk5,output wire pb5,
 input wire root_done,root_fault,root_busy
);
 wire load_v,commit,bound,start,armed,pfault,bfault;wire[7:0]addr,cwsc;wire[280:0]entry;wire[8:0]count;wire[5:0]cpk;wire cpb;
 ot_hnx_fused_host_boot #(.TARGET(TARGET)) boot(.clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),.load_v(load_v),.load_addr(addr),.load_entry(entry),.cfg_commit(commit),.cfg_calendar_bound(bound),.cfg_count(count),.cfg_wsc(cwsc),.cfg_pk5(cpk),.cfg_pb5(cpb),.start(start),.provider_armed(armed),.provider_busy(active),.provider_done(done),.provider_fault(pfault),.ready(ready),.active(),.fault(bfault));
 ot_hnx_fused_job217_provider #(.DELIVERED_RESET(DELIVERED_RESET)) provider(.clk(clk),.rst_n(rst_n),.load_v(load_v),.load_addr(addr),.load_entry(entry),.cfg_commit(commit),.cfg_calendar_bound(bound),.cfg_count(count),.cfg_wsc(cwsc),.cfg_pk5(cpk),.cfg_pb5(cpb),.start(start),.job_v(job_v),.job(job),.wsc(wsc),.pk5(pk5),.pb5(pb5),.root_done(root_done),.root_fault(root_fault),.root_busy(root_busy),.done(done),.fault(pfault),.busy(active),.armed(armed));
 assign fault=bfault|pfault;
endmodule
