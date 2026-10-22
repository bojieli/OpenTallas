from pathlib import Path
import sys,types,json,hashlib,shutil
B=Path.cwd();W=Path('/home/ubuntu/ot-scratch/claude/qwen-kvsys/wt-kvs14r-c6520b2ee-dsg6f')
R=W.with_name('kvs14r-c6520b2ee-dsg6f');case=B/'case_kv';libs=B/'libs';case.mkdir(exist_ok=True);libs.mkdir(exist_ok=True)
for n in ['elements.lef','die.v']:shutil.copy2(R/'case_kv'/n,case/n)
for p in (R/'libs').glob('qfd_elements_*.lib'):shutil.copy2(p,libs/p.name)
sys.path[:0]=[str(W/'tools/qwen_kv_die'),str(W/'tools'),str(W/'tools/qwen_split')]
for name in ['kv_grp_safe2','bind_views']:
 mod=types.ModuleType(name);mod.__file__=str(W/'tools/qwen_kv_die'/(name+'.py'));sys.modules[name]=mod
 exec(compile((B/(name+'.py')).read_text(),mod.__file__,'exec'),mod.__dict__)
V=sys.modules['bind_views'];V.KV._set_geometry(True);records={}
for master,kit in [('qkd_kvs_grp_s6c','qkd_kvs_grp_s6a'),('qkd_kvs_grp_h_s6c','qkd_kvs_grp_h_s6a')]:
 records[master]=V.bind(case,libs,master,W/'physical/ref_tile'/kit/'views'/master)
receipt=dict(source_base='c6520b2ee',scope='retry failed view-binding stage on copies of exact emitted dsg6f GEN; real private parent slices asserted, strict pin_map unchanged',source_inputs={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest()for p in [R/'case_kv/die.v',R/'case_kv/elements.lef']},repair_sources={n:hashlib.sha256((B/n).read_bytes()).hexdigest()for n in ['kv_grp_safe2.py','bind_views.py']},records=records,verdict='PASS'if all(r['bound']for r in records.values())else'FAIL',whole_die_bind='PENDING')
(B/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2),flush=True)
raise SystemExit(0 if receipt['verdict']=='PASS'else 1)
