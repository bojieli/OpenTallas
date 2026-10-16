#!/usr/bin/env python3
"""Assign additive local-data clock pins for native static memory candidates.
The local pin grant does not adopt a die home or certify incident routes.
"""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE="eba5e0db0"
DIR="results/arch/qwen_split_1014/kvsys_v1_4_3_design/static_io"
OUT=ROOT/"results/arch/qwen_split_1014/static_memory_mc_grant_2330"

def build():
 OUT.mkdir(parents=True,exist_ok=True)
 records={}
 for old,new,w in [("qkd_kv_hbm_elastic_front_r2","qkd_kv_hbm_elastic_front_mc_r3",259.2),("qkd_static_kv_return_slots_r2","qkd_static_kv_return_slots_mc_r3",194.4)]:
  raw=subprocess.check_output(["git","show",f"{BASE}:{DIR}/{old}.tcl"],cwd=ROOT,text=True)
  lines=[];pins={};changed=[]
  pattern=re.compile(r"place_pin -pin_name \{([^}]+)\} -layer (M[45]) -location \{([0-9.]+) ([0-9.]+)\}")
  for line in raw.splitlines():
   if not line or line.startswith("#"):continue
   m=pattern.search(line);assert m,line
   name,layer,x,y=m.groups();x=float(x);y=float(y)
   if old.startswith("qkd_kv_hbm") and x==194.4:
    x=w;line=line.replace("-location {194.400 ",f"-location {{{w:.3f} ");changed.append(name)
   pins[name]=dict(layer=layer,xy=[x,y]);lines.append(line)
  for i in range(4):
   x=.06+.192*round((w/2+(i-1.5)*1.344-.06)/.192)
   name=f"pll_hbm_data[{i}]";assert name not in pins
   pins[name]=dict(layer="M5",xy=[round(x,3),0])
   lines.append(f"place_pin -pin_name {{{name}}} -layer M5 -location {{{x:.3f} 0.000}} -pin_size {{.024 .144}}")
  for name,p in pins.items():
   x,y=p['xy'];assert 0<=x<=w and 0<=y<=216
   axis=y if p['layer']=='M4' else x
   origin,pitch=(.012,.048) if p['layer']=='M4' else (.06,.192)
   assert abs((axis-origin)/pitch-round((axis-origin)/pitch))<1e-6,(name,p)
  for name,a in pins.items():
   if not name.startswith('pll_hbm_data['):continue
   assert min(abs(a['xy'][0]-b['xy'][0]) for n,b in pins.items() if n!=name and b['xy'][1]==0)>=.192-1e-6
  dest=OUT/(new+'.tcl');dest.write_text('\n'.join(lines)+'\n')
  records[new]=dict(outline_um=[w,216],base_commit=BASE,base_pin_path=DIR+'/'+old+'.tcl',base_sha256=hashlib.sha256(raw.encode()).hexdigest(),pin_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),pin_count=len(pins),changed_existing_pins=changed,new_clocks={n:p for n,p in pins.items() if n.startswith('pll_hbm_data[')},clock_obligation='Four separate die-driven roots at the exact frequency and phase of pll_hbm; actual native insertion/spread and phi-R evidence required',homes_status='UNADOPTED: no current wholegraph static front/ring source nets; historical reservation is not actual integration')
 receipt=dict(schema='opentallas.static-memory-mc-pin-grant.v1',status='OFFICIAL_LOCAL_PIN_GRANT_ONLY',native_qualified=False,normal_cycle_delta=0,masters=records,open=['Actual source ports and exact production bench plus failing mutants','Native CTS sink census and phase-aligned data-root delivery','Whole connected die homes and every incident data/control/reset/clock cut','Fresh actual source-bound die case and TT/FF/DRC0'])
 (OUT/'grant.json').write_text(json.dumps(receipt,indent=2)+'\n')
 print(json.dumps({n:dict(pins=d['pin_count'],clocks=d['new_clocks']) for n,d in records.items()}))
if __name__=='__main__':build()
