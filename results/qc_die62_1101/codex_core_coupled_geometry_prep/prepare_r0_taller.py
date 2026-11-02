"""Disabled R0/MY-only coupled geometry exploration; no source generation."""
import json,gzip,copy,re
from pathlib import Path
B=Path(__file__).resolve().parent;o=B/'geometry_r0_taller';o.mkdir(exist_ok=True)
g=json.load(open(B/'geometry_eio2/MACRO_GEOMETRY.json'));p=json.load(gzip.open(B/'geometry_eio2/DISABLED_PARENT_PLAN_UNRELEASED.json.gz'));ms=g['macros']
yof={'u_pring.g_b[0].u_m':155.52,'u_pring.g_b[1].u_m':288,'u_rring.g_b[0].u_m':416.016,'u_rring.g_b[1].u_m':544.032,'g_sring[0].u_m':111.24,'g_sring[1].u_m':249.48,'g_sring[2].u_m':505.656,'g_sring[3].u_m':633.672,'g_sring[4].u_m':377.64}
for m in ms:
 name=m['inst'];suffix=name.split('u_coll.')[-1]
 if m['module']=='ot_coll_fold_slice':continue
 m['outline_um']=m.pop('unrotated_outline_um',m['outline_um'])
 if m['module']=='ot_sram_1r1w_64x512_m1_r2c2':
  face=int(re.search(r'g_face_([01])',name)[1]);bank=int(re.search(r'g_bank\[(\d)\]',name)[1]);m['origin_um']=[17.28 if face==0 else 240.48,829.44+95.04*bank];m['orient']='R0'
 elif m['module']=='ot_sram_1r1w2c_64x546_m1':
  face=int(re.search(r'g_face_([01])',name)[1]);tx='u_tx.'in name;m['origin_um']=[463.68,{(0,False):17.28,(0,True):672.048,(1,False):767.088,(1,True):862.128}[face,tx]];m['orient']='R0'
 else:m['origin_um']=[440.208 if suffix=='g_sring[4].u_m' else 463.68,yof[suffix]];m['orient']='R0'
core=p['partition_types']['coll_core'];core['outline_um']=[760.32,1296];core['hard_cores']=copy.deepcopy(ms)
for m in core['hard_cores']:m.pop('view_status',None)
ft=p['partition_types'][next(x['type']for x in p['partitions']if x['name']=='coll_f1')];ft['outline_um']=[760.32,864]
for part in p['partitions']:
 if part['name']=='coll_core':part['origin_um']=[803.52,8173.44]
 if part['name']=='coll_f2':part['origin_um']=[803.52,7309.44]
 if part['name']=='coll_ucie':part['origin_um']=[0,7344]
errs=[]
for i,a in enumerate(ms):
 x,y=a['origin_um'];w,h=a['outline_um'];z=a['halo_um'];aa=[x-z,y-z,x+w+z,y+h+z]
 if min(aa[:2])<0 or aa[2]>760.32 or aa[3]>1291.68:errs.append({'kind':'OUTSIDE','macro':a['inst']})
 for b in ms[:i]:
  x,y=b['origin_um'];w,h=b['outline_um'];z=b['halo_um'];bb=[x-z,y-z,x+w+z,y+h+z]
  if min(aa[2],bb[2])>max(aa[0],bb[0])+1e-7 and min(aa[3],bb[3])>max(aa[1],bb[1])+1e-7:errs.append({'kind':'HALO_OVERLAP','macros':[a['inst'],b['inst']]})
g.update(status='DISABLED_R0_TALLER_SOURCE_REACH_UNQUALIFIED',outline_um=[760.32,1296],actual_core_box_um=[0,0,760.32,1291.68],macros=ms,body_and_halo_errors=errs,coupled_parent={'core_origin_um':[803.52,8173.44],'both_sharedFT_outline_um':[760.32,864],'F1_origin_um':[803.52,6445.44],'F2_origin_um':[803.52,7309.44],'ucie_origin_um':[0,7344],'ucie_outline_um':[803.52,1347.84],'F0_F3_publicface_dieedge_preserved':True},station_price={'status':'UNPRICED','existing_sharedFT_postring_data_edges':3,'note':'No added-edge inference; shorter864um outline must have exact perbit endpoints/registeredABI and boot/clock/reset source rederive before0totalcyclecredit.'})
(o/'MACRO_GEOMETRY.json').write_text(json.dumps(g,indent=2)+'\n')
with gzip.open(o/'DISABLED_PARENT_PLAN_UNRELEASED.json.gz','wt')as f:json.dump(p,f,separators=(',',':'))
print(json.dumps({'macros':len(ms),'rotations':sorted({m['orient']for m in ms}),'body_and_halo_errors':errs}))
