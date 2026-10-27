`default_nettype none
// HBM-MU-QUAD-4 2026-10-27: TIME-SERIALISED key replay buffer hard core (opt-in successor of ot_hnx_idxn_keybuf for the
// 324 x 324 MU hub outline; the original module is UNCHANGED and is instantiated inside as the functional core).
// Problem: ot_hnx_idxn_keybuf has 8792 key_in + 8792 key_out + 31 control = 17615 port bits = 13.6 pins/um on a
// 324 x 324 outline (limit 6). Fix: the wide key buses cross the core boundary as NB beats of W = ceil(8792/NB) bits.
// STATIC SCHEDULE, no valid/ready, no credits, no counters: every serialiser/assembler is an always-shifting register
// chain, so beat j of a line is on the wire exactly j edges after beat 0 (fixed by construction). The calendar must
// space key events (live or replay) >= NB edges apart; the producer shim faults on a closer pair (collision = fault,
// as the IDXN calendar). EVERY core pin is registered (input flops on all inputs, outputs driven by flops only).
// Timing (producer cycle e = the edge the ORIGINAL keybuf would see live_v/replay_v, pre_v one edge earlier):
//   producer shim (ot_hnx_idxn_kb_tx): output flops, beat j on the wire in cycle e+1+j, control in cycle e+1
//   core input flops: beat j in cycle e+2+j, control in cycle e+2; control delayed NB-1 more -> inner event c = e+NB+1
//   inner ot_hnx_idxn_keybuf sees exactly the original control sequence delayed by L = NB+1 (pre_v still 1 edge ahead)
//   core output serialiser: key_out beat j on the pin in cycle c+1+j
//   consumer shim (ot_hnx_idxn_kb_rx): input flops beat j in cycle c+2+j; full line in cycle e+K, K = 2 NB + 2
//   fault pin = original fault delayed by NB+2.
// Equivalence (results/hbm_mu_quad_4/keybuf): for every key event at e, rx line(e+K) == original key_out(e); the
// scorer samples key_lines only on its beat_v edges, so beat_v/beat_index are delayed by K in the consumer shim.
module ot_hnx_idxn_ser_tx #(parameter integer DW=8792,NB=3,W=(DW+NB-1)/NB)(
 input wire clk,input wire ev,input wire[DW-1:0]d,output reg[W-1:0]q
);
 // always-shifting serialiser: on ev beat 0 of d leaves now, beats 1..NB-1 follow on the next NB-1 edges
 reg[W*NB-1:0]hold;
 wire[W*NB-1:0]dx={{(W*NB-DW){1'b0}},d};
 always @(posedge clk)begin
  if(ev)begin q<=dx[W-1:0];hold<=dx>>W;end
  else begin q<=hold[W-1:0];hold<=hold>>W;end
 end
endmodule
module ot_hnx_idxn_ser_rx #(parameter integer DW=8792,NB=3,W=(DW+NB-1)/NB)(
 input wire clk,input wire[W-1:0]b,output wire[DW-1:0]d
);
 // always-shifting assembler: d = {current beat, previous NB-1 beats}; valid in the cycle the last beat is present
 generate if(NB==1)begin:g1
  assign d=b[DW-1:0];
 end else begin:gn
  reg[W*(NB-1)-1:0]sh;
  if(NB==2)begin:g2 always @(posedge clk)sh<=b; end
  else begin:g3 always @(posedge clk)sh<={b,sh[W*(NB-1)-1:W]}; end
  wire[W*NB-1:0]full={b,sh};
  assign d=full[DW-1:0];
 end endgenerate
endmodule
module ot_hnx_idxn_dpipe #(parameter integer N=1,D=1)(input wire clk,rst_n,input wire[N-1:0]i,output wire[N-1:0]o);
 generate if(D==0)begin:g0 assign o=i; end else begin:gd
  reg[N*D-1:0]p;
  if(D==1)begin:d1 always @(posedge clk or negedge rst_n)if(!rst_n)p<=0;else p<=i; end
  else begin:dn always @(posedge clk or negedge rst_n)if(!rst_n)p<=0;else p<={p[N*(D-1)-1:0],i}; end
  assign o=p[N*D-1-:N];
 end endgenerate
endmodule
// ---- the hard core (plan module hnx_idxn_keybuf, opt-in NB): 2 W + 31 port bits
module ot_hnx_idxn_keybuf_ser #(parameter integer NB=3,DW=8792,W=(DW+NB-1)/NB)(   // DW != 8792 only with OT_KB_FORMAL
 input wire clk,rst_n,clear,
 input wire live_v,input wire[7:0]live_index,input wire[W-1:0]key_in_ser,
 input wire pre_v,input wire[7:0]pre_index,
 input wire replay_v,input wire[7:0]replay_index,
 output reg[W-1:0]key_out_ser,output reg fault
`ifdef OT_KB_FORMAL
 ,output wire[DW-1:0]fv_key_line,output wire[27:0]fv_ctl,input wire[DW-1:0]fv_key_o,input wire fv_fault
