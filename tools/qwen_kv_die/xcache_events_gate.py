#!/usr/bin/env python3
"""Tiny event-protocol gate; this is not arithmetic/physical/CDC qualification."""
import argparse,hashlib,json,pathlib,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rtl=pathlib.Path('rtl/physical/ot_qwen_xcache_context32_events.sv');bench=pathlib.Path('rtl/test/qwen_kv_die/tb_qwen_xcache_events.sv');source=rtl.read_text()
cases={'positive':source,'ignored_fill_credit':source.replace('load_v&&load_ready','load_v'),'wrong_root_provenance':source.replace('tokens[ri],roots[ri],phases[ri]','tokens[ri],5\'d0,phases[ri]'),'one_shot_fill_level':source.replace('fill_toggle<=!fill_toggle','fill_toggle<=1\'b1')}
results={}
with tempfile.TemporaryDirectory(prefix='qwen-events-') as tmp:
 for name,content in cases.items():
  path=pathlib.Path(tmp)/f'{name}.sv';path.write_text(content);exe=path.with_suffix('.vvp')
  build=subprocess.run(['iverilog','-g2012','-s','tb_qwen_xcache_events','-o',str(exe),str(path),str(bench)],capture_output=True,text=True);assert build.returncode==0,build.stderr
  run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(a.out/f'{name}.log').write_text(run.stdout+run.stderr)
  results[name]={'exit':run.returncode,'source_sha256':hashlib.sha256(content.encode()).hexdigest()}
  assert (run.returncode==0)==(name=='positive'),f'{name} unexpected outcome'
(a.out/'record.json').write_text(json.dumps({'status':'EVENT_MAILBOX_UNIT_GATE_PASS_NOT_CDC_ARITHMETIC_OR_PHYSICAL','source_sha256':hashlib.sha256(rtl.read_bytes()).hexdigest(),'bench_sha256':hashlib.sha256(bench.read_bytes()).hexdigest(),'cases':results},indent=2)+'\n')
