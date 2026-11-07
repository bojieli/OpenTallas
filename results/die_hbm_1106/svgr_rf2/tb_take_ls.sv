// DIE-HBM-82-SVGR 11-06: unit lock-step of the ot_svgr_own RF2 take-count path (ot_svgr_split.sv RF2 lines 736-753,
// copied verbatim) against the RF1 form (lines 884-894: count formed from response_accepted/response_bank in the
// accept cycle, registered).  RF2 registers accept+bank and forms the count one edge later, so
// take_q_rf2(t) must equal take_q_rf1(t-1) every cycle.  Random accepts and banks (banks change every cycle).
module tb;
 parameter integer MUT=0, SEED=1, N=200000; localparam integer LB=2, LBANKS=4;
 reg hbm_clk=0, hrst=0; always #5 hbm_clk=~hbm_clk;
 reg [3:0] response_accepted; reg [LB-1:0] response_bank[0:3];
 // ---- RF2 (verbatim) ----
 integer ta,tb;
 reg [3:0] acc_q;reg [LB-1:0] acc_bank_q[0:3];
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)begin acc_q<=0;for(ta=0;ta<4;ta=ta+1)acc_bank_q[ta]<=0;end
  else begin acc_q<=response_accepted;for(ta=0;ta<4;ta=ta+1)acc_bank_q[ta]<=response_bank[ta];end
 end
 reg [2:0] h_take_b[0:LBANKS-1];reg [2:0] take_q[0:LBANKS-1];
 always @*begin
  for(tb=0;tb<LBANKS;tb=tb+1)begin
   h_take_b[tb]=0;
   for(ta=0;ta<4;ta=ta+1)if(acc_q[ta]&&int'((MUT==14)?response_bank[ta]:acc_bank_q[ta])==tb)h_take_b[tb]=h_take_b[tb]+3'd1;
  end
 end
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)begin for(tb=0;tb<LBANKS;tb=tb+1)take_q[tb]<=0;end
  else for(tb=0;tb<LBANKS;tb=tb+1)take_q[tb]<=(MUT==7&&tb==0)?3'd0:h_take_b[tb];
 end
 // ---- RF1 reference (lines 884-894 form) ----
 integer ua,ub;
 reg [2:0] r_take_b[0:LBANKS-1];reg [2:0] r_take_q[0:LBANKS-1];reg [2:0] r_take_d[0:LBANKS-1];
 always @*begin
  for(ub=0;ub<LBANKS;ub=ub+1)begin
   r_take_b[ub]=0;
   for(ua=0;ua<4;ua=ua+1)if(response_accepted[ua]&&int'(response_bank[ua])==ub)r_take_b[ub]=r_take_b[ub]+3'd1;
  end
 end
 always @(posedge hbm_clk or negedge hrst)begin
  if(!hrst)begin for(ub=0;ub<LBANKS;ub=ub+1)begin r_take_q[ub]<=0;r_take_d[ub]<=0;end end
  else for(ub=0;ub<LBANKS;ub=ub+1)begin r_take_q[ub]<=r_take_b[ub];r_take_d[ub]<=r_take_q[ub];end
 end
 integer c,k,mm,s,x,tot; 
 initial begin
  s=SEED; x=$urandom(s); mm=0; tot=0; response_accepted=0; for(k=0;k<4;k=k+1)response_bank[k]=0;
  repeat(3)@(negedge hbm_clk); hrst=1;
  for(c=0;c<N;c=c+1)begin
   @(negedge hbm_clk);
   for(k=0;k<LBANKS;k=k+1)if(take_q[k]!==r_take_d[k])mm=mm+1;
   for(k=0;k<LBANKS;k=k+1)tot=tot+take_q[k];
   response_accepted=$urandom; for(k=0;k<4;k=k+1)response_bank[k]=$urandom;
  end
  $display("TAKE_LS MUT=%0d SEED=%0d cycles=%0d takes=%0d mismatches=%0d %s",MUT,SEED,N,tot,mm,mm==0?"PASS":"FAIL");
  $finish;
 end
endmodule
