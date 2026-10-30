"""Unqualified same-cycle SD DATA FF placement model from exhaustive R52 mapped census."""
import json,re,math,collections,sys
from pathlib import Path
r=Path(__file__).resolve().parent;d=json.load(open(r/'sd_r52_full_mapped_xy_inventory.json'));old=json.load(open(r/'phy_wide_data_ff_rows.json'))['positions'];out={};rows=collections.defaultdict(list);collision=[]
# Real mapped max widths from old matched master dimensions, conservative maximum for new FFs.
widths={}
for s in (r/'geom_sdpg_after/geom.tsv').read_text().splitlines():
 a=s.split('\t')
 if a[0]=='C' and a[2]=='S':widths[a[3]]=max(widths.get(a[3],0),float(a[6])-float(a[4]))
# Reserve all real E control groups plus actual primary tap macro and forwarded-clock access.
blocked=[(635.4,644.76),(644.76,648.54),(652.86,657.72),(797.58,802.44),(817.56,822.42)]
rxys=[]
for g in range(261):
 y=(528.12 if not rxys else rxys[-1]+1.08)
 while any(y<b and y+.27>a for a,b in blocked):y=round(y+.27,8)
 rxys.append(y)
def put(n,x,y,group,bit,slot,source):
 m=next(z['master'] for z in [byname[n]]);w=widths[m]
 x=round(x,6);y=round(y,6)
 assert x>=4.32 and x+w<=1896.48+1e-6 and y>=4.32 and y+.27<=1032.48
 assert abs((x-4.32)/.054-round((x-4.32)/.054))<1e-5
 assert abs((y-4.32)/.27-round((y-4.32)/.27))<1e-5
 for a,b,k in rows[y]:
  if x<b-1e-7 and x+w>a+1e-7:collision.append((n,k))
 rows[y].append((x,x+w,n))
 out[n]={'xy_um':[x,y],'body_um':[w,.27],'group':group,'bit':bit,'slot':slot,'basis':source}
byname={z['instance']:z for z in d}
for n,z in byname.items():
 m=re.search(r'u_tx\.mem\\?\[(\d+)\\?\]\\?\[(\d+)',n)
 if m:
  word,bit=map(int,m.groups());i=bit*8+word
  if i<2300:x=1760.4+(i%76)*1.188;y=17.28+(i//76)*.81;group='TXmem_S4'
  elif i<3426:j=i-2300;x=1877.04+(j%16)*1.188;y=60.48+(j//16)*1.08;group='TXmem_E5'
  else:j=i-3426;x=1877.04+(j%16)*1.188;y=469.8+(j//16)*1.08;group='TXmem_E6'
  put(n,x,y,group,bit,word,'split SAME native primary TX FIFO cells, unchanged cycles')
  continue
 m=re.search(r'p_tx_d\\?\[(\d+)',n)
 if m:
  bit=int(m[1]);y=170.1+.27*bit
  # keep START/status E spine controls clear; columns lie before FDI bank.
  x=1875.906
  put(n,x,y,'TXcapture_PHY',bit,0,'actual same native PHY p_tx capture near fixed macro pins')
  continue
 slot=bit=None
 m=re.search(r'u_rx\.mem\\?\[(\d+)\\?\]\\?\[(\d+)',n)
 if m:word,bit=map(int,m.groups());slot=word+1
 else:
  for pat,sl in [(r'rq_d\\?\[(\d+)',0),(r'c_rx_d\\?\[(\d+)',9),(r'u_bout_o_serdes_W_rx_flit/q\\?\[(\d+)',10)]:
   m=re.search(pat,n)
   if m:bit=int(m[1]);slot=sl;break
 if bit is not None and bit<522:
  put(n,1870.56+(bit%2)*12.474+slot*1.134,rxys[bit//2],'RXwhole',bit,slot,'whole native RX memory/rq/c_rx/boundary FF bit group, no relay/cycle change')
assert not collision,collision[:5]
counts=collections.Counter(x['group'] for x in out.values());assert sum(counts.values())==10440,counts
# No actual placement is changed by this proposal.
report={'physical_qualified':False,'positions':out,'counts':dict(counts),'pairwise_data_ff_overlaps':len(collision),'RX_y_span':[min(rxys),max(rxys)],'actual_mapped_names':True,'unchanged_RTL_cycles_pins_taps':True,'pending':['RX two scalar boundary FFs + all remaining actual control/logic cells','control/spine obstruction check beyond listed E reserved rows','clock reset actuallegalpacking/PGaccess','all actual mapped related pairs/macro/pin reach newG1','electricalclock TTFF actualinventory model','GRT/PGcontinuityIR'],'row_lattice':'.054 x .27, origin4.32; exact actual master max widths'}
(r/'phy_split_data_ff_rows.json').write_text(json.dumps(report,indent=1))
# Exhaustive full-FF model, preserve disclosed old/control basis for all others.
for z in d:
 if z['instance'] in out:z['xy_um']=out[z['instance']]['xy_um'];z['basis']='split data row candidate:'+out[z['instance']]['group']
# Include c_rx_v and two scalar output face flops near their RX data bank without changing logical depth.
for z in d:
 if ('u_bout_o_serdes_W_rx_flit' in z['instance'] and z['instance'] not in out) or re.search(r'\.c_rx_v\$',z['instance']):
  z['xy_um']=[1883.52,675.0];z['basis']='RX actual scalar boundary/control proposed anchor'
sys.path.insert(0,str(r/'src/tools/die_plan'));import taps
p=json.load(open(r/'plan_of_record/plan_c_sd_pg_anchor_v2.json'));ts=[(x['name'],*x['xy']) for x in p['partition_types']['kv3_sys_SD']['clock']['taps']]
primary=[z for z in d if z['clock_net']=='clk'];ss=[z['xy_um']+[1] for z in primary]
load,far,asg=taps.assign(ts,ss,2400,400,max_distance_um=400)
cap=[{'root':t[0],'load':n,'max_L1_um':v} for t,n,v in zip(ts,load,far)]
summary={k:v for k,v in report.items() if k!='positions'};summary['primary_cap']=cap;summary['over220']=[{'instance':z['instance'],'xy':z['xy_um'],'root':ts[j][0],'L1':abs(z['xy_um'][0]-ts[j][1])+abs(z['xy_um'][1]-ts[j][2])} for z,j in zip(primary,asg) if abs(z['xy_um'][0]-ts[j][1])+abs(z['xy_um'][1]-ts[j][2])>220]
(r/'phy_split_capacity_prep.json').write_text(json.dumps(summary,indent=2))
(r/'sd_r52_split_full_mapped_xy_inventory.json').write_text(json.dumps(d,indent=1))
print(json.dumps({k:v for k,v in summary.items() if k!='over220'},indent=2));print('over220',len(summary['over220']));print(str(summary['over220'][:20]))
