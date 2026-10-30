"""Pure NLDM+plan-wire model for adaptive A0 leaf geometry; never reads clock timing measurements."""
import sys,json,gzip,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path('tool_snapshot/tools/die_plan').resolve()))
import die_clock_128 as C
import core_infra_plan_metrics as M
src,census,kit,out,rep=sys.argv[1:]
sl=json.load(open(src));t=sl['core_tree']
points={};info={}
for line in gzip.open(census,'rt'):
 f=line.rstrip().split('\t')
 if f[0]!='S':continue
 key=f[3]+'/'+f[4];points[key]=[float(f[6]),float(f[7])];info[key]=(f[5],f[4])
pts={k:points[k] for l in t['leaves'] for k in l['sinks']}
names=sorted({n['master'] for n in t['nodes']});gnames=sorted({g['master'] for g in t['gates']})
libs={};caps={k:{} for k in pts}
for corner in ('TT','FF'):
 L=C.lib_cells(corner,'lib',names);L.update(M.icg_lib_cells(corner,'lib',gnames));libs[corner]=L
 sf=next(Path('lib').glob(f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_*.lib*'))
 seq=(gzip.open if sf.suffix=='.gz' else open)(sf,'rt').read()
 cache={}
 for key in pts:
  master,pin=info[key]
  if (master,pin) not in cache:
   if master.startswith('ot_'):txt=Path(kit,'macros',f'{master}_{corner.lower()}.lib').read_text()
   else:
    i=seq.index(f'cell ({master})');j=seq.find('\n  cell (',i+10);txt=seq[i:j if j>=0 else len(seq)]
   pat=r'pin\s*\(\s*"?'+re.escape(pin)+r'"?\s*\)\s*\{.*?\b(?:rise_)?capacitance\s*:\s*([0-9.eE+-]+)'
   m=re.search(pat,txt,re.S)
   if m is None:raise ValueError(('missing actual clock pin cap',master,pin))
   cache[master,pin]=float(m[1])
  caps[key][corner]=cache[master,pin]
model=M.predict_tree(sl,libs,pts,caps,.018515*.8,.17137*.9,input_slew_ps=20.)
q={'measured_timing_used':False,'band_policy':'info','window_policy':'info','corners':{}}
for corner,row in model['corners'].items():
 q['corners'][corner]=dict(leaf_min=row['min_ps'],leaf_max=row['max_ps'],leaf_window=row['window_ps'],slew_max=row['slew_max_ps'])
 print(corner,json.dumps(q['corners'][corner]))
t['model_qualification']=q
json.dump(sl,open(out,'w'),indent=1);json.dump(model,open(rep,'w'),indent=1)
