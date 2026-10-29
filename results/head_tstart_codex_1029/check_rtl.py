"""Reproduce metadata-only RTL equality using an explicit repository asset root, no lane worktree dependencies."""
import argparse, copy, gzip, hashlib, json, sys
from pathlib import Path

ap=argparse.ArgumentParser()
ap.add_argument('--repo-root',required=True,help='source-pinned OpenTallas checkout with HEAD sources/views')
ap.add_argument('--out',required=True)
ap.add_argument('--reference-gen',help='optional retained generated source directory')
a=ap.parse_args()
HERE=Path(__file__).resolve().parent; ROOT=Path(a.repo_root).resolve(); OUT=Path(a.out).resolve()
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import gen_rtl as G
with gzip.open(HERE/'landed_lat_ft_tstart.json.gz','rt') as f: after=json.load(f)
with gzip.open(HERE/'landed_sidecar.json.gz','rt') as f: side=json.load(f)
before=copy.deepcopy(after);before['clock']['landing_network'].pop('start_tree')
# Resolve the original plan's exported pin assets against the explicitly given
# checkout. This identical path rebase in both inputs changes no pin geometry.
for raw in (before,after):
    for t in raw['partition_types'].values():
        for c in t.get('hard_cores',[]):
            p=c.get('pins_file','')
            marker='physical/die_plan/'
            if marker in p:
                f=ROOT/marker/p.split(marker,1)[1]
                if not f.is_file():raise FileNotFoundError(f)
                c['pins_file']=str(f)
OUT.mkdir(parents=True,exist_ok=True)
G.write_rtl(before,OUT/'gen_before',rtl_root=ROOT,plan_path=str(OUT/'before.json'),landing=side)
G.write_rtl(after,OUT/'gen_after',rtl_root=ROOT,plan_path=str(OUT/'after.json'),landing=side)
files=sorted((OUT/'gen_before').glob('*.sv')); hashes={}; bad=[]; vs_reference=[]
expected=json.loads((HERE/'rtl_receipt.json').read_text())['sha256']
for f in files:
    x=f.read_bytes();y=(OUT/'gen_after'/f.name).read_bytes()
    if x!=y:bad.append(f.name)
    hashes[f.name]=hashlib.sha256(y).hexdigest()
    if hashes[f.name]!=expected.get(f.name):vs_reference.append(f.name)
    if a.reference_gen:
        p=Path(a.reference_gen)/f.name
        if not p.is_file() or p.read_bytes()!=y:vs_reference.append(f.name)
receipt=dict(schema='opentallas.head_tstart_rtl.v1',files=len(files),changed_before_after=bad,
             diff_vs_recorded_source=sorted(set(vs_reference)),sha256=hashes)
(OUT/'rtl_receipt.json').write_text(json.dumps(receipt,indent=1)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='sha256'}))
if bad or vs_reference:sys.exit(1)
