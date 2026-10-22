import pathlib, shutil, subprocess, json
D=pathlib.Path.cwd(); S=D/'source35e931766/tools/tt_views/view_export.py'
rows=[]
def run(label,variant='inv',transform=None,flag=True,expected=True,pair='ck:ck_o'):
 root=D/'qual35'/label; root.mkdir(parents=True,exist_ok=True)
 inp=root/'orfs';shutil.copytree(D/variant/'orfs',inp,dirs_exist_ok=True)
 base=inp/'results/asap7/fc_coupon/base'
 if transform: transform(base)
 cmd=['python3',str(S),'--orfs-dir',str(inp),'--name','fc_coupon','--out',str(root/'export'),'--no-verdict','--corners','tt','--image','openroad/orfs:asap7lock']
 if flag:cmd+=['--forwarded-clock',pair]
 with (root/'export.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 rows.append(dict(label=label,rc=r.returncode,expected_success=expected,pass_expected=(r.returncode==0)==expected)); print(rows[-1],flush=True)
 (D/'qual35/results.json').write_text(json.dumps(rows,indent=2))
def edit(b,a,z):
 p=b/'6_final.sdc';p.write_text(p.read_text().replace(a,z))
for v in ['buf','inv','chain']:
 run(v+'_latency0',v,lambda b:edit(b,'-source 17.0000','-source 0.0000'))
run('default_absent',flag=False)
run('wrong_invert',transform=lambda b:edit(b,' -invert',''),expected=False)
run('wrong_source',transform=lambda b:edit(b,'-source [get_ports {ck}]','-source [get_ports {d}]'),expected=False)
run('wrong_master',transform=lambda b:edit(b,'-divide_by 1','-master_clock [get_clocks {ck_o_fwd}] -divide_by 1'),expected=False)
run('wrong_root',pair='d:ck_o',expected=False)
run('missing_spef',transform=lambda b:(b/'6_final.spef').unlink(),expected=False)
run('partial_proof',pair='ck:q',expected=False)
