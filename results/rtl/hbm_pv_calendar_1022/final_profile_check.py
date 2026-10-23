from pathlib import Path
import sys,json,hashlib,tempfile,copy
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'repo/tools'))
from hbm_layer_vehicle.native_profile import NativePretreeTiming
p=json.loads((root/'pretree_profile.json').read_text())
for k,v in p['sources'].items():
    v['module']='ot_hbm_su_red_pretree_s_m72' if k=='slice' else 'ot_hbm_su_red_pretree_j_r13_m73'
final=root/'pretree_profile_final.json';final.write_text(json.dumps(p,indent=2)+'\n')
assert NativePretreeTiming.load(final).tree_to_reducer==77
caught=[]
with tempfile.TemporaryDirectory(dir=root) as d:
    q=Path(d)/'bad.json'
    for label in ['changed_source','wrong_module','wrong_age']:
        bad=copy.deepcopy(p)
        if label=='changed_source':bad['sources']['slice']['sha256']='0'*64
        if label=='wrong_module':bad['sources']['join']['module']='nonexistent_selected_join'
        if label=='wrong_age':bad['tree_to_reducer']=69
        q.write_text(json.dumps(bad))
        try:NativePretreeTiming.load(q)
        except ValueError:caught.append(label)
        else:raise AssertionError('unsafe profile accepted: '+label)
print(json.dumps(dict(status='PASS',real_profile=NativePretreeTiming.load(final).as_dict(),causal_negatives_caught=caught),indent=2))
