import sys, pathlib, hashlib, json, subprocess, importlib.util
D=pathlib.Path('/srv/opentallas-scratch/claude/engc-clock1014')
J=pathlib.Path(sys.argv[1]); dbs=list(J.glob('routes/*/work/orfs/results/asap7/*/base/6_final.odb'))
assert len(dbs)==1, dbs
B=dbs[0].parent; tag=J.name; O=D/tag; O.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('ck', D/'ck_insertion_normalized.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
paths=[B/x for x in ['6_final.odb','6_final.sdc','6_final.spef']]+[D/'ck_insertion_normalized.py']
for c in ['tt','ff','ss']:
 root, libs=mod.macro_libs(B,c)
 if root: paths += [root / l.removeprefix('/src/') for l in libs]
def receipt():
 return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
before=receipt(); (O/'inputs.json').write_text(json.dumps(before,indent=2)+'\n')
result=subprocess.run([sys.executable,str(D/'ck_insertion_normalized.py'),'--base',str(B),'--routed','--clock','ck','--image','openroad/orfs:asap7lock','--route-corner','TT','--output',str(O/'insertion.json')],capture_output=True,text=True)
(O/'measure.log').write_text(result.stdout+result.stderr)
after=receipt(); (O/'terminal.json').write_text(json.dumps({'exit':result.returncode,'inputs_unchanged':before==after,'base':str(B),'image_id':subprocess.check_output(['docker','image','inspect','openroad/orfs:asap7lock','--format','{{.Id}}'],text=True).strip()},indent=2)+'\n')
print(tag,result.returncode,'inputs_unchanged',before==after,flush=True)
print(result.stdout[-1500:]+result.stderr[-1500:],flush=True)
assert before==after
sys.exit(result.returncode)
