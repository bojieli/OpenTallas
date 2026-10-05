import json,hashlib,subprocess,time,os,pathlib
S=pathlib.Path('/home/ubuntu/nash-banked-owner-045507509-source-r1');O=pathlib.Path('/home/ubuntu/nash-banked-owner-045507509-runtime-r1')
O.mkdir(exist_ok=False)
V='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'
files=['rtl/experimental/canonical_qwen_banked_manifest_owner_20261003/ot_gpu_qwen_banked_manifest_range_owner.sv','rtl/test/canonical_qwen_banked_manifest_owner_20261003/tb.sv','rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv']
manifest=json.loads((S/'results/uarch/canonical_qwen_banked_manifest_owner_20261003/manifest.json').read_text())
for f in files:assert hashlib.sha256((S/f).read_bytes()).hexdigest()==manifest[f],f
version=subprocess.check_output([V,'--version'],text=True).strip();assert version.startswith('Verilator 5.050'),version
assert hashlib.sha256(pathlib.Path(V).read_bytes()).hexdigest()=='fb2cc573b1055cf096c90e1efc9966fe56bdb4b265c83590cf2a49f7a0defcdf', 'compiler enrollment hash'
preflight=dict(host=os.uname().nodename,PID=os.getpid(),source_commit='0455075096f39068260b9acdbd0f3d19ab55ce73',version=version,compiler_sha256=hashlib.sha256(pathlib.Path(V).read_bytes()).hexdigest(),source_sha256={f:manifest[f] for f in files},limits='No memory/swap/time/file/CPU process caps; two build workers',headroom=subprocess.check_output(['bash','-c','uptime; free -m; df -h /home/ubuntu'],text=True))
(O/'preflight.json').write_text(json.dumps(preflight,indent=2)+'\n')
cmd=[V,'--binary','--timing','-Wno-fatal','--top-module','tb','--Mdir',str(O/'obj'),'-j','2']+[str(S/f) for f in files]
(O/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
t=time.monotonic()
with (O/'compile.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
compile_s=time.monotonic()-t;runtime_rc=None;binary=None
if r.returncode==0:
 binary=hashlib.sha256((O/'obj/Vtb').read_bytes()).hexdigest()
 with (O/'runtime.log').open('w') as log:runtime_rc=subprocess.run([str(O/'obj/Vtb')],stdout=log,stderr=subprocess.STDOUT).returncode
terminal=dict(PID=os.getpid(),compile_rc=r.returncode,runtime_rc=runtime_rc,compile_seconds=compile_s,elapsed_seconds=time.monotonic()-t,binary_sha256=binary,verdict='PASS' if r.returncode==0 and runtime_rc==0 else 'FAIL',source_sha256=preflight['source_sha256'])
(O/'terminal.json').write_text(json.dumps(terminal,indent=2)+'\n')
