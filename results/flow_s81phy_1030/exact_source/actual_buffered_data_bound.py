"""Literal proposed noninverting DATA repeater model, with actual mapped source inversion.
No RTL generation, inferred repair, physical qualification or extra cycles.
"""
import json,sys,math
from pathlib import Path
R=Path(__file__).parent;sys.path.insert(0,str(R/'tool_snapshot/tools/die_plan'))
from die_clock_128 import _bilin
LIB=json.load(open(R/'stage_lib.json'))['corners']
def data(c,length,inslew,pol,kind='start',fanout=1,spacing=80,local_um=1.0,native=False):
 lib=LIB[c]['cells'];source='INVx1_ASAP7_75t_R' if kind=='start' else 'INVx3_ASAP7_75t_R';buf='BUFx8_ASAP7_75t_R';end='DFFHQNx1_ASAP7_75t_R' if native else 'DFFLQNx1_ASAP7_75t_R';n=max(1,math.ceil(length/spacing));q='fall' if pol=='rise' else 'rise';slew=inslew;total=0.;mx=0.;receipts=[]
 # Source INV drives one dedicated first buffer per outgoing edge; raw kept
 # BUF2 receiver is an additional genuine mapped local load, not imaginary.
 own=lib[buf]['cap_ff']*fanout+(lib['BUFx2_ASAP7_75t_R']['cap_ff'] if kind=='raw' else 0.)
 steps=[('DFFHQNx1_ASAP7_75t_R',local_um,lib[source]['cap_ff'],pol), (source,fanout*3.0,own,q)]
 steps += [(buf,length/n,lib[end if i==n-1 else buf]['cap_ff'],q) for i in range(n)]
 for cell,wire,cap,p in steps:
  cw=wire*.187*1.7;rw=wire*.0125096;el=rw*(cw/2+cap)
  d=_bilin(lib[cell]['cell_'+p],slew,cw+cap);s=_bilin(lib[cell][p+'_transition'],slew,cw+cap)
  total+=d+el;slew=math.hypot(s,2.2*el);mx=max(mx,slew);receipts.append(dict(master=cell,wire_um=wire,load_ff=cw+cap,delay_ps=d+el,slew_ps=slew))
 return total,mx,receipts
rows=[]
for kind in ['start','raw']:
 for fanout in [1,2,3,4]:
  for spacing in [50,65,80,100]:
   for length in [50,100,200,300,405]:
    corners={}
    for c in ['TT','FF']:
     vals=[data(c,length,s,p,kind,fanout,spacing) for s in [5,80] for p in ['rise','fall']]
     corners[c]=dict(delay_ps=[min(z[0] for z in vals)*.95,max(z[0] for z in vals)*1.1011],max_slew_ps=max(z[1] for z in vals),buffer_count=max(1,math.ceil(length/spacing)),worst_path=max(vals,key=lambda z:z[1])[2])
    rows.append(dict(kind=kind,fanout=fanout,max_segment_um=spacing,wire_um=length,corners=corners,slew80=all(z['max_slew_ps']<=80 for z in corners.values())))
out=dict(scope='PROPOSED literal source DFFHQN QN→actual INV1 START/INV3 RAW→dedicated BUF8 per fanout→<=spacing BUF8→DFF D. Both-corner NLDM, actual mapped kept RAW BUF2 input load, local placement bound1um+1um, stock M6/7 maxRC+1.7coupling. No cycles added. Sites/RTL/completeCA NOT qualified.',rows=rows,build_allowed=False)
(R/'actual_buffered_data.json').write_text(json.dumps(out,indent=1)+'\n')
for f in [1,2,3,4]:
 good=[r for r in rows if r['kind']=='start' and r['fanout']==f and r['slew80']];print('STARTfanout',f,'qualifiedmaxspacing',max((r['max_segment_um'] for r in good),default=None))
