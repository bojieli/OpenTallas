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
ledger=dict(source_branch='claude/kv-kvsctl4-1027@bc1a556176',proof='codex-lec-0815/kvsctl_composed_fp/composed_proof.json',pins=6849,approved_dead_drop=250,added_live=added,pin_spacing_um=0.24,pin_density_per_um=4.1667,preserved_r26_entry=entry,source_pin_class=c['pin_class'],source_port_decl=c['port_decl'],added_bound_connections=c['report']['added'],cycles='KVSCTL3:166b retimed0;305b static-config +1;setup_ready+1boot; no token data-cycle delta')
(out/'kvs_ctl_pin_ledger.json').write_text(json.dumps(ledger,indent=1)+'\n')
print('KVSCTL_COMPLETE_VIEW',len(p['pins']),'added',len(added),'preserved_entry',entry)
