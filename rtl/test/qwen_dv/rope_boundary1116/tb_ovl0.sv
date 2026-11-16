`timescale 1ns/1fs
module tb;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0;reg[98:0]ctx=0;reg tv=0,ts=0;reg[511:0]td=0;reg[17:0]tt=0;reg[5:0]ti=0;reg[15:0]te=0;reg slot=0;
wire pv,bv,mv,pf,bf,mf,ps,bs,ms,pa,ba,ma;wire[547:0]pd,bd,md;wire[17:0]pt,bt,mt;wire[15:0]pe,be,me;wire[60:0]po,bo,mo;
`define PINS .ck(ck),.rst_n(rst_n),.i_ctx(ctx),.head_rx_user(2'd0),.emb_tx_user(2'd0),.kvn_ctx_fault(1'b0),.ovl_adm_done(1'b1),.d2d__emb_tx_slot(slot),.i_ctl(73'd0),.i_hroot_WS(299'd0),.i_hroot_WN(299'd0),.i_hroot_ES(299'd0),.i_hroot_EN(299'd0),.test_v(tv),.test_scale(ts),.test_data(td),.test_token(tt),.test_index(ti),.test_epoch(te)
rope_ctx_probe #(.FIX_ROPE_SLOT_GUARD(1),.NATIVE32(1),.PIPE_JOIN(1),.ROPE(1),.ROPE_DELAY(1024),.OVL(0)) p(`PINS,.rowtx__emb_tx_v(pv),.rowtx__emb_tx_payload(pd),.px_st(ps),.px_tok(pt),.px_tep(pe),.emb_fault(pf),.accepted_start(pa),.accepted_owner_o(po));
rope_ctx_probe #(.FIX_ROPE_SLOT_GUARD(0),.NATIVE32(1),.PIPE_JOIN(1),.ROPE(1),.ROPE_DELAY(1024),.OVL(0)) base(`PINS,.rowtx__emb_tx_v(bv),.rowtx__emb_tx_payload(bd),.px_st(bs),.px_tok(bt),.px_tep(be),.emb_fault(bf),.accepted_start(ba),.accepted_owner_o(bo));
rope_ctx_probe #(.FIX_ROPE_SLOT_GUARD(1),.TOKEN_INDEX_MUT(1),.NATIVE32(1),.PIPE_JOIN(1),.ROPE(1),.ROPE_DELAY(1024),.OVL(0)) mut(`PINS,.rowtx__emb_tx_v(mv),.rowtx__emb_tx_payload(md),.px_st(ms),.px_tok(mt),.px_tep(me),.emb_fault(mf),.accepted_start(ma),.accepted_owner_o(mo));
integer ci=-1,rx=0,total=0,checks=0,cy=0,first_baseline_fault=-1;reg[17:0]tok=0;reg[12:0]pos=0;reg[15:0]epoch=0;
reg core=0,cre=0,sre=0;reg[23:0]ca=0;reg[17:0]sa=0;wire[511:0]cq;wire[15:0]sq;wire qf;
wire hdr=rx==0;wire wrscale=hdr||pd[512];
wire[5:0]wi=hdr?6'd0:(pd[512]?pd[529:524]+6'd1:pd[529:524]);
qfd_embedding_word_provider #(.ROPE(1),.ROPE_FF(1)) qc(.ck(ck),.rst_n(rst_n),.word_v(pv),.word_data(pd[511:0]),.word_token(pd[547:530]),.word_index(wi),.word_scale(wrscale),.word_epoch(epoch),.expected_word_slot(pv),.expected_token(tok),.expected_word(hdr?6'd0:(rx>=65?6'(rx-64):6'(rx-1))),.expected_scale(hdr||rx>=65),.expected_epoch(epoch),.fill_begin(pa),.fill_token(tok),.fill_epoch(epoch),.core_start(core),.core_token(tok),.core_epoch(epoch),.embed_code_re(cre),.embed_code_addr(ca),.embed_code_q(cq),.embed_scale_re(sre),.embed_scale_addr(sa),.embed_scale_q(sq),.fault(qf));
reg[511:0]sweep[0:255],gold[0:31];reg[511:0]seen[0:31];
function automatic[511:0]embword(input[17:0]t,input integer w);
 reg[511:0]v;begin for(integer l=0;l<16;l=l+1)v[32*l+:32]=32'h40000000|(32'(t)<<10)|32'(16*w+l);embword=v;end
