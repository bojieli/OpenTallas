import json,re,sys,hashlib,collections,math
from pathlib import Path
B=Path('/srv/opentallas-scratch/claude/hd4g/gen2d');P=B/'forest_codex9d5a2c350';C=Path('/srv/opentallas-scratch/claude/hd4g/gen2c/case_a')
sys.path.insert(0,str(B/'forest_1e3fbe31b/hhpref/src/tools/hbm_die_v16'))
from reset_forest_geometry import Geometry,md
c=json.load(open(P/'contract_pre.json'));m=json.load(open(P/'manifest.json'));g=Geometry(m,P/'views',P/'relay_views',405,overfly='hbfd_(rly|lh|land)')
p=(12761.158,19794.988);r={'point':p,'hashes':{str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in [P/'contract_pre.json',P/'manifest.json',C/'run.tcl']}}
cl=[]
for l in open(C/'run.tcl'):
 a=re.search(r'place_inst -name (dkh_\S+) -location \{([\d.]+) ([\d.]+)\}',l)
 if a:
  n,x,y=a.groups();cl.append(dict(name=n,xy=[float(x),float(y)],distance=md(p,(float(x),float(y)))))
r['clock_buffers_nearest']=sorted(cl,key=lambda a:a['distance'])[:12];r['clock_buffers_total']=len(cl)
names={x['name'] for x in r['clock_buffers_nearest']};decs={};nets=set()
for l in open(C/'die.v'):
 if any(n+' ' in l for n in names):
  if len(l)<2000:
   for n in names:
    if n+' ' in l:decs[n]=l.strip();nets.update(re.findall(r'\.A\((\w+)\)',l))
r['clock_declarations']=decs
# A bounded three-stage distinct local reservation, not a whole forest retry.
snap=g.snapshot();tile=g.reserve('hop',p,targets=[('rst_n_in',p)]);r['local_carrier']=dict(tile,input=g.tile_pin(tile,'rst_n_in'),output=g.tile_pin(tile,'rst_n'),clk=g.tile_pin(tile,'clk'))
r['local_clock_candidates']=[dict(x,clk_span=md(x['xy'],g.tile_pin(tile,'clk'))) for x in r['clock_buffers_nearest']]
r['all_clock_occupancy_checked']=False
r['source_pll_pin']=g.pin('hb_ckgen','pll_hbm');r['raw_por_pin']=g.pin('hb_ckgen','por_hbm')
r['direct_clock_distance']=md(r['source_pll_pin'],r['local_carrier']['clk']);r['clock_min405spans']=math.ceil(r['direct_clock_distance']/405)
r['note']='Clock xy is standard-cell origin; native Y contact, fanout, waveform and complete occupancy require source/LEF binding.'
print(json.dumps(r,indent=2))
