import json,re,pathlib
r=json.load(open(pathlib.Path(__file__).with_name('cuts_today.json')))
def vmwide(f): return bool(re.match(r'(hgi_lg|hgi_vmr2|hgi_vmw|hgi_vmap|hb_vm_su|hb_su_(SW|SE|NW|NE)_vm|xt|rt_|hgi_vmq)',f))
def lane(f): return f.startswith('hgi_lg')
RING=2*(2048+2048+200)    # two ring links cross any centre line, each 2,048 b each way + ~100 b ctrl each way
COLLB=2*(1024+64)         # coll -> slice broadcast tree: two branches cross a centre line
out={}
for k,v in r.items():
  if k=='lane_group_buses': continue
  f=v['fam']; tot=v['bits']; vw=sum(b for n,b in f.items() if vmwide(n)); lg=sum(b for n,b in f.items() if lane(n))
  b2=tot-vw+RING+COLLB
  c_full=tot   # C, 32-lane groups kept: same hub cut bits
  c_half=tot-vw/2
  u=v['usable_tracks']
  out[k]=dict(bits=tot,lane=lg,vmwide=vw,usable=u,A=round(tot/u,3),B2_bits=b2,B2=round(b2/u,3),C32=round(c_full/u,3),C16=round(c_half/u,3))
  print(f"{k:14s} bits {tot:7d} lane {lg:6d} vmwide {vw:6d} usable {u:7d} A {tot/u:5.2f} B2 {b2:6d} {b2/u:5.2f} C16 {c_half/u:5.2f}")
json.dump(out,open(pathlib.Path(__file__).with_name('cuts_options.json'),'w'),indent=1)
