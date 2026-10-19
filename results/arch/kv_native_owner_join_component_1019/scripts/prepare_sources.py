#!/usr/bin/env python3
"""Prepare immutable source slice; no simulator or compiler is launched."""
import argparse, hashlib, json, pathlib, subprocess
p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--out',required=True);p.add_argument('--private-rev',required=True);a=p.parse_args()
repo=pathlib.Path(a.repo).resolve();out=pathlib.Path(a.out).resolve()
if out.exists():raise SystemExit('refuse existing output: preserve earlier source and logs')
out.mkdir(parents=True)
base=pathlib.Path(__file__).resolve().parents[1]
inventory=json.loads((base.parent/'kv_native_join_bench_plan_1019/dependency_inventory.json').read_text())
manifest=[];files=[]
def save(rel,data,origin):
 dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 manifest.append(dict(path=rel,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),origin=origin));files.append(rel)
def blob(rev,path):return subprocess.check_output(['git','-C',str(repo),'show',rev+':'+path])
for r in inventory['modules']:save('baseline/'+r['path'],blob('5f2ce19bc',r['path']),'5f2ce19bc:'+r['path'])
private_dir='results/arch/kv_native_owner_join_component_1019/private'
paths=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',a.private_rev,private_dir],text=True).splitlines()
for f in paths:
 if f.endswith('.sv'):save('private/'+pathlib.Path(f).name,blob(a.private_rev,f),a.private_rev+':'+f)
for name in ['qkd_host_axi_packet_rc','qkd_host_native_token_endpoint_cancel_rc']:
 f='results/arch/kv_retained_commit_component_1019/integration_final/integrated_'+name+'.sv'
 save('private/'+name+'.sv',blob('60bb2c145',f),'60bb2c145:'+f)
for f in sorted((base/'bench').glob('*.sv')):save('bench/'+f.name,f.read_bytes(),'reviewed bench source '+str(f))
(out/'sources.f').write_text('\n'.join(files)+'\n')
(out/'source_manifest.json').write_text(json.dumps({'kind':'FUNCTIONAL_ONLY','private_revision':a.private_rev,'sources':manifest,'component_H':512,'component_deadline':384,'production_H':None,'production_calendar':None,'declared_added_bits_H512':1829,'newly_live_repurposed_rank0_bits':2,'conservative_repurposed_packet_bits_all8':16,'event_indexed_bits':2912,'fixture_watchdog_default':1<<22,'separate_cancellation_watchdog':512,'new_wrapper_holding_bits':0,'clock_fixture':'all source clock ports same clk; no native phase qualification'},indent=2)+'\n')
print('PREPARED',len(files),'sources',sum(r['bytes'] for r in manifest),'bytes')