`endif
);
 // input pin flops
 reg[W-1:0]kin_r;reg[27:0]ctl_r;
 always @(posedge clk)kin_r<=key_in_ser;
 always @(posedge clk or negedge rst_n)if(!rst_n)ctl_r<=0;
  else ctl_r<={clear,live_v,live_index,pre_v,pre_index,replay_v,replay_index};
 wire[27:0]ctl_d;
 ot_hnx_idxn_dpipe #(.N(28),.D(NB-1)) dctl(.clk(clk),.rst_n(rst_n),.i(ctl_r),.o(ctl_d));
 wire[DW-1:0]key_line;
 ot_hnx_idxn_ser_rx #(.DW(DW),.NB(NB),.W(W)) asm(.clk(clk),.b(kin_r),.d(key_line));
 wire i_clear=ctl_d[27],i_live=ctl_d[26],i_pre=ctl_d[17],i_rep=ctl_d[8];
 wire[7:0]i_live_ix=ctl_d[25:18],i_pre_ix=ctl_d[16:9],i_rep_ix=ctl_d[7:0];
 wire[DW-1:0]key_o;wire f_i;
`ifdef OT_KB_FORMAL
 // formal cut (results/hbm_mu_quad_4/keybuf/formal): the inner keybuf is replaced by free signals so the proof covers
 // the wrapper for ANY inner behaviour: inner inputs = original inputs delayed by NB+1, outputs reach the pins unchanged.
 assign fv_key_line=key_line;assign fv_ctl=ctl_d;assign key_o=fv_key_o;assign f_i=fv_fault;
`else
 ot_hnx_idxn_keybuf core(.clk(clk),.rst_n(rst_n),.clear(i_clear),.live_v(i_live),.live_index(i_live_ix),.key_in(key_line),
  .pre_v(i_pre),.pre_index(i_pre_ix),.replay_v(i_rep),.replay_index(i_rep_ix),.key_out(key_o),.fault(f_i));
`endif
 // output serialiser = the output pin flops
 wire[W-1:0]kout_q;
 ot_hnx_idxn_ser_tx #(.DW(DW),.NB(NB),.W(W)) ser(.clk(clk),.ev(i_live|i_rep),.d(key_o),.q(kout_q));
 always @*key_out_ser=kout_q;
 always @(posedge clk or negedge rst_n)if(!rst_n)fault<=0;else fault<=f_i;
endmodule
// ---- producer-side shim (instantiated in the partner partition next to the IDXN calendar / HBM key-line service)
module ot_hnx_idxn_kb_tx #(parameter integer NB=3,DW=8792,W=(DW+NB-1)/NB)(
 input wire clk,rst_n,clear,
 input wire live_v,input wire[7:0]live_index,input wire[DW-1:0]key_in,
 input wire pre_v,input wire[7:0]pre_index,
 input wire replay_v,input wire[7:0]replay_index,
 output wire o_clear,o_live_v,output wire[7:0]o_live_index,output wire[W-1:0]o_key_ser,
 output wire o_pre_v,output wire[7:0]o_pre_index,output wire o_replay_v,output wire[7:0]o_replay_index,
 output reg fault   // two key events closer than NB edges (static-schedule violation)
);
 reg[27:0]c;
 always @(posedge clk or negedge rst_n)if(!rst_n)c<=0;
  else c<={clear,live_v,live_index,pre_v,pre_index,replay_v,replay_index};
 assign {o_clear,o_live_v,o_live_index,o_pre_v,o_pre_index,o_replay_v,o_replay_index}=c;
 ot_hnx_idxn_ser_tx #(.DW(DW),.NB(NB),.W(W)) ser(.clk(clk),.ev(live_v|replay_v),.d(key_in),.q(o_key_ser));
 generate if(NB==1)begin:g1 always @(posedge clk or negedge rst_n)if(!rst_n)fault<=0; end
 else begin:gn
  reg[NB-1:0]recent;   // recent[0] = event on the previous edge .. recent[NB-2] = NB-1 edges ago
  always @(posedge clk or negedge rst_n)if(!rst_n)begin recent<=0;fault<=0;end
   else begin recent<={recent[NB-2:0],live_v|replay_v};if((live_v|replay_v)&&|recent[NB-2:0])fault<=1;end
 end endgenerate
endmodule
// ---- consumer-side shim (scorer side): registers the beats, assembles the line, delays the scorer's beat fields by K
module ot_hnx_idxn_kb_rx #(parameter integer NB=3,DW=8792,W=(DW+NB-1)/NB,CW=9,K=2*NB+2)(
 input wire clk,rst_n,input wire[W-1:0]key_ser,input wire[CW-1:0]beat_in,
 output wire[DW-1:0]key_line,output wire[CW-1:0]beat_out
);
 reg[W-1:0]b_r;
 always @(posedge clk)b_r<=key_ser;
 ot_hnx_idxn_ser_rx #(.DW(DW),.NB(NB),.W(W)) asm(.clk(clk),.b(b_r),.d(key_line));
 ot_hnx_idxn_dpipe #(.N(CW),.D(K)) dbeat(.clk(clk),.rst_n(rst_n),.i(beat_in),.o(beat_out));
endmodule
`default_nettype wire
