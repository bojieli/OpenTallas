#!/usr/bin/env python3
"""Die assignment for native READ_STAGE1 HC return strips, from actual neighbors.
Per-column registered-control aliases avoid the unrouteable single-pin broadcast.
External rd_in/tid/last ingress ownership remains an explicit parent audit.
"""
import json
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
OUT=R/'physical/s81_die_pins/v20_hc_return'
H=751.68

def leaf(kind):return V.lef_bits(f'physical/ref_tile/s81hc_{kind}_ref/views/ot_s81_hc_{kind}/ot_s81_hc_{kind}.lef')[1]
def main():
 OUT.mkdir(exist_ok=True);ln=[leaf('ctnl_l'+str(i)) for i in range(4)];rn=leaf('ctrn');cp=leaf('ctpl')
 cap=json.loads((R/'physical/s81_die_pins/v20_hc_capture/ot_s81_hc_ctfx_cap.json').read_text())['ports']
 records=[]
 for kind,offset in [('ctra',321.84),('ctrb',343.44)]:
  pp={};neighbors=[];sw=H-offset-21.6
  def add(p,n,face,xy=None,layer='M5'):
   pp[p]=[[face,layer,round(xy(i) if xy else 3.036+.096*i,3),.192] for i in range(n)]
  def join(p,b,tag,x,y):neighbors.append((p,b,tag,x,y))
  # Registered local capture control is immediately south of the strips.
  for p,src,n in [('fv','fv_local',7),('fdx','fdx_local',104)]:
   add(p,n,'S',lambda i:cap[src]['per_bit'][i][2], 'M3')
   for i in range(n):join(p,i,'ctfx_cap.'+src,cap[src]['per_bit'][i][2],H-365.04-25.92+.042)
  # Align both return-slot halves to the actual north return transport pins.
  add('rv_in',8,'S',lambda i:rn['rv_out'][i][2])
  if kind=='ctra':
   add('rd_in',1132,'S',lambda i:rn['rd_out'][i][2]);add('rvm',8,'N',lambda i:rn['rvm'][i][2])
   add('rdm',1132,'N',lambda i:rn['rdm'][i][2])
   for p,n,rp in [('rvm',8,'rvm'),('rdm',1132,'rdm')]:
    for i in range(n):join(p,i,'ctrn.'+rp,rn[rp][i][2],H-12.96+rn[rp][i][3])
  else:
   add('rdh_in',108,'S',lambda i:rn['rd_out'][i][2]);add('rdd_in',1152,'S',lambda i:rn['rd_out'][1004+i][2]);add('rdm',1024,'N',lambda i:rn['rdm'][1132+i][2])
   for i in range(1024):join('rdm',i,'ctrn.rdm',rn['rdm'][1132+i][2],H-12.96+rn['rdm'][1132+i][3])
  # n indexes the two bank rows on one side; l is the physical column.
  for suffix,banks,face in [('n',[0,1],'N'),('s',[2,3],'S')]:
   def hrx(i):
    n,qbit=divmod(i,128);q,b=divmod(qbit,64);col=n%4
    return 144.72*col+ln[col]['hrq'][64*(q+(2 if kind=='ctrb' else 0))+b][2]
   add('hrq_'+suffix,1024,face,hrx)
   add('yb_'+suffix,128,face,lambda i:144.72*((i//16)%4)+ln[(i//16)%4]['yb'][i%16][2])
   for i in range(1024):
    n,qbit=divmod(i,128);q,b=divmod(qbit,64);col=n%4;j=banks[n//4];pin=ln[col]['hrq'][64*(q+(2 if kind=='ctrb' else 0))+b]
    row=[12.96,108.,535.68,630.72][j];join('hrq_'+suffix,i,f'ctnl[{j}][{col}].hrq',144.72*col+pin[2],H-row-95.04+pin[3])
   for i in range(128):
    n,b=divmod(i,16);col=n%4;j=banks[n//4];pin=ln[col]['yb'][b];row=[12.96,108.,535.68,630.72][j]
    join('yb_'+suffix,i,f'ctnl[{j}][{col}].yb',144.72*col+pin[2],H-row-95.04+pin[3])
   if kind=='ctra':
    add('nflt_'+suffix,8,face,lambda i:144.72*(i%4)+ln[i%4]['flt'][0][2])
    for i in range(8):
     col=i%4;j=banks[i//4];pin=ln[col]['flt'][0];row=[12.96,108.,535.68,630.72][j];join('nflt_'+suffix,i,'ctnl.flt',144.72*col+pin[2],H-row-95.04+pin[3])
    for p,src in [('hnz','hnz_d'),('pflt','pflt_d')]:
     add(p+'_'+suffix,4,face,lambda i:144.72*i+cp[src][0][2])
     for i in range(4):join(p+'_'+suffix,i,'ctpl.'+src,144.72*i+cp[src][0][2],H-([203.04,416.88][suffix=='s'])-118.8+cp[src][0][3])
  if kind=='ctra':
   # One physical source for each column: exact ctnl N control x positions.
   for c in range(4):
    suff='' if c==0 else '_c'+str(c)
    for p,n in [('rq_q',64),('hs_run',1),('hs_c',16)]:
     add(p+suff,n,'N',lambda i:144.72*c+ln[c][p][i][2], 'M3')
     for i in range(n):
      for j,row in enumerate([12.96,108.,535.68,630.72]):
       pin=ln[c][p][i];join(p+suff,i,f'ctnl[{j}][{c}].'+p,144.72*c+pin[2],H-row-95.04+pin[3])
   add('cs',128,'E',lambda i:4.032+.096*i,'M4')
   for i in range(128):
    j,b=divmod(i,32);pin=ln[3]['acc_out'][b];row=[12.96,108.,535.68,630.72][j];join('cs',i,'ctnl.acc_out',434.16+pin[2],H-row-95.04+pin[3])
   add('hov_d',1,'N',lambda i:cp['hov_d'][0][2]);join('hov_d',0,'ctpl[0][0].hov_d',cp['hov_d'][0][2],H-203.04-118.8+cp['hov_d'][0][3])
  add('clk',1,'W',lambda i:4.032,'M4');add('rst_in',1,'N',lambda i:288.012,'M3');add('tid',8,'W',lambda i:6.048+.096*i,'M4');add('last',1,'W',lambda i:7.968,'M4')
  join('rst_in',0,'ctfn.rst_c',.042,344.844)
  V.write(OUT,'ot_s81_hc_'+kind,[576.72,21.6],pp,'clk','actual CLOSED ctnl/ctrn/CPL neighbors; registered per-column control copies; M3 capture/control and M5 return lanes','v20_hc_return',{'clock_entries':{'serial':['clk']},'source':'tools/s81/hc_return_pins.py','params':{'S_RD':2,'S_RT':4,'READ_STAGE':1,'CHAIN_STEP':6},'qualification':'NEW assigned native successor; TT/FF/CTS/reset/pair reach pending; external rd_in/tid/last boundary delivery OPEN'})
  for p,b,tag,x,y in neighbors:
   f,ly,c,dep=pp[p][b];px,py={'N':(c,sw+21.558),'S':(c,sw+.042),'W':(.042,sw+c),'E':(576.678,sw+c)}[f]
   records.append({'master':kind,'port':p,'bit':b,'neighbor':tag,'length_um':round(abs(px-x)+abs(py-y),3)})
 bad=[v for v in records if v['length_um']>500]
 (OUT/'neighbor_geometry.json').write_text(json.dumps({'scope':'actual CLOSED neighbor geometry plus die-assigned capture pins; external ingress not a qualified seam','hops':records,'over500':bad,'max_um':max(v['length_um'] for v in records),'qualification':'geometric audit only; native pair timing/reset/clock still required'},indent=1)+'\n')
 print('RETURN_ASSIGN',len(records),'joins',len(bad),'over500',max(v['length_um'] for v in records),'max_um')
if __name__=='__main__':main()
