`timescale 1ns/1ps
`default_nettype none
// Real native target49 -> mapped outer programme -> actual mapped event/query
// producer. Host transport is external configuration only; no on-chip ready.
module ot_hbm_attn_physical_host_program_front(
 input wire clk,rst_n,input wire cfg_v,input wire[7:0]cfg_target,
 input wire[11:0]cfg_addr,input wire[255:0]cfg_data,
 input wire desc_v,input wire[11:0]desc_base,input wire[12:0]desc_limit,input wire[15:0]desc_loops,
 input wire launch_v,output wire active,done,output wire fault,
 output wire[135:0]query_rq,input wire[2055:0]query_rr,
 output wire[6:0]events,output wire[9:0]phase,output wire event_valid,
 output wire[15:0]rows,output wire pv_only,output wire[8191:0]q_words,output wire q_present,output wire[1023:0]p_words,output wire p_present
);
 wire we,sv,configured,tf,iv,cf,ff;wire[9:0]addr,base;wire[10:0]limit;wire[15:0]loops;wire[255:0]data;
 wire[222:0]instruction;wire[31:0]ordinal;
 ot_static_program_target #(.TARGET(8'd49),.PCW(10))u_target(
 .clk(clk),.rst_n(rst_n),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
 .program_active(active),.program_cfg_we(we),.program_cfg_addr(addr),.program_cfg_data(data),
 .program_start_v(sv),.program_start_base(base),.program_start_limit(limit),.program_start_loops(loops),.configured(configured),.fault(tf));
 ot_vms_calendar_static #(.W(223))u_outer(.clk(clk),.rst_n(rst_n),.cfg_we(we),.cfg_addr(addr),.cfg_data(data),
 .start_v(sv),.start_base(base),.start_limit(limit),.start_loops(loops),.calendar(instruction),.calendar_v(iv),.ordinal(ordinal),.active(active),.done(done),.fault(cf));
 ot_hbm_attn_physical_program_query_front u_front(.clk(clk),.rst_n(rst_n),.instruction_v(iv),.instruction(instruction),
 .query_rq(query_rq),.query_rr(query_rr),.events(events),.phase(phase),.event_valid(event_valid),.rows(rows),.pv_only(pv_only),.q_words(q_words),.q_present(q_present),.p_words(p_words),.p_present(p_present),.fault(ff));
 assign fault=tf|cf|ff;
endmodule
`default_nettype wire
