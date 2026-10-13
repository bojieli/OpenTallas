# usage (repo root): python3 tools/qwen_tp8/cut_residuals.py ITDIR/rom_tp8b.json [drop_fam,...]  -> fine cuts > 0.55 (CAP_MODE v3)
import sys, json
sys.path.insert(0,'results/arch/qwen_tp8_1012')
import cuts as C
C.CAP_MODE='v3'
d=json.load(open(sys.argv[1])); drop=set(sys.argv[2].split(',')) if len(sys.argv)>2 else set()
d['buses']=[b for b in d['buses'] if b[1] not in drop]
import tempfile, os
TMP=os.path.join(tempfile.gettempdir(),'cut_residuals_x.json')
json.dump(d,open(TMP,'w'))
A=C.Net(''+__import__('tempfile').gettempdir()+'/cut_residuals_x.json')
for r in A.fine(top=25):
    if r['util']>0.55: print(r['ax'],r['pos'],r['win'],r['bits'],r['usable'],float(r['util']),{str(k):v for k,v in r['fam'].items()})
