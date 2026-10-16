from pathlib import Path
import argparse, hashlib, importlib.util, json, os, shlex, sys
BASE=Path('/srv/opentallas-scratch/claude/s81-die-r10/src19')
OUT=Path('/srv/opentallas-scratch/codex/s81-pin-repair-1319')
sys.path[:0]=[str(BASE/'tools'),'/srv/opentallas-scratch/claude/s81-die-r10/deps']
import cloudpickle
which=sys.argv[1]
source=BASE/'tools/dsrom_s81_fulldie.py' if which=='baseline' else OUT/'tools/dsrom_s81_fulldie.py'
spec=importlib.util.spec_from_file_location('dsrom_s81_fulldie',source)
G=importlib.util.module_from_spec(spec);sys.modules[spec.name]=G;spec.loader.exec_module(G);G.ROOT=BASE
os.chdir(BASE)
p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--k',type=int,default=16);G.die_options(p)
opts=p.parse_args(['real']+shlex.split((BASE/'results/physical/die_iter_1012/s81/s81_layer1_gen19rb.opts').read_text()))
G.apply_options(opts);G.ALIGN_EXT[0]=True
cp=Path('/srv/opentallas-scratch/claude/s81-die-r10/gen19rb/model_before_finalize3.pickle')
with cp.open('rb') as f:m=cloudpickle.load(f)
for it in m["insts"]:
 if it.kind == "rly": G.RLY_FACES[it.master] = tuple(it.master.rsplit("_",1)[1])
G.finalize_r8(m)
texts=G.die_lef_texts(m);r=G.pin_align_gate(m,texts,raise_on_fail=False)
result=dict(which=which,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),checkpoint_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),legality=G.legality(m),pin_align=r,frozen_loads=list(m.get('spread_load_pin_maps',{})),native_qualified=False,scope='EXACT_PRESERVED_MODEL_FINAL_ALIGNMENT_REPLAY_NO_ROUTE_NO_STA')
(OUT/(which+'.json')).write_text(json.dumps(result,indent=2,default=list))
print('REPLAY_DONE',which,r['by_verdict'],result['legality'],result['frozen_loads'],flush=True)
