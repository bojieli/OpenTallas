from pathlib import Path
import json,hashlib
from collections import Counter
p=Path(__file__).parent

def rd(f):
 d={}
 for s in (p/f).read_text().splitlines():
  a=s.split('\t');k=tuple(a[:3]) if a[0]=='FF_INPUT' else tuple(a[:2]);d[k]=a[3:] if a[0]=='FF_INPUT' else a[2:]
 return d

def clk(f):return {a[0]:a[1:] for a in (s.split('\t') for s in (p/f).read_text().splitlines())}
a=rd('repaired_baseline_hb_structure.tsv');b=rd('repaired_repaired_hb_structure.tsv')
assert not a.keys()-b.keys()
for k,v in a.items():
 assert v==b[k] if k[0] in ('FF_INPUT','PORT') else v[0]==b[k][0], k
x=clk('baseline_clockpaths_static.tsv');y=clk('repaired_clockpaths_static.tsv');assert x.keys()==y.keys()
diff=[n for n in x if x[n]!=y[n]];assert len(diff)==64
for n in diff:
 before=x[n][2].split();after=[m for c,m in zip(y[n][1].split(),y[n][2].split()) if not c.startswith('ot_eclk_real_stage_')]
 assert before==after and int(y[n][0])==int(x[n][0])+3,n
clockcells={c for v in x.values() for c in v[1].split()}
clock_moved=[n for n in clockcells if a[('INST',n)]!=b[('INST',n)]]
assert (p/'baseline_native_ff_fanout.tsv').read_bytes()==(p/'repaired_native_ff_fanout.tsv').read_bytes()
added={k:v for k,v in b.items() if k not in a and k[0]=='INST'}
fan=sorted((int(a[2]),a[0],a[1]) for a in (s.split('\t') for s in (p/'repaired_native_ff_fanout.tsv').read_text().splitlines()))
report=dict(source='b30f8454c6db1309ee4ec7a154943f6c737b43f2',diagnostic_only=True,adoption=False,original_cells=72883,original_masters_unchanged=True,ports_unchanged=3670,ff_input_equations_unchanged=27576,clock_population=10967,changed_E_clock_paths=64,unchanged_other_clock_paths=10903,original_clock_cells_moved=len(clock_moved),original_clock_cells_moved_names=clock_moved,E_clock_levels_before=13,E_clock_levels_after=16,original_clock_master_polarities_unchanged=True,added_cell_masters=dict(Counter(v[0] for v in added.values())),original_cells_legally_moved=sum(a[k]!=b[k] for k in a if k[0]=='INST'),native_ff_fanout_identical_to_original=True,native_ff_outputs_over32=sum(v[0]>32 for v in fan),native_ff_fanout_max=fan[-1][0],fanout_top10=fan[-10:],TT=dict(setup_ps=96.496696,hold_ps=37.962635,boundary_spread_ps=70.090698),FF=dict(setup_ps=199.703476,hold_ps=30.002916,boundary_spread_ps=64.026001),remaining_blockers=['64 native FF outputs exceed32 buffer-collapsed loads','two SRAM clock slew violations TT274.6744/267.3019 FF285.7455/278.0821 versus260ps','104 new open power/ground pins before global-connect; baseline43204 open too','routed clock corridor and full escape DRC not qualified'])
(p/'d2d_eclock_prototype_audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
