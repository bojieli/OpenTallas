import sys, json
from pathlib import Path
sys.path.insert(0,'/work')
from infra_replay import load_db, physical_snapshot, terminals
before,b=load_db('/work/replayed_before.odb');after,a=load_db('/work/replayed_after.odb')
r={'verdict':'PASS','scope':'actual small importer followed by signal GRT50; not die timing/IR/freeze','nets':{}}
for name in ['clk','VDD']:
 bn=b.findNet(name);an=a.findNet(name)
 before_shape=physical_snapshot(bn);after_shape=physical_snapshot(an)
 before_terms=terminals(bn);after_terms=terminals(an)
 assert before_shape==after_shape,(name,'physical changed')
 assert before_terms==after_terms,(name,'terminals changed')
 r['nets'][name]={'physical_before':before_shape,'physical_after':after_shape,'terminals':before_terms,'unchanged':True}
g=Path('/work/replayed_signals.guide').read_text()
names=[x for x in g.splitlines() if x and x not in ['(',')'] and not x[0].isdigit()]
assert set(names)=={'sig_in','sig_mid','sig_out'},names
r['signal_guide_nets']=names;r['grt_iterations_requested']=50
r['signal_terminals']={n:terminals(a.findNet(n)) for n in names}
Path('/work/replayed_proof.json').write_text(json.dumps(r,indent=2)+'\n')
print('ACTUAL_REPLAY_GRT_PRESERVE_PASS',names)
