from pathlib import Path
import json,hashlib,shutil,re
b=Path('/srv/opentallas-scratch2/claude/codex-kv-ahub-fault-full-2055');o=Path('/srv/opentallas-scratch2/claude/codex-nf2-reset-negative-0200');o.mkdir(exist_ok=False)
s=o/'source';shutil.copytree(b/'normal/rtl',s/'rtl');p=s/'rtl/qkd_ahub_static_dw.sv';old=p.read_text();assert hashlib.sha256(p.read_bytes()).hexdigest()=='dbff40e4b29d0fa1a81ec75167557dce3dbb9a06194c3c5eab77c99ce216a14b'
m=re.search(r'\bmodule qkd_ahub_static_core_la_ck7\b.*?\bendmodule\b',old,re.S);assert m
body=m.group();needle='if(!rn[3])fault<=0;';assert body.count(needle)==1
new=old[:m.start()]+body.replace(needle,'if(!rn[3])fault<=1;')+old[m.end():];assert old.count(needle)==new.count(needle)+1;p.write_text(new)
for f in ['stubs.v','wrap_gold.v','lecff.v','gold.ys']:
 shutil.copy2(b/'proof/normal'/f,o/f)
shutil.copy2('/srv/opentallas-scratch2/claude/codex-nf2-profile-replay-2338/lec.py',o/'lec.py')
files={}
for f in sorted((s/'rtl').glob('*')):
 if f.is_file():files['/work/rtl/'+f.name]=hashlib.sha256(f.read_bytes()).hexdigest()
for f in ['proof/normal/gate.aig','proof/normal/gate.map','proof/normal/lec.json','proof/normal/gold.aliases.json','normal/rtl/qkd_ahub_static_dw.sv']:
 files['/subject/'+f]=hashlib.sha256((b/f).read_bytes()).hexdigest()
for f in ['stubs.v','wrap_gold.v','lecff.v','gold.ys','lec.py']:
 files['/out/'+f]=hashlib.sha256((o/f).read_bytes()).hexdigest()
r={'classification':'ACTUAL_SOURCE_RESET_POLARITY_NEGATIVE','subject':str(b),'mount':'/subject:ro','gold_source':'qualified normal NF2 source with exactly one selected _ck7 reset assignment0->1','old_source_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_source_sha256':hashlib.sha256(new.encode()).hexdigest(),'rtl_files':len(list((s/'rtl').glob('*'))),'files':files}
(o/'EXPECTED.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='files'},indent=2))
