`timescale 1ns/1ps
// Installed two-home-stack aperture. All units explicitly documented:
// stack inputs GLOBAL32B sectors; PC bounds LOCAL32B atoms, exclusive.
// Producer must include every deployed mutable key/window/CKV region in rsv.
// Never derive usable capacity from address width. No config defaults.
module ot_s81_engram_aperture #(parameter integer ENABLE=0)(
 input wire ck,rst_n,
 input wire stack_v,stack_sel,input wire[29:0] usable,rsv,plain,yarn,span,
 input wire pc_v,input wire[5:0] pc,input wire[29:0] base,limit,
 input wire commit,
 output wire aperture_valid,output wire[1919:0] pc_base,pc_limit,
 output wire corrected,output reg fault
);
 reg[215:0] smem[0:1];reg[71:0] pmem[0:63];reg[1:0] sv;reg[63:0] pv;
 reg sv_par,pv_par,locked;
 wire[215:0] senc;wire[71:0] penc;
 wire[191:0] ss={42'b0,span,yarn,plain,rsv,usable};
 ot_s81_secded_enc72 se0(ss[63:0],senc[71:0]);
 ot_s81_secded_enc72 se1(ss[127:64],senc[143:72]);
 ot_s81_secded_enc72 se2(ss[191:128],senc[215:144]);
 ot_s81_secded_enc72 pe({4'b0,limit,base},penc);
 wire[191:0] sd[0:1];wire[63:0] pd[0:63];wire[5:0] sce,sue;wire[63:0] pce,pue;
 genvar s,p,k;
 generate for(s=0;s<2;s=s+1)begin:gs
  for(k=0;k<3;k=k+1)begin:gk
   ot_s81_secded_dec72 dec(smem[s][72*k+:72],sd[s][64*k+:64],sce[3*s+k],sue[3*s+k]);
  end
 end
 for(p=0;p<64;p=p+1)begin:gp
  ot_s81_secded_dec72 dec(pmem[p],pd[p],pce[p],pue[p]);
  assign pc_base[p*30+:30]=pd[p][29:0];
  assign pc_limit[p*30+:30]=pd[p][59:30];
 end endgenerate
 wire protection_bad=(sv_par!=(^sv))||(pv_par!=(^pv))||(|(pue&pv))||
  (sv[0]&&(|sue[2:0]))||(sv[1]&&(|sue[5:3]));
 reg config_bad;integer i;reg[63:0] cap,rs,pl,ya,sp,b,e;
 always @* begin
  config_bad=0;cap=0;rs=0;pl=0;ya=0;sp=0;b=0;e=0;
  for(i=0;i<64;i=i+1)begin
   cap={34'b0,sd[i/32][29:0]};rs={34'b0,sd[i/32][59:30]};
   pl={34'b0,sd[i/32][89:60]};ya={34'b0,sd[i/32][119:90]};sp={34'b0,sd[i/32][149:120]};
   b={34'b0,pd[i][29:0]};e={34'b0,pd[i][59:30]};
   // Whole128-sector group rounding prevents inverse-address tail aliases.
   if(cap==0||rs==0||sp==0||((rs|pl|ya|sp)&127)!=0||
      pl<rs||ya<rs||pl+sp>cap||ya+sp>cap||
      (pl<ya+sp&&ya<pl+sp)||b>=e||b<rs/32||
      e>(cap/128)*4||e>pl/32||e>ya/32)config_bad=1;
  end
 end
 assign aperture_valid=ENABLE&&locked&&!fault&&!protection_bad&&!config_bad;
 assign corrected=(|(pce&pv))||(sv[0]&&(|sce[2:0]))||(sv[1]&&(|sce[5:3]));
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin sv<=0;pv<=0;sv_par<=0;pv_par<=0;locked<=0;fault<=0;end
  else if(ENABLE)begin
   if(protection_bad)fault<=1;
   if((stack_v||pc_v||commit)&&locked)fault<=1;
   if(!locked&&!fault)begin
    if(stack_v)begin smem[stack_sel]<=senc;sv[stack_sel]<=1;sv_par<=^(sv|(2'b1<<stack_sel));end
    if(pc_v)begin pmem[pc]<=penc;pv[pc]<=1;pv_par<=^(pv|(64'b1<<pc));end
    if(commit)begin
     // Commit is separate from installation: never observe stale final record.
     if(stack_v||pc_v||sv!=3||pv!={64{1'b1}}||config_bad||protection_bad)fault<=1;
     else locked<=1;
    end
   end
  end
 end
endmodule
