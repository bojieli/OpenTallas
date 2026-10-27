// HBM-MU-QUAD-4 formal: tx shim -> ot_hnx_idxn_keybuf_ser (inner cut, OT_KB_FORMAL) -> rx shim, reduced width DW with the production residue DW mod NB (8792 mod NB).
// Assume: key events (live_v|replay_v) >= NB edges apart (the static schedule; the tx shim faults otherwise).
// Prove for all t (k-induction):
//  P1 inner control(t) == original control(t-L), L = NB+1, every cycle (so pre_v stays exactly one edge ahead)
//  P2 live event at e: inner key line(e+L) == key_in(e)
//  P3 inner event at c: rx key_line(c+NB+1) == inner key_out(c)   => end to end K = 2NB+2
//  P4 core fault pin(t+1) == inner fault(t);  P5 tx spacing fault never rises under the assumption
module fv_top #(parameter integer NB=3,DW=11)(input wire clk,
 input wire clear,live_v,input wire[7:0]live_index,input wire[DW-1:0]key_in,input wire pre_v,input wire[7:0]pre_index,
 input wire replay_v,input wire[7:0]replay_index,input wire[DW-1:0]fv_key_o,input wire fv_fault);
 localparam integer W=(DW+NB-1)/NB, L=NB+1, K=2*NB+2;
 reg [3:0] init=0; wire rst_n=init!=0; always @(posedge clk) if(init!=4'hf) init<=init+1;
 wire ev=live_v|replay_v;
 reg[NB-2:0]rec=0; always @(posedge clk) rec<={rec,ev};
 always @* if(rst_n) assume(!(ev && |rec));
 always @* if(!rst_n) assume(!ev && !pre_v && !clear);
 wire t_clear,t_live,t_pre,t_rep,txf,cf; wire[7:0]t_lix,t_pix,t_rix; wire[W-1:0]t_ser,c_ser;
 ot_hnx_idxn_kb_tx #(.NB(NB),.DW(DW)) tx(.clk(clk),.rst_n(rst_n),.clear(clear),.live_v(live_v),.live_index(live_index),.key_in(key_in),
  .pre_v(pre_v),.pre_index(pre_index),.replay_v(replay_v),.replay_index(replay_index),.o_clear(t_clear),.o_live_v(t_live),
  .o_live_index(t_lix),.o_key_ser(t_ser),.o_pre_v(t_pre),.o_pre_index(t_pix),.o_replay_v(t_rep),.o_replay_index(t_rix),.fault(txf));
 wire[DW-1:0]kl; wire[27:0]ctl;
 ot_hnx_idxn_keybuf_ser #(.NB(NB),.DW(DW)) dut(.clk(clk),.rst_n(rst_n),.clear(t_clear),.live_v(t_live),.live_index(t_lix),.key_in_ser(t_ser),
  .pre_v(t_pre),.pre_index(t_pix),.replay_v(t_rep),.replay_index(t_rix),.key_out_ser(c_ser),.fault(cf),
  .fv_key_line(kl),.fv_ctl(ctl),.fv_key_o(fv_key_o),.fv_fault(fv_fault));
 wire[DW-1:0]rxl; wire[8:0]bo;
 ot_hnx_idxn_kb_rx #(.NB(NB),.DW(DW)) rx(.clk(clk),.rst_n(rst_n),.key_ser(c_ser),.beat_in(9'd0),.key_line(rxl),.beat_out(bo));
 // histories
 wire[27:0]c_in={clear,live_v,live_index,pre_v,pre_index,replay_v,replay_index};
 reg[27:0]hc[0:L]; reg[DW-1:0]hk[0:L]; reg hl[0:L]; reg[DW-1:0]ho[0:NB+1]; reg he[0:NB+1]; reg hf; reg[7:0]age=0;
 integer i;
 always @(posedge clk) begin
  hc[0]<=c_in; hk[0]<=key_in; hl[0]<=live_v&&rst_n;
  for(i=1;i<=L;i=i+1) begin hc[i]<=hc[i-1]; hk[i]<=hk[i-1]; hl[i]<=hl[i-1]; end
  ho[0]<=fv_key_o; he[0]<=ctl[26]|ctl[8]; for(i=1;i<=NB+1;i=i+1) begin ho[i]<=ho[i-1]; he[i]<=he[i-1]; end
  hf<=fv_fault; if(rst_n && age!=8'hff) age<=age+1;
 end
 always @* if(age>L+1) begin
  P1: assert(ctl==hc[L-1]);
  if(hl[L-1]) P2: assert(kl==hk[L-1]);
 end
 always @* if(age>K+2) begin
  if(he[NB]) P3: assert(rxl==ho[NB]);
  P4: assert(cf==hf);
  P5: assert(!txf);
 end
endmodule