endfunction
always@(posedge ck)begin
 cy<=cy+1;
 if(rst_n&&ci>=0&&pv)begin
  if(pd[547:530]!==tok)$fatal(1,"TX_TOKEN");
  if(rx==0)begin if(pd[47:32]!==epoch||pd[15:0]!==16'h3f80)$fatal(1,"TX_HEADER");end
  else if(rx<=64)begin if(pd[529:524]!==6'(rx-1)||pd[511:0]!==embword(tok,rx-1))$fatal(1,"TX_EMBED_DATA rx%0d",rx);end
  else begin if(!pd[512]||pd[529:524]!==6'(rx-65)||pd[511:0]!==gold[ci*8+rx-65])$fatal(1,"TX_ROPE_DATA case%0d rx%0d",ci,rx);end
  rx<=rx+1;total<=total+1;
 end
end
always@(negedge ck)if(ci>=0&&bf&&first_baseline_fault<0)begin first_baseline_fault=cy;$display("AS_FOUND_FAIL terminal_guard65 case%0d rx%0d cy%0d",ci,rx,cy);end

task step;@(negedge ck);endtask
integer waits,k,b;reg[60:0]owner;reg[35:0]header;
initial begin
 $readmemh("rope_sweep.hex",sweep);$readmemh("rope_expected.hex",gold);
 repeat(32)step();rst_n=1;repeat(96)step();
 for(integer c=0;c<4;c=c+1)begin
  ci=c;rx=0;tok=c<2?18'd17:18'd29;pos=c==0?13'd0:(c==3?13'd8:13'd1);epoch=16'h1000+16'(4*c);
  owner={2'd0,epoch,6'd0,tok,pos,6'd0};header={5'd0,4'd12,6'd63,epoch,5'd0};ctx={1'b1,1'b1,header,owner};step();ctx=0;
  waits=0;while(!pa&&waits<32)begin step();waits=waits+1;end
  if(!pa||po!==owner)$fatal(1,"CTX_NOT_ACCEPTED");
  repeat(8)step();
  for(k=0;k<64;k=k+1)begin tv=1;ts=0;tt=tok;te=epoch;ti=6'(k);td=embword(tok,k);step();end
  tv=1;ts=1;ti=0;td=512'h3f80;step();tv=0;ts=0;
  waits=0;while(!ps&&waits<1100)begin step();waits=waits+1;end
  if(!ps||pt!==18'(151936+(pos>>3))||pe!==epoch)$fatal(1,"POSITION_ROW_REQUEST got%0d want%0d",pt,151936+(pos>>3));
  repeat(8)step();
  for(k=0;k<64;k=k+1)begin tv=1;ts=0;tt=18'(151936+(pos>>3));te=epoch;ti=6'(k);td=sweep[64*c+k];step();end
  tv=0;repeat(16)step();
  if(!p.g_rope.u_rowtx.row_ready||pf)$fatal(1,"PRODUCER_NOT_READY fault%b",pf);
  slot=1;repeat(73)step();slot=0;repeat(12)step();
  if(rx!=73||pf||qf)$fatal(1,"ROW_TRANSPORT case%0d count%0d pf%b qf%b",c,rx,pf,qf);
  core=1;step();core=0;repeat(4)step();
  for(b=0;b<8;b=b+1)begin
   ca=24'd9723904+{3'd0,tok,3'd0}+24'(b);cre=1;@(posedge ck);#0.001;
   if(cq!==gold[8*c+b])$fatal(1,"QC_RESIDENT_ROPE case%0d beat%0d",c,b);
   seen[8*c+b]=cq;checks=checks+1;step();cre=0;step();
  end
  if(qf||pf)$fatal(1,"POSITIVE_FAULT");
  $display("REQUEST_PASS token%0d position%0d epoch%0d packets%0d ropewords8",tok,pos,epoch,rx);
  ci=-1;repeat(24)step();
 end
 if(seen[0]===seen[8])$fatal(1,"SAME_TOKEN_DIFFERENT_POS_NOT_DISTINGUISHED");
 for(b=0;b<8;b=b+1)if(seen[8+b]!==seen[16+b])$fatal(1,"SAME_POS_DIFFERENT_TOKEN_CHANGED_ROPE");
 if(!mf||first_baseline_fault<0)$fatal(1,"NEGATIVE_CONTROL_NOT_CAUGHT");
 $display("TOKEN_INDEX_MUTANT_CAUGHT fault%b",mf);$display("AS_FOUND_TERMINAL_GUARD_FAIL_PRESERVED cy%0d",first_baseline_fault);
 $display("ROPE_RESIDENT_BOUNDARY_PASS requests4 packets%0d goldwords%0d same-token-diff-pos same-pos-diff-token",total,checks);$finish;
end
endmodule
