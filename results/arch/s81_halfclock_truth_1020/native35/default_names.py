import pathlib,re,subprocess,json
D=pathlib.Path.cwd()
def rename(s):return re.sub(r"\bck_o\b","clk_out",re.sub(r"\bck\b","clk_in",s))
(D/'build_default.tcl').write_text(rename((D/'build.tcl').read_text()))
rows=[]
for v in ['buf','inv']:
 n='default'+v;p=D/n;p.mkdir(exist_ok=True)
 for f in ['input.v','input.sdc']:(p/f).write_text(rename((D/v/f).read_text()))
 cmd=['docker','run','--rm','--user',str(__import__('os').getuid())+':'+str(__import__('os').getgid()),'--entrypoint','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-v',str(D)+':/coupon','-e','COUPON_VARIANT='+n,'openroad/orfs:asap7lock','-threads','1','-no_init','-exit','/coupon/build_default.tcl']
 with (p/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 print(n,'build',r.returncode,flush=True)
 if r.returncode:continue
 cmd=['python3',str(D/'source35e931766/tools/tt_views/view_export.py'),'--orfs-dir',str(p/'orfs'),'--name','fc_coupon','--out',str(p/'export35e931766'),'--no-verdict','--corners','ss,ff,tt','--image','openroad/orfs:asap7lock']
 with (p/'export.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 rows.append(dict(variant=n,rc=r.returncode)); print(rows[-1],flush=True)
(D/'default_names_results.json').write_text(json.dumps(rows,indent=2))
