`timescale 1ns/1ps
// TRANSPORT-1 bench 1: QC embedding + RoPE row read, native59 -> embed_prov over parameterised actual-transport depths.
// Instantiates the actual RTL (qfd_native59_dv_headprep_obs1 #(.ROPE(1)), qfd_embedding_word_provider #(.ROPE(1)) ) with
// run-time stage counts on the six crossing buses (+D_CRE +D_CA +D_CQ +D_SRE +D_SA +D_SQ).  D=0 = zero-transport oracle.
module tb_dly #(parameter W=1)(input wire ck, input wire [7:0] d, input wire [W-1:0] a, output wire [W-1:0] b);
 reg [W-1:0] r [0:63]; integer i;
 always @(posedge ck) begin r[0]<=a; for(i=1;i<64;i=i+1) r[i]<=r[i-1]; end
 assign b = (d==0)? a : r[d-1];
endmodule

module tb_emb_transport;
 reg ck=0; always #1 ck=~ck;
 reg rst_n=0;
 integer D_CRE=0,D_CA=0,D_CQ=0,D_SRE=0,D_SA=0,D_SQ=0,HOLD=0;
 localparam [17:0] T=18'd5;
 localparam [15:0] E=16'd3;
 function [511:0] code(input integer i); reg [511:0] x; integer j; begin x=0; for(j=0;j<16;j=j+1) x[32*j+:32]=32'hC0DE0000^(i*(j+1)*32'h01000193)^j; code=x; end endfunction
 function [511:0] rope(input integer i); reg [511:0] x; integer j; begin x=0; for(j=0;j<16;j=j+1) x[32*j+:32]=32'hA5A50000^(i*(j+3)*32'h000F4243)^(j<<8); rope=x; end endfunction
 localparam [15:0] SCALE=16'h4242;

 // provider face
 reg word_v=0; reg [511:0] word_data=0; reg [17:0] word_token=0; reg [5:0] word_index=0; reg word_scale=0; reg [15:0] word_epoch=0;
 reg exp_slot=0; reg [17:0] exp_token=0; reg [5:0] exp_word=0; reg exp_scale=0; reg [15:0] exp_epoch=0;
 reg fill_begin=0; reg [17:0] fill_token=0; reg [15:0] fill_epoch=0;
 reg core_start=0; reg [17:0] core_token=0; reg [15:0] core_epoch=0;
 wire n_cre; wire [23:0] n_ca; wire n_sre; wire [17:0] n_sa;
 wire p_cre; wire [23:0] p_ca; wire p_sre; wire [17:0] p_sa;
 wire [511:0] p_cq, n_cq; wire [15:0] p_sq, n_sq; wire prov_fault, n59_fault;
 reg [379:0] cmd=0; wire [519:0] dr_o;
 reg [7:0] dcre,dca,dcq,dsre,dsa,dsq;
 tb_dly #(1) d0(ck,dcre,n_cre,p_cre); tb_dly #(24) d1(ck,dca,n_ca,p_ca); tb_dly #(512) d2(ck,dcq,p_cq,n_cq);
 tb_dly #(1) d3(ck,dsre,n_sre,p_sre); tb_dly #(18) d4(ck,dsa,n_sa,p_sa); tb_dly #(16) d5(ck,dsq,p_sq,n_sq);

 qfd_embedding_word_provider #(.ROPE(`PROPE),.ROPE_FF(`PFF)) u_prov(.ck(ck),.rst_n(rst_n),.word_v(word_v),.word_data(word_data),.word_token(word_token),.word_index(word_index),
  .word_scale(word_scale),.word_epoch(word_epoch),.expected_word_slot(exp_slot),.expected_token(exp_token),.expected_word(exp_word),
  .expected_scale(exp_scale),.expected_epoch(exp_epoch),.fill_begin(fill_begin),.fill_token(fill_token),.fill_epoch(fill_epoch),
  .core_start(core_start),.core_token(core_token),.core_epoch(core_epoch),.embed_code_re(p_cre),.embed_code_addr(p_ca),.embed_code_q(p_cq),
  .embed_scale_re(p_sre),.embed_scale_addr(p_sa),.embed_scale_q(p_sq),.fault(prov_fault));

 qfd_native59_dv_headprep_obs1 #(.ROPE(1),.EMB_RT_CODE(`RC),.EMB_RT_SCALE(`RS)) u_n59(.ck(ck),.rst_n(rst_n),.native_cmd(cmd),.dr_o(dr_o),.emb_code_re(n_cre),.emb_code_addr(n_ca),
  .emb_scale_re(n_sre),.emb_scale_addr(n_sa),.emb_code_q(n_cq),.emb_scale_q(n_sq),.fault(n59_fault));

 // trace of the raw pin-register payloads and the ring tags
 integer c=-1; integer ck_rec=0;
 reg [511:0] t_ecq [0:2047]; reg [15:0] t_esq [0:2047];
 integer c_k [0:127]; integer k; initial for(k=0;k<128;k=k+1) c_k[k]=-1;
 integer ndro=0, dro_err=0;
 function [6:0] seq_k(input integer n); seq_k = (n<=64)? 7'(n) : 7'(n-65+77); endfunction

 always @(posedge ck) begin
  if(c>=0 && c<2048) begin t_ecq[c]<=u_n59.u_svc.p_ecq; t_esq[c]<=u_n59.u_svc.p_esq; end
  if(c>=0 && u_n59.u_svc.e3 && c_k[u_n59.u_svc.k3]<0) c_k[u_n59.u_svc.k3]=c;
  if(c>=0 && dr_o[519] && dr_o[518]) begin
   automatic reg [6:0] kk=seq_k(ndro);
   automatic reg [511:0] want;
   if(kk<64) want=code(kk); else if(kk==64) want={496'd0,SCALE}; else want=rope(kk-7'd77);
   if(dr_o[511:0]!==want) begin
    dro_err=dro_err+1;
    if(dro_err<=6) $display("DRO_MISS n=%0d k=%0d beat=%0d got[31:0]=%h want[31:0]=%h",ndro,kk,dr_o[517:512],dr_o[31:0],want[31:0]);
   end
   ndro=ndro+1;
  end
  if(c>=0) c=c+1;
 end

 integer i,L,err_c,err_s,cnt; reg [511:0] want;
 initial begin
  if(!$value$plusargs("D_CRE=%d",D_CRE)) D_CRE=0; if(!$value$plusargs("D_CA=%d",D_CA)) D_CA=0; if(!$value$plusargs("D_CQ=%d",D_CQ)) D_CQ=0;
  if(!$value$plusargs("D_SRE=%d",D_SRE)) D_SRE=0; if(!$value$plusargs("D_SA=%d",D_SA)) D_SA=0; if(!$value$plusargs("D_SQ=%d",D_SQ)) D_SQ=0;
  dcre=D_CRE;dca=D_CA;dcq=D_CQ;dsre=D_SRE;dsa=D_SA;dsq=D_SQ;
  repeat(40) @(negedge ck); rst_n=1; repeat(100) @(negedge ck);
  // fill
  fill_begin=1; fill_token=T; fill_epoch=E; @(negedge ck); fill_begin=0; repeat(3) @(negedge ck);
  word_token=T; exp_token=T; word_epoch=E; exp_epoch=E;
  for(i=0;i<64;i=i+1) begin word_v=1; exp_slot=1; word_index=i; exp_word=i; word_scale=0; exp_scale=0; word_data=code(i); @(negedge ck); end
  word_index=0; exp_word=0; word_scale=1; exp_scale=1; word_data={496'd0,SCALE}; @(negedge ck);
  for(i=1;i<=8;i=i+1) begin word_index=i; exp_word=i; word_scale=1; exp_scale=1; word_data=rope(i-1); @(negedge ck); end
  word_v=0; exp_slot=0; repeat(10) @(negedge ck);
  // issue one embedding command (cmd[379:376]=E, token [375:358], [357:0]=0)
  cmd[379:376]=4'hE; cmd[375:358]=T; c=0; @(negedge ck); cmd=0;
  repeat(1200) @(negedge ck);
  $display("CFG D_CRE=%0d D_CA=%0d D_CQ=%0d D_SRE=%0d D_SA=%0d D_SQ=%0d",D_CRE,D_CA,D_CQ,D_SRE,D_SA,D_SQ);
  $display("DRO_BEATS=%0d DRO_ERRORS=%0d PROV_FAULT=%b N59_FAULT=%b DVF=%b",ndro,dro_err,prov_fault,n59_fault,u_n59.u_svc.dvf);
  for(L=-4;L<=40;L=L+1) begin
   err_c=0;
   for(k=0;k<64;k=k+1) begin if(c_k[k]<0||c_k[k]+L<0) continue; if(t_ecq[c_k[k]+L]!==code(k)) err_c=err_c+1; end
   for(k=77;k<=84;k=k+1) begin if(c_k[k]<0||c_k[k]+L<0) continue; if(t_ecq[c_k[k]+L]!==rope(k-77)) err_c=err_c+1; end
   $display("LAG_CODE L=%0d errors=%0d",L,err_c);
  end
  for(L=-4;L<=40;L=L+1) begin
   err_s=0;
   if(c_k[64]<0||c_k[64]+L<0) err_s=1; else if(t_esq[c_k[64]+L]!==SCALE) err_s=1;
   $display("LAG_SCALE L=%0d errors=%0d",L,err_s);
  end
  $finish;
 end
endmodule
