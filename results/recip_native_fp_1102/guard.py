from pathlib import Path
import hashlib,json,sys
r=Path('/srv/opentallas-scratch2/claude/codex-recip-native-fp-0640');k=r/'kit';d=json.loads((r/'EXPECTED.json').read_text());bad=[]
for n,h in d['expected'].items():
 p=k/n
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=h:bad.append(n)
assert not bad,bad
base=k/'run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base';assert not any(base.glob('[3456]_*')),'unrequested later stage outputs'
if sys.argv[-1]=='post':
 assert (base/'2_floorplan.odb').is_file() and (base/'2_floorplan.sdc').is_file(),'normal FP not complete'
 assert all(hashlib.sha256((base/n).read_bytes()).hexdigest()==h for n,h in d['authentic_synth'].items()),'SYNTH changed'
print('MANUAL_PHYSICAL_CONTINUATION guardPASS',sys.argv[-1],len(d['expected']),'exact inputs; normalKWRS FULL retained')
