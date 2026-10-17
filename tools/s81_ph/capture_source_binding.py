#!/usr/bin/env python3
"""Expand source-current capture wrappers and bind literal CLOSED LEF contacts.

Produces an executable import packet in the capture slot frame. Homes are a
candidate, not a die closure claim. No synthesis, placement or reroute is run.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from capture_split_census import ROOT, BASE, PARENT, GROUPS
from gather_flatten_plan import lef_pins
sys.path.insert(0, str(ROOT / "tools/hier_contract"))
from pinreg_audit import parse_lib
from native_pin_audit import audit_one

WRAPPERS = ('dsfd_capt_x8_data_e', 'dsfd_capt_x8_data_w', 'dsfd_capt_status_dual')
KITS = {
 'dsfd_capt_cd': 'dsfd_capt_cd_split1016p',
 'dsfd_capt_ctl': 'dsfd_capt_ctl_split1016',
 'dsfd_capt_g2_dualho': 'dsfd_capt_g2_dualho_split1016',
 **{f'dsfd_capt_rly_{w}_{d}': f'dsfd_capt_rly_{w}_{d.lower()}_split1016'+('r' if w==64 else '') for w,d in [(12,'SN'),(31,'EW'),(36,'WE'),(64,'EW')]},
 **{f'dsfd_capt_status_x43_{s}': f'dsfd_capt_status_x43_{s}_split1016'+('x' if s=='t' else 'y') for s in ('s','t')},
 **{f'dsfd_capt_x8x_{s}_{d}': f'dsfd_capt_x8x_{s}_{d}_split1016'+('x' if s=='t' else 'z') for s in ('s','t') for d in ('e','w')},
 **{f'dsfd_rly_{w}_{d}': f's81_rly_{w}_{d.lower()}' for w,d in [(68,'EW'),(2,'WE'),(63,'WE'),(2,'EW')]},
}

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def module(text, name):
 m=re.search(r'\bmodule\s+'+name+r'\b.*?endmodule',text,re.S)
 if not m: raise ValueError('missing module '+name)
 return m[0]

def elaborate():
 groups={p:[n for n in ns if n not in WRAPPERS] for p,ns in GROUPS.items()}
 groups[BASE+'dsfd_capt_x8_x43.sv']=[n for n in KITS if n.startswith('dsfd_capt_x8x_')]
 groups[BASE+'dsfd_capt_status_x43.sv']=[n for n in KITS if n.startswith('dsfd_capt_status_x43_')]
 headers=[]; buses={}; hashes={}
 for p,ns in groups.items():
  text=(ROOT/p).read_text(); hashes[p]=sha(ROOT/p)
  text=re.sub(r'/\*.*?\*/|//[^\n]*','',text,flags=re.S)
  for n in ns:
   h=module(text,n).split(';',1)[0]+';'
   headers.append(h+'\nendmodule\n'); buses[n]=[]
   for decl in re.split(r'\b(?:input|output|inout)\b',h)[1:]:
    if re.search(r'\[\s*0\s*:\s*0\s*\]',decl):
     buses[n]+=[v for v in re.findall(r'\b[A-Za-z_]\w*\b',re.sub(r'\[[^]]*\]',' ',decl)) if v not in ('wire','reg','logic','signed')]
 text=(ROOT/(BASE+'dsfd_capt_split.sv')).read_text()
 wrappers='\n'.join(module(text,n) for n in WRAPPERS)
 hashes[PARENT]=sha(ROOT/PARENT)
 with tempfile.TemporaryDirectory() as td:
  t=Path(td); (t/'headers.sv').write_text('`define CAPT_KB 99\n'+'\n'.join(headers)); (t/'wrappers.sv').write_text(wrappers)
  (t/'net.ys').write_text(f'read_verilog -sv -lib {t}/headers.sv\nread_verilog -sv {t}/wrappers.sv {ROOT/PARENT}\nhierarchy -check -top dsfd_sp_capture_split_candidate\nproc; flatten; opt_clean\nwrite_json {t}/net.json\n')
  subprocess.run(['yosys','-Q','-q',str(t/'net.ys')],check=True,capture_output=True)
  mod=json.loads((t/'net.json').read_text())['modules']['dsfd_sp_capture_split_candidate']
 return mod,buses,hashes

def home(n,size):
 """Structured 4x2 candidate, retaining historical origins where they fit."""
 g=re.search(r'g_t\[(\d+)\]',n)
 if g:
  g=int(g[1]); gx=15.108+429.84*(g//2); gy=129.6+194.4*(g%2)
  if '.u_x' in n:
   # t_e -> s_e, s_w <- t_w; bank contacts abut, tops flush.
   x=gx+(285.12 if '.u_x1.' in n else 0)
   west='.u_x1.' in n
   return [round(x+(86.4 if west else 0) if n.endswith('.u_t') else x+(0 if west else 32.4),3),round(gy+(10.8 if n.endswith('.u_t') else 0),3)]
  if n.endswith('u_g'): return [round(gx+144.72,3),gy]
  role={'u_ka':0,'u_kb':1,'u_sb':2}[n.rsplit('.',1)[1]]; ix=role+(3 if g in (2,3,4,5) else 0)
  x=336.384+37.44*ix if g<4 else 1727.976-388.8-37.44*ix-size[0]
  if g==7 and role==2:x=1451.52
  return [round(x,3),21.6+39.96*(g%2)]
 return {'u_ctl':[701.988,21.6],'u_status.u_t':[598.308,21.6],'u_status.u_s':[619.908,21.6], 'u_sn':[663.108,55.296], 'u_cd':[561.588,21.6], 'u_cr':[590.76,501.12]}[n]

def build():
 mod,buses,hashes=elaborate(); children={}; ends=defaultdict(list); clocks=[]; views={}; trees={}
 for n,c in sorted(mod['cells'].items()):
  m=c['type']; assert m in KITS,m
  view=Path('physical/ref_tile')/KITS[m]/'views'/m
  if m not in views:
   paths=[view/(m+'.lef'),view/'insertion.json',*[view/(m+'_'+co+'.lib') for co in ('ss','tt','ff')]]
   for p in paths: assert (ROOT/p).is_file(),p
   views[m]={'view':str(view),'sha256':{str(p):sha(ROOT/p) for p in paths}}
   audit=audit_one((str(ROOT),m,str(view))); assert audit.get('pass'),audit
   views[m]['native_audit']=audit
   trees[m]={co:parse_lib(ROOT/view/(m+'_'+co+'.lib')) for co in ('ss','ff','tt')}
  size,pins=lef_pins(ROOT/view/(m+'.lef')); at=home(n,size); ins=json.loads((ROOT/view/'insertion.json').read_text()); pp={}
  for port,bits in c['connections'].items():
   for i,bit in enumerate(bits):
    pin=f'{port}[{i}]' if len(bits)>1 or port in buses[m] else port
    assert pin in pins,(m,pin)
    layer,x,y=pins[pin]; datum={'layer':layer,'local_xy_um':[x,y],'xy_um':[round(at[0]+x,6),round(at[1]+y,6)],'bit':bit,'direction':c['port_directions'][port]}
    pp[pin]=datum; ends[bit].append({'child':n,'pin':pin,**datum})
    if port in ('ck','ckv','ckvb'):
     cm=ins.get('clock_measurements',{}).get(pin,ins if len([p for p in c['connections'] if p in ('ck','ckv','ckvb')])==1 else None)
     assert cm is not None,('missing literal clock insertion',m,pin)
     parent=[f'{p}[{j}]' if len(v['bits'])>1 else p for p,v in mod['ports'].items() for j,b in enumerate(v['bits']) if b==bit]
     assert len(parent)==1,(n,pin,parent)
     etm={}
     for co in ('ss','ff','tt'):
      arcs=trees[m][co]['pins'][pin]['arcs']
      values={typ:[v for a in arcs if a[0]==typ+'_clock_tree_path' for v in a[2].get('cell_rise',[])] for typ in ('min','max')}
      if values['min'] and values['max']: etm[co]=max(values['max']) if co=='ss' else min(values['min']) if co=='ff' else (min(values['min'])+max(values['max']))/2
     clocks.append({'etm_die_balance_R_ps':etm,'child':n,'pin':pin,'parent_clock_pin':parent[0],'domain':'serial' if parent[0].startswith('ckv') else 'stream','xy_um':datum['xy_um'],'R_ps':{co:cm[co]['boundary']['mean'] for co in ('ss','ff','tt')},'spread_ps':{co:cm[co]['boundary']['max']-cm[co]['boundary']['min'] for co in ('ss','ff','tt')},'delivery':'phi - R per literal entry'})
  children[n]={'master':m,'kit':KITS[m],'view':str(view),'at_um':at,'outline_um':list(size),'orient':'R0','parameters':c.get('parameters',{}),'pins':pp}
 ports={}; internal=[]; errors=[]
 for p,v in mod['ports'].items():
  for j,b in enumerate(v['bits']): ports[f'{p}[{j}]' if len(v['bits'])>1 else p]={'direction':v['direction'],'bit':b,'contacts':ends[b]}
 parent_inputs={b for v in mod['ports'].values() if v['direction']=='input' for b in v['bits']}
 for b,es in ends.items():
  ds=[e for e in es if e['direction']=='output']; ss=[e for e in es if e['direction']=='input']
  if isinstance(b,str) or len(ds)>1 or (not ds and b not in parent_inputs): errors.append(str(b))
  for d in ds:
   for s in ss: internal.append({'bit':b,'driver':d['child']+'/'+d['pin'],'sink':s['child']+'/'+s['pin'],'manhattan_um':round(sum(abs(a-z) for a,z in zip(d['xy_um'],s['xy_um'])),6)})
 assert not errors,errors[:5]
 overlaps=[]
 for n,a in children.items():
  for m,b in children.items():
   if n>=m:continue
   if all(min(a['at_um'][i]+a['outline_um'][i],b['at_um'][i]+b['outline_um'][i])-max(a['at_um'][i],b['at_um'][i])>1e-6 for i in (0,1)): overlaps.append([n,m])
 assert not overlaps,overlaps
 assert all(c['at_um'][i] >= 0 and c['at_um'][i]+c['outline_um'][i] <= (1727.976,561.576)[i]+1e-6 for c in children.values() for i in (0,1))
 assert children['u_cd']['parameters'].get('PINREG') == 1
 assert len(clocks) == 86 and len(mod['cells']) == 70
 return {'schema':'opentallas.s81.capture_source_binding.v1','adopted':False,'physical_qualified':False,'scope':'Source-current literal LEF import packet; local candidate homes, die GRT/STA pending','counts':{'children':len(children),'masters':len(views),'parent_clock_bits':sum(len(v['bits']) for p,v in mod['ports'].items() if p.startswith('ck')),'literal_clock_contacts':len(clocks),'parent_logic_cells':0,'overlaps':len(overlaps),'internal_bit_paths':len(internal)},'outline_um':[1727.976,561.576],'children':children,'views':views,'clock_entries':clocks,'die_ports':ports,'internal_paths':internal,'source_sha256':hashes,'reset_contract':{'rst':'stream epoch reset active low; first post-release stream edge is epoch 0','rsv':'serial epoch reset active low; first post-release serial edge is epoch 0','status_s':'rv0/rv1 local release stage; sp=1,se=1,warm=1 compensate first active edge 2; zero added serial edges','x8_s':'ckv and ckvb separate literal entries on same serial bus, each phi-R; preserve cross-entry reserve and related-clock timing'},'cycle_cost':{'cd_PINREG':1,'unit':'serial ckv edge on DONE; PINREG=1 bound in candidate','status_reset_stage':0,'x8_split1016z':0}}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True); a=p.parse_args(); data=build(); out=ROOT/a.out;out.parent.mkdir(parents=True,exist_ok=True);payload=(json.dumps(data,separators=(',',':'))+'\n').encode(); out.write_bytes(gzip.compress(payload,mtime=0) if out.suffix=='.gz' else payload);print(json.dumps(data['counts']))
