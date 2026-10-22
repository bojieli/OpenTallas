import pathlib,sys,json,hashlib,shutil,subprocess
side=sys.argv[1]; n={'main':'svc5','fb':'svc5b'}[side]
old=pathlib.Path('/srv/opentallas-scratch/claude/ref_gate/qfd_n59_'+n+'-20261021-194515')
root=pathlib.Path('/srv/opentallas-scratch/claude/codex-n59-resume-1021')
new=root/side
sys.path.insert(0,str(old/'src/tools/ref_tile'))
import source_binding as SB
binding=json.loads(pathlib.Path(str(old)+'.source_snapshot.json').read_text())
original=(root/('original_'+side+'.sh')).read_bytes()
verified=SB.recover_verified_snapshot(binding,old/'src',(old/'execution.log').read_bytes(),original)
base=list((old/'routes/gate/work/orfs/results/asap7').glob('*/base'))
assert len(base)==1
mapped=base[0]/'1_2_yosys.v'
log=old/'routes/gate/work/orfs/logs/asap7'/base[0].parent.name/'base/1_2_yosys.log'
assert mapped.is_file() and mapped.stat().st_size>0 and 'End of script.' in log.read_text(), 'Mapping is still progressing; preserve it'
assert not new.exists(), 'Continuation directory already exists'
new.mkdir()
shutil.copytree(old/'src',new/'src',copy_function=shutil.copy2,symlinks=True)
shutil.copytree(old/'routes',new/'routes',copy_function=shutil.copy2,symlinks=True)
(new/'bin').mkdir()
receipt={'schema':'opentallas.n59.exact_object_continuation.v1','original_run':str(old),'original_source_recovery':verified['recovery'],'original_manifest_sha256':binding['manifest_sha256'],'original_archive_sha256':binding['archive_sha256'],'continuation_script_sha256':hashlib.sha256((root/('continue_'+side+'.sh')).read_bytes()).hexdigest(),'reused_artifacts':{str(p.relative_to(old)):hashlib.sha256(p.read_bytes()).hexdigest() for p in base[0].glob('1_*') if p.is_file()},'continuation':'Native census and floorplan, followed by unchanged original normal gate measurements, CTS and trial GRT; original failure retained'}
(new/'continuation_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(new/'original_source_binding.json').write_text(json.dumps(verified,indent=1)+'\n')
r=subprocess.run(['bash',str(root/('continue_'+side+'.sh'))])
(new/'terminal.json').write_text(json.dumps({'returncode':r.returncode,'receipt':'continuation_receipt.json'})+'\n')
sys.exit(r.returncode)
