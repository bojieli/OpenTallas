`timescale 1ns/1ps
`default_nettype none
// Actual source front shared by the full arithmetic parent and its independent
// exact port-trace proof. All state is flops or real programme/query macros.
module ot_hbm_attn_program_query_front(
 input wire clk,rst_n,input wire instruction_v,input wire[222:0]instruction,
 output wire[135:0]query_rq,input wire[2055:0]query_rr,
 output wire[6:0]events,output wire[7:0]phase,output wire event_valid,
 output wire[15:0]rows,output wire pv_only,output wire[8191:0]q_words,
 output wire q_present,output wire fault
);
 wire query_epoch,fr,fv,fe;wire[15:0]fs;wire[3:0]fh;wire[2:0]fb;wire pf,qf;
 reg[3:0]qh;
 always @(posedge clk or negedge rst_n)if(!rst_n)qh<=0;
 else if(events[0])qh<=0;else if(events[1])qh<=qh+1'b1;
 wire qread=!pv_only&&(events[0]||(events[1]&&qh!=15));
 wire[3:0]qreadhead=events[0]?4'd0:qh+1'b1;
 ot_hbm_attn_program_consumer u_program(.clk(clk),.rst_n(rst_n),.instruction_v(instruction_v),.instruction(instruction),
  .events(events),.phase(phase),.event_valid(event_valid),.rows(rows),.pv_only(pv_only),.query_epoch(query_epoch),
  .fetch_v(fv),.fetch_epoch(fe),.fetch_head(fh),.fetch_burst(fb),.fetch_base_sector(fs),.running(fr),.fault(pf));
 ot_hbm_attn_query_prefetch u_query(.clk(clk),.rst_n(rst_n),.fetch_v(fv),.fetch_epoch(fe),.fetch_head(fh),.fetch_burst(fb),.fetch_base_sector(fs),
  .rq(query_rq),.rr(query_rr),.read_v(qread),.read_epoch(query_epoch),.read_head(qreadhead),.q_v(q_present),.q_w(q_words),.fault(qf));
 assign fault=pf|qf;
endmodule
`default_nettype wire
