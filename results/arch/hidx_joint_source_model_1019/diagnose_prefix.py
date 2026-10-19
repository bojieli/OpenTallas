import json,gzip,hashlib,collections
from pathlib import Path
P=Path(__file__).resolve().parent
source=(P/'kit/joint_model.py').read_text();namespace={'__file__':str(P/'kit/joint_model.py')}
# Replay only deterministic definition/allocation stage, NEVER the failed packer.
exec(compile(source.split('plan={};grid=')[0].replace("O=P/'out'","O=P/'diagnostic_defs'"),str(P/'kit/joint_model.py'),'exec'),namespace)
regions=namespace['regions'];items=namespace['items'];groups=namespace['groups'];areas=namespace['areas']
for g,r in regions.items():
 its=[i for i in items if i['cohort']==g]
 r['reserved_atom_sites']=sum(i['w']*i['h'] for i in its)
 r['region_sites']=(r['x1']-r['x0'])*r['rows']
 r['atom_reservation_ratio']=r['reserved_atom_sites']/r['region_sites']
 r['bundle_count']=sum(i['h']>1 for i in its)
 r['native_cell_count']=len(groups[g])
 r['placed_contact_status']='HOLD_NO_COMPLETE_NEW_SITE_PLAN'
verdict={'status':'FAIL_NATIVE_PACKING','first_failure':{'cohort':'pair[0]','atom':'$flatten\\on.pair[0].own.$auto$ff.cc:337:slice$23603','width_sites':39},'regions':regions,'native_cells':11145,'native_ff':2904,'nonclock_native_contacts':31384,'contacts_accounting':{'new_assigned':0,'explicit_hold':31384},'physical_engine_run':False,'new_buffers':0,'old_checkpoint_sha256':'70042afe82ff76fc2657f45fb6c2a89f91eed2993add8e9dc89f2fc612fc88a6','model_constraints':{'cohort_assignment':'12 real quad cohorts jointly assigned to four outer buckets, 3 per bucket; 4 slices fill those buckets; 6 pairs+5 slices jointly assigned to two central buckets, actual port-cap cost','rows':[36,32,36],'outline_um':140.4,'clock_spine_um':[64.8,75.6]},'open':['Complete legal native site packing','Every real native contact new access','Simultaneous M3+M5 signal ownership and default native vias','Actual PG and candidate clock reservation composition','All new RC/via fringe','Native waveform/setup/hold/clock-root budget'],'source_sha256':hashlib.sha256(source.encode()).hexdigest()}
(P/'STATIC_FAILURE.json').write_text(json.dumps(verdict,indent=2))
from PIL import Image,ImageDraw,ImageFont
im=Image.new('RGB',(1450,750),'white');d=ImageDraw.Draw(im);f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
d.text((30,20),'HIDX DISTINCT JOINT SOURCE MODEL — TERMINAL NATIVE PACKING FAIL',font=f,fill='#a00000')
d.text((30,52),'Cohort allocation only; no complete new site plan, placement, CTS or route',font=f,fill='black')
for g,r in regions.items():
 x0=45+r['x0']*.50;x1=45+r['x1']*.50;y0=120+r['row0']*4.3;y1=120+(r['row0']+r['rows'])*4.3
 col='#ffd2d2' if r['atom_reservation_ratio']>1 else '#dce8f5'
 d.rectangle((x0,y0,x1,y1),fill=col,outline='black');d.text((x0+4,y0+4),g,font=f,fill='black');d.text((x0+4,y0+29),format(r['ordinary_fill']*100,'.1f')+'% cells',font=f,fill='black');d.text((x0+4,y0+54),format(r['atom_reservation_ratio']*100,'.1f')+'% atoms',font=f,fill='#900000' if r['atom_reservation_ratio']>1 else 'black')
d.text((30,610),'Red: genuine functional atom reservations exceed cohort region; first pack failure pair[0], 39 sites.',font=f,fill='#a00000')
d.text((30,645),'Native mass 40–60% is necessary but insufficient. All 31,384 contacts remain HOLD.',font=f,fill='black')
d.text((30,680),'Original actual checkpoint 70042afe and every predecessor failure are preserved unchanged.',font=f,fill='black')
im.save(P/'SOURCE_FAILURE.png')
print(json.dumps({'status':verdict['status'],'overfull_regions':{g:r['atom_reservation_ratio'] for g,r in regions.items() if r['atom_reservation_ratio']>1}},indent=2))
