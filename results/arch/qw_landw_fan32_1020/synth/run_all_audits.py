import pathlib,subprocess,os,json,hashlib
r=pathlib.Path.cwd();a=r/'results/arch/qw_landw_fan32_1020/synth';rows=[]
for label,top in [('landw116final','qfd_landh0d8f_116_EW_54x54'),('landw107final','qfd_landh0d8f_107_EW_52x52'),('landwn107final','qfd_landh0d8fn_107_EW_52x52'),('landwn116final','qfd_landh0d8fn_116_EW_54x54')]:
 paths=list((r/'native_synth_out'/label).glob('**/1_2_yosys.raw.v'));assert len(paths)==1;d=paths[0].parent
 for fn in ['flatten.py','audit.py','constant_roles.py']:(d/fn).write_text((a/fn).read_text())
 for fn in ['constant_roles.py','flatten.py']:
  with(d/(fn+'.log')).open('w')as f:subprocess.run(['docker','run','--rm','--network','none','-v',str(d)+':/out','-e','OT_NATIVE_TOP='+top,'openroad/orfs:asap7lock','python3','/out/'+fn],stdout=f,stderr=subprocess.STDOUT,check=True)
 p=subprocess.run(['python3','audit.py'],cwd=d,env=dict(os.environ,OT_NATIVE_TOP=top),check=True,text=True,capture_output=True);print(top,p.stdout,flush=True);j=json.loads((d/'native32.json').read_text());rows.append(dict(top=top,label=label,over32=j['over32_non_tie'],maximum=j['max_non_tie'],ff=j['ff'],mapped_sha256=hashlib.sha256(paths[0].read_bytes()).hexdigest()))
(a/'all_variant_native.json').write_text(json.dumps(rows,indent=2)+'\n')
