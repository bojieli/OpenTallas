from pathlib import Path
import json,sys
sys.path.insert(0,str(Path('tools/die_plan').resolve()))
import die_trial as D
import schema as S
import die_infra as DI
p=Path('/srv/opentallas-scratch2/claude/codex-kv-25-1029/inputs/event/plan_sites_astk.json')
P=S.Plan(S.load(p),p);out=Path('pgkit')
for x in ['abstracts','psm','grt']: (out/x).mkdir(parents=True,exist_ok=True)
mods=D.standin_module_names(P);lefs=[]
for tn in sorted(P.types):
 txt,st=D.abstract_lef(P,tn,module_name=mods[tn])
 fn=mods[tn]+'.lef';(out/'abstracts'/fn).write_text(txt);lefs.append(fn)
 print('ABSTRACT',tn,flush=True)
(out/'psm/psm.v').write_text('\n'.join([f'module {D.sv(P.name)}_psm ();']+[f'  {mods[q["type"]]} {D.sv(n)} ();' for n,q in sorted(P.parts.items())]+['endmodule'])+'\n')
(out/'psm/pdn.tcl').write_text(D.psm_pdn_tcl(P))
(out/'grt/tracks.tcl').write_text(D.coarse_tracks(P,1.08))
s=D.psm_tcl(P,lefs,{},[]);s=s[:s.index('source /work/psm/bumps.tcl')]
s+='\nputs PG_GEOMETRY_ONLY_DONE\nexit\n';(out/'psm/pg_only.tcl').write_text(s)
R=DI.pg_rects(P,DI.pg_grid(P))
Path('pg_model_rects.json').write_text(json.dumps(R))
print('PG_MODEL_RECTS',len(R),'PG_PREP_DONE',flush=True)
