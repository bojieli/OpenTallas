import hashlib,importlib.util,json,pathlib,sys,collections,re
w=pathlib.Path(sys.argv[1]); pd=pathlib.Path(sys.argv[2]); out=pathlib.Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
h=w/'physical/die_plan/qwen_kvsys/cores/harden';sys.path.insert(0,str(h))
import gen_core_kit_kv as g
c=json.load(open(w/'results/kv_cores_r2/kvsctl3/rtl/qkd_kvs_ctl_core.json'))
p=json.load(open(w/'results/kv_core_slice_1/pd_slice_delta/cores/kvs_ctl_pins.json'));old=json.load(open(pd/'cores/kvs_ctl_pins.json'))
by={x['name']:x for x in old['pins']}
entry=[]
for pin in p['pins']:
 if pin['name'] in ('ck[0]','rst_n[0]','rst_n','ck') and pin['name'] in by:
  pin.update(by[pin['name']]);entry.append(pin.copy())
want=set(c['pin_class']);have={x['name'] for x in p['pins']}
assert not have-want, sorted(have-want)[:5]
def order(n):
 m=re.fullmatch(r'(.*)\[(\d+)\]',n)
 return (m[1],int(m[2])) if m else (n,-1)
added=[dict(name=n,layer='M5',x=round(149.4+0.24*j,3),y=0.096) for j,n in enumerate(sorted(want-have,key=order))]
assert len(added)==304
p['pins']+=added;p['source']+=' | CODEX: complete approved KVSCTL2 dead-drop plus304 existing live cut bits; R26 clock/reset entry preserved'
# Whole quadrant bundles follow their physical direction; redistribute the
# north ingress buses to the corresponding west/east glue channels.
move={'o_hroot_WN':'N','i_hroot_WN':'N','o_hroot_ES':'S','i_hroot_ES':'S','d2d__srx_10':'W','embgw__bw':'E'}
facepins={f:[] for f in 'WENS'}
for pin in p['pins']:
 d,f=min((pin['x'],'W'),(371.52-pin['x'],'E'),(pin['y'],'S'),(371.52-pin['y'],'N'))
 if d>0.5:continue
 f=move.get(pin['name'].split('[')[0],f);facepins[f].append(pin)
for f,pins in facepins.items():
 def faceorder(pin):
  base=pin['name'].split('[')[0]
  group=0
  if f=='W':group=0 if base in ('o_hroot_WS','i_hroot_WS') else 1
  if f=='N':group=0 if base in ('o_hroot_WN','i_hroot_WN') else 1
  if f=='E':group=1 if base in ('o_hroot_EN','i_hroot_EN') else 0
  if f=='S':group=1 if base in ('o_hroot_ES','i_hroot_ES') else 0
  return (group,*order(pin['name']))
 pins.sort(key=faceorder);layer='M4' if f in 'WE' else 'M5'
 start=g.OFFS[layer]+g.PITCH[layer]*round((185.76-(len(pins)-1)*0.192/2-g.OFFS[layer])/g.PITCH[layer])
 for j,pin in enumerate(pins):
  a=round(start+j*0.192,3);pin['layer']=layer
  pin['x'],pin['y']=((0.096 if f=='W' else 371.424),a) if f in 'WE' else (a,(0.096 if f=='S' else 371.424))
added=[pin for pin in p['pins'] if pin['name'] in want-have]
p['source']+=' | CODEX physical repair: whole WN/ES quadrant bundles re-faced N/S; d2d_srx west ingress, embgw east glue; all face buses ordered at0.192um pitch'
assert len(p['pins'])==len(want)==6849
assert len({x['name'] for x in p['pins']})==6849
assert len({(x['layer'],x['x'],x['y']) for x in p['pins']})==6849
faces={}
for pin in p['pins']:
 d,face=min((pin['x'],'W'),(371.52-pin['x'],'E'),(pin['y'],'S'),(371.52-pin['y'],'N'))
 if d>0.5:continue
 f=faces.setdefault(face,dict(pins=0,layers=[]));f['pins']+=1
 if pin['layer'] not in f['layers']:f['layers'].append(pin['layer'])
p['faces']=faces;p['frame']='core R0, origin (0,0), outline 371.52 x 371.52'
(out/'kvs_ctl_pins_complete.json').write_text(json.dumps(p,indent=1)+'\n')
parent_path=w/'results/kv_cores_r2/kvsctl3/kit_rtl/kv3_hub_C/kv3_hub_C_part_bound.sv'
text=parent_path.read_text();begin=text.index('qkd_kvs_ctl u_kvs_ctl (')+len('qkd_kvs_ctl u_kvs_ctl (');depth=1;end=begin
while depth:
 if text[end]=='(':depth+=1
 if text[end]==')':depth-=1
 end+=1
args=text[begin:end-1];parent_connections={}
for m in re.finditer(r'\.(\w+)\s*\(',args):
 start=m.end();stop=start;depth=1
 while depth:
  if args[stop]=='(':depth+=1
  if args[stop]==')':depth-=1
  stop+=1
 parent_connections[m[1]]=args[start:stop-1].strip()
assert set(parent_connections)==set(c['port_decl']), (len(parent_connections),set(c['port_decl'])-set(parent_connections))
peak10={}
for f,pins in facepins.items():
 xs=sorted(q['y'] if f in 'WE' else q['x'] for q in pins);j=0;peak=0
 for a,v in enumerate(xs):
  while v-xs[j]>10:j+=1
  peak=max(peak,a-j+1)
 assert peak<=60,(f,peak)
 peak10[f]=peak
ledger=dict(source_branch='claude/kv-kvsctl4-1027@bc1a556176',proof='codex-lec-0815/kvsctl_composed_fp/composed_proof.json',pins=6849,approved_dead_drop=250,added_live=added,pin_spacing_um=0.192,pin_density_per_um=5.3,whole_bus_face_moves=move,face_counts={f:len(q) for f,q in facepins.items()},preserved_r26_entry=entry,source_pin_class=c['pin_class'],source_port_decl=c['port_decl'],parent_source=str(parent_path.relative_to(w)),parent_sha256=hashlib.sha256(parent_path.read_bytes()).hexdigest(),parent_connections=parent_connections,peak_pins_per_10um=peak10,added_bound_connections=c['report']['added'],cycles='RTL unchanged from approved KVSCTL3:166b retimed0,305b static-config andsetup_ready+1boot; parentplan must recheckreach/relaycalendar onmovedports beforefreeze')
(out/'kvs_ctl_pin_ledger.json').write_text(json.dumps(ledger,indent=1)+'\n')
print('KVSCTL_COMPLETE_VIEW',len(p['pins']),'added',len(added),'preserved_entry',entry)
