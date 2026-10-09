`timescale 1ns/1ps
// PIN-REGISTERED VARIANT of the TX idle-insertion pacer wrapper (redesign-hbm 2026-10-08).
// The original wrapper exposed the core's combinational in_v -> send (= in_v && slot) as an in -> out path, which
// the consistent die-link budget (in max = out max = T-60-254.5 ps) cannot hold at any corner (TT -353.5 ps).
// Here every output is a flop and in_v reaches only flops:
//   slot   : registered, cycle-exact equal to the core's slot (the permission for the CURRENT cycle);
//   send   : registered, the core's send DELAYED ONE CYCLE (an observation output; +1 cycle latency, 0 throughput);
//   in_v   -> in_q (pin flop), and one AND gate into slot_q / send_q (the same-cycle ready contract of slot needs
//             this cycle's in_v; there is no wider logic between the pin and a flop).
// The pacer state is tracked one edge late from (in_q, slot_d) and the next slot is precomputed:
//   slot(t+1) = !(in_v(t) && slot(t) && run(t) >= M-1),  run(t) = send(t-1) ? run(t-1)+1 : 0.
// Exactness against ot_hbm_coll_idle_insert: tb_coll_idle_tx_pin (every cycle: slot equal, send one cycle late).
module hfd_coll_idle_tx #(parameter integer M=1024)(input wire clk,rst_n,in_v,output wire slot,send);
 localparam integer RW=$clog2(M+1)+1;
 localparam [RW-1:0] MM1=M-1;
 (* ASYNC_REG="TRUE" *) reg [1:0] rst_s;
 always @(posedge clk or negedge rst_n)if(!rst_n)rst_s<=2'b00;else rst_s<={rst_s[0],1'b1};
 wire rst_i=rst_s[1];
 reg in_q,slot_q,slot_d,send_q;reg [RW-1:0] run_q;      // run_q = run(t-1)
 wire sent_prev=in_q&&slot_d;                          // send(t-1)
 wire [RW-1:0] run_t=sent_prev?run_q+1'b1:{RW{1'b0}};  // run(t)
 wire near=slot_q&&(run_t>=MM1);                       // registered-state decode (reg -> reg)
 always @(posedge clk or negedge rst_i)
  if(!rst_i)begin in_q<=1'b0;slot_q<=1'b1;slot_d<=1'b1;send_q<=1'b0;run_q<={RW{1'b0}};end
  else begin
   in_q<=in_v;slot_d<=slot_q;run_q<=run_t;
   slot_q<=!(in_v&&near);
   send_q<=in_v&&slot_q;
  end
 assign slot=slot_q;assign send=send_q;
endmodule
