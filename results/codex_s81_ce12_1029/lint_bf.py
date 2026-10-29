from pathlib import Path
import subprocess,json,re
root=Path.cwd()
params=dict(NSEG=8,NCH=16,XF=8,LV=5,BF16=1,NCHB=8,NB=2,MTP=1,EARLY=1,CG=1,DRAIN=200,FAST=1,PP=1,BP=0,QTIMING_FIX=1,QPIPE=1,QP_XS=1,QP_CAP=0,QP_P1=1,QP_CSAM=10,QZ=1,QZ_NS=8,QZ_NE=4,QY=1,QX=10,QBF=2,QZE=1,TCG=1,GRADUAL_RNE=1,BXST=2,FXST=2,RCG=1)
files=sorted(str(p) for p in (root/'rtl').iterdir() if p.suffix in ('.sv','.v'))
rows=[]
for g in (0,4,16):
    cmd=['verilator','--lint-only','--top-module','ot_v41_bf_col','-Wno-fatal',f'-GTAG_GROUPS={g}']+[f'-G{k}={v}' for k,v in params.items()]+files
    p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (root/f'lint{g}.log').write_text(p.stdout)
    rows.append(dict(groups=g,rc=p.returncode,warnings=sorted(set(re.findall(r'%Warning-(\w+)',p.stdout))),errors=re.findall(r'%Error[^\n]*',p.stdout)))
(root/'lint.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
assert all(r['rc']==0 for r in rows)
assert rows[1]['warnings']==rows[0]['warnings']==rows[2]['warnings']
