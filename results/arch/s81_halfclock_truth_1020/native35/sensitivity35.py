import pathlib, shutil, subprocess, json
D=pathlib.Path.cwd(); S=D/'source35e931766/tools/tt_views/view_export.py'
rows=[]
def run(label,variant='inv',transform=None,flag=True,expected=True,pair='ck:ck_o'):
 root=D/'sensitivity35'/label; root.mkdir(parents=True,exist_ok=True)
 inp=root/'orfs';shutil.copytree(D/variant/'orfs',inp,dirs_exist_ok=True)
 base=inp/'results/asap7/fc_coupon/base'
 if transform: transform(base)
 cmd=['python3',str(S),'--orfs-dir',str(inp),'--name','fc_coupon','--out',str(root/'export'),'--no-verdict','--corners','tt','--image','openroad/orfs:asap7lock']
 if flag:cmd+=['--forwarded-clock',pair]
 with (root/'export.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 rows.append(dict(label=label,rc=r.returncode,expected_success=expected,pass_expected=(r.returncode==0)==expected)); print(rows[-1],flush=True)
 (D/'sensitivity35/results.json').write_text(json.dumps(rows,indent=2))
def edit(b,a,z):
 p=b/'6_final.sdc';p.write_text(p.read_text().replace(a,z))

def scale(b):
 p=b/'6_final.spef';lines=[];mode=False
 for line in p.read_text().splitlines():
  tok=line.split()
  if line.startswith('*D_NET '):tok[-1]=str(float(tok[-1])*2);line=' '.join(tok)
  elif line in ['*CAP','*RES']:mode=True
  elif line.startswith('*'):mode=False
  elif mode and tok and tok[0].isdigit():tok[-1]=str(float(tok[-1])*2);line=' '.join(tok)
  lines.append(line)
 p.write_text('\n'.join(lines)+'\n')
run('load74',transform=lambda b:edit(b,'37.0000 [get_ports {ck_o}]','74.0000 [get_ports {ck_o}]'))
run('spef2',transform=scale)
