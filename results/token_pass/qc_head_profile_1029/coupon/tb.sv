module tb;
 reg[3:0]txs=0,tk=0;reg emb_act=0,ev_stage=0;reg[6:0]emb_k=0;reg[5:0]ta=0;
 wire h,r,l;integer m=0,n,heads=0,rope=0,layers=0;
 parameter integer MUT=0;
 d #(.HEAD_CONTEXT(MUT==1?0:1),.ROPE(MUT==2?0:1),.L_CONTEXTS(MUT==3?0:1)) u(
 .txs(txs),.tk(tk),.emb_act(emb_act),.emb_k(emb_k),.ev_stage(ev_stage),.ta(ta),
 .prog_head_context_slot(h),.emb_read(r),.l_context_seg(l));
 initial begin
  for(n=0;n<128;n=n+1)begin
   txs=2;tk=4'(n);emb_act=1;emb_k=7'(n);ev_stage=1;ta=6'(n);
   #1;
   if(h!==(tk==12))$fatal(1,"HEAD_CONTEXT missing callback");
   if(r!==(n<=64||n>=77))$fatal(1,"ROPE read admission disabled");
   if(l!==(ta>=2&&ta<=36))$fatal(1,"L_CONTEXTS wrong layer programme segment");
   if(h)heads=heads+1;
   if(r&&n>=77&&n<=84)rope=rope+1;
   if(l&&n<64)layers=layers+1;
  end
  if(rope!=8||layers!=35||heads!=8)$fatal(1,"missing full shape source controls");
  $display("PASS coherent_source_controls HEAD_callbacks%0d ROPE_words%0d L1_layers%0d",heads,rope,layers);$finish;
 end
endmodule
