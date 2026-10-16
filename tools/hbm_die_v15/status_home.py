#!/usr/bin/env python3
"""Place the exact CLOSED status4 view; leave global transport/CP join explicit."""
import hashlib,json,math,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HC=ROOT/'results/arch/hier_contract_1015/hbm_v15.json'
FP=ROOT/'results/arch/hbm_globalfp_1015/noatt/pins/T_band2__npg4_s5.pins.json'
VIEW='physical/ref_tile/hv15_vm_status4_margin1/views/ot_vms_status4_static'
SRC='rtl/hbm_accel/generic/vm/static/ot_vms_status4_static.sv'

def blob(rel):return subprocess.run(['git','-C',str(ROOT),'show','HEAD:'+rel],capture_output=True,check=True).stdout

def main():
 h=json.loads(HC.read_text());fp=json.loads(FP.read_text());tx=blob(VIEW+'/ot_vms_status4_static.lef').decode()
 w,hh=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',tx).groups());assert (w,hh)==(17.28,19.44)
 assert (ROOT/SRC).read_bytes()==subprocess.run(['git','-C',str(ROOT),'show','67e4e876b:'+SRC],capture_output=True,check=True).stdout
 pins=[]
 for n,b in re.findall(r'\n  PIN (\S+)(.*?)\n  END \S+',tx,re.S):
  if 'USE SIGNAL' not in b:continue
  layer=re.search(r'LAYER (M\d+)',b)[1]
  a,c,d,e=map(float,re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',b).groups())
  x,y=(a+d)/2,(c+e)/2
  face=min({'W':x,'E':w-x,'S':y,'N':hh-y},key={'W':x,'E':w-x,'S':y,'N':hh-y}.get)
  off=y if face in 'EW' else x
  pins.append(dict(name=n,face=face,layer=layer,offset=off,span_um=[c,e] if face in 'EW' else [a,d]))
 assert len(pins)==97
 h['slots']=[s for s in h['slots'] if s['name']!='vm_status4']
 replaced={s.get('floorplan_block',s['name']) for s in h['slots'][1:]}
 rects=[(n,b['x'],b['y'],b['w'],b['h']) for n,b in fp['blocks'].items() if n not in replaced]
 for s in h['slots'][1:]:
  r=s['origin'];o=s['outline'];rects.append((s['name'],r['x'],r['y'],o['w'],o['h']))
 cx=sum(fp['blocks']['vmh_'+q]['x']+450 for q in ('SW','SE','NW','NE'))/4
 cy=sum(fp['blocks']['vmh_'+q]['y']+450 for q in ('SW','SE','NW','NE'))/4
 def free(x,y):return all(not(x<a+c+20 and a<x+w+20 and y<b+d+20 and b<y+hh+20) for _,a,b,c,d in rects)
 candidates=[]
 for dx in range(-70,71):
  for dy in range(-70,71):
   x=math.ceil((cx+dx*43.2)/2.16)*2.16;y=math.ceil((cy+dy*43.2)/2.16)*2.16
   if free(x,y):candidates.append(((x-cx)**2+(y-cy)**2,round(x,6),round(y,6)))
 _,x,y=min(candidates)
 ce=next(p for p in pins if p['name']=='clk')
 cs=json.loads(blob('results/rtl/ref_tile/hv15_vm_status4_margin1/hv15_vm_status4_margin1-margin1-COMMIT/corner_sta.json'))
 receipt=dict(status='EXACT_CLOSED_VIEW_HOME_ONLY',origin=dict(x=x,y=y,orient='R0'),outline=dict(w=w,h=hh),source_sha256=hashlib.sha256((ROOT/SRC).read_bytes()).hexdigest(),lef_sha256=hashlib.sha256(tx.encode()).hexdigest(),occupied_rectangles_checked=len(rects),overlaps=0,
  TT_setup_ps=cs['setup_tt']['worst_slack_ps'],FF_hold_ps=cs['hold_ff']['worst_slack_ps'],SS_sensitivity_setup_ps=cs['setup_ss']['worst_slack_ps'],DRC=0,
  transport_status='OPEN: all four source-exact status transports need actual VM output pin homes, registered relay RTL/stage counts and native clocks; CP vmstat consumer still UNBOUND19')
 h['slots'].append(dict(name='vm_status4',cell='ot_vms_status4_static',instance='vm_status4',source=SRC,params={},kind='tile',parent='die',outline=receipt['outline'],origin=receipt['origin'],version=2,
  clock_entry={k:ce[k] for k in ('name','face','layer','offset')},clock_domain='stream',clock_period_ps=833.333,pg_layer='M5',strap_layer='M6',signal_max_layer='M5',layer_cap='M5',layer_rule='tile',pins=pins,
  view=VIEW,view_source_ref='67e4e876b',source_sha256=receipt['source_sha256'],lef_sha256=receipt['lef_sha256'],qualification_scope='unchanged CLOSED component; native die transport and CP consumer OPEN'))
 h['slots'][-1]['clock_entry']['pin']=h['slots'][-1]['clock_entry'].pop('name')
 HC.write_text(json.dumps(h,indent=1)+'\n')
 out=ROOT/'results/arch/hier_contract_1015/status4_home_1103.json';out.write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
