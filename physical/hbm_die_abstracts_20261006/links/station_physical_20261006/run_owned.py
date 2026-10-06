#!/usr/bin/env python3
"""Owned driver adapter: retain intermediate attributes and mapped source.
The underlying shared driver is unchanged. Every source transform is recorded.
No synthesis/route wall, file or address-space cap is imposed.
"""
import argparse,hashlib,json,sys,types,shutil,re,os,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[4];sys.path.insert(0,str(root/'tools'))
import run_abi3_physical_persistent as persistent
path=root/'tools/run_abi3_physical.py';original=path.read_text()
old='f"write_verilog -noattr {raw_netlist}"';new='f"write_verilog {raw_netlist}"'
assert original.count(old)==1
code=original.replace(old,new)
legacy='if endpoint_netlist and metrics.get("sequential_cell_count", 0) < 270418:'
assert code.count(legacy)==1
code=code.replace(legacy,'if endpoint_netlist and metrics.get("sequential_cell_count", 0) < (5916 if block["parameters"]["NO"]==2 else 6566):')
code=code.replace('Routed W11 endpoint netlist fell below the original full-size guard','Routed selected native station fell below its actual mapped state inventory')
driver=types.ModuleType('gauss_station_physical_driver');driver.__file__=str(path);sys.modules[driver.__name__]=driver
exec(compile(code,str(path),'exec'),driver.__dict__)
p=argparse.ArgumentParser();p.add_argument('--persistent-workdir',required=True);p.add_argument('--launch-receipt',required=True);p.add_argument('--reuse-synthesis-dir',type=Path)
a,argv=p.parse_known_args()
receipt=Path(a.launch_receipt)
receipt.with_name('owned_adapter.json').write_text(json.dumps(dict(source_driver_sha256=hashlib.sha256(original.encode()).hexdigest(),effective_driver_sha256=hashlib.sha256(code.encode()).hexdigest(),adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),changes=['write_verilog preserves attributes in host mapped.raw.v/mapped.v','ORFS reuses the exact mapped netlist when routing, no independent re-synthesis'],original_source_pin=(root/'SOURCE_PIN.txt').read_text().strip() if (root/'SOURCE_PIN.txt').is_file() else None),indent=2)+'\n')
def mapped(block,work,case):
 net=work/'mapped.v'
 if not net.is_file():raise driver.FlowError('actual selected mapped netlist missing')
 dest=case/'w11_endpoint_mapped.v';shutil.copyfile(net,dest)
 if os.environ.get('GAUSS_SOURCE_LOCAL_SDC'):
  shutil.copyfile(os.environ['GAUSS_SOURCE_LOCAL_SDC'],case/'source_local.sdc')
 return {'mapped_netlist_sha256':driver.sha256_file(net),'basis':'Gauss exact attribute-preserving mapped single-station input; legacy filename only, no W11 guard/claim'}
# OpenROAD constraint reader accepts port glob patterns. Returning thousands of
# BTerm strings causes its own bracket quoting to quote bus names twice.
def pin_constraints(regions):
 lines=['# Owned actual ABI pin-face constraints; glob binding includes bus bits.']
 for region in regions:
  edge=region['edge']+':*'
  patterns={'^(clk_sm|por_n|in_.*|release_.*)$':'clk_sm por_n in_* release_*',
            '^(fclk_o|out_.*|ACK_.*)$':'fclk_o out_* ACK_*'}
  assert region['regex'] in patterns
  lines.append('set_io_pin_constraint -region '+edge+' -pin_names {'+patterns[region['regex']]+'}')
 return '\n'.join(lines)+'\n'
