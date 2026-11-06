#!/usr/bin/env python3
"""Prepare ONLY a child prototype plan/spec/recipe; never a parent bind/collector event."""
import argparse,copy,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'cores'))
import qc_core_wave as W

def main():
 a=argparse.ArgumentParser();a.add_argument('--plan',required=True);a.add_argument('--out',required=True);x=a.parse_args();out=Path(x.out).resolve()
 if out.exists():raise ValueError('fresh output directory required')
 out.mkdir(parents=True);p=json.loads(Path(x.plan).read_text());meta=json.loads((HERE/'child.json').read_text());tn=meta['type'];m=meta['master'];t=p['partition_types'][tn]
 if any(h['module']==m for h in t.get('hard_cores',[])):raise ValueError('prototype already present')
 (out/'pins.json').write_bytes((HERE/'pins.json').read_bytes());pins=json.loads((HERE/'pins.json').read_text())['pins'];clk=next(z for z in pins if z['name']=='clk');org=meta['origin_um']
 t.setdefault('hard_cores',[]).append(dict(inst='cl_x_ctl_i',module=m,origin_um=org,outline_um=meta['outline_um'],orient='R0',pins_file='pins.json',physical_inst='u_bound.u_cland_x_ctl_i',physical_master=m,param_wrap=dict(base='ot_dp_clk_landing_cas',params=meta['params']),reset_net='cland_start',cells=meta['cells']))
 t['clock']['taps'].append(dict(name='cl_x_ctl_i.clk',kind='core',xy=[round(org[0]+clk['x']+.012,3),round(org[1]+clk['y']+.012,3)],insertion_ps=250,insertion_ff_ps=202.5,budget_owner='UNSIGNED child prototype target; not parent clock qualification'))
 e=dict(module=m,rtl=str((HERE/'wrapper.sv').relative_to(REPO)),view=m+'@fw1106',pins_file='pins.json');rec=W.sle_cland_recipe(e,out,p);(out/'recipes.json').write_text(json.dumps({m:rec},indent=1)+'\n');(out/'plan_child_only.json').write_text(json.dumps(p,separators=(',',':'))+'\n')
 (out/'SCOPE.txt').write_text('UNADOPTED child-only prototype. Parent native/reset/collector event NOT provided. No parent GEN/route with this plan. Targets250TT/202.5FF are estimates until own actual signoff. Zero new data cycles.\n')
 print('PREPARED_CHILD_ONLY',out)
if __name__=='__main__':main()
