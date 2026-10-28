`timescale 1ns/1ps
// KV-KITS-9 10-28: qkd_host_tx_class RST_Q=0 (random power-up queues, --x-initial unique) vs RST_Q=1 (reset queues):
// outputs equal on every edge after reset release => no queue slot is read before it is written.
module tb_tx_rstq;
 reg ck=0, rst_n=0; always #1 ck=~ck;
 reg host_v,ctrl_v,ing_v,irq=0,tx_cr; reg[511:0]host_d,ctrl_d; reg[63:0]ing_d; reg[23:0]credit_return,peer_credit;
 wire a_hc,a_cc,a_ic,a_tv,a_f,b_hc,b_cc,b_ic,b_tv,b_f; wire[527:0]a_td,b_td;
 qkd_host_tx_class #(.RST_Q(0)) ua(.ck(ck),.rst_n(rst_n),.host_v(host_v),.host_d(host_d),.host_cr(a_hc),.ctrl_v(ctrl_v),.ctrl_d(ctrl_d),.ctrl_cr(a_cc),
   .ing_v(ing_v),.ing_d(ing_d),.ing_cr(a_ic),.credit_return(credit_return),.peer_credit(peer_credit),.irq(irq),.tx_v(a_tv),.tx_d(a_td),.tx_cr(tx_cr),.fault(a_f));
 qkd_host_tx_class #(.RST_Q(1)) ub(.ck(ck),.rst_n(rst_n),.host_v(host_v),.host_d(host_d),.host_cr(b_hc),.ctrl_v(ctrl_v),.ctrl_d(ctrl_d),.ctrl_cr(b_cc),
   .ing_v(ing_v),.ing_d(ing_d),.ing_cr(b_ic),.credit_return(credit_return),.peer_credit(peer_credit),.irq(irq),.tx_v(b_tv),.tx_d(b_td),.tx_cr(tx_cr),.fault(b_f));
 integer e=0, mis=0, sends=0, rel=0, r;
 function [511:0] rnd512; for(integer k=0;k<16;k++) rnd512[k*32+:32]=$urandom; endfunction
 // well-behaved environment: sources push only with a local credit (4/class, back on *_cr), the peer returns one
 // application credit per class packet some edges later, the physical link returns one tx_cr per tx packet.
 integer sc[0:2], pk[0:2], ph;
 always @(negedge ck) begin
  if(!rst_n) begin for(integer k=0;k<3;k++) begin sc[k]=4; pk[k]=0; end ph=0; end
  else begin
   if(a_hc) sc[0]++; if(a_cc) sc[1]++; if(a_ic) sc[2]++;
   if(a_tv) begin ph++; case(a_td[527:524]) 0: pk[0]++; 1: pk[1]++; 5: pk[2]++; default:; endcase end
  end
  host_v=rst_n && sc[0]>0 && $urandom%3==0; ctrl_v=rst_n && sc[1]>0 && $urandom%3==0; ing_v=rst_n && sc[2]>0 && $urandom%4==0;
  if(host_v) sc[0]--; if(ctrl_v) sc[1]--; if(ing_v) sc[2]--;
  irq=($urandom%200==0)?~irq:irq;
  tx_cr=rst_n && ph>0 && $urandom%2==0; if(tx_cr) ph--;
  host_d=rnd512(); ctrl_d=rnd512(); ing_d={$urandom,$urandom};
  credit_return=($urandom%40==0)?{8'($urandom%4),8'($urandom%4),8'($urandom%4)}:24'd0;
  peer_credit=0;
  for(integer k=0;k<3;k++) if(pk[k]>0 && $urandom%3==0) begin peer_credit[k*8+:8]=1; pk[k]--; end
 end
 always @(posedge ck) if(rst_n) begin
  e++; if(a_tv) sends++;
  if({a_hc,a_cc,a_ic,a_tv,a_f}!=={b_hc,b_cc,b_ic,b_tv,b_f} || (a_tv && a_td!==b_td)) begin
    mis++; if(mis<6) $display("MISMATCH edge=%0d tv %b/%b td %h / %h", e, a_tv, b_tv, a_td[527:496], b_td[527:496]); end
 end
 initial begin
  for(r=0;r<6;r++) begin rst_n=0; repeat(5) @(posedge ck); #0.3 rst_n=1; repeat(4000) @(posedge ck); end
  if(mis==0 && sends>1000 && !a_f) $display("PASS tx_rstq edges=%0d sends=%0d mismatches=0 resets=6", e, sends);
  else $display("FAIL tx_rstq edges=%0d sends=%0d mismatches=%0d fault=%b", e, sends, mis, a_f);
  $finish;
 end
endmodule
