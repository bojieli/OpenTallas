#!/usr/bin/env python3
"""Stage the pinned whole-reader source for the required native-only measurement."""
import pathlib,re,subprocess,sys
ref=sys.argv[1];r=pathlib.Path(sys.argv[2]);r.mkdir(parents=True,exist_ok=False);s=r/'src';s.mkdir()
g='/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git'
run=subprocess.check_output(['git','--git-dir='+g,'show',ref+':tools/s81_dv/eng_rr/run_eng_rr.sh'],text=True)
f=re.search(r'F=\((.*?)\)\n',run,re.S)[1].split()
paths=[]
for p in f:
 if '/test/' in p:continue
 paths.append(str(pathlib.Path(p).parent) if p.startswith('physical/') else p)
paths+=['tools/s81_dv/eng_rr','tools/ref_tile/native_census.py','tools/textbook_lint.py','physical/common_flow']
paths=list(dict.fromkeys(paths))
a=subprocess.Popen(['git','--git-dir='+g,'archive',ref,*paths],stdout=subprocess.PIPE)
b=subprocess.run(['tar','-xf','-','-C',str(s)],stdin=a.stdout);a.stdout.close();assert a.wait()==0 and b.returncode==0
(r/'snapshot_ref.txt').write_text(subprocess.check_output(['git','--git-dir='+g,'rev-parse',ref],text=True))
subprocess.run([sys.executable,str(s/'tools/s81_dv/eng_rr/native_rr.py')],cwd=r,check=True)
