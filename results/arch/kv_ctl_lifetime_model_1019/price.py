import json,re,collections,pathlib,hashlib
p=pathlib.Path(__file__).parent;f=json.load(open(p/'fixedpoint.json'));inv=json.load(open(p/'pin_inventory.json'));area=collections.defaultdict(float);clock=collections.Counter();resets=collections.Counter()
for r in f['copies']:
 n=r['total_copies']-1;area[r['kind']]+=n*inv['masters'][r['master']]['area_um2']
 if r['kind']=='FF':
  name=r['driver'].rsplit('/',1)[0]
  for pin in inv['instance_inputs'][name]:
   if pin['pin'] in ('CLK','CK'):clock[pin['net']]+=n
   if pin['pin'] in ('RESETN','SETN'):resets[pin['net']]+=n
f['native_copy_area_um2']=dict(area);f['native_copy_total_area_um2']=sum(area.values());f['extra_clock_pin_contacts_by_native_net']=dict(clock);f['extra_async_pin_contacts_by_native_net']=dict(resets)
f['price_scope']='Exact existing master area, not resynthesis area or power. FF master clock contacts included by net. No Liberty caps or kept-copy realization claimed.'
json.dump(f,open(p/'fixedpoint.json','w'),indent=2)
s=(p/'n64.lef').read_text();faces=collections.defaultdict(list)
for name,body in re.findall(r'\n  PIN (\S+)\n(.*?)\n  END \S+',s,re.S):
 if 'USE POWER' in body or 'USE GROUND' in body:continue
 for a,b,c,d in re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',body):
  x1,y1,x2,y2=map(float,(a,b,c,d));faces['W' if x1==0 else 'E'].append(dict(pin=name,y_um=(y1+y2)/2))
out={}
for face,pins in faces.items():
 pins.sort(key=lambda r:r['y_um']);ds=[b['y_um']-a['y_um'] for a,b in zip(pins,pins[1:])]
 out[face]=dict(contact_count=len(pins),min_pitch_um=min(ds),local_contacts_per_um=1/min(ds),first_center_um=pins[0]['y_um'],last_center_um=pins[-1]['y_um'],occupied_span_um=pins[-1]['y_um']-pins[0]['y_um'],contacts=pins)
json.dump(dict(source_commit='bc42f77a8',lef_sha256=hashlib.sha256(s.encode()).hexdigest(),verdict='HOLD_CLUSTERED_ACCESS_NOT_QUALIFIED',face_height_um=27.576,faces=out,scope='Pin centers only. No escape routing, OBS/via/PG, parent grid or dualclock physical guarantee.'),open(p/'contact_audit.json','w'),indent=2)
print('area',dict(area),sum(area.values()));print('clock',dict(clock));print({k:{a:b for a,b in v.items()if a!='contacts'}for k,v in out.items()})
