#!/usr/bin/env python3
"""Cold source/terminal review for directed control evidence, no compile/solver."""
import gzip,hashlib,json,pathlib,importlib.util
ROOT=pathlib.Path(__file__).resolve().parents[1]
PACK=pathlib.Path('results/uarch/qwen_rom_connected_control_20261003')
def sha(data):return hashlib.sha256(data).hexdigest()
def load_driver(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.ROOT=ROOT;m.ARCH=ROOT/'results/uarch/qwen_rom_issue_lockstep_terminal_20261003';return m

def review():
 p=ROOT/PACK;pins=json.loads((p/'artifact-pins-r1.json').read_text())
 for name,want in pins.items():
  if sha((ROOT/name).read_bytes())!=want:raise ValueError('pin mismatch '+name)
 plan=json.loads((p/'frozen-plan-r1.json').read_text())
 for name,want in plan['source_pins'].items():
  if sha((ROOT/'results/uarch/qwen_rom_issue_lockstep_terminal_20261003'/name).read_bytes())!=want:raise ValueError('original source changed '+name)
 drivers={1:load_driver(p/'driver-r1-FAIL.py','control_r1'),2:load_driver(p/'driver-r2.py','control_r2'),3:load_driver(ROOT/'tools/qrom_connected_control_gate.py','control_r3')}
 marks={'ungated_go':'accepted go cycle=6','KV_PREP':'state pcnt_0','ib_bit':'every-edge ib/x capture','address':'independent ROM address','hold':'directed transaction failed to drain','pipeline':'independent KV control address'}
 runs=[('directed-r1-FAIL',1,None),('directed-r2-PASS',2,None),('directed-r3-PASS',3,None)]+[('mutant-r2-'+m,2,m) for m in marks]
 for name,version,mutant in runs:
  r=p/name;terminal=json.loads((r/'terminal.json').read_text())
  for asset,want in terminal['artifacts'].items():
   data=gzip.decompress((r/'sim.vvp.gz').read_bytes()) if asset=='sim.vvp' else (r/asset).read_bytes()
   if sha(data)!=want:raise ValueError('run artifact changed '+name+'/'+asset)
  driver=drivers[version];texts=driver.generate(mutant)
  for asset,text in zip(['control.sv','operators.sv','tb.sv'],texts):
   if (r/asset).read_text()!=text:raise ValueError('source reproduction mismatch '+name+'/'+asset)
  driverpath=ROOT/'tools/qrom_connected_control_gate.py' if version==3 else p/('driver-r1-FAIL.py' if version==1 else 'driver-r2.py')
  if terminal['source_before']!=terminal['source_after'] or terminal['source_before']['tools/qrom_connected_control_gate.py']!=sha(driverpath.read_bytes()):raise ValueError('unstable driver '+name)
  if any(terminal[k] for k in ['formal','whole_engine','owned_ready','provider_or_ACK','CDC_or_physical','new_numerical_token']):raise ValueError('scope promotion '+name)
  if any(v!=[-1,-1] for v in terminal['limits'].values()):raise ValueError('unexpected native limits '+name)
  if len(terminal['results'])!=2 or terminal['results'][0]['rc']!=0:raise ValueError('compile did not qualify '+name)
  log=(r/'run.log').read_text()
  if mutant:
   if terminal['status']!='FAIL_DIRECTED_CONTROL' or terminal['results'][1]['rc']==0 or marks[mutant] not in log:raise ValueError('mutation not rejected '+name)
  elif version==1:
   if 'coverage not met acc=7' not in log or terminal['status']!='FAIL_DIRECTED_CONTROL':raise ValueError('original failure changed')
  elif terminal['status']!='PASS_DIRECTED_CONTROL_ONLY' or terminal['results'][1]['rc']!=0 or 'PASS_QROM_DIRECTED_CONNECTED_CONTROL' not in log:raise ValueError('positive failed '+name)
 return {'status':'PASS_COLD_DIRECTED_CONTROL_SOURCE_REVIEW','pins':len(pins),'terminal_archives':len(runs),'rejected_mutants':len(marks),'final':'160cycles8accept14busyreject155checked65ROM48KV5pending5reset','source_equivalent_control_projection':True,'formal_or_whole_engine':False,'physical':False,'solver_or_build_launched':False}
if __name__=='__main__':print(json.dumps(review(),indent=2,sort_keys=True))
