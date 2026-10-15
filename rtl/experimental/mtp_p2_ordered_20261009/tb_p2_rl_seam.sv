`timescale 1ns/1ps
// el1011-ds-mtp 2026-10-12: READY-LATENCY seam bench (ot_p2h_xport station -> ot_p2h_arith xfer, PINREG=2).
// Random producer valid and random consumer stalls; the sender pops on its registered copy of in_ready only and drives
// registered {t_v, t_d}; the receiver captures every valid beat.  PASS = 4000 beats in order, none lost / duplicated,
// no overflow ($fatal in ot_sc_pfifo), and full rate (>= 0.95 beats/cycle) in an unstalled window.
// Mutant: -DOT_SC_PFIFO_RL_MUT (receiver forgets the older in-flight authorisation) must overflow.
module tb_p2_rl_seam;
  reg clk=0, rn=0; always #0.5 clk=~clk;
  localparam integer W=32, N=4000;
  reg [W-1:0] gen; reg pv_src; wire src_r;
  wire o_v; wire [W-1:0] o_d; reg rq, t_v; reg [W-1:0] t_d;
  ot_sc_pfifo #(.W(W),.S(2),.G(8)) opin(.clk(clk),.rst_n(rn),.in_valid(pv_src),.in_ready(src_r),.in_data(gen),
    .out_valid(o_v),.out_ready(rq),.out_data(o_d));
  wire x_r, a_v; wire [W-1:0] a_d; reg a_r;
  always @(posedge clk or negedge rn) if(!rn) begin rq<=0; t_v<=0; end else begin rq<=x_r; t_v<=o_v&&rq; end
  always @(posedge clk) t_d<=o_d;
  ot_sc_pfifo #(.W(W),.S(6),.G(8),.PINREG(2)) xfer(.clk(clk),.rst_n(rn),.in_valid(t_v),.in_ready(x_r),.in_data(t_d),
    .out_valid(a_v),.out_ready(a_r),.out_data(a_d));
  integer cyc=0, got=0, exp_v=0, win_beats=0, seed=7, phase=0;
  always @(posedge clk) begin
    if(!rn) begin gen<=0; pv_src<=0; a_r<=0; end else begin
      cyc<=cyc+1;
      if(pv_src&&src_r) gen<=gen+1;
      phase = (cyc>=1500 && cyc<2500);        // unstalled window
      pv_src <= phase ? 1'b1 : ($random(seed)%4!=0);
      a_r    <= phase ? 1'b1 : ($random(seed)%3==0);
      if(a_v&&a_r) begin
        if(a_d!==exp_v) begin $display("SEAM FAIL beat %0d got %0d", exp_v, a_d); $finish; end
        exp_v<=exp_v+1; got<=got+1;
        if(cyc>=1700 && cyc<2500) win_beats<=win_beats+1;
      end
      if(got>=N) begin
        if(win_beats < 760) begin $display("SEAM FAIL rate %0d/800 in the unstalled window", win_beats); $finish; end
        $display("SEAM PASS %0d beats in order, unstalled window %0d/800", got, win_beats); $finish;
      end
      if(cyc>200000) begin $display("SEAM FAIL timeout got %0d", got); $finish; end
    end
  end
  initial begin repeat(5) @(posedge clk); rn=1; end
endmodule
