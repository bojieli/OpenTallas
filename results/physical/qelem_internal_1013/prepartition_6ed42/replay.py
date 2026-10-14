from pathlib import Path
import subprocess,json,hashlib
base=Path('/srv/opentallas-scratch/codex/q-full-map-6ed42');out=base/'prepartition';out.mkdir(exist_ok=True)
ys=(base/'output/generic.ys').read_text().split('synth -top')[0]
ys += 'hierarchy -top ot_v41_rom_elem_q_qxpq_w10\nproc\nflatten\nopt_clean\nstat\nwrite_json '+str(out/'source_graph.json')+'\n'
(out/'source_graph.ys').write_text(ys)
image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
cmd=['docker','run','--rm','-v',str(base)+':'+str(base),image,'/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','-s',str(out/'source_graph.ys')]
with (out/'source_graph.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
receipt={'source_commit':'6ed42d12c','full_map_receipt_sha256':hashlib.sha256((base/'output/receipt.json').read_bytes()).hexdigest(),'returncode':r.returncode,'command':cmd,'qualification':'Pre-memory-map source graph for genuine five-leaf extraction; not physical admission','log_sha256':hashlib.sha256((out/'source_graph.log').read_bytes()).hexdigest()}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('SOURCE_GRAPH',r.returncode,flush=True)
raise SystemExit(r.returncode)
