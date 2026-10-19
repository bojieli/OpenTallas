import hashlib,json,pathlib,subprocess
m=json.load(open('/src/diagnostic_manifest.json')); got={}
for k,v in m['source_hashes'].items():
 p=pathlib.Path('/OpenROAD-flow-scripts/flow/platforms/asap7')/k.split(':',1)[1] if k.startswith('platform:') else pathlib.Path('/src')/k.split(':',1)[1]
 h=hashlib.sha256(p.read_bytes()).hexdigest();got[k]=h
 assert h==v,(k,h,v)
for p,h in {'/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys':'5cd52bc790d39b1e59a88112e9132ef8de338c2a26e4b0df8222d937e65bab92','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad':'21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846'}.items():
 got[p]=hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest();assert got[p]==h,(p,got[p],h)
for p in sorted(pathlib.Path('/src').rglob('*')):
 if p.is_file():got[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
json.dump(got,open('/work/preflight_hashes.json','w'),indent=2)
print('PASS complete source/helper/platform/lib/binary preflight')
