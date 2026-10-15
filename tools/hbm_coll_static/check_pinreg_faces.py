#!/usr/bin/env python3
"""Mapped direct launch/capture faces and real macro-address audit."""
import argparse,json,pathlib
p=argparse.ArgumentParser();p.add_argument('netlist',type=pathlib.Path);p.add_argument('out',type=pathlib.Path);a=p.parse_args()
m=json.loads(a.netlist.read_text())['modules']['ot_hgi_coll_static_link_pinreg']
q={};ds={};clockbits=m['ports']['ck']['bits'];counts=[0]*5
for name,c in m['cells'].items():
 if 'dff' in c['type'].lower():
  root=c['connections'].get('C',c['connections'].get('CLK'))[0]
  assert root in clockbits,(name,root)
  i=clockbits.index(root);counts[i]+=len(c['connections']['Q'])
  for b in c['connections']['Q']:q[b]=i
  for b in c['connections']['D']:ds.setdefault(b,set()).add(i)
def ff(bits,root,label):
 for b in bits:
  assert (b in ('0','1') if isinstance(b,str) else b in q and q[b]==root),(label,b,'not direct root Q')
 return len([b for b in bits if isinstance(b,int)])
checks={}
for name,port in m['ports'].items():
 if port['direction']=='output':checks['output.'+name]=ff(port['bits'],0,name)
for n in ['bank_we','bank_wa','bank_ra','bank_data']:
 bits=m['netnames'][n]['bits'];checks[n]=ff(bits,0,n)
 for i in range(1,5):
  # wa/ra/we fan out to every bank; data stripes captured only by their bank.
  if n!='bank_data':
   assert all(isinstance(b,str) or i in ds.get(b,set()) for b in bits),(n,i,'missing capture FF')
for i in range(4):
 outbits=m['netnames'][f'g_bank[{i}].u_store.dout']['bits'][:(141 if i<3 else 138)]
 checks[f'bank{i}.dout']=ff(outbits,i+1,f'bank{i}.dout')
 assert all(0 in ds.get(b,set()) for b in outbits if isinstance(b,int)),(i,'missing controller q_data capture')
 prefix=f'g_bank[{i}].u_store.'
 for n in ['we_pin','wa_pin','ra_pin','din_pin']:
  bits=m['netnames'][prefix+n]['bits'];checks[prefix+n]=ff(bits,i+1,prefix+n)
  # Every physical input capture D must come straight from a controller launch Q.
  # Optimized nonobservable high padding is allowed constant, never X on used bits.
  launch=['bank_we'] if n=='we_pin' else ['bank_wa'] if n=='wa_pin' else ['bank_ra'] if n=='ra_pin' else ['bank_data']
  launchbits=set(m['netnames'][launch[0]]['bits'])
  captures=[c for c in m['cells'].values() if 'dff' in c['type'].lower() and any(b in bits for b in c['connections']['Q'])]
  for c in captures:
   for qb,db in zip(c['connections']['Q'],c['connections']['D']):
    if qb in bits:assert db in launchbits or db in ('0','1'),(prefix,n,'nonlaunch capture D',db)
macros=[(n,c) for n,c in m['cells'].items() if c['type']=='ot_sram_1r1w_64x512_m1_r2c2']
assert len(macros)==4
for n,c in macros:
 i=int(n.split('[')[1].split(']')[0])+1
 for port in ['r_addr_in','w_addr_in','w_ce_in','wd_in']:
  checks[n+'.'+port]=ff(c['connections'][port],i,n+'.'+port)
 # Macro read port must specifically use the pin capture Q, not another root.
 assert c['connections']['r_addr_in']==m['netnames'][f'g_bank[{i-1}].u_store.ra_pin']['bits']
assert all(n<15000 for n in counts),counts
result=dict(status='PASS',top='ot_hgi_coll_static_link_pinreg',checks=checks,register_bits_per_root=counts,
 actual_macro_count=4,scope='mapped generic gate FF-Q launch/capture and all macro input faces; no route or TT/FF timing claim')
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
