from pathlib import Path
import gzip,hashlib,json,shutil
p=Path('results/rtl/qlb_c4b_1018/lmh_cal/closed_equiv');o=p/'failed_attempts';o.mkdir(exist_ok=True)
names=['yosys.log','yosys_optimized.log','yosys_async.log','yosys_fullrtl.log','yosys_fullrtl_r5.log','yosys_macro_cut_r1_import_error.log','yosys_macro_cut.log','yosys_focus.log']
records=[]
for n in names:
 q=p/n
 if not q.exists():continue
 target=o/(n+'.gz');h=hashlib.sha256()
 with q.open('rb')as f,gzip.open(target,'wb',compresslevel=1)as z:
  while data:=f.read(1024*1024):h.update(data);z.write(data)
 with q.open('rb')as f:f.seek(max(0,q.stat().st_size-4096));tail=f.read().decode(errors='replace')
 records.append(dict(source=n,uncompressed_bytes=q.stat().st_size,uncompressed_sha256=h.hexdigest(),archive=target.name,archive_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),tail=tail,claim='NOT EQUIVALENCE PASS; harness/tool/unproved attempt preserved'))
(o/'index.json').write_text(json.dumps(records,indent=2)+'\n')
