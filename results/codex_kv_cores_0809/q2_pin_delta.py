import hashlib,json,pathlib,re,sys
pd=pathlib.Path(sys.argv[1]); p=pd/'cores/qkd_ectlk_q2_pins_r25.json'; old=p.read_bytes();x=json.loads(old);changes=[]
for pin in x['pins']:
 m=re.fullmatch(r'si\[(\d+)\]',pin['name'])
 if m and 283<=int(m[1])<=536:
  prev=pin['name'];pin['name']='si_283['+m[1]+']';changes.append([prev,pin['name']])
assert len(changes)==254,len(changes)
p.write_text(json.dumps(x,indent=1)+'\n')
manifest=''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  cores/'+f.name+'\n' for f in sorted((pd/'cores').glob('*.json')))
(pd/'cores.sha256').write_text(manifest)
report=dict(rule='COORD 2026-10-27 07:38 approved q2 plan rename; actual RTL si_283[536:283]',old_sha256=hashlib.sha256(old).hexdigest(),new_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),changed_bits=254,geometry_changed=0,changes=changes)
(pd/'q2_pin_delta.json').write_text(json.dumps(report,indent=1)+'\n')
print('q2 pin names 254 renamed; geometry unchanged')
