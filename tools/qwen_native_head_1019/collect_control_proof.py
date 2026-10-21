import hashlib,importlib.util,json,sys
from pathlib import Path
root=Path.cwd();sp=importlib.util.spec_from_file_location('head_source_driver',root/'tools/qwen_native_head_1019/run_production.py');driver=importlib.util.module_from_spec(sp);sp.loader.exec_module(driver)
paths=set(driver.B.SRCS2+driver.B.XSRCS)
for m in list(sys.modules.values()):
 f=getattr(m,'__file__',None)
 if f:
  p=Path(f).resolve()
  if p.is_relative_to(root):paths.add(str(p.relative_to(root)))
paths.add('tools/qwen_native_head_1019/run_production.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out={'source_files':{p:sha(root/p)for p in sorted(paths)if(root/p).is_file()},'runs':{}}
for run in ('control_r2','control_bank_mut','control_slot_mut','trim_positive'):
 p=root/run
 if not p.exists():continue
 out['runs'][run]={str(f.relative_to(p)):sha(f)for f in p.rglob('*')if f.is_file()and(f.suffix in('.ev','.log')and 'obj2'not in str(f.relative_to(p))or f.name=='Vtb')}
Path('source_and_run_receipt.json').write_text(json.dumps(out,indent=2)+'\n');print('SOURCE_AND_RUN_RECEIPT',len(out['source_files']),list(out['runs']))
