from pathlib import Path
import tempfile,subprocess,json,os,hashlib
script=Path(__file__).resolve().with_name('stage_stg.sh')
root=Path(tempfile.mkdtemp(prefix='qw-reuse-identity-'))
src=root/'tree';bench=src/'rtl/test/qwen_dv';bench.mkdir(parents=True);(src/'tools/qwen_layerbench').mkdir(parents=True)
(bench/'dv_bench2.py').write_text("SRCS2=['rtl/dut.sv']\nXSRCS=[]\n")
for name in ('main2.cpp','dv_lower_bench.py','dv_bench.py'):(bench/name).write_text('// fixture source\n')
(src/'tools/qwen_layerbench/dv_lower.py').write_text('NSLICE=12\n')
(src/'rtl/dut.sv').write_text('module dut; endmodule\n')
overlay=root/'overlay.sha256';overlay.write_text('original overlay\n')
obj=root/'objects';obj.mkdir();exe=obj/'Vtb';exe.write_bytes(b'NEVER EXECUTED synthetic identity-only fixture\n');exe.chmod(0o755)
env=dict(os.environ,DV_LOWER_VFLAGS='-GMU_NU=4 -GSU_LT=1')
snapshot=root/'snapshot.json'
def run(mode,snap=snapshot,flags=None):
 e=env.copy()
 if flags is not None:e['DV_LOWER_VFLAGS']=flags
 return subprocess.run(['bash',str(script),'--object-manifest',mode,str(src),str(snap),str(overlay),str(obj)],env=e,text=True,capture_output=True)
assert run('snapshot').returncode==0
cases={}
r=run('verify');cases['missing_manifest_refused']=r.returncode!=0 and 'unavailable' in r.stderr
assert run('bind').returncode==0
cases['exact_binary_source_overlay_match']=run('verify').returncode==0
old=exe.read_bytes();exe.write_bytes(old+b'changed');r=run('verify');cases['binary_mismatch_refused']=r.returncode!=0 and 'identity mismatch' in r.stderr;exe.write_bytes(old)
old=(src/'rtl/dut.sv').read_bytes();(src/'rtl/dut.sv').write_bytes(old+b'// actual RTL change\n');r=run('verify');cases['source_mismatch_refused']=r.returncode!=0 and 'source/flags/overlay differ' in r.stderr
# A fresh snapshot of changed RTL still cannot relabel the old binary manifest.
fresh=root/'changed_source_snapshot.json';assert run('snapshot',fresh).returncode==0;r=run('verify',fresh);cases['new_snapshot_cannot_relabel_old_binary']=r.returncode!=0 and 'identity mismatch' in r.stderr
(src/'rtl/dut.sv').write_bytes(old)
old=overlay.read_bytes();overlay.write_bytes(old+b'next overlay');r=run('verify');cases['overlay_mismatch_refused']=r.returncode!=0 and 'source/flags/overlay differ' in r.stderr;overlay.write_bytes(old)
r=run('verify',flags='-GMU_NU=4 -GSU_LT=1 -GARF=1');cases['flag_mismatch_refused']=r.returncode!=0 and 'source/flags/overlay differ' in r.stderr
cases['exact_match_still_passes']=run('verify').returncode==0
assert all(cases.values()),cases
out=dict(scope='pure manifest guard; synthetic Vtb never executed; no hardware build/simulation',script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),cases=cases,fixture_path=str(root),verdict='PASS')
print(json.dumps(out))
