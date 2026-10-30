`timescale 1ns/1ps
// DIE-KV-46 2026-10-30: lockstep bench for qkd_host_rx_class_admission FAULT_DREG.
// ref  = origin/main module (renamed qkd_host_rx_class_admission_ref, copied by run.sh)
// d0   = new source FAULT_DREG=0 : every output must equal ref every cycle
// d1   = new source FAULT_DREG=1 : every output except host_d/ing_d/ing_cls must equal ref every
//        cycle; host_d (ing_d,ing_cls) must equal ref whenever host_v (ing_v) is 1; no grant may
//        leave in any cycle after fault was seen (incl. the extra fault_q cycle).
// Random traffic of all classes, random credits/returns/reservation, injected protocol faults and
// overflow faults, periodic resets. Reports FAULT episodes and blocked-grant data-only differences.
module tb;
 parameter integer SEED=1,CYC=400000,STRAPPED=1,IR_REPL=0;
 reg ck=0;always #5 ck=~ck;
 reg rst_n=0,rv=0,reserved=0,valid=1,hcr=0,ccr=0;reg[4:0]icrn=0;reg[527:0]rd=0;reg[2:0]die=0;
`define PORTS(P) .ck(ck),.rst_n(rst_n),.die_id(die),.rx_v(rv),.rx_d(rd),.rx_cr(P``rcr),.native_reserved(reserved),.ownership_valid(valid),\
  .host_v(P``hv),.host_d(P``hd),.host_cr(hcr),.ctrl_v(P``cv),.ctrl_d(P``cd),.ctrl_cr(ccr),.ing_v(P``iv),.ing_cls(P``ic),.ing_d(P``id),.ing_crn(icrn),\
  .credit_return(P``cr),.peer_credit(P``pc),.fault(P``f),.admission_open(P``o),.launch_quiet(P``q),.deferred(P``df)
`define WIRES(P) wire P``rcr,P``hv,P``cv,P``iv,P``f,P``o,P``q,P``df;wire[511:0]P``hd,P``cd,P``id;wire[1:0]P``ic;wire[23:0]P``cr,P``pc;
 `WIRES(r_) `WIRES(a_) `WIRES(b_)
 qkd_host_rx_class_admission_ref #(.STRAPPED(STRAPPED),.IR_REPL(IR_REPL)) ref0(`PORTS(r_));
 qkd_host_rx_class_admission #(.STRAPPED(STRAPPED),.IR_REPL(IR_REPL),.FAULT_DREG(0)) d0(`PORTS(a_));
 qkd_host_rx_class_admission #(.STRAPPED(STRAPPED),.IR_REPL(IR_REPL),.FAULT_DREG(1)) d1(`PORTS(b_));
 wire[1100:0] rctl={r_rcr,r_hv,r_cv,r_iv,r_f,r_o,r_q,r_df,r_cd,r_cr,r_pc};
 wire[1100:0] bctl={b_rcr,b_hv,b_cv,b_iv,b_f,b_o,b_q,b_df,b_cd,b_cr,b_pc};
 integer cyc=0,faults=0,hgr=0,igr=0,ddiff=0,blocked=0,resets=0;reg fseen=0;
 always @(posedge ck)if(rst_n)begin
  #1;
  if({rctl,r_hd,r_id,r_ic}!=={a_rcr,a_hv,a_cv,a_iv,a_f,a_o,a_q,a_df,a_cd,a_cr,a_pc,a_hd,a_id,a_ic})$fatal(1,"D0_MISMATCH cyc %0d",cyc);
  if(rctl!==bctl)$fatal(1,"D1_CTRL_MISMATCH cyc %0d",cyc);
  if(r_hv&&r_hd!==b_hd)$fatal(1,"D1_HOST_DATA cyc %0d",cyc);
  if(r_iv&&{r_ic,r_id}!=={b_ic,b_id})$fatal(1,"D1_ING_DATA cyc %0d",cyc);
  if(fseen&&(b_hv||b_iv))$fatal(1,"D1_GRANT_AFTER_FAULT cyc %0d",cyc);
  if({r_ic,r_id,r_hd}!=={b_ic,b_id,b_hd})ddiff=ddiff+1;
  if(d1.fault&&!d1.fault_q&&(d1.hp_d||d1.ip_d))blocked=blocked+1;
  if(b_hv)hgr=hgr+1;if(b_iv)igr=igr+1;
  if(b_f&&!fseen)faults=faults+1;
  fseen=fseen|b_f;
 end
 integer i,k,seed,cls,hb,cb,ib,hp,cp,ip,inj;
 // board side keeps the receive windows (HOST4/CTRL4/ING16) refilled from credit_return; the
 // downstream returns host/ctrl/ingest credits after random delays. Faults are injected rarely
 // (bad header, bad class, window overrun, downstream credit over-return, wrong-role HOST).
 always @(posedge ck)if(rst_n)begin
  if(r_hv)hp=hp+1; if(r_cv)cp=cp+1; if(r_iv)ip=ip+1;
  hb=hb+r_cr[0]; cb=cb+r_cr[8]; ib=ib+r_cr[20:16];
 end
 initial begin
  seed=SEED;hb=4;cb=4;ib=16;hp=0;cp=0;ip=0;
  for(i=0;i<CYC;i=i+1)begin
   @(negedge ck);cyc=i;
   if(i%5000==0)begin rst_n=0;fseen=0;resets=resets+1;hb=4;cb=4;ib=16;hp=0;cp=0;ip=0;reserved=0;valid=1;die=0;end
   else if(!rst_n)rst_n=1;
   inj=(($random(seed)&8191)==0)?1+(($random(seed)&255)%6):0;
   cls=$unsigned($random(seed))%5; rv=0;
   if(($random(seed)&3)!=0)begin
    if(cls==0&&hb>0)begin rv=1;hb=hb-1;end
    else if(cls==1&&cb>0)begin rv=1;cb=cb-1;end
    else if(cls>=2&&ib>0)begin rv=1;ib=ib-1;end
   end
   rd={4'(cls),12'd0,{16{$random(seed)}}};
   if(inj==1)begin rv=1;rd[523:512]=12'h001;end
   else if(inj==2)begin rv=1;rd[527:524]=4'd9;end
   else if(inj==3)begin rv=1;rd[527:524]=4'd0;end            // HOST without window check
   else if(inj==5)begin rv=1;rd={4'd7,12'd0,488'd0,8'd9,8'd1,8'd1};end
   else if(inj==6)die=3'd1;
   hcr=0;ccr=0;icrn=0;
   if(hp>0&&($random(seed)&1))begin hcr=1;hp=hp-1;end
   if(cp>0&&($random(seed)&1))begin ccr=1;cp=cp-1;end
   if(ip>0&&($random(seed)&1))begin icrn=5'(ip>3?1+($unsigned($random(seed))%3):ip);ip=ip-icrn;end
   if(inj==4)hcr=1;                                            // credit over-return
   if(($random(seed)&511)==0)reserved=~reserved;
  end
  $display("PASS SEED %0d cycles %0d resets %0d fault_episodes %0d host_grants %0d ing_grants %0d blocked_fault_onset_grants %0d data_only_diff_cycles %0d",
           SEED,CYC,resets,faults,hgr,igr,blocked,ddiff);
  $finish;
 end
endmodule
