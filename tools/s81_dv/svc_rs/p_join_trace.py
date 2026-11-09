#!/usr/bin/env python3
"""Replay exact dated native E rows through the actual P join; ATT/SM trace doubles are bench-only.
GO parent-consume anchor1448/2489 is source-derived from imageGO1426/2467 +6 +Wentrygd16,
and checked against first rootP1798 and second POunderflow2897. This is not a live-GO measurement.
Usage: python3 -I p_join_trace.py FAILED_H8_IMAGE OUTDIR (from repo root).
"""
from pathlib import Path
import sys,json
R=Path.cwd();O=Path(sys.argv[2]).resolve();O.mkdir(parents=True,exist_ok=True)
I=Path(sys.argv[1]).resolve()
meta=json.loads((I/'image.json').read_text())
assert (meta['frames']['GO'],meta['frames']['GO.1'],meta['pio'],meta['po'],meta['pvo'])==(1426,2467,297,407,517), 'replay calendar is pinned to collected productionT128 image'
assert len((I/'pexp_p0.hex').read_text().splitlines())==33
# Preserve provider dates and actual full-precision E rows. Global head is the low4 address bits.
rows=[[] for _ in range(16)]
for l in (I/'ls_dump_h8_s1.txt').read_text().splitlines():
 a=l.split()
 if a[0]=='W' and a[5]=='ffff':
  sid,c=int(a[1]),int(a[2]);addr=int(a[4],16);head=addr%16
  rows[head].append((c,int(a[6],16)))
for h,rr in enumerate(rows):
 assert len(rr)==8,(h,len(rr))
 (O/f'w{h}.hex').write_text(''.join(f'@{c:x}\n{(1<<512)|d:0129x}\n' for c,d in rr))
