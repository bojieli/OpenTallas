import sys,json,hashlib,shutil
from pathlib import Path
S=Path(sys.argv[1]);D=Path(sys.argv[2]);patch=Path(sys.argv[3]);assert not D.exists();D.mkdir(parents=True);K=D/'kit'
shutil.copytree(S,K,ignore=shutil.ignore_patterns('run'))
for f in (S/'run/results').rglob('*'):
 if f.is_file() and (f.name.startswith(('1_','2_','3_4_')) or (f.name.startswith('ot_') and f.suffix=='.txt')):
  t=K/f.relative_to(S);t.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,t)
shutil.copy2(patch,K/'ctl_native_rows_fix.tcl')
hook=K/'ctl_repack_pre_dpl.tcl';hook.write_text(hook.read_text()+'source /work/ctl_native_rows_fix.tcl\n')
r=json.load(open(S/'repack_source_receipt.json'));unchanged=[]
for row in r['unchanged_inputs']:
 f=K/row['relative'];assert hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256'];unchanged.append(row)
for rel in ['config.mk','ctl_ff_repack.tcl','run/results/asap7/hc_qkd_kvs_ctl__371_52x371_52/base/3_4_place_resized.odb']:
 f=K/rel;assert hashlib.sha256(f.read_bytes()).hexdigest()==hashlib.sha256((S/rel).read_bytes()).hexdigest();unchanged.append(dict(relative=rel,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
for f in (K/'run/results').rglob('ot_*.txt'):
 unchanged.append(dict(relative=str(f.relative_to(K)),sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
geometry={n:hashlib.sha256((K/n).read_bytes()).hexdigest() for n in ['ctl_repack_pre_dpl.tcl','ctl_native_rows_fix.tcl']}
(K/'dpl_only_receipt.json').write_text(json.dumps(dict(unchanged_inputs=unchanged,geometry=geometry,FF_count=18768,moved_FF_count=70,source_cycles_delta=0,normal_targets=['do-3_5_place_dp','do-3_place']),indent=2)+'\n')
print('STAGED_DPL_ONLY',D,'unchanged',len(unchanged),'sourceFF18768/70poses')
