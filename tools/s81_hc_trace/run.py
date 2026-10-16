#!/usr/bin/env python3
"""Compile actual RTL only, run one full-shape six-kind program, retain raw events."""
import pathlib,subprocess,sys,json,hashlib
root=pathlib.Path(__file__).resolve().parents[2]
out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
files=(root/'tools/s81_hc_trace/sources.txt').read_text().splitlines()
assert not any('dpi' in f.lower() for f in files)
obj=out/'build';exe=obj/'Vtb_s81_hc_master'
if not exe.exists():
 vl=pathlib.Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
 cmd=[str(vl),'--binary','--timing','-O2','-Wno-fatal','-Wno-WIDTH','--top-module','tb_s81_hc_master','-Mdir',str(obj),'-j','16','--unroll-count','4','-fno-dfg','-GNG=256','-GHIER=1','-GHALF=1','-GCSPLIT=1','-GTAIL_SPLIT=2','-GHEAD_ROWS=10','-GCNL_PIN=1','-GCHAIN_STEP=6','-GLANE_SPECIALIZE=1','-GPIPE=1','-GPIPE_PD=40','-GNTREE=1','-GNT_K=67','-GCCF_BP=3','-GLVM=10',*files,'-CFLAGS','-O1']
 with(out/'build.log').open('w')as log:
  log.write(' '.join(cmd)+'\n');log.flush();r=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
fixture=out/'fixture'
assert (fixture/'prog.mem').is_file()
for name,arg in [('positive',None),('live_scalar_mutant','+TRACE_MUT'),('discarded_scalar_control','+TRACE_UNUSED_MUT')]:
 with(out/(name+'.log')).open('w')as log:r=subprocess.run([str(exe)]+([arg]if arg else[]),cwd=fixture,stdout=log,stderr=subprocess.STDOUT)
 txt=(out/(name+'.log')).read_text()
 if name=='live_scalar_mutant':
  assert 'HCG FAIL' in txt,'live actual scalar mutant did not reject expected numerical results'
 else:assert 'HCG PASS' in txt,(name,r.returncode,'No actual PASS marker')
 print(name,'EXPECTED_VERDICT',flush=True)
(out/'run_receipt.json').write_text(json.dumps({'source':json.loads((root/'results/rtl/s81_hc_trace_1016/prebuild.json').read_text()),'log_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in out.glob('*.log')},'scope':'unit-boundary profile only; not actual integrated producer/VM/bridge schedule'},indent=2)+'\n')
print('HC6_NATIVE_UNIT_TRACE_PASS',flush=True)
