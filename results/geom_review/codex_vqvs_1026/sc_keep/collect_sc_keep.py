import json,re,sys
from pathlib import Path
p=Path(sys.argv[1]); old=Path(sys.argv[2])
ids=['225277','225304','225558','225585','225830','225857']
def latches(path):
 return [line for line in path.read_text().splitlines() if line.startswith('latch ')]
def presence(lines):
 return {n: sorted({line.split()[1] for line in lines if f'.u_{n}.Q' in line}) for n in ids}
a=presence(latches(old));b=presence(latches(p/'current.map'));c=presence(latches(p/'mutant.map'))
rec={'scope':'actual SC gate-formal-preparation diagnostic, no full equivalence rerun','tool_fix':'fffc9dd55 GATE_PHYSICAL_FF_KEEP','old':a,'current':b,'deleted_physical_mutant':c,'restored':sum(bool(b[n]) and not a[n] for n in ids),'mutant_caught':not c[ids[0]],'others_preserved':all(c[n] for n in ids[1:])}
rec['verdict']='PASS' if rec['restored']==6 and rec['mutant_caught'] and rec['others_preserved'] else 'FAIL'
(p/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,indent=2))