driver.io_constraints_tcl=pin_constraints
driver.prepare_w11_orfs_endpoint_netlist=mapped
if a.reuse_synthesis_dir:
 cached=a.reuse_synthesis_dir.resolve()
 ev=json.loads((cached.parent/'physical.json').read_text())
 assert ev['flow_completed'] and 'synth' in ev['stages_completed']
 def reuse(view,corner,block,work,period,dont_use):
  assert ev['design']['parameters']['NO']==block['parameters']['NO'], 'NO2/NO3 cached width mismatch'
  assert ev['design']['parameters']['ENABLE']==block['parameters']['ENABLE']==1
  for entry in ev['design']['sources']:
   assert driver.sha256_file(root/entry['path'])==entry['sha256'], 'cached actual source changed'
  for name in ['mapped.v','mapped.raw.v','stat.txt','synth.ys','yosys.log']:
   shutil.copyfile(cached/name,work/name)
  record=dict(ev['synthesis'])
  old_hash=driver.sha256_file(cached/'mapped.v')
  assert record['netlist_normalization']['normalized_netlist_sha256']==old_hash
  if block['top']!=ev['design']['top']:
   pattern=r'(?m)^module\s+'+re.escape(ev['design']['top'])+r'(?=\s*\()'
   for name in ['mapped.v','mapped.raw.v']:
    text,count=re.subn(pattern,'module '+block['top'],(work/name).read_text())
    assert count==1, 'physical variant module rename must be unique'
    (work/name).write_text(text)
   record['netlist_normalization']=dict(record['netlist_normalization'])
   record['netlist_normalization']['normalized_netlist_sha256']=driver.sha256_file(work/'mapped.v')
   record['netlist_normalization']['raw_netlist_sha256']=driver.sha256_file(work/'mapped.raw.v')
  record['reused_actual_synthesis']=dict(directory=str(cached),original_mapped_sha256=old_hash,selected_mapped_sha256=driver.sha256_file(work/'mapped.v'),source_record_sha256=driver.sha256_file(cached.parent/'physical.json'),variant_transform='unique top module name only; all cells/nets/ports/connectivity and attributes retained')
  return dict(netlist=work/'mapped.v',record=record)
 driver.run_synthesis=reuse
if os.environ.get('GAUSS_RESUME_ORFS'):
 old_case=Path(os.environ['GAUSS_RESUME_ORFS']).resolve()
 assert list(old_case.glob('results/asap7/*/base/3_1_place_gp_skip_io.odb'))
 original_pnr=driver.run_pnr
 def resume_pnr(*args,**kwargs):
  work=args[4];case=work/'orfs'
  shutil.copytree(old_case,case,copy_function=shutil.copy2)
  bases=list((case/'results/asap7').glob('*/base'));assert len(bases)==1
  checkpoint=bases[0]/'3_1_place_gp_skip_io.odb'
  selected=Path(os.environ['GAUSS_SOURCE_LOCAL_SDC'])
  assert driver.sha256_file(old_case/'source_local.sdc')==driver.sha256_file(selected),'actual source clock/load contract changed'
  assert driver.sha256_file(old_case/'w11_endpoint_mapped.v')==driver.sha256_file(work/'mapped.v'),'actual mapped source changed'
  for directory in ('logs','reports'):
   for f in (case/directory).rglob('3_2_place_iop.*'):f.unlink() # new copy only; original failure retained
  proof=dict(source_case=str(old_case),checkpoint_sha256=driver.sha256_file(checkpoint),checkpoint_relative=str(checkpoint.relative_to(case)),mapped_sha256=driver.sha256_file(work/'mapped.v'),sdc_sha256=driver.sha256_file(selected),reused_stages='actual synthesis/floorplan/global-placement-skip-IO; IO correction only, no passing stage replay')
  (work.parent/'resume_checkpoint.json').write_text(json.dumps(proof,indent=2)+'\n')
  original_run=driver.run
  def resume_run(cmd,*aa,**kk):
   if isinstance(cmd,list) and cmd[:2]==['docker','run'] and len(cmd)>1:
    script=cmd[-1]
    if '&& chmod a+w /work/results/' in script:
     return subprocess.CompletedProcess(cmd,0,'Actual pinned synthesis/checkpoint reused; no gate replay.\n','')
    if 'finish metadata-generate' in script:
     cmd=list(cmd);cmd[-1]=script.replace('finish metadata-generate','-o /work/'+proof['checkpoint_relative']+' finish metadata-generate')
   return original_run(cmd,*aa,**kk)
  driver.run=resume_run
  try:return original_pnr(*args,**kwargs)
  finally:driver.run=original_run
 driver.run_pnr=resume_pnr
raise SystemExit(persistent.launch(driver,argv,workdir=a.persistent_workdir,receipt=a.launch_receipt))
