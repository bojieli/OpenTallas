"""Minimum dynamic control gate; run only on an admitted remote host."""
import hashlib
import json
from pathlib import Path
import subprocess

root=Path.cwd()
src=root/'rtl/hbm_accel/control/ot_hbm_native_index_control.sv'
tb=root/'rtl/test/hbm_accel/tb_hbm_native_index_control.sv'
checks={}
for name,body in [('positive',src.read_text()),
                  ('positive_prefetch',src.read_text()),
                  ('generation_drop',src.read_text().replace('desc[35:32],desc[31:0]',"4'b0,desc[31:0]"))]:
    case=root/name
    case.mkdir(exist_ok=True)
    source=case/'control.sv'
    source.write_text(body)
    argv=['iverilog','-g2012','-s','tb_hbm_native_index_control','-o',str(case/'gate.vvp'),str(source),str(tb)]
    if name=='positive_prefetch':argv.insert(2,'-Ptb_hbm_native_index_control.PREFETCH_CASE=1')
    compile_result=subprocess.run(argv,capture_output=True,text=True)
    (case/'compile.log').write_text(compile_result.stdout+compile_result.stderr)
    run_result=subprocess.run(['vvp',str(case/'gate.vvp')],capture_output=True,text=True) if compile_result.returncode==0 else None
    output='' if run_result is None else run_result.stdout+run_result.stderr
    (case/'run.log').write_text(output)
    checks[name]=dict(compile_returncode=compile_result.returncode,
        run_returncode=None if run_result is None else run_result.returncode,
        passed=compile_result.returncode==0 and run_result is not None and
          ((run_result.returncode==0 and 'PASS_NATIVE_INDEX_CONTROL' in output) if name.startswith('positive') else
           (run_result.returncode!=0 and 'dynamic frame metadata mismatch' in output)),argv=argv)
record=dict(source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
    bench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest(),checks=checks,
    passed=all(c['passed'] for c in checks.values()),
    scope='24 dynamic frames,48 full342b masks,24 source starts/receipts; publication stalls and retained return debt. Control only; production query/VM/TU joins and physical qualification remain incomplete.')
(root/'record.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
raise SystemExit(0 if record['passed'] else 1)
