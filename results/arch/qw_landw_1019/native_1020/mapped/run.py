import pathlib,json,subprocess,os
r=pathlib.Path.cwd();script=r/'native_dump.tcl';rows=[]
for j in json.loads((r/'gates.json').read_text()):
 gate=pathlib.Path(j['gate']);found=list(gate.glob('routes/**/1_synth.odb'));o=r/j['job'];o.mkdir(exist_ok=True)
 if len(found)!=1:rows.append(dict(job=j['job'],error='missing/ambiguous synthODB',matches=[str(x) for x in found]));continue
 odb=found[0];(o/'input.sha256').write_text(subprocess.check_output(['sha256sum',str(odb)],text=True));(o/'native_dump.tcl').write_text(script.read_text());(o/'dump_body.tcl').write_text((r/'dump_body.tcl').read_text())
 cmd=['docker','run','--rm','--network','none','-v',str(o)+':/work','-v',str(gate)+':/input:ro','-e','OT_CENSUS_ODB=/input/'+str(odb.relative_to(gate)),'openroad/orfs:asap7lock','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-exit','/work/native_dump.tcl']
 with (o/'native.log').open('w') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 check=subprocess.run(['sha256sum','-c',str(o/'input.sha256')],text=True,capture_output=True);(o/'input_verify.log').write_text(check.stdout+check.stderr);rows.append(dict(job=j['job'],rc=p.returncode,sha_rc=check.returncode));print(rows[-1],flush=True)
 if p.returncode==0:
  subprocess.run(['gzip','-f',str(o/'pickup_all_roots.tsv')],check=True)
(r/'summary.json').write_text(json.dumps(rows,indent=2)+'\n')
