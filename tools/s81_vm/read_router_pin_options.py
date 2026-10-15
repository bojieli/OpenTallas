#!/usr/bin/env python3
"""Source-derived candidate face assignment. Not a routed/accepted die contract.
Pitch .432um uses alternate .216um signal tracks; final layers/PG owned by die.
"""
import hashlib,json,pathlib,re,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
VM=ROOT/'rtl/dsrom_sys/s81_ph/vm'
def ports(source,name):
 text=source.read_text();body=re.search(r'module\s+'+name+r'\((.*?)\);',text,re.S).group(1)
 result={}
 for field in body.split(','):
  if field.strip()=='rst_n':result['rst_n']=['rst_n'];continue
  m=re.search(r'(input|output)\s+wire\s*(?:\[(\d+):0\])?\s*(\w+)',field)
  if not m:raise ValueError(field)
  n=int(m[2])+1 if m[2]else 1
  result[m[3]]=[m[3]]if n==1 else[f'{m[3]}[{i}]'for i in range(n)]
 return result
result={'scope':'Whole512b VM read egress; source-exact candidate signal pins only, not accepted physical contract. All64data+8control leaves separately clocked.','signal_track_pitch_um':.216,'used_pin_pitch_um':.432,'layers':'Unassigned: die pin/layer contract required; no PG/contact/timing proof.','types':{},'total_instances':72}
for g in range(8):
 for kind,file in [('q','dsfd_vm_static_read_quartets.sv'),('v','dsfd_vm_static_read_valid_quartets.sv')]:
  name=f'dsfd_vm_static_read_{kind}{g}';src=VM/file;p=ports(src,name)
  faces={'W':[],'N':[],'E':[]}
  for port,bits in p.items():
   if port in ('ck','rst_n','i_su1_group','i_peer_data','i_peer_valid','o_peer_data','o_peer_valid'):
    face='N' if kind=='q' else ('N'if port in ('ck','rst_n')else'W')
   elif port.startswith('o_')or port=='fault':face='E'
   elif kind=='v'and port in ('i_expected','i_slot'):face='N'
   else:face='W'
   faces[face]+=bits
  width,height=((103.68,129.6)if g==4 or g>=6 else(155.52,237.6))if kind=='q'else(51.84,51.84)
  pins=[]
  for face,bits in faces.items():
   length=height if face in ('W','E')else width
   start=int((length-(len(bits)-1)*.432)/2/.216)*.216
   assert start>=4.32,(name,face,len(bits),start)
   for i,bit in enumerate(bits):
    d=round(start+.432*i,6);x=0 if face=='W'else width if face=='E'else d;y=d if face in ('W','E')else height
    pins.append(dict(port=bit,face=face,x_um=x,y_um=y))
  np=9 if g==1 else 2 if g==4 else 4 if g>=6 else 8;no=8 if g==1 else np;nv=5 if g==5 else no
  ff=64*(np+no)+np+3 if kind=='q'else np+nv+4
  result['types'][name]={'source':str(src.relative_to(ROOT)),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'instances':8 if kind=='q'else 1,'outline_um':[width,height],'signal_pins':len(pins),'face_counts':{k:len(v)for k,v in faces.items()},'rtl_ff_before_constant_optimization':ff,'pins':pins}
result['total_rtl_ff_before_constant_optimization']=sum(t['instances']*t['rtl_ff_before_constant_optimization']for t in result['types'].values())
path=pathlib.Path(sys.argv[1]);path.write_text(json.dumps(result,indent=2)+'\n');print('READ_ROUTER_PINS',result['total_instances'],'leaves',result['total_rtl_ff_before_constant_optimization'],'FF')
