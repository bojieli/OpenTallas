`timescale 1ns/1ps
module tb_ccf_bankpipe;
 // EXTRA (HC-COMB 2026-10-16): the candidate's uniform public shift; 2 = PINREG 0 source, 3 = PINREG 1 (all leaf pins registered)
 parameter integer EXTRA = 2;
 localparam FVW=7,FSW=1128,FDW=2920,YS=2560;
 reg ck=0; always #0.5 ck=~ck;
 reg rst=0;reg[FVW-1:0]fv=0;reg[FSW-1:0]fd=0;reg yv=0;reg[YS-1:0]yd=0;
 wire ro,rn,fo,fn;wire[FVW-1:0]vo,vn;wire[FDW-1:0]do_,dn;
 reg[6:0] allow_roots=7'b1111111;wire[4:0]bc={5{ck}}&allow_roots[6:2];
 wire ckn=ck&allow_roots[0],cks=ck&allow_roots[1];
 integer mode=0,seed=1,faultcase=0,cycle=0,k,checks=0,errors=0,tag,cclass,old_fault_seen=0,new_fault_seen=0,old_first_fault=-1,new_first_fault=-1;
 reg[FDW+FVW+1:0] hist[0:3];
 wire[FDW+FVW+1:0] older=hist[EXTRA-1];
 integer samples_old[0:5],samples_new[0:5],lat_old[0:5],lat_new[0:5];
 reg[31:0] prng=32'h715ac3d9;
 function automatic[31:0]next_rand(input[31:0]x);
  reg[31:0]r;begin r=x^(x<<13);r=r^(r>>17);next_rand=r^(r<<5);end
 endfunction
 ot_s81_hc_ccf #(.HALF(1),.RLY(2),.RF(5),.DW(6),.FIFO_SLICE(512),.KEEP_POP(1),.Y_RELAY(1)) old_dut(
  .sk(ck),.srs(rst),.fv_i(fv),.fd_i(fd),.n_yacc(yv),.n_y(yd),.ch_rst(ro),.ch_fv(vo),.ch_fd(do_),.yfl(fo));
 ot_s81_hc_ccf_bankpipe #(.HALF(1),.RLY(2),.RF(5),.DW(6),.FIFO_SLICE(512),.KEEP_POP(1),.Y_RELAY(1),.PINREG(EXTRA==3)) dut(
  .sk_n(ckn),.sk_s(cks),.bank_ck(bc),.srs(rst),.fv_i(fv),.fd_i(fd),.n_yacc(yv),.n_y(yd),.ch_rst(rn),.ch_fv(vn),.ch_fd(dn),.yfl(fn));
 initial begin
  if($value$plusargs("MODE=%d",mode))begin end
  if($value$plusargs("SEED=%d",seed))begin end
  if($value$plusargs("FAULTCASE=%d",faultcase))begin end
  prng=32'h715ac3d9^seed;
  for(k=0;k<4;k=k+1)hist[k]=0;
  for(k=0;k<6;k=k+1)begin samples_old[k]=0;samples_new[k]=0;lat_old[k]=0;lat_new[k]=0;end
  for(cycle=0;cycle<2400;cycle=cycle+1)begin
   @(negedge ck);
   rst=(cycle>=12 && !(cycle>=1200&&cycle<1212));
   fv=0;yv=0;fd=0;yd=0;
   for(k=0;k<FSW;k=k+32)begin prng=next_rand(prng);fd[k+:8]=prng[7:0];end
   for(k=0;k<YS;k=k+32)begin prng=next_rand(prng);yd[k+:32]=prng;end
   fd[20:5]=cycle;
   if(cycle>=40&&cycle<56)yv=1;
   if(cycle>=80&&cycle<96)fv[2]=1;
   if(cycle>=128&&cycle<144)begin fv[1:0]=3;fd[1:0]=0;end // HLOAD
   if(cycle>=160&&cycle<176)begin fv[1:0]=3;fd[1:0]=2;end // COEF
   if(cycle>=192&&cycle<208)begin fv[1:0]=3;fd[1:0]=1;end // GAIN
   if(cycle>=224&&cycle<240)fv[3]=1; // NORM-go
   if(cycle>=256&&cycle<272)fv[6]=1; // HSTORE
   if(cycle>=300)begin prng=next_rand(prng);fv=prng[6:0];yv=prng[7];end
   if(faultcase!=0)begin
    fv=0;yv=0;
    if(faultcase==1 && cycle==80)fv[2]=1; // genuine FIFO underflow
    if(faultcase==2 && cycle>=40 && cycle<180)yv=1; // genuine overflow
    if(faultcase==3)begin
     if(cycle>=40&&cycle<56)yv=1; // safe count, isolate real bank-overflow input term
     if(cycle==100)force old_dut.yf_ovf=1'b1;
     if(cycle==101)force dut.g_bank[0].u_b.u_h0.ovf=1'b1;
     if(cycle==104)release old_dut.yf_ovf;
     if(cycle==105)release dut.g_bank[0].u_b.u_h0.ovf;
    end
    if(faultcase==4)begin
     if(cycle>=40&&cycle<56)yv=1;
     if(cycle==80)fv[2]=1;
     if(cycle==80)force old_dut.yf_hv=1'b0;
     if(cycle==82)force dut.valid[0]=1'b0;
     if(cycle==84)release old_dut.yf_hv;
     if(cycle==86)release dut.valid[0];
    end
    if(faultcase==5 && cycle==2350)fv[2]=1; // fresh post-reset fault near final component-output window
   end
   if(mode>=1&&mode<=7&&cycle==64)allow_roots[mode-1]=0;
   @(posedge ck);#0.001;
   if(cycle>20)begin
    checks=checks+1;
    if(fo===1'b1)begin old_fault_seen=1;if(old_first_fault<0)old_first_fault=cycle;end
    if(fn===1'b1)begin new_fault_seen=1;if(new_first_fault<0)new_first_fault=cycle;end
    if({rn,vn,dn,fn} !== older)begin
     errors=errors+1;
     if(errors<4)$display("CCF_DIFF cycle=%0d mode=%0d reset=%0b fvnew=%h fvexpected=%h",cycle,mode,rn,vn,older[FDW+FVW:FDW+1]);
    end
   end
   if(mode==0 && faultcase==0)begin
    for(k=0;k<2;k=k+1)begin
     tag=k==0 ? do_[20:5] : dn[20:5];cclass=-1;
     if(tag>=128&&tag<144)cclass=0;
     if(tag>=160&&tag<176)cclass=1;
     if(tag>=192&&tag<208)cclass=2;
     if(tag>=224&&tag<240)cclass=3;
     if(tag>=80&&tag<96)cclass=4;
     if(tag>=256&&tag<272)cclass=5;
     if(cclass>=0 && ((k==0&&vo!=0)||(k==1&&vn!=0)))begin
      if(k==0)begin samples_old[cclass]=samples_old[cclass]+1;lat_old[cclass]=cycle-tag;end
      else begin samples_new[cclass]=samples_new[cclass]+1;lat_new[cclass]=cycle-tag;end
     end
    end
   end
   for(k=3;k>0;k=k-1)hist[k]=hist[k-1];hist[0]={ro,vo,do_,fo};
  end
  if(errors!=0)$fatal(1,"CCF_BANKPIPE_FAIL checks=%0d mismatches=%0d mode=%0d seed=%0d",checks,errors,mode,seed);
  if(faultcase!=0 && (!old_fault_seen || !new_fault_seen))$fatal(1,"CCF_FAULT_NOT_OBSERVED case=%0d old=%0d new=%0d",faultcase,old_fault_seen,new_fault_seen);
  if(faultcase!=0)begin
   if(new_first_fault!=old_first_fault+EXTRA)$fatal(1,"CCF_FIRST_FAULT_PHASE_FAIL case=%0d old=%0d new=%0d",faultcase,old_first_fault,new_first_fault);
   $display("CCF_FIRST_FAULT case=%0d old_edge=%0d new_edge=%0d extra_edges=%0d reset_assert_release_checked=1",faultcase,old_first_fault,new_first_fault,EXTRA);
  end
  if(mode==0 && faultcase==0)for(k=0;k<6;k=k+1)begin
   if(samples_old[k]!=16 || samples_new[k]!=16 || lat_old[k]!=1 || lat_new[k]!=1+EXTRA)
    $fatal(1,"CCF_LATENCY_FAIL class=%0d oldsamples=%0d newsamples=%0d oldedges=%0d newedges=%0d",k,samples_old[k],samples_new[k],lat_old[k],lat_new[k]);
   $display("CCF_BOUNDARY_LATENCY class=%0d old_edges=%0d new_edges=%0d extra_edges=%0d II=1 samples=%0d",k,lat_old[k],lat_new[k],EXTRA,samples_new[k]);
  end
  $display("CCF_BANKPIPE_PASS checks=%0d bits_per_check=%0d output_shift_edges=%0d II=1 mode=%0d seed=%0d",checks,FDW+FVW+2,EXTRA,mode,seed);
  $finish;
 end
endmodule
