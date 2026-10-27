import sys,pathlib,json,collections
sys.path.insert(0,'eng/tools/die_plan')
import lec
p=pathlib.Path('pv')
L=lec.Lec(lec.read_aig(p/'gold.aig'),lec.read_map(p/'gold.map'),lec.read_aig(p/'gate.aig'),lec.read_map(p/'gate.map'))
h=json.load(open(p/'hyp.json')); print(type(h),str(h)[:1000],flush=True)
