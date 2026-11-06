from pathlib import Path
import json,hashlib,re
p=Path(__file__).parent;old=json.load(open(p.parent/'main_pins.json'))
for width,variant in [(103.68,'A'),(120.96,'B')]:
 a=json.loads(json.dumps(old))
 for x in a:
  bus=x.get('bus',x.get('name','').split('[')[0]);idx=x.get('bit')
  if idx is None:
   m=re.search(r'\[(\d+)\]',x.get('name',''));idx=int(m[1]) if m else 0
  if abs(x['x']-86.304)<.001:x['x']=round(width-.096,3)
  if bus=='g_d':g,bit=divmod(idx,286);x['y']=round(50.76+55.08*g+.096*bit,3)
  if bus in ('g_v','g_credit'):
   x['y']=round(50.76+55.08*idx+27.456+(0 if bus=='g_v' else .096),3)
  if bus in ('hbm_clk','stream_clk'):x['x']=round(x['x']+(width-86.4)/2,3)
 positions={}
 for x in a:
  key=x['x'],x['y'];assert key not in positions,(key,x,positions.get(key));positions[key]=x
 path=p/f'main_wide{variant}_{width:.2f}_candidate.json';path.write_text(json.dumps(a,indent=1)+'\n')
 print(variant,width,len(a),hashlib.sha256(path.read_bytes()).hexdigest())
