#!/usr/bin/env python3
"""Admitted private checkpoint continuation of the failed TMR post-IO hook.

No original file is changed. Prepare first, inspect receipts, execute only on
an admitted host. The exact image ID must match the signoff helper's alias.
"""
import argparse,hashlib,json,re,shlex,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
P='physical/qwen_link_forwarded_tmr_pair'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--old-orfs',type=Path,required=True);p.add_argument('--old-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--image-id',required=True);p.add_argument('--threads',type=int,default=8);p.add_argument('--execute',action='store_true');a=p.parse_args()
 if not re.fullmatch(r'sha256:[0-9a-f]{64}',a.image_id) or a.threads<1:p.error('immutable image ID and positive admitted threads required')
 old=a.old_orfs.resolve();oldsrc=a.old_source.resolve();out=a.out.resolve()
 if any(out==r or r in out.parents for r in (old,oldsrc,ROOT)):p.error('private output must be outside all input trees')
 unchanged=['rtl/physical/ot_qwen_die_link_fwd_full_tmr.sv']+[P+'/'+n for n in ['pair.sv','clocks.sdc','propagate.tcl','audit.tcl','reset_inventory.tcl','signoff.py']]+['tools/w18/corner_sta.py','tools/orfs_allcorner_spef.py']
 source={}
 for n in unchanged:
  source[n]=sha(ROOT/n)
  if sha(oldsrc/n)!=source[n]:raise RuntimeError('Source differs beyond resolver: '+n)
 corrected=ROOT/P/'regions.tcl'
 if 'qwen_fwd_normal_name' not in corrected.read_text():raise RuntimeError('Corrected resolver missing')
 bases=list((old/'results/asap7').glob('*/base'))
 if len(bases)!=1:raise RuntimeError('Expected one retained design')
 base=bases[0];rel=base.relative_to(old)
 required=['1_2_yosys.v','1_synth.odb','2_floorplan.odb','2_floorplan.sdc','3_1_place_gp_skip_io.odb']
 upstream={n:sha(base/n) for n in required}
 oldhook=old/'hooks/post_io_placement_regions.tcl'
 if sha(oldhook)!=sha(oldsrc/P/'regions.tcl'):raise RuntimeError('Original failed hook not source-identical')
 want='export POST_IO_PLACEMENT_TCL = /work/hooks/post_io_placement_regions.tcl'
 repl='export POST_IO_PLACEMENT_TCL = /work/recovery_postio.tcl'
 config=(old/'config.mk').read_text()
 if config.splitlines().count(want)!=1:raise RuntimeError('Unexpected original postIO configuration')
 out.mkdir(parents=True,exist_ok=False);work=out/'orfs';shutil.copytree(old,work)
 (work/'config.mk').write_text(config.replace(want,repl))
 assert (work/'config.mk').read_text().replace(repl,want)==config
 # IO stage writes its ODB before the post hook. Persist regions and clock
 # retention explicitly so subsequent placement sees the corrected database.
 (work/'recovery_postio.tcl').write_text(f'source /src/{P}/regions.tcl\nwrite_db /work/{rel}/3_2_place_iop.odb\nputs "TMR_RECOVERY_POSTIO_PERSISTED"\n')
 probe=(ROOT/'results/uarch/qwen_link_forwarded_tmr_resolver_20261007/clock_probe.tcl').read_text()
 check='''
set block [ord::get_db_block]
foreach name {s0 s1} {
 set r [$block findRegion "fwd_$name"]
 if {$r=="NULL"} {error "Missing persisted region $name"}
 set g [$block findGroup "fwd_$name"]
 if {$g=="NULL" || [llength [$g getInsts]]<1068} {error "Missing persisted stage group $name"}
 puts "TMR_PERSISTED_REGION $name cells=[llength [$g getInsts]]"
}
puts "TMR_RECOVERY_READBACK_PASS"
exit
'''
 (work/'recovery_readback.tcl').write_text(f'read_db /work/{rel}/3_2_place_iop.odb\n'+probe+check)
 completed=sorted('/work/'+str(f.relative_to(work)) for f in (work/rel).iterdir() if f.is_file())
 make=['make','DESIGN_CONFIG=/work/config.mk','WORK_HOME=/work','FLOW_VARIANT=base',f'NUM_CORES={a.threads}']
 ignore=[x for f in completed for x in ['-o',f]]
 commands={'dryrun_io':make+ignore+['-n','do-3_2_place_iop'],'dryrun_finish':make+ignore+['-n','finish'],'io':make+ignore+['do-3_2_place_iop'],'readback':['/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/work/recovery_readback.tcl'],'cts':make+ignore+['cts'],'finish':make+ignore+['finish']}
 record={'schema':'opentallas.qwen_tmr_checkpoint_recovery.v1','status':'PREPARED','original_orfs':str(old),'original_source':str(oldsrc),'source_sha256_unchanged':source,'resolver_sha256':sha(corrected),'original_hook_sha256':sha(oldhook),'original_config_sha256':sha(old/'config.mk'),'private_config_sha256':sha(work/'config.mk'),'upstream_sha256':upstream,'image_id':a.image_id,'runner_sha256':sha(Path(__file__)),'commands':commands,'original_artifacts_modified':False,'physical_signoff':False,'scope':'Correct resolver + persist actual postIO regions/retention; preserveRTL/SDC and completed synth/globalplace. Original failed run remains immutable.'}
 receipt=out/'recovery.json'
 def save():receipt.write_text(json.dumps(record,indent=2)+'\n')
 save()
 if not a.execute:print('RECOVERY_PREPARED');return 0
 def image_check():
  for image in [a.image_id,'openroad/orfs:asap7lock']:
   r=subprocess.run(['docker','image','inspect',image,'--format','{{.Id}}'],capture_output=True,text=True)
   if r.returncode or r.stdout.strip()!=a.image_id:raise RuntimeError('Immutable image/STA alias binding mismatch: '+image)
 image_check()
 for stage,command in commands.items():
  shell='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; '+shlex.join(command)
  cmd=['docker','run','--rm','-v',str(ROOT)+':/src:ro','-v',str(work)+':/work','-w','/OpenROAD-flow-scripts/flow',a.image_id,'bash','-lc',shell]
  with (out/(stage+'.log')).open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
  record.setdefault('exit_codes',{})[stage]=r.returncode;record['status']=stage.upper()+'_DONE' if not r.returncode else 'FAILED_'+stage.upper();save()
  if r.returncode:return r.returncode
  text=(out/(stage+'.log')).read_text()
  if stage.startswith('dryrun'):
   if re.search(r'(?:flow\.sh|yosys\.sh)\s+(?:1_|2_|3_1_)|\byosys\s+-',text):raise RuntimeError('Dry-run would redo completed upstream stage')
  if stage=='io' and 'TMR_RECOVERY_POSTIO_PERSISTED' not in text:raise RuntimeError('PostIO persistent DB marker missing')
  if stage=='readback' and ('TMR_RECOVERY_READBACK_PASS' not in text or 'TMR_ACTUAL_ODB_CLOCK_RESOLVER_PASS count=8' not in text):raise RuntimeError('Actual retained clock/region readback failed')
  for n,h in upstream.items():
   if sha(base/n)!=h or sha(work/rel/n)!=h:raise RuntimeError('Original or private upstream artifact changed: '+n)
 image_check()
 with (out/'signoff.log').open('w') as log:r=subprocess.run(['python3',str(ROOT/P/'signoff.py'),'--orfs-dir',str(work),'--output',str(out/'corner_sta.json')],stdout=log,stderr=subprocess.STDOUT)
 record['exit_codes']['signoff']=r.returncode;record['status']='ROUTED_FRESH_STA_RECORDED' if not r.returncode else 'FAILED_SIGNOFF';record['upstream_checkpoints_unchanged']=True
 if (out/'corner_sta.json').exists():record['corner_sta_sha256']=sha(out/'corner_sta.json')
 record['physical_signoff']=False # Actual SS/FF margins,DRC,inventory still require verdict review.
 save();return r.returncode
if __name__=='__main__':raise SystemExit(main())
