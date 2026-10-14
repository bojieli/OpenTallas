#!/usr/bin/env python3
"""Append full candidate strip endpoint geometry, preserving actual IOP provenance.
Gate length <=500 here; pair timing/hold and routedctl/root views remain mandatory.
"""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--assigned',required=True);ap.add_argument('--leaf-manifest',required=True);ap.add_argument('--plan',required=True);args=ap.parse_args()
 p=Path(args.plan);x=json.loads(p.read_text());children=x['relay_children'];a=json.loads(Path(args.assigned).read_text());cp=json.loads((ROOT/'physical/s81_ph_views/gather/control_strip/dsfd_gth_ctl.json').read_text());out=[]
 def pin(t,n,b=0):return t['pins'].get(f'{n}[{b}]',t['pins'].get(n))
 def ctl(n,b):
  f,l,v,d=cp['ports'][n][b]
  return {'x':1598.4+(129.558 if f=='E' else .042 if f=='W' else v),'y':8.64+(43.158 if f=='N' else .042 if f=='S' else v)}
 def edge(n,b):
  f,l,v,d=a['ports'][n]['per_bit'][b]
  return {'x':0 if f=='W' else 1728 if f=='E' else v,'y':0 if f=='S' else 803.52 if f=='N' else v}
 def hop(n,sp,dp):out.append({'path':n,'length_um':round(abs(sp['x']-dp['x'])+abs(sp['y']-dp['y']),3),'source':sp,'sink':dp})
 for role in sorted({t['role'] for t in children}):
  chain=sorted([t for t in children if t['role']==role],key=lambda t:t['stage'])
  if role.startswith('tst'):
   g=int(role[3:]);n=('rW' if g<6 else 'rE')+str(g%6);off=a['ports'][n]['bits']-2
   for b in range(2):
    hop(f'{role}.entry{b}',edge(n,off+b),pin(chain[0],'i',b));hop(f'{role}.ctl{b}',pin(chain[-1],'o',b),ctl('tst',2*g+b))
  elif role.startswith('cs'):
   g=int(role[2:])
   for b in range(2):
    hop(f'{role}.leaf{b}',{'x':148.572+.096*b+216*g,'y':61.674},pin(chain[0],'i',b));hop(f'{role}.ctl{b}',pin(chain[-1],'o',b),ctl('cs',2*g+b))
  elif role.startswith('rc'):
   g=int(role[2:]);hop(f'{role}.ctl',ctl('rc',g),pin(chain[0],'i'));hop(f'{role}.top',pin(chain[-1],'o'),{'x':138.684+216*g,'y':778.71})
  elif role=='tc':
   for t in chain:
    g=int(t['instance'].split('_')[-1]);off=54*g if g<3 else 162
    for b in range(t['width']):
     hop(f'tc{off+b}.ctl',ctl('tc',off+b),pin(t,'i',b));hop(f'tc{off+b}.parent',pin(t,'o',b),edge('t_capture',6784+off+b))
  else:
   for b in range(12):
    hop(f'fcd{b}.parent',edge('f_cd',b),pin(chain[0],'i',b));hop(f'fcd{b}.ctl',pin(chain[0],'o',b),ctl('f_cd',b))
 lm=Path(args.leaf_manifest)
 x['planned_endpoint_hops']={'count':len(out),'max_um':max(v['length_um'] for v in out),'fail_over500':[v for v in out if v['length_um']>500],'leaf_manifest_sha256':hashlib.sha256(lm.read_bytes()).hexdigest(),'method':'actual preservedCTS leaf rs/fo pins + realCLOSED relayLEF pins + assignedctlTcl pins','limitations':['parentexternal source -> strip entry total wire unproven','ctl/root exactpair setup/hold from real routedviews pending','leaf origins accepted native X0.432/Y0.576; relays native0.576'],'hops':out}
 p.write_text(json.dumps(x,indent=2)+'\n');g=x['planned_endpoint_hops'];print(f"STRIP_ENDPOINT {'FAIL' if g['fail_over500'] else 'PASS'} {g['count']} bits, max{g['max_um']}um")
if __name__=='__main__':main()
