from pathlib import Path
import json,hashlib,subprocess,sys
base=Path(__file__).resolve().parent;out=base/'output';out.mkdir(exist_ok=True)
manifest=json.loads((base/'source_manifest.json').read_text())
assert all(hashlib.sha256((base/p).read_bytes()).hexdigest()==h for p,h in manifest['sha256'].items())
image='sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
cmd=['docker','run','--rm','-v',str(base)+':'+str(base),image,'/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','-s',str(base/'source_graph.ys')]
with (out/'source_graph.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
receipt={'source_commit':'7602aac02','extractor_commit':'cd377489a','command':cmd,'returncode':r.returncode,'source_manifest':manifest,'physical_admission':False}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2));print('SOURCE_GRAPH',r.returncode,flush=True)
if r.returncode:raise SystemExit(r.returncode)
r=subprocess.run([sys.executable,str(base/'q_native_partition_graph.py'),str(out/'source_graph.json'),str(out/'partition')])
print('SOURCE_RECONSTRUCTION',r.returncode,flush=True)
if r.returncode:raise SystemExit(r.returncode)
r=subprocess.run([sys.executable,str(base/'q_native_partition_graph.py'),str(out/'source_graph.json'),str(out/'containers'),'--coalesce-containers'])
print('CONTAINER_RECONSTRUCTION',r.returncode,flush=True)
if r.returncode:raise SystemExit(r.returncode)
ys='read_json '+str(out/'containers/partitioned.json')+'\nhierarchy -top ot_v41_rom_elem_q_qxpq_w10\ncheck\nwrite_verilog -noattr '+str(out/'containers/compiled_source.sv')+'\n'
(out/'containers/check.ys').write_text(ys)
cmd=['docker','run','--rm','-v',str(base)+':'+str(base),image,'/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys','-s',str(out/'containers/check.ys')]
with (out/'containers/check.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
receipt['container_check_command']=cmd;receipt['container_check_returncode']=r.returncode;receipt['container_check_log_sha256']=hashlib.sha256((out/'containers/check.log').read_bytes()).hexdigest();(out/'receipt.json').write_text(json.dumps(receipt,indent=2))
print('CONTAINER_CHECK',r.returncode,flush=True);raise SystemExit(r.returncode)
