#!/usr/bin/env python3
"""Opt-in HEAD native port event: expose all 40 core FT pins without invented die nets."""
import argparse,copy,json,hashlib,os
from pathlib import Path
FTS=('ck0','ck1','mesh','rst')
def apply(P,plan_dir,infra=None):
 P=copy.deepcopy(P);t=P['partition_types']['hd_tile'];t['contents'][0]['module']='ot_s81hd_tile_native'
 replacements={'ot_s81hd_tile.sv':'ot_s81hd_tile_native.sv','ot_s81hd_bundle.sv':'ot_s81hd_bundle_native.sv','ot_s81hd_elem_cv_bb.v':'ot_s81hd_elem_cv_bb_native.v'}
 t['sources']=[str(Path(s).with_name(replacements[Path(s).name])) if Path(s).name in replacements else s for s in t['sources']]
 t['simulation_substitutions']={'rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv_bb_native.v':'rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv_native.sv'}
 ports=[];arcs=[];index=[]
 for h in t['hard_cores']:
  k=4 if 'elemB' in h['module'] else int(h['inst'][-1]);pins=json.loads((plan_dir/h['pins_file']).read_text())['pins'];by={p['name']:p for p in pins};w,hh=h['outline_um'];ox,oy=h['origin_um'];dx,dy=h.get('track_offset_um',[0,0]);orient=h.get('orient','R0')
  for n in FTS:
   for sf,dr in (('i','in'),('o','out')):
    q=by['ft_'+n+'_'+sf];x,y=q['x'],q['y']
    if orient in ('MY','R180'):x=w-x
    if orient in ('MX','R180'):y=hh-y
    name='hci'+str(k)+'_'+n+'_'+sf
    native=[round(ox+dx+x,6),round(oy+dy+y,6)]
    # Symmetric ASAP7 M7 track grid, matching schema.ASAP7_LAYERS / generated make_tracks.tcl.
    snapped=[round(.032+round((v-.032)/.064)*.064,6) for v in native]
    ports.append(dict(name=name,dir=dr,kind='reset' if n=='rst' else 'clock',leaf='u_core.'+name,layer='M7',xy_um=snapped,native_xy_um=native,native_core=h['inst'],native_port=q['name']))
   cell={'ck0':'u_isl_ck0','ck1':'u_isl_ck1','mesh':'u_isl_m0','rst':'u_isl_rstft'}[n]
   arcs.append(dict(cell=h['inst']+'.'+cell,source='hci'+str(k)+'_'+n+'_i',sink='hci'+str(k)+'_'+n+'_o',kind='reset' if n=='rst' else 'clock'))
  index.append(dict(index=k,inst=h['inst'],functional_clock_port='ft_mstrap_i',ft_ports=8))
 t['infra_ports']=sorted(ports,key=lambda p:p['name']);t['infra_arcs']=sorted(arcs,key=lambda p:p['source'])
 if infra is not None:P['infrastructure']=infra
 report=dict(schema='opentallas.head_native_delta/1',ports_per_tile=len(ports),arcs_per_tile=len(arcs),instances=sum(p['type']=='hd_tile' for p in P['partitions']),data_cycles_added=0,core_index=index,active_network='REQUIRED actual physical clock/reset provider; no implicit clk/rst or dummy data ties',hardware='ports expose existing hardened FT buffers; no buffers/flops added by this delta')
 return P,report
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('plan',type=Path);a.add_argument('--out',type=Path,required=True);a.add_argument('--infra',type=Path);o=a.parse_args()
 P,r=apply(json.loads(o.plan.read_text()),o.plan.parent,json.loads(o.infra.read_text()) if o.infra else None)
 # Preserve plan-relative pin metadata when the candidate lives outside the native plan directory.
 for t in P['partition_types'].values():
  for h in t.get('hard_cores',[]):
   if h.get('pins_file') and not Path(h['pins_file']).is_absolute():h['pins_file']=os.path.relpath((o.plan.parent/h['pins_file']).resolve(),o.out.parent.resolve())
 o.out.write_text(json.dumps(P,indent=2)+'\n');print(json.dumps(r,indent=1))
