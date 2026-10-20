import pathlib,subprocess,re,json
r=pathlib.Path.cwd();a=r/'results/arch/qw_landw_fan32_1020/synth';base=(a/'kit.env').read_text();rows=[]
for top,label in [('qfd_landh0d8f_107_EW_44x44','landw107v2'),('qfd_landh0d8fn_107_EW_44x44','landwn107v2'),('qfd_landh0d8fn_116_EW_46x46','landwn116v2')]:
 k=a/(label+'.env');k.write_text(re.sub(r'^TOP=.*$', 'TOP='+top,base,flags=re.M));cmd=['bash',str(a/'ref_synth.sh'),str(k),label,str(r/'native_synth_out'),'floorplan'];p=subprocess.run(cmd,env=dict(__import__('os').environ,SRC=str(r),SYNTH_TIMEOUT='unlimited',OT_ORFS_CORNER_OVERRIDE='TC'));rows.append(dict(top=top,label=label,rc=p.returncode));print(rows[-1],flush=True)
(a/'variant_synth_summary.json').write_text(json.dumps(rows,indent=2)+'\n')
