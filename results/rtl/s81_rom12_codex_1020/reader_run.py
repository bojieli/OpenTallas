"""Replay an admitted image with distinct retained causal-negative witnesses."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
D=Path('/srv/opentallas-scratch/codex/s81-rom12-1020');L=sys.argv[1]
P=D/f'out/pack_real/{L}';V=D/f'reader/vectors_{L}';O=D/f'reader/witnesses_{L}'
O.mkdir(parents=True,exist_ok=False)
if not V.exists():subprocess.run([sys.executable,str(D/'reader/reader_vectors.py'),str(P),str(V)],check=True)
n=json.loads((V/'summary.json').read_text())['end'];exe=D/'reader/objfail/Vtb_reader_segments'
results=[]
for mode in [0,1,2]:
 r=subprocess.run([str(exe),f'+OT_ROM_DIR={P}',f'+end={n}',f'+mode={mode}'],cwd=V,capture_output=True,text=True)
 (O/f'mode{mode}.log').write_text(r.stdout+r.stderr)
 ok=r.returncode==0 if mode==0 else r.returncode!=0 and bool(re.search('reader fault|action mismatch',r.stdout+r.stderr))
 results.append(dict(mode=mode,returncode=r.returncode,PASS=ok,fail_regex='reader fault|action mismatch' if mode else None))
 print('READER_REPLAY',L,results[-1],flush=True)
(O/'summary.json').write_text(json.dumps(dict(PASS=all(x['PASS'] for x in results),layer=L,cycles=n,results=results,binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest()),indent=1)+'\n')
assert all(x['PASS'] for x in results)
