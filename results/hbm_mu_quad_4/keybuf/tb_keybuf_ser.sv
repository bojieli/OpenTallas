`timescale 1ns/1ps
// HBM-MU-QUAD-4: old ot_hnx_idxn_keybuf vs (kb_tx shim -> ot_hnx_idxn_keybuf_ser core -> kb_rx shim), same stimulus.
// Check A: every key event (live_v|replay_v) at cycle e: rx key_line at e+K == old key_out at e (all 8792 bits).
// Check B: core fault pin at t+NB+2 == old fault at t, every cycle. Stimulus: static records (clear, 171 live beats,
// R replay rows with PRE one edge ahead) with event spacing >= NB, plus injected schedule faults.
module tb;
 parameter integer NB=3; localparam integer W=(8792+NB-1)/NB, K=2*NB+2, LF=NB+2;
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0,clear=0,live_v=0,pre_v=0,replay_v=0; reg[7:0]live_index=0,pre_index=0,replay_index=0; reg[8791:0]key_in=0;
 wire[8791:0]old_out; wire old_fault;
 ot_hnx_idxn_keybuf ref0(.clk(clk),.rst_n(rst_n),.clear(clear),.live_v(live_v),.live_index(live_index),.key_in(key_in),
  .pre_v(pre_v),.pre_index(pre_index),.replay_v(replay_v),.replay_index(replay_index),.key_out(old_out),.fault(old_fault));
 wire t_clear,t_live,t_pre,t_rep; wire[7:0]t_lix,t_pix,t_rix; wire[W-1:0]t_ser,c_ser; wire tx_fault,c_fault;
 ot_hnx_idxn_kb_tx #(.NB(NB)) tx(.clk(clk),.rst_n(rst_n),.clear(clear),.live_v(live_v),.live_index(live_index),.key_in(key_in),
  .pre_v(pre_v),.pre_index(pre_index),.replay_v(replay_v),.replay_index(replay_index),
  .o_clear(t_clear),.o_live_v(t_live),.o_live_index(t_lix),.o_key_ser(t_ser),.o_pre_v(t_pre),.o_pre_index(t_pix),
  .o_replay_v(t_rep),.o_replay_index(t_rix),.fault(tx_fault));
 ot_hnx_idxn_keybuf_ser #(.NB(NB)) dut(.clk(clk),.rst_n(rst_n),.clear(t_clear),.live_v(t_live),.live_index(t_lix),.key_in_ser(t_ser),
  .pre_v(t_pre),.pre_index(t_pix),.replay_v(t_rep),.replay_index(t_rix),.key_out_ser(c_ser),.fault(c_fault));
 wire[8791:0]rx_line; wire[8:0]beat_d;
 ot_hnx_idxn_kb_rx #(.NB(NB)) rx(.clk(clk),.rst_n(rst_n),.key_ser(c_ser),.beat_in({live_v|replay_v,replay_v?replay_index:live_index}),
  .key_line(rx_line),.beat_out(beat_d));
 // reference histories
 integer cyc=0, nev=0, nerr=0, nferr=0, nfault_cyc=0, ninj=0;
 reg[8791:0]hist_out[0:63]; reg hist_ev[0:63]; reg hist_f[0:63]; reg[8:0]hist_beat[0:63];
 always @(posedge clk) if(rst_n) begin
  hist_out[cyc%64]<=old_out; hist_ev[cyc%64]<=live_v|replay_v; hist_f[cyc%64]<=old_fault;
  hist_beat[cyc%64]<={live_v|replay_v,replay_v?replay_index:live_index};
  if(cyc>=K && hist_ev[(cyc-K)%64]) begin
   nev=nev+1;
   if(rx_line!==hist_out[(cyc-K)%64]) begin nerr=nerr+1; if(nerr<5)$display("DATA MISMATCH cyc %0d event %0d",cyc,cyc-K); end
   if(beat_d!==hist_beat[(cyc-K)%64]) begin nerr=nerr+1; if(nerr<5)$display("BEAT MISMATCH cyc %0d",cyc); end
  end
  if(cyc>=LF) begin
   if(c_fault!==hist_f[(cyc-LF)%64]) begin nferr=nferr+1; if(nferr<5)$display("FAULT MISMATCH cyc %0d",cyc); end
   if(c_fault) nfault_cyc=nfault_cyc+1;
  end
  cyc<=cyc+1;
 end
 task automatic idle(input integer n); repeat(n) @(negedge clk) begin live_v=0;pre_v=0;replay_v=0;clear=0; key_in={275{$urandom}}; end endtask
 task automatic rand_key; integer i; for(i=0;i<275;i=i+1) key_in[i*32+:32]=$urandom; endtask
 integer rec,b,r,gap,seed,bad; integer M;
 initial begin
  if(!$value$plusargs("seed=%d",seed)) seed=1; void'($urandom(seed));
  repeat(3)@(negedge clk); rst_n=1;
  for(rec=0;rec<6;rec=rec+1) begin
   bad=(rec>=4);  // records 4,5 inject schedule faults (old and new must fault identically)
   M=(rec==0)?171:($urandom%171+1);
   @(negedge clk) begin clear=1; live_v=0;pre_v=0;replay_v=0; end
   idle(NB);
   for(b=0;b<M;b=b+1) begin
    @(negedge clk) begin clear=0; live_v=1; live_index=b; rand_key; end
    gap=NB-1+($urandom%3==0 ? $urandom%3 : 0); idle(gap);
   end
   for(r=1;r<=3;r=r+1) for(b=0;b<M;b=b+1) begin
    // PRE one edge before the replay edge; replay spacing >= NB
    @(negedge clk) begin live_v=0; replay_v=0; pre_v=1; pre_index=(bad&&$urandom%40==0)?8'(M+3):8'(b); rand_key; end
    @(negedge clk) begin pre_v=(bad&&$urandom%50==0); pre_index=b; replay_v=1; replay_index=b; rand_key;
      if(bad&&$urandom%60==0) begin replay_index=b+1; ninj=ninj+1; end end
    gap=NB-2+($urandom%4==0 ? $urandom%3 : 0); if(gap>0) idle(gap);
   end
   idle(K+4);
  end
  idle(2*K);
  $display("RESULT NB=%0d W=%0d K=%0d events=%0d data_err=%0d fault_err=%0d fault_cycles=%0d injected=%0d tx_spacing_fault=%0d cycles=%0d",
           NB,W,K,nev,nerr,nferr,nfault_cyc,ninj,tx_fault,cyc);
  if(nerr==0&&nferr==0&&nev>0&&tx_fault==0) $display("PASS"); else $display("FAIL");
  $finish;
 end
endmodule
