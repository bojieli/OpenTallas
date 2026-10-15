#!/usr/bin/env python3
"""Actual per-bit pin sizing options for static duplex relay masters.
Unclosed new masters only. These local pin options require S-DIE seam assignment
and mapped-area/CTS proof before submission or promotion to any parent plan.
"""
import json,sys,collections,math,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'));sys.path.insert(0,str(R/'tools/s81'))
import die_port_bind as D
import v19_pins_1014 as V
RESPONSE={'sv','cv','sd','st','ct','ca','cm'}
def main():
 out=R/'physical/s81_die_pins/v20_vm_static_transport_options';out.mkdir(exist_ok=True);reports=[]
 for top,side in [('dsfd_vm_static_relay128_b4',129.6),('dsfd_vm_static_relay128_b8',172.8),('dsfd_vm_static_relay128_b16',345.6)]:
  p=R/'rtl/dsrom_sys/s81_ph/vm'/(top+'.sv');m=D.parse_modules(p.read_text(),str(p))[0];env=m.env();faces=collections.defaultdict(list)
  for name,(direction,_) in m.ports.items():
   bits=m.width(name,env)
   if name in ['ck_req','ck_rsp','rst_n']:f='W'
   else:
    response=name[2:] in RESPONSE
    f=('W' if direction=='input' else 'E') if response else ('N' if direction=='input' else 'S')
   faces[f].append((name,bits))
  pp={};demand={}
  for face,ports in faces.items():
   n=sum(w for _,w in ports);demand[face]=n;start=.012+math.ceil((side-n*.096)/2/.048)*.048
   if top.endswith('b4') and face in ['W','S']:start-=21.6 # local-bank group assignment, keeps all tracks/spacing
   k=0
   for name,w in ports:
    pp[name]=[[face,'M5' if face in 'NS' else 'M4',round(start+.096*(k+i),4),.192] for i in range(w)];k+=w
  V.write(out,top,[side,side],pp,'ck_req','REQUEST i_* N -> o_* S; RESPONSE i_* W -> o_* E; native .096um pitch, new unclosed source only','static_transport_sizing_option',{'status':'LOCAL_PIN_OPTION_NOT_ASSIGNED_TO_PARENT','clock_entries':{'stream_request':['ck_req'],'stream_response':['ck_rsp']},'reset_entries':{'stream':['rst_n']},'adoption':'mapped area/CTS and actual parent seam/cut/phi-R required','source_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  reports.append(dict(master=top,outline_um=[side,side],face_bits=demand,face_raw_capacity=int(side/.096),maximum_face_demand_ratio=max(demand.values())/(side/.096),state='PIN_BOUNDARY_OPTION_ONLY'))
 (out/'receipt.json').write_text(json.dumps({'status':'LOCAL_PER_BIT_PIN_OPTIONS','masters':reports,'native_pitch_um':.096,'no_routed_master_repinned':True,'next':'S-DIE exact native seam assignment; mapping/CTS; revised parent localgroups with measured outlines'},indent=2)+'\n');print(json.dumps(reports))
if __name__=='__main__':main()
