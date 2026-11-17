import json,sys,collections
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/fable-fix-head-reset/rs1');sys.path.insert(0,str(R/'code/tools/die_plan'))
import schema as S, reset_tree as RT, pin_entry_phase as PH
def wf(path):
    raw=json.loads(Path(path).read_text());P=S.Plan(raw,str(path));return P,RT.wf_plan(P)
P0,w0=wf('/srv/opentallas-scratch2/claude/head-die-r/nf15e_e10/stage/prep_f1/source_plan.json')
P1,w1=wf(R/'prep_rs1/source_plan.json')
errs=PH.plan_errors(P1.raw);print('plan_errors',len(errs),errs[:3])
d={p:w1['parts'][p]['release']-w0['parts'][p]['release'] for p in w0['parts']}
print('parts',len(d),'max_release old/new',w0['max_release'],w1['max_release'],'delta hist',sorted(collections.Counter(d.values()).items()))
print('entry cell types',sorted(tn for tn in w1['types'] if RT.for_type(P1,tn).get('pin_entry_phase')).__len__(),'of',len(w1['types']),'root',w1['root'],w1['root_type'])
t=RT.for_type(P1,'hd_tile');print('hd_tile entry_stages',RT.entry_stages(t),'release_clocks',RT.release_clocks(t),RT.summary(t).get('pin_entry_phase'))
print([l for l in RT.rtl_lines(t) if 'ot_dp_rrelay_ph' in l][:2])
json.dump(dict(old_max_release=w0['max_release'],new_max_release=w1['max_release'],delta=d),open(R/'wf_rs1_delta.json','w'),indent=1)
