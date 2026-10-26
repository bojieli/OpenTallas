#!/usr/bin/env python3
"""Stage the current QC source closure and an explicit portable probe manifest."""
import argparse,gzip,json,re,shutil,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'tools/die_plan'))
import bind_elab as E

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',type=Path,required=True);a=ap.parse_args();out=a.stage.resolve();out.mkdir(parents=True,exist_ok=False)
 rel=Path('physical/die_plan/qwen_compute/bind/asbuilt_meth_fixed_su.json');ab=json.loads((ROOT/rel).read_text());probe=dict(ab)
 for k in ('land_align','land_r8','land_r8_extra','param_regen'):probe.pop(k,None)
 ab['prefer']=list(ab.get('prefer',[]))+['rtl/physical/a0_rc14_selected_2000/qfd_tile_nk_rp2_romleaf_rr.sv','rtl/physical/a0_rc14_selected_2000/qfd_tile_nl_rp2_romleaf_rr.sv','rtl/qwen_dv/qfd_dv_slice2.sv'];probe['prefer']=ab['prefer']
 ab['dissolve']=list(ab['dissolve'])+['qfd_dv_s8_suvm_rp1','qfd_dv_s8_vm8q_rp1'];probe['dissolve']=ab['dissolve'];probe['type_canon']=True
 selected={ROOT/rel,ROOT/'physical/die_plan/qwen_compute/plan_notes.json',ROOT/'results/token_pass/qc_cb16_phase_2209/run_bind.sh'};idx=E.module_index(ab.get('rtl_roots',[]),ab.get('files',[]),ROOT)
 with tempfile.TemporaryDirectory() as temp:
  temp=Path(temp);scan=dict(ab);scan['netlist']=[]
  for f in ab['netlist']:
   path=ROOT/f;selected.add(path)
   if path.suffix=='.gz':q=temp/path.stem;q.write_bytes(gzip.open(path).read());scan['netlist'].append(str(q))
   else:scan['netlist'].append(str(path))
  tops,full,lib,rec=E.plan_sources(scan,ROOT,idx,shim_dir=temp)
  declared=ab.get('transport',[])+ab.get('sources',[])+ab.get('reducers',[])
  unmodeled=[n for n in rec['undefined'] if not any(re.fullmatch(d['module'],n) for d in declared)]
  if unmodeled or rec['ambiguous']:raise ValueError(json.dumps(dict(unmodeled=unmodeled,ambiguous=rec['ambiguous'])))
  selected.update(Path(x) for x in full+lib if Path(x).is_relative_to(ROOT))
  prefer=[str(ROOT/f) for f in ab.get('prefer',[])]
  for n,r in ab.get('substitute',{}).items():
   for name in (n,r if isinstance(r,str) else r['module']):
    path,amb=E.pick(idx,name,prefer);assert path and not amb,(name,amb);selected.add(Path(path))
 # Preserve every literal include from the selected source closure.
 todo=list(selected)
 while todo:
  path=todo.pop()
  if path.suffix not in ('.sv','.v','.svh','.vh'):continue
  for inc in re.findall(r'`include\s+"([^"]+)"',path.read_text(errors='replace')):
   found=next((p.resolve() for p in (path.parent/inc,ROOT/inc,ROOT/'rtl'/inc) if p.is_file()),None)
   if found is None:raise ValueError(f'missing include {path}: {inc}')
   if not found.is_relative_to(ROOT):raise ValueError(f'external include {found}')
   if found not in selected:selected.add(found);todo.append(found)
 for f in ab.get('files',[])+ab.get('prefer',[]):
  path=ROOT/f
  if path.is_file():selected.add(path)
 for f in ('physical/die_plan/qwen_compute/die_plan.json','physical/die_plan/qwen_compute/die_plan_base_2209.json','physical/die_plan/qwen_compute/bind/'+ab['map_file'],ab['param_regen']['file'],ab['rewires']['file'],'physical/die_plan/qwen_compute/apply_cb16_phase_types.py','physical/die_plan/qwen_compute/inputs/cb16_phase_profiles_1713.json','tools/die_port_bind.py'):
  selected.add(ROOT/f)
 # Plan pin tables / physical abstracts must be copied with the logical source.
 def strings(x):
  if isinstance(x,dict):
   for v in x.values():yield from strings(v)
  elif isinstance(x,list):
   for v in x:yield from strings(v)
  elif isinstance(x,str):yield x
 plan=ROOT/'physical/die_plan/qwen_compute/die_plan.json'
 for value in strings(json.loads(plan.read_text())):
  if '/' not in value or len(value)>255 or value.startswith('/') or any(c.isspace() for c in value):continue
  for p in (ROOT/value,plan.parent/value):
   if p.is_file():selected.add(p);break
 for path in selected:
  dest=out/path.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
 shutil.copytree(ROOT/'tools/die_plan',out/'tools/die_plan')
 for f in ('cb16_dag.py','cb16_pads.py','test_cb16_dag.py'):
  dest=out/'physical/die_plan/qwen_compute/bind'/f;shutil.copy2(ROOT/'physical/die_plan/qwen_compute/bind'/f,dest)
 dest=out/'results/rtl/qc_cb16_flow_1713';dest.mkdir(parents=True)
 for f in ('README.txt','dag_candidate.json','gen.py','run.sh'):shutil.copy2(ROOT/'results/rtl/qc_cb16_flow_1713'/f,dest/f)
 probe['rtl_roots']=[];probe['files']=sorted(str(p.relative_to(ROOT)) for p in selected if p.suffix in('.sv','.v') and str(p.relative_to(ROOT)) not in probe['netlist']);probe['note']+=' | QC phase2209 current explicit selected source closure; fresh ELAB required.'
 (out/'physical/die_plan/qwen_compute/bind/asbuilt_phase_probe_2209.json').write_text(json.dumps(probe,indent=1)+'\n')
 (out/'source_selection.json').write_text(json.dumps(dict(source_files=len(selected),resolution=rec),indent=1)+'\n');print(json.dumps(dict(stage=str(out),source_files=len(selected),resolution=rec)))
if __name__=='__main__':main()
