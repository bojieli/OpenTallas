import pathlib,json,gzip,copy,re,shutil
B=pathlib.Path(__file__).resolve().parent;i=B/'geometry_nio129p6_a5';o=B/'geometry_nio129p6_a9';o.mkdir(exist_ok=True);g=json.load(open(i/'MACRO_GEOMETRY.json'));p=json.load(gzip.open(i/'DISABLED_PARENT_PLAN_UNRELEASED.json.gz'));pol=json.load(open(i/'NEW_FOLD_NIO_PIN_POLICY_UNQUALIFIED.json'));placed=[]
for m in g['macros']:
 x,y=m['origin_um'];dx,dy=m['track_offset_um'];m['origin_um']=[round(x+dx,6),round(y+dy,6)];m['track_offset_um']=[0,0];n=m['inst']
 if m['module']=='ot_coll_fold_slice':m['origin_um'][1]=207.36 if 'g_pf['in n else 388.8
 elif m['origin_um'][1]>=475:m['origin_um'][1]+=34.56
 if 'g_sring[4]'in n:m['origin_um']=[319.68,345.612]
 if 'g_face_1'in n and 'g_bank[0]'in n:m['origin_um']=[570.24,535.584]
 if 'g_face_1'in n and 'g_bank[1]'in n:m['origin_um']=[570.24,889.92]
 if 'g_face_1'in n and n.endswith('.u_rx.u_mem'):m['origin_um']=[207.36,855.36]
 if 'g_face_0'in n and any('g_bank['+str(k)+']'in n for k in [0,1,2]):m['origin_um'][0]=388.8
 if 'g_face_0'in n and any('g_bank['+str(k)+']'in n for k in [1,2]):m['origin_um'][0]=397.44
 if 'g_face_1'in n and 'g_bank['in n:m['origin_um'][0]=578.88
 if 'g_xf['in n:
  m['orient']='MX';m['origin_um'][0]=[4.32,142.56,488.16,626.4][int(n.split('g_xf[')[1].split(']')[0])]
 if 'g_sring[4]'in n:m['origin_um']=[293.76,440.64]
for m in sorted(g['macros'],key=lambda m:m['origin_um'][1]):
 x,y=m['origin_um'];w,h=m['outline_um'];z=m['halo_um']
 if m['module']!='ot_coll_fold_slice':
  dy=round((.012-y)%.048,6);y=round(y+(0 if abs(dy-.048)<1e-6 else dy),6)
 for _ in range(100):
  bb=[x-z,y-z,x+w+z,y+h+z];hit=any(min(bb[2],a[2])>max(bb[0],a[0])+1e-7 and min(bb[3],a[3])>max(bb[1],a[1])+1e-7 for a in placed)
  if not hit:break
  assert m['module']!='ot_coll_fold_slice';y=round(y+.048,6)
 else:raise ValueError(('macrohalo',m['inst'],[x,y],bb))
 assert min(bb[:2])>=-1e-6 and bb[2]<=760.32 and bb[3]<=1084.32
 actual=[x,y];anchors=[round(v/8.64)*8.64 for v in actual];m['origin_um']=[round(v,6)for v in anchors];m['track_offset_um']=[round(v-z,6)for v,z in zip(actual,anchors)];placed.append(bb)
for c in p['partition_types']['coll_core']['hard_cores']:
 m=next(x for x in g['macros']if x['inst']==c['inst']);c['origin_um']=m['origin_um'];c['track_offset_um']=m['track_offset_um'];c['orient']=m['orient']
g['revision']='A9: split XF columns4.32/142.56/488.16/626.4 and Sring4 central gap293.76,440.64; actual f_md→Nflag lower-bound repair. A8: XF MX preserves one shared fold view and gives SRAM4 metadata a short southernred landing; codec1bank1 right889.92/RX1central198.72; codec0 central3banks388.8. A7: PF207.36/XF380.16, both fault outputs N-left in same single NIO view target, actual fanout lower-bound driven repack. A6: PF row198.72/XF354.24 to shorten exact PF-error→pe_q→f_ar→northflag source path; Sring4left721.44, codec1bank1low17.28. A4: twoPbanksparallel492.48, bank1MY(readscenter); bulkSrings587.52; Rringsparallel630.72;2codecSRAMscentral725.76/820.8; zero added data edge target. Source/phase/viewqualification held.';(o/'MACRO_GEOMETRY.json').write_text(json.dumps(g,indent=2)+'\n');shutil.copyfile(i/'NEW_FOLD_NIO_PIN_POLICY_UNQUALIFIED.json',o/'NEW_FOLD_NIO_PIN_POLICY_UNQUALIFIED.json');shutil.copytree(i/'PROPOSED_macro_pins',o/'PROPOSED_macro_pins',dirs_exist_ok=True)
with gzip.open(o/'DISABLED_PARENT_PLAN_UNRELEASED.json.gz','wt')as f:json.dump(p,f,separators=(',',':'))

pol['proposed_local_pin_centers_um']['e_out']=[2.952,129.558];pol['proposed_local_pin_centers_um']['v_out']=[5.352,129.558];pol['revision']='A7: e/v N-left to reduce measured PF-error→pe_q→f_ar→Nfault registered reach, one same8-copyview.'
(o/'NEW_FOLD_NIO_PIN_POLICY_UNQUALIFIED.json').write_text(json.dumps(pol,indent=2)+'\n');g['proposed_fold_pin_policy']=pol;(o/'MACRO_GEOMETRY.json').write_text(json.dumps(g,indent=2)+'\n');pf=o/'PROPOSED_macro_pins/ot_coll_fold_slice_nio.json';pd=json.load(open(pf))
for pin in pd['pins']:
 if pin['name']in ['e_out','v_out']:pin['x'],pin['y']=pol['proposed_local_pin_centers_um'][pin['name']]
pf.write_text(json.dumps(pd,indent=2)+'\n')
