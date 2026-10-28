from pathlib import Path
import json,lec
P=Path('/old');L=lec.Lec(lec.read_aig(P/'gold.aig'),lec.read_map(P/'gold.map'),lec.read_aig(P/'gate.aig'),lec.read_map(P/'gate.map'))
lec.noreset_classify(L)
result=[]
for s,k,h in json.load(open(P/'hints.json')):
 if k in ['ff:u_dut._80365_']+['ff:u_dut._'+str(n)+'_' for n in range(80394,80401)]:
  result.append(dict(gate=k,gold=h[2],gate_base=L.rst_val.get(('gate',k)),gold_base=L.rst_val.get(('gold',h[2]))))
print(json.dumps(result,indent=1))
Path('/work/base.json').write_text(json.dumps(result,indent=1))
