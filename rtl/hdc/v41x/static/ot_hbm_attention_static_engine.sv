`timescale 1ns/1ps
`default_nettype none
// Actual compiler consumer + programme SRAM + mapped query prefetch + full H16
// attention arithmetic/staging. This source composition is not a physical view.
// programme phase follows explicit VM prefetch; PS rows/P words have separate
// native producer ownership and are checked, never used to gate issue events.
module ot_hbm_attention_static_engine(
 input wire clk,rst_n,input wire instruction_v,input wire[222:0]instruction,
 output wire[135:0]query_rq,input wire[2055:0]query_rr,
 input wire kv_present,input wire[3:0]kv_mask,input wire[16959:0]kv_words,
 input wire p_present,input wire[1023:0]p_word,
 output wire sc_v,output wire[15:0]sc_row,output wire[3:0]sc_mask,
 output wire[2047:0]sc_data,output wire[63:0]sc_fault,
 output wire pv_v,output wire[7:0]pv_dim,output wire[16383:0]pv_data,output wire[511:0]pv_fault,
 output wire fault
);
 wire[6:0]events;wire[7:0]phase;wire event_valid,pv_only,pf,cf,qv;
 wire[15:0]rows;wire[8191:0]qw;
 ot_hbm_attn_program_query_front u_front(.clk(clk),.rst_n(rst_n),.instruction_v(instruction_v),.instruction(instruction),
  .query_rq(query_rq),.query_rr(query_rr),.events(events),.phase(phase),.event_valid(event_valid),
  .rows(rows),.pv_only(pv_only),.q_words(qw),.q_present(qv),.fault(pf));
 ot_hdc_v41x_attn_calendar #(.H(16),.D(512),.TD(64),.NL(4),.TROWS(640),.SRAM_MACRO(1),.MODES(1))u_engine(
  .clk(clk),.rst_n(rst_n),.job_v(events[0]),.job_t(rows|(pv_only?16'h4000:16'h2000)),.calendar_fault(cf),
  .slot_qk(events[5]),.slot_fill(events[4]),.slot_pv(events[6]),.q_present(qv),.kv_present(kv_present),.p_present(p_present),
  .q_v(events[1]),.q_w(qw),.kv_v(events[2]),.kv_m(kv_mask),.kv_w(kv_words),.p_v(events[3]),.p_w(p_word),
  .sc_v(sc_v),.sc_row(sc_row),.sc_m(sc_mask),.sc_y(sc_data),.sc_f(sc_fault),.pv_v(pv_v),.pv_c(pv_dim),.pv_y(pv_data),.pv_f(pv_fault),.qk_iss(),.pv_iss());
 assign fault=pf|cf;
endmodule
`default_nettype wire
