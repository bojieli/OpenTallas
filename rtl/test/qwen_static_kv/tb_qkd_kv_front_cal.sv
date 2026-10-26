`timescale 1ns/1ps
// Q-VMWB 2026-10-16: qkd_kv_front_cal against kv_calendar.py (the landing_cal case files): every blk_go edge at
// A + (H0 - 3) + off(8 b) for b < ceil(n / 8) of the K pass then the V pass, A = the HBM edge that sees the start,
// no extra releases, fault 0.  MUT must FAIL.
module tb_qkd_kv_front_cal;
 parameter integer MUT=0;
 reg ck=0; always #0.512 ck=~ck;
 reg rst_n=0, cfg_we=0, kgo=0, vgo=0; reg [7:0] cfg_addr=0; reg [63:0] cfg_data=0; reg [13:0] ctx_t=0;
 wire [3:0] blk_go; wire fault;
 qkd_kv_front_cal #(.MUT(MUT)) dut(.hck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
  .kgo_h(kgo),.vgo_h(vgo),.ctx_t(ctx_t),.blk_go(blk_go),.fault(fault));
 integer cs,ce,cT,ph0,xu,h0,rc,ld,kgo_r,vgo_r,nk,nv,kp0,kg,vp0,vg,fd,i,x,tmp,cyc=0,errors=0,gp=0,tot=0;
 integer sec[0:511],off[0:511],gedge[0:63];
 string f;
 always @(posedge ck)cyc<=cyc+1;
 initial begin
  if(!$value$plusargs("CASE=%s",f))$fatal(1,"+CASE");
  fd=$fopen(f,"r"); if(fd==0)$fatal(1,"no case %0s",f);
  x=$fscanf(fd,"%d %d %d %d %d %d %d %d %d %d %d %d %d %d %d %d",cs,ce,cT,ph0,xu,h0,rc,ld,kgo_r,vgo_r,nk,nv,kp0,kg,vp0,vg);
  for(i=0;i<=nk;i=i+1)begin x=$fscanf(fd,"%d",tmp);sec[i]=tmp;end for(i=0;i<=nk;i=i+1)begin x=$fscanf(fd,"%d",tmp);off[i]=tmp;end
  for(i=0;i<=nv;i=i+1)begin x=$fscanf(fd,"%d",tmp);sec[nk+i]=tmp;end for(i=0;i<=nv;i=i+1)begin x=$fscanf(fd,"%d",tmp);off[nk+i]=tmp;end
  $fclose(fd);
  // HBM edges (vgo shortly after the K pass's last release)
  kgo_r=40+(kgo_r%200); vgo_r=kgo_r+h0+16+off[nk>0?nk-1:0]+(vgo_r%30);
  for(i=0;i<(nk+7)/8;i=i+1)begin gedge[tot]=kgo_r+h0-3+off[8*i]; tot=tot+1; end
  for(i=0;i<(nv+7)/8;i=i+1)begin gedge[tot]=vgo_r+h0-3+off[nk+8*i]; tot=tot+1; end
  repeat(4)@(negedge ck); rst_n=1;
  @(negedge ck); cfg_we=1; cfg_addr=0; cfg_data={cs[1:0],ce[2:0]};
  @(negedge ck); cfg_addr=2; cfg_data=h0;
  @(negedge ck); cfg_addr=4; cfg_data={kg[3:0],kp0[8:0]};
  @(negedge ck); cfg_addr=5; cfg_data={vg[3:0],vp0[8:0]};
  @(negedge ck); cfg_we=0; ctx_t=14'(cT);
  while(cyc!=kgo_r-2)@(negedge ck);        // kgo_q at edge kgo_r-1, seen (A) at edge kgo_r
  kgo=1; @(negedge ck); kgo=0; ctx_t=14'h3fff;
  while(cyc!=vgo_r-2)@(negedge ck);
  vgo=1; @(negedge ck); vgo=0;
  repeat(3000)@(negedge ck);
  if(gp!=tot)begin $display("COUNT %0d of %0d",gp,tot);errors=errors+1;end
  if(fault)begin $display("FAULT");errors=errors+1;end
  $display("%s front_cal s%0d e%0d T%0d nk%0d nv%0d blocks%0d errors %0d",errors==0?"PASS":"FAIL",cs,ce,cT,nk,nv,tot,errors);
  $finish;
 end
 // blk_go register set on edge A + G0 + off: seen at the following negedge with cyc = that edge
 always @(negedge ck)begin
  #0.01;
  if(blk_go!==4'h0&&blk_go!==4'hf)begin $display("split");errors=errors+1;end
  if(blk_go[0])begin
   if(gp>=tot||cyc!=gedge[gp])begin if(errors<6)$display("GO c%0d want c%0d (#%0d)",cyc,gp<tot?gedge[gp]:-1,gp);errors=errors+1;end
   gp=gp+1;
  end else if(gp<tot&&cyc==gedge[gp])begin if(errors<6)$display("GO missing #%0d c%0d",gp,cyc);errors=errors+1;gp=gp+1;end
 end
endmodule
