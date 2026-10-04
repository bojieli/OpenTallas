import pathlib,struct,json,time,datetime,hashlib,subprocess,re
pid=568829
base=pathlib.Path('/home/ubuntu/otjobs/dsrom-headreg-c411a972b')
obj=base/'run/obj_parity_relay_gw4';out=base/'live-inspection'
exe=obj/'Vtb_dsrom_collective_headreg'
assert pathlib.Path(f'/proc/{pid}/exe').resolve()==exe
layout=(out/'layout_detailed.txt').read_text().splitlines()
root_offset=int(layout[0].split()[1])
fields=[(n,int(o),int(s)) for n,o,s in (line.split() for line in layout[1:])]
maps=pathlib.Path(f'/proc/{pid}/maps').read_text().splitlines()
load=int(next(x.split()[0].split('-')[0] for x in maps if str(exe) in x and x.split()[2]=='00000000'),16)
nm=subprocess.check_output(['nm','-C',str(exe)],text=True)
vtable=int(next(x.split()[0] for x in nm.splitlines() if x.endswith('vtable for Vtb_dsrom_collective_headreg')),16)+load+16
mem=open(f'/proc/{pid}/mem','rb',buffering=0)
roots=[]
for mapping in maps:
 if '[heap]' not in mapping:continue
 lo,hi=[int(x,16) for x in mapping.split()[0].split('-')]
 mem.seek(lo);data=mem.read(hi-lo);needle=struct.pack('<Q',vtable)
 start=0
 while True:
  at=data.find(needle,start)
  if at<0:break
  model=lo+at;mem.seek(model+root_offset);root=struct.unpack('<Q',mem.read(8))[0]
  roots.append((model,root));start=at+8
assert len(roots)==1,roots
model,root=roots[0]
record={'pid':pid,'scope':'Read-only existing process state, no pause/restart/replay or memory writes',
 'source_commit':'c411a972b','exe_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),
 'layout_header_sha256':hashlib.sha256((obj/'Vtb_dsrom_collective_headreg___024root.h').read_bytes()).hexdigest(),
 'model_address':hex(model),'root_address':hex(root),'samples':[]}
for sample in range(2):
 values={}
 for name,offset,size in fields:
  mem.seek(root+offset);b=mem.read(size)
  key=name.removeprefix('tb_dsrom_collective_headreg__DOT__')
  if key in ('cyc','sent','received'):values[key]=list(struct.unpack('<'+'I'*(size//4),b))
  else:values[key]=list(b)
 record['samples'].append({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fields':values})
 if sample==0:time.sleep(5)
p=out/'live_state_samples_r2.json'
with p.open('x') as f:json.dump(record,f,indent=2)
for sample in record['samples']:
 print(sample['utc'],{k:v for k,v in sample['fields'].items() if k in ('cyc','sent','received','valid','ready','fault','code','ov')})
print('SAVED',p)
