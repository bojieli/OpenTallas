`timescale 1ns/1ps
`default_nettype none
// Opt-in exactG25param369 H1 source join, full H16 arithmetic retained: nativeprogramme/currentVM Q64partition/P4 prefetch ->
// sharedHG1/localK-Vmode34/explicitFFtranspose arithmetic. KVnativeproducer,
// SC/PVnativewriteprogramme, physicalpipeline/cut/route andfullprice OPEN.
module ot_hbm_attention_h1_static_engine(
 input wire clk,rst_n,input wire[3:0]bank_clk,
 input wire instruction_v,input wire[222:0]instruction,
 output wire[135:0]query_rq,input wire[2055:0]query_rr,
 input wire kv_present,input wire[1:0]kv_mask,input wire[8479:0]kv_words,
 output wire sc_v,output wire[15:0]sc_row,output wire[1:0]sc_mask,
 output wire[1023:0]sc_data,output wire[31:0]sc_fault,
 output wire pv_v,output wire[7:0]pv_dim,output wire[16383:0]pv_data,output wire[511:0]pv_fault,
 output wire fault
);
 wire[6:0]events;wire[9:0]phase;wire ev,pv_only,pf,cf,qv,pp;
 wire[15:0]rows;wire[8191:0]qf;wire[4095:0]pw;
 ot_hbm_attn_physical_program_query_front_h1 u_front(.clk(clk),.rst_n(rst_n),.bank_clk(bank_clk),
  .instruction_v(instruction_v),.instruction(instruction),.query_rq(query_rq),.query_rr(query_rr),
  .events(events),.phase(phase),.event_valid(ev),.rows(rows),.pv_only(pv_only),
  .q_words(),.q_fields(qf),.q_present(qv),.p_words(),.p_fields(pw),.p_present(pp),.fault(pf));
 ot_hdc_v41x_attn_local_calendar u_engine(
  .clk(clk),.rst_n(rst_n),.job_v(events[0]),.job_t(rows|(pv_only?16'h4000:16'h2000)),.calendar_fault(cf),
  .slot_qk(events[5]),.slot_fill(events[4]),.slot_pv(events[6]),.q_present(qv),.kv_present(kv_present),.p_present(pp),
  .q_v(events[1]),.q_field_words(qf),.kv_v(events[2]),.kv_m(kv_mask),.kv_w(kv_words),.p_v(events[3]),.p_field_words(pw),
  .sc_v(sc_v),.sc_row(sc_row),.sc_m(sc_mask),.sc_y(sc_data),.sc_f(sc_fault),
  .pv_v(pv_v),.pv_c(pv_dim),.pv_y(pv_data),.pv_f(pv_fault),.qk_iss(),.pv_iss());
 assign fault=pf|cf;
endmodule
`default_nettype wire
