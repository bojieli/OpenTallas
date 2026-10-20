from pathlib import Path
import importlib.util,sys,hashlib,json,time
root=Path.cwd();base=Path('/srv/opentallas-scratch/claude/s81-final-fold-1019');script=root/'tools/s81_dv/layer_prog/vs/gen_final_ffn.py'
spec=importlib.util.spec_from_file_location('candidate_gen',script);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
files=['img.mem','imgv.mem','prog.mem','exp.mem','expm.mem','xq.mem','xqi.mem','params.txt'];checks=[];t=time.time()
for beat in range(80):
 out=root/'vectors'/f'b{beat}';sys.argv=[str(script),'--fixtures',str(base/'fixtures'),'--out',str(out),'--beat',str(beat),'--post'];mod.main()
 previous=base/'postall80'/f'b{beat}'
 for name in files:
  a=(out/name).read_bytes();b=(previous/name).read_bytes();assert a==b,(beat,name);checks.append({'beat':beat,'file':name,'sha256':hashlib.sha256(a).hexdigest()})
 current=json.loads((out/'manifest.json').read_text());old=json.loads((previous/'manifest.json').read_text())
 assert current['golden_sha256']==old['golden_sha256']
 assert sorted(current['inputs'].values())==sorted(old['inputs'].values())
proof=dict(beats=80,byte_identical_vector_files=len(checks),files_per_beat=files,elapsed_s=time.time()-t,final_ffn_sha256=hashlib.sha256((root/'tools/s81_dv/layer_prog/final_ffn.py').read_bytes()).hexdigest(),generator_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),old_source_hash_note='Archived sources.sha256 retains an intermediate final_ffn.py hash. Final committed compiler regenerates all640 functional vector files identically; other47 recorded RTL/runner/helper source hashes match.',qualified_token=False,qualified_transport=False,checks=checks)
(root/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('FINAL_FFN_ALL80_FINAL_COMPILER_VECTOR_BYTE_IDENTITY_PASS files='+str(len(checks)))
