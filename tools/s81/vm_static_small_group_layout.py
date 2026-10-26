#!/usr/bin/env python3
"""Actual 188-core-child small-group geometry candidate; global endpoint hops open."""
import json,sys,importlib.util
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/ref_tile'))
spec=importlib.util.spec_from_file_location('rt',R/'tools/ref_tile/ref_tile.py');rt=importlib.util.module_from_spec(spec);spec.loader.exec_module(rt)
def main():
 nodes=[]
 for s in range(4):
  def add(name,master,x,y,w,h,**extra):nodes.append(dict(name=f'vm_s{s}_{name}',slice=s,master=master,xy_um=[round(x,3),round(y+1468.8*s,3)],outline_um=[w,h],**extra))
  for q in range(8):
   ox=1123.2*((q//2)%2);oy=388.8*((q%2)+2*(q//4))
   for k in range(4):add(f'bank{4*q+k}','dsfd_vm_static_bank128',ox+43.2+475.2*(k//2),oy+43.2+129.6*(k%2),220.32,75.6,bank=4*q+k)
   add(f'quarter{q}','dsfd_vm_static_relay128_b4',ox+345.6,oy+86.4,129.6,129.6)
  for b in range(4):add(f'bridge{b}','dsfd_vm_static_relay128_b8',302.4+1123.2*(b%2),259.2+777.6*(b//2),172.8,172.8)
  add('wscatter','dsfd_vm_static_scatter',777.6,432,345.6,103.68)
  add('read_frontend','dsfd_vm_static_suhc_fsr',777.6,604.8,345.6,51.84)
  add('return32','dsfd_vm_static_return',777.6,734.4,345.6,207.36,NROW=32)
 outline=[1944,6480]
 blocks=[dict(name=n['name'],master=n['master'],idx=i,kind='child',x=n['xy_um'][0],y=n['xy_um'][1],w=n['outline_um'][0],h=n['outline_um'][1],offtrack=None) for i,n in enumerate(nodes)]
 checks=rt.floorplan_checks(dict(kind='cluster',pins={f:['pending'] for f in 'NSEW'}),*outline,blocks,None);assert not checks,checks
 d=dict(schema='opentallas.s81.static-vm-small-groups-option.v1',status='NATIVE_PIN_REACH_AND_GLOBAL_HIERARCHY_NOT_YET_PROVEN',source='cd1242953',parent_outline_um=outline,core_slice_outline_um=[1944,1468.8],nodes=nodes,hard_children=len(nodes),checks=checks,edge_service_reserved_band_xywh_um=[43.2,5875.2,1857.6,561.6],new_parent_mm2=outline[0]*outline[1]/1e6,actual_registered_stages_each_direction=2,requirements=['exact assigned signal-bit reach with actual bank and b4/b8pins','global FSR/scatter/return distribution uniform registered hops and actual compiler ages','realmapped child dimensions and native clocks/PG/cuts','cap16/CDC/53writer+edge packing and fullcanonicaldiejoin'])
 out=R/'physical/s81_die_pins/v20_vm_static_small_groups';out.mkdir(exist_ok=True);(out/'layout_option.json').write_text(json.dumps(d,indent=1)+'\n');print('SMALL_GROUPS_GEOMETRY',len(nodes),checks)
if __name__=='__main__':main()
