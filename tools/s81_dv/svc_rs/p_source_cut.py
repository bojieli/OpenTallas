#!/usr/bin/env python3
"""Extract the actual production P producer for a small GO/two-pass control bench."""
from pathlib import Path
import sys
src=Path('rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs.sv').read_text()
module=src[src.index('module dsdv_svc_p_source #'):]
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
if len(sys.argv)>2 and sys.argv[2]=='mut':
 module=module.replace('assign fire=pon &&','assign fire=pon && hsel &&')
(out/'producer.sv').write_text(module)
(out/'tb.sv').write_text('''module tb;
localparam H=8,LW=1076;
reg ck=0;always #5 ck=~ck;
reg go=0,hb_h=0,hb_p=0;reg[15:0]jc=0;reg[7:0]pk=0;
wire[15:0]fire,missing;wire[LW-1:0]beat[0:15];reg[15:0]pl_v=0;reg[LW-1:0]pl_d[0:15];
wire[15:0]hsel;
genvar g;
generate for(g=0;g<16;g=g+1)begin
 assign hsel[g]=(g/8)==hb_p;
 wire[15:0]val=16'h3f80+16'(g)+16'(pk/4);
 dsdv_svc_p_source u(.pon(1'b1),.hsel(hsel[g]),.pk(pk),.tile(4'(g)),.tjob(10'd128),
 .jcs(jc),.pio(16'd20),.prw({16{val}}),.rows_ready(hsel[g]&&pk!=3?6'd8:6'd0),.fire(fire[g]),.missing(missing[g]),.beat(beat[g]));
 always@(posedge ck)begin pl_v[g]<=fire[g];pl_d[g]<=beat[g];end
end endgenerate
// Same register/counter equations as the production parent; no extra stages.
always@(posedge ck)begin
 jc<=go?16'd1:jc+1'b1;
 if(go)begin pk<=0;hb_p<=hb_h;end else if(fire[0])pk<=pk+1'b1;
end
integer cyc,hd,r,errs=0,n=0;reg expv;reg[15:0]ms,em;reg[LW-1:0]exp[0:15];
initial begin
 for(cyc=0;cyc<205;cyc=cyc+1)begin
  @(negedge ck);go=(cyc==2||cyc==104);if(cyc==103)hb_h=1;
  @(posedge ck);
  expv=jc>=20&&jc<84&&jc[0]==0;ms=missing;
  for(hd=0;hd<16;hd=hd+1)em[hd]=expv&&(hd/8==hb_p)&&pk==3;
  for(hd=0;hd<16;hd=hd+1)begin
   exp[hd]='0;exp[hd][LW-1-:16]=16'(4*pk);
   for(r=0;r<4;r=r+1)begin
    exp[hd][LW-20+r]=1;
    exp[hd][4*H+(H*r+hd%H)*32+:32]=(hd/8==hb_p)?{16'(16'h3f80+hd+pk/4),16'd0}:32'd0;
   end
  end
  #1;
  for(hd=0;hd<16;hd=hd+1)begin
   if(pl_v[hd]!==expv || ms[hd]!==em[hd])errs++;
   if(expv)begin n++;if(pl_d[hd]!==exp[hd])errs++;end
  end
 end
 $display("P_SOURCE cases=%0d errors=%0d",n,errs);
 if(n==1024&&errs==0)$display("P_SOURCE PASS");else $display("P_SOURCE FAIL");
 $finish;
end
endmodule
''')
