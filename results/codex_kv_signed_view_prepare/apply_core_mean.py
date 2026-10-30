#!/usr/bin/env python3
"""Prepare an actual selected core view/mean delta only after SIGNED + routed EQ."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('kit');p.add_argument('module');p.add_argument('lec');p.add_argument('out');a=p.parse_args()
k=Path(a.kit);so=k/'signoff/signoff.json';s=json.load(so.open());l=json.load(open(a.lec))
if s.get('verdict')!='SIGNED':raise SystemExit('HOLD: physical signoff is not SIGNED')
if l.get('verdict')!='EQUIVALENT':raise SystemExit('HOLD: routed netlist LEC is not EQUIVALENT')
# Caller supplies the post-route LEC receipt; require an actual completed final netlist.
net=Path(s['inputs']['base'])/'6_final.v'
if not net.is_file():raise SystemExit('HOLD: signed final netlist missing')
views=k/'views';tt=views/(a.module+'_tt.lib');ff=views/(a.module+'_ff.lib');lef=views/(a.module+'.lef')
for f in [tt,ff,lef]:
 if not f.is_file():raise SystemExit('HOLD: selected view missing '+str(f))
for f in [tt,ff]:
 m=re.search(r'\bcell\s*\(\s*"?([^"\s)]+)',f.read_text())
 if not m or m.group(1)!=a.module:raise SystemExit('HOLD: selected cell identity differs')
vals={c:s['corners'][c]['insertion_pinflops'] for c in ('tt','ff')}
for c,v in vals.items():
 if not(v.get('n',0)>0 and isinstance(v.get('mean'),(int,float))):raise SystemExit('HOLD: no measured boundary mean at '+c)
clock=s['corners']['tt']['clock_ports']
if len(clock)!=1 or s['corners']['ff']['clock_ports']!=clock:raise SystemExit('HOLD: explicit per-clock contract needed')
h=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
o=Path(a.out);o.mkdir(parents=True,exist_ok=False)
for f in [tt,ff,lef]:shutil.copy2(f,o/f.name)
contract=dict(schema='opentallas.core_clock_contract.v1',view_lib_sha256=h(tt),signed=True,signoff_source=str(so),signoff_verdict='SIGNED',pins={clock[0]:{c:dict(mean_ps=v['mean'],n=v['n'],basis='pin_register_mean',source=f'{so}:{c}:insertion_pinflops') for c,v in vals.items()}},physical_view_alias=dict(signed_design=s['corners']['tt']['design'],view_cell=a.module,final_netlist_sha256=h(net),postroute_lec=str(Path(a.lec).resolve()),postroute_lec_sha256=h(a.lec),note='Canonical master alias exported from same signed physical kit; no extrema/ratio substitution'))
(o/'clock_contract.json').write_text(json.dumps(contract,indent=2)+'\n')
x=json.load(open(a.plan));count=0
for tn,t in x['partition_types'].items():
 insts={c['inst'] for c in t.get('hard_cores',[]) if c['module']==a.module}
 for c in t.get('hard_cores',[]):
  if c['inst'] in insts:c.update(lef=str(o/lef.name),lib=str(o/tt.name))
 for tp in t.get('clock',{}).get('taps',[]):
  if tp.get('kind')=='core' and any(tp.get('name','').startswith(i+'.') for i in insts):
   tp.update(insertion_ps=vals['tt']['mean'],insertion_ff_ps=vals['ff']['mean'],budget_owner='SIGNED:'+a.module+'@'+h(tt)[:12]);count+=1
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
import core_clock_contract as CC
CC.load(dict(inst=a.module,module=a.module,lib=str(o/tt.name)),require_signed=True)
(o/'plan_core_mean.json').write_text(json.dumps(x))
(o/'receipt.json').write_text(json.dumps(dict(module=a.module,taps_changed=count,tt_mean=vals['tt']['mean'],ff_mean=vals['ff']['mean'],logical_cycles_added=0,postroute_lec=str(a.lec),status='PREPARE: re-read die clocks and re-kit affected parents before adoption'),indent=2)+'\n')
print('CORE_MEAN_PREPARED',count,vals['tt']['mean'],vals['ff']['mean'])
