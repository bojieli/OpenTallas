`timescale 1ns/1ps
// Q-VMWB 2026-10-16: qkd_kv_landing_cal against the compiler model.  The case file (tools/qwen_static_kv/
// landing_cal_golden.py, from kv_calendar.py) gives the group's K and V sector sequences and put offsets at context T
// and random boot constants (PH0 is the elaborated phase, the rest go through the cfg port).  The bench computes, by
// its own integer arithmetic, the core edge of every return-slot pop (first edge >= A + 768 (H0 + off) + 625 RC, A the
// first HBM edge >= kgo/vgo edge + XU) and of every landing put (LD later), and checks each r_put / l_put edge and
// sector exactly, no extra puts, arm one edge after the K start, epoch/layer/ctx, fault 0.  MUT must FAIL.
module tb_qkd_kv_landing_cal;
 parameter integer MUT=0, PH0=0, SAME_CLOCK=0;
 localparam integer HBM_U = SAME_CLOCK ? 625 : 768;
 reg ck=0; always #(SAME_CLOCK ? 0.4165 : 0.416667) ck=~ck;
 reg rst_n=0, cfg_we=0, kgo=0, vgo=0; reg [7:0] cfg_addr=0; reg [63:0] cfg_data=0;
 reg [13:0] ctx_t=0; reg [15:0] epoch=16'd7; reg [5:0] layer=6'd3;
 wire arm,fault; wire [15:0] l_epoch,r_epoch; wire [5:0] l_layer,r_layer; 
 wire [3:0] l_put,r_put; wire [39:0] l_sector,r_sector;
 qkd_kv_landing_cal #(.MUT(MUT),.PH0(PH0),.SAME_CLOCK(SAME_CLOCK)) dut(.ck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .kgo(kgo),.vgo(vgo),.ctx_t(ctx_t),.epoch(epoch),.layer(layer),.arm(arm),.l_epoch(l_epoch),.l_layer(l_layer),
  .l_put(l_put),.l_sector(l_sector),.r_put(r_put),.r_sector(r_sector),.r_epoch(r_epoch),.r_layer(r_layer),.fault(fault));
 integer cs,ce,cT,ph0,xu,h0,rc,ld,kgo_r,vgo_r,nk,nv,kp0,kg,vp0,vg,fd,i,x,cyc=0,E0=-1,tmp,errors=0,rp=0,lp=0,tot,armed_at=-1;
 integer sec[0:511],off[0:511],redge[0:511];
 string f;
 longint A,P,base;
 function automatic integer first_hbm_at_or_after(input longint t);   // HBM edges at 625 E0 + PH0 + 768 m
  longint m; begin m=(t-(625*E0+ph0)+HBM_U-1)/HBM_U; if(t-(625*E0+ph0)<=0) m=0; first_hbm_at_or_after=0; A=625*E0+ph0+HBM_U*m; end
 endfunction
 task automatic sched(input integer k0, input integer first, input integer cnt);
  integer j,dummy; longint num;
  begin
   dummy=first_hbm_at_or_after(625*longint'(k0)+xu);
   for(j=0;j<cnt;j=j+1)begin
    P=A+HBM_U*(h0+off[first+j]);
    num=P+625-1; redge[first+j]=int'(num/625)+rc;
   end
  end
 endtask
 always @(posedge ck)cyc<=cyc+1;                 // index of the last posedge, stable at every negedge
 always @(negedge ck)if(E0<0 && dut.rn)E0=cyc+1;   // the next posedge is the first that sees rn = 1
 initial begin
  if(!$value$plusargs("CASE=%s",f))$fatal(1,"+CASE");
  fd=$fopen(f,"r"); if(fd==0)$fatal(1,"no case %0s",f);
  x=$fscanf(fd,"%d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d",cs,ce,cT,ph0,xu,h0,rc,ld,kgo_r,vgo_r,nk,nv,kp0,kg,vp0,vg);
  if(ph0!=PH0)$fatal(1,"case PH0 %0d != elaborated %0d",ph0,PH0);
  for(i=0;i<=nk;i=i+1)begin x=$fscanf(fd,"%d",tmp);sec[i]=tmp;end for(i=0;i<=nk;i=i+1)begin x=$fscanf(fd,"%d",tmp);off[i]=tmp;end
  for(i=0;i<=nv;i=i+1)begin x=$fscanf(fd,"%d",tmp);sec[nk+i]=tmp;end for(i=0;i<=nv;i=i+1)begin x=$fscanf(fd,"%d",tmp);off[nk+i]=tmp;end
  $fclose(fd); tot=nk+nv;
  repeat(4)@(negedge ck); rst_n=1;
  @(negedge ck); cfg_we=1; cfg_addr=0; cfg_data={cs[1:0],ce[2:0]};
  @(negedge ck); cfg_addr=1; cfg_data=xu;
  @(negedge ck); cfg_addr=2; cfg_data=h0;
  @(negedge ck); cfg_addr=3; cfg_data={ld[3:0],rc[3:0]};
  @(negedge ck); cfg_addr=4; cfg_data={kg[3:0],kp0[8:0]};
  @(negedge ck); cfg_addr=5; cfg_data={vg[3:0],vp0[8:0]};
  @(negedge ck); cfg_we=0;
  ctx_t=14'(cT);
  wait(E0>=0);
  while(cyc!=E0+kgo_r-2)@(negedge ck);       // drive before edge E0+kgo-1 -> kgo_q there -> seen at edge E0+kgo
  kgo=1; sched(E0+kgo_r,0,nk); @(negedge ck); kgo=0; ctx_t=14'h3fff;   // T is latched at kgo
  while(cyc!=E0+vgo_r-2)@(negedge ck);
  vgo=1; sched(E0+vgo_r,nk,nv); @(negedge ck); vgo=0;
  repeat(2000)@(negedge ck);
  if(rp!=tot||lp!=tot)begin $display("COUNT r %0d l %0d of %0d",rp,lp,tot);errors=errors+1;end
  if(armed_at!=E0+kgo_r)begin $display("ARM at %0d want %0d",armed_at,E0+kgo_r);errors=errors+1;end
  if(fault)begin $display("FAULT");errors=errors+1;end
  if(l_epoch!==16'd7||l_layer!==6'd3||r_epoch!==16'd7||r_layer!==6'd3)begin $display("META");errors=errors+1;end
  $display("%s landing_cal s%0d e%0d T%0d nk%0d nv%0d ph0 %0d xu %0d h0 %0d rc %0d ld %0d errors %0d",
   errors==0?"PASS":"FAIL",cs,ce,cT,nk,nv,ph0,xu,h0,rc,ld,errors);
  if(errors!=0)$fatal(1,"landing calendar mismatch");
  $finish;
 end
 // checks at every negedge (after the posedge that updated the outputs; cyc = that edge's index)
 always @(negedge ck)if(E0>=0)begin
  #0.01;
  if(arm&&armed_at<0)armed_at=cyc;
  if(r_put!==4'h0&&r_put!==4'hf)begin $display("r_put split");errors=errors+1;end
  if(r_put[0])begin
   if(rp>=tot||cyc!=redge[rp]||r_sector!=={4{10'(sec[rp])}})begin
    if(errors<6)$display("R put c%0d sector %0d / want c%0d sector %0d (#%0d)",cyc,r_sector[9:0],rp<tot?redge[rp]:-1,rp<tot?sec[rp]:-1,rp);errors=errors+1;end
   rp=rp+1;
  end else if(rp<tot&&cyc==redge[rp])begin if(errors<6)$display("R missing #%0d c%0d",rp,cyc);errors=errors+1;rp=rp+1;end
  if(l_put[0])begin
   if(lp>=tot||cyc!=redge[lp]+ld||l_sector!=={4{10'(sec[lp])}})begin
    if(errors<6)$display("L put c%0d sector %0d / want c%0d (#%0d)",cyc,l_sector[9:0],lp<tot?redge[lp]+ld:-1,lp);errors=errors+1;end
   lp=lp+1;
  end else if(lp<tot&&cyc==redge[lp]+ld)begin if(errors<6)$display("L missing #%0d",lp);errors=errors+1;lp=lp+1;end
 end
endmodule
