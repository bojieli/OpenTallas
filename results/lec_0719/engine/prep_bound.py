import pathlib
import lec_struct as L

def prep_only(*args,**kwargs):
    raise L.Unproven('AIG preparation only; no equivalence verdict attempted')
L.correspond=prep_only
p=pathlib.Path('/work/eng_bound')
r=L.check('/work/eng_boundkit',out=p)
assert r['verdict']=='UNPROVEN' and r.get('reason')=='AIG preparation only; no equivalence verdict attempted',r
assert all((p/n).is_file() for n in ['gold.aig','gate.aig','gold.map','gate.map'])
print('AIG_PREPARED (equivalence NOT RUN)',flush=True)