for n in ['pexp_p0.hex','pexp_p1.hex']:(O/n).write_bytes((I/n).read_bytes())
s=(R/'rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv').read_text();s=s[s.index('module dsdv_svc_att #'):];s=s[:s.index('\n);')+4]
s+='''
`include "dsdv_svc_sx_roles_h8.svh"
integer c=0;always@(posedge clk)c<=c+1;
wire[15:0]g0=16'(1448+sx_role_off(int'(sid))),g1=g0+1041;
wire second=c>=int'(g1);wire[15:0]jc=16'(c)-(second?g1:g0);
assign go_o=c==int'(g0)||c==int'(g1);
assign jc_o=(c>=int'(g0))?jc:16'd0;
assign hb_o=second;assign pio_o=297;assign pvo_o=517;assign st_o=0;assign allq_o=1;
assign tjob_o=128;assign tagj=0;assign done=0;assign qrq=0;
assign l_v=0;assign l_d=0;assign pv_ov=0;assign pv_od=0;
assign sm_st=((c==int'(g0)-8)&&(tile<8))||((c==int'(g1)-8)&&(tile>=8));
assign sm_kind=4;assign sm_jid=1;assign sm_rv=0;assign sm_rp=0;assign sm_rj=0;assign sm_rd=0;
assign hcr=0;assign hack=0;
integer pw=0,pr=0,left=0,ql=0,typ=0,ph=-1,wi=0,err=0,under=0,first[0:1],last[0:1];
reg[511:0]expect0[0:32],expect1[0:32];string dir;
initial begin
 if(!$value$plusargs("dir=%s",dir))$fatal(1,"dir required");
 $readmemh({dir,"/pexp_p0.hex"},expect0);$readmemh({dir,"/pexp_p1.hex"},expect1);
 first[0]=-1;first[1]=-1;last[0]=-1;last[1]=-1;
end
wire ef=(left>0)&&(c>=int'(g0))&&(jc>=407)&&(jc[0]==1'b1);
assign fault=err!=0||under!=0;assign fault_code={11'd0,under!=0,20'd0};
always@(posedge clk)begin
 if(go_o)left<=32;
 else if(ef)begin if(pw-pr<2)under++;pr<=pr+2;left<=left-2;end
 if(q_v)begin
  if(ql==0)begin
   typ=int'(q_d[511:508]);ql=int'(q_d[491:480]);
   if(typ==5)begin ph++;wi=0;if(ph>1)err++;end
  end else begin
   ql--;
   if(typ==5)begin
    if(first[ph]<0)first[ph]=c;last[ph]=c;
    if(q_d!==(ph==0?expect0[wi+1]:expect1[wi+1]))err++;
    wi++;pw<=pw+1;
   end
  end
 end
 if(c==3300)begin
  $display("JOIN sid%0d ph%0d words%0d consumed%0d errors%0d under%0d first%0d/%0d last%0d/%0d go%0d/%0d",sid,ph,pw,pr,err,under,first[0],first[1],last[0],last[1],g0,g1);
  if(ph==1&&pw==64&&pr==64&&err==0&&under==0)$display("JOIN_PASS sid%0d",sid);else $display("JOIN_FAIL sid%0d",sid);
 end
end
endmodule
'''
(O/'att_trace.sv').write_text(s)
(O/'sms_trace.sv').write_text('''module ot_s81_su_sms_fold2(
input wire clk,rst_in,input wire[3:0]cfg_g,input wire j_st,input wire[3:0]j_kind,input wire[7:0]j_jid,
input wire r_v,r_p,input wire[2:0]r_j,input wire[511:0]r_d,
output wire w_v,output wire[13:0]w_a,output wire[15:0]w_m,output wire[511:0]w_d,
output wire o_fu,o_fo,o_alive,o_den,output wire[7:0]o_rjid);
integer c=0,late=0;always@(posedge clk)c<=c+1;
reg[512:0]a[0:3399];integer k;string dir,name;
initial begin for(k=0;k<3400;k++)a[k]=0;void'($value$plusargs("late=%d",late));end
always@(posedge clk)if(c==100)begin
 if(!$value$plusargs("dir=%s",dir))$fatal;name=$sformatf("%s/w%0d.hex",dir,cfg_g);$readmemh(name,a);
end
wire[512:0]row=(c>=late&&c-late<3400)?a[c-late]:513'd0;
assign w_v=row[512];assign w_d=row[511:0];assign w_a={10'd0,cfg_g};assign w_m=16'hffff;
assign o_fu=0;assign o_fo=0;assign o_alive=1;assign o_den=0;assign o_rjid=1;
endmodule
''')
# Build the original mesh wiring. Only attention+SM providers are explicit trace doubles.
tb='''module tb_join;
reg ck=0,rst=0;always #0.5 ck=~ck;integer c=0;always@(posedge ck)begin c<=c+1;if(c==3)rst<=1;if(c==3400)$finish;end
localparam W=1076,SW=1076,DW=805,UW=16;
wire[3:0]gi_v[0:15],go_v[0:15],si_v[0:15],so_v[0:15];
wire[4*W-1:0]gi_d[0:15],go_d[0:15];wire[4*SW-1:0]si_d[0:15],so_d[0:15];
wire[4*DW-1:0]dn_i[0:15],dn_o[0:15];wire[4*UW-1:0]up_i[0:15],up_o[0:15];wire[4*514-1:0]ri[0:15],ro[0:15];
wire[1622:0]obs[0:15];
function automatic integer nb(input integer sd,fc);integer r,c;begin r=sd%2;c=sd/2;case(fc)
0:nb=r==0?2*c+1:-1;1:nb=c<7?2*(c+1)+r:-1;2:nb=r==1?2*c:-1;default:nb=c>0?2*(c-1)+r:-1;endcase end endfunction
genvar gs,gf;generate for(gs=0;gs<16;gs++)begin:g_s
for(gf=0;gf<4;gf++)begin:g_f
localparam integer NBS=nb(gs,gf),OF=(gf+2)%4;
if(NBS>=0)begin
assign gi_v[gs][gf]=go_v[NBS][OF];assign gi_d[gs][W*gf+:W]=go_d[NBS][W*OF+:W];
assign si_v[gs][gf]=so_v[NBS][OF];assign si_d[gs][SW*gf+:SW]=so_d[NBS][SW*OF+:SW];
assign dn_i[gs][DW*gf+:DW]=dn_o[NBS][DW*OF+:DW];assign up_i[gs][UW*gf+:UW]=up_o[NBS][UW*OF+:UW];
assign ri[gs][514*gf+:514]=ro[NBS][514*OF+:514];
end else begin
assign gi_v[gs][gf]=0;assign gi_d[gs][W*gf+:W]=0;assign si_v[gs][gf]=0;assign si_d[gs][SW*gf+:SW]=0;
assign dn_i[gs][DW*gf+:DW]=0;assign up_i[gs][UW*gf+:UW]=0;assign ri[gs][514*gf+:514]=0;
end end
'''
ports='''(.ck(ck),.rst(rst),.sid(4'(gs)),.j(33'd0),.q(515'd0),.hw(292'd0),
.dn_i(dn_i[gs]),.dn_o(dn_o[gs]),.up_i(up_i[gs]),.up_o(up_o[gs]),.ri(ri[gs]),.ro(ro[gs]),
.gi_v(gi_v[gs]),.gi_d(gi_d[gs]),.go_v(go_v[gs]),.go_d(go_d[gs]),.si_v(si_v[gs]),.si_d(si_d[gs]),.so_v(so_v[gs]),.so_d(so_d[gs]),
.rk(2'd0),.wd(2'd0),.rv(2'd0),.r_data(512'd0),.r_tag(34'd0),.r_beat(8'd0),.hs(2'd0),.obs(obs[gs]));
'''
tb+='if(gs==5||gs==11)begin rsc1_pl u'+ports+'end else begin rsc0_pl u'+ports+'end\n'
tb+='always@(posedge ck)if(c==3301)$display("JOIN_LOCAL sid%0d lf%0d fc%08x",gs,obs[gs][0],obs[gs][32:1]);\nend endgenerate\nendmodule\n'
(O/'tb_join.sv').write_text(tb)
print(O)
