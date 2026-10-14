import pathlib,hashlib,json,subprocess,importlib.util,sys
S=pathlib.Path('/srv/opentallas-scratch/claude/el1013-engc-compose/io18')
P=S/'src/physical/s81_engc_tiles/compose/gate/records/child_clock_refs_1014/ck_insertion_normalized.py'
for kind,eco in [('pbc','pbc_hold_eco')]:
 B=next((S/eco/'orfs/results/asap7').glob('*/base')); O=S/'proofck'/kind; O.mkdir(exist_ok=True)
 paths=[B/x for x in ['6_final.odb','6_final.sdc','6_final.spef']]+[P]
 def receipt():return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 before=receipt(); (O/'inputs.json').write_text(json.dumps(before,indent=2)+'\n')
 cmd=[sys.executable,str(P),'--base',str(B),'--routed','--clock','ck','--image','openroad/orfs:asap7lock','--route-corner','TT','--output',str(O/'insertion.json')]
 q=subprocess.run(cmd,text=True,capture_output=True); (O/'measure.log').write_text(q.stdout+q.stderr)
 after=receipt(); (O/'terminal.json').write_text(json.dumps({'exit':q.returncode,'inputs_unchanged':before==after,'image_id':subprocess.check_output(['docker','image','inspect','openroad/orfs:asap7lock','--format','{{.Id}}'],text=True).strip()},indent=2)+'\n')
 print(kind,q.returncode,'inputs_unchanged',before==after,flush=True)
 if q.returncode or before!=after:sys.exit(1)
