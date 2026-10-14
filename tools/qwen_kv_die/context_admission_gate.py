#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
src=pathlib.Path('rtl/physical/ot_qwen_context_admission.sv');bench=pathlib.Path('rtl/test/qwen_kv_die/tb_qwen_context_admission.sv');s=src.read_text()
cases={'positive':s,'duplicate_unguarded':s.replace('&&!duplicate',''),'pending_unguarded':s.replace('&&!pending',''),'toggle_missing':s.replace('accept_toggle<=!accept_toggle','accept_toggle<=accept_toggle')};records={}
with tempfile.TemporaryDirectory(prefix='qwen-admit-') as tmp:
 for name,content in cases.items():
  path=pathlib.Path(tmp)/f'{name}.sv';path.write_text(content);exe=path.with_suffix('.vvp')
  build=subprocess.run(['iverilog','-g2012','-s','tb_qwen_context_admission','-o',str(exe),str(path),str(bench)],capture_output=True,text=True);assert build.returncode==0,build.stderr
  run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(a.out/f'{name}.log').write_text(run.stdout+run.stderr);records[name]={'exit':run.returncode,'source_sha256':hashlib.sha256(content.encode()).hexdigest()};assert (run.returncode==0)==(name=='positive'),name
(a.out/'record.json').write_text(json.dumps({'status':'ADMISSION_UNIT_PASS_ACTUAL_U_ME_ARITHMETIC_PENDING','cases':records,'bench_sha256':hashlib.sha256(bench.read_bytes()).hexdigest()},indent=2)+'\n')
