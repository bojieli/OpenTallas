import hashlib,json,subprocess,tarfile
from pathlib import Path
root=Path.cwd();archive=root/'compiler_370008088.tar'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='ae30b8605239d4b8f1c12679a1ff5fc9cda27a66a7e7c286ad2ef51c1bf46582'
compiler=root/'compiler';compiler.mkdir(exist_ok=False)
with tarfile.open(archive) as t:
 members=t.getmembers();assert all(not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and (m.isfile() or m.isdir()) for m in members)
 t.extractall(compiler)
inputs=root/'inputs'
args=['python3',str(compiler/'tools/s81_dv/tokfunc/generate_wkv_phase_source.py'),'--compiler-root',str(compiler),'--profile-archive',str(inputs/'g9_configured_source_r1.tgz'),'--profile-receipt',str(inputs/'g9_configured_terminal_r1.json'),'--baseline-frame-model',str(inputs/'selected_rf3r_schedule_r3.json'),'--die-v',str(inputs/'die.v'),'--plan',str(inputs/'plan_routed_g9.json'),'--audit',str(inputs/'actual_G9_source_binding_7373.json'),'--port-bind',str(inputs/'port_bind.json'),'--tap-consumer',str(inputs/'frozen_tap_modules.sv'),'--address-readset',str(inputs/'actual_G9_address_readset.json'),'--fixtures',str(root/'fixtures'),'--producer',str(inputs/'norm_producer_r1.json'),'--inventory',str(inputs/'shipping_s0N_selected.json'),'--out',str(root/'source_run_r1')]
rec=dict(source_commit='37000808832dfe7193557c45f8e4e42991570cf1',compiler_archive_sha256='ae30b8605239d4b8f1c12679a1ff5fc9cda27a66a7e7c286ad2ef51c1bf46582',argv=args,compiler_run=False,simulation_performed=False,inputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs.iterdir() if p.is_file()})
(root/'launch_receipt.json').write_text(json.dumps(rec,indent=1)+'\n')
with (root/'source_run_r1.log').open('w') as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
rec['exit_code']=r.returncode;(root/'launch_receipt.json').write_text(json.dumps(rec,indent=1)+'\n');print('SOURCE_ONLY_EXIT',r.returncode,flush=True);raise SystemExit(r.returncode)
