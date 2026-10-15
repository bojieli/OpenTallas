from pathlib import Path
import hashlib,json,re,shutil
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p,bit,unit,collect,export in [('su10',244,'2277038','2303816','2328401'),('sfu14',235,'2277037','2303815','2328409')]:
 b=Path(f'/srv/opentallas-scratch/codex/lg-{p}-slew-repair-1015');top=f'hfd_vm_lg_{p}'
 odbdir=next((b/'work/results/asap7').glob('*/base'));reportdir=next((b/'work/reports/asap7').glob('*/base'))
 e=b/'publication';e.mkdir(exist_ok=True)
 for n in ('corner_sta.json','ck_routed.json','final_actual_pin_pg.json','final_pin_audit.json','upstream_check.json','route.log','collect.sh','check_export.sh','prepared.json','lef_postprocess.log','strict_child_lint.json','export_checked.log'):
  shutil.copy2(b/n,e/n)
 for n in ('6_final.v','native_bank_pin_coordinates.tsv'):
  shutil.copy2(odbdir/n,e/n)
 for n in ('6_finish.rpt',):shutil.copy2(reportdir/n,e/n)
 c=json.loads((b/'corner_sta.json').read_text());clock=json.loads((b/'ck_routed.json').read_text());pin=json.loads((b/'final_pin_audit.json').read_text());up=json.loads((b/'upstream_check.json').read_text())
 assert c['closes_signoff'] and pin['pass'] and up['changed']==[]
 s=(reportdir/'6_finish.rpt').read_text()
 counts={k:int(re.search(rf'{re.escape(k)} violation count (\d+)',s).group(1)) for k in ('max slew','max fanout','max cap','setup','hold')};assert all(v==0 for v in counts.values()),counts
 view=b/'views_checked'/top
 lint=json.loads((b/'strict_child_lint.json').read_text());assert lint['verdict']=='PASS',lint
 d={'schema':'opentallas.hbm.lg-native-routed-leaf.v2','result':'PASS_SINGLE_LITERAL_LEAF_PROTOTYPE','master':top,'source_commit':'f3fa747d8','functional_receipt_commit':'506e762c6','functional_scope':'812 realprogramme words→24 literal near/middle/far leaves→24 current7b2 VM SRAMs,3072 exact writes/readbacks and real payload mutant rejected','native_parameters':{'READ_RETURN':10 if p=='su10' else 14,'WRITE_RETURN':7 if p=='su10' else 11},'baseline_failure':'one native actual return-D max-slew violation; original complete ODB/SPEF kept separately','repair':{'hook_commit':'63f59cc86','capture_bit':bit,'old':'INVx2_ASAP7_75t_R','new':'INVx4_ASAP7_75t_R','additional_area_um2':0.02916,'additional_FF':0,'additional_cycles':0,'clock_roots_changed':False,'constraints_changed':False,'native_CTS_objects_unchanged':24},'route':{'host':'ot-epyc4','unit_prefix':'oth-ubuntu-'+unit,'directory':str(b),'status':'TERMINAL exit0','collection_unit_prefix':collect,'checked_export_unit_prefix':export,'DRC':0,'antenna_nets':0,'violation_counts':counts,'TT_setup_ps':c['setup_tt']['worst_slack_ps'],'SS_setup_ps':c['setup_ss']['worst_slack_ps'],'actual_FF_hold_ps':c['hold_ff']['worst_slack_ps'],'odb_sha256':sha(odbdir/'6_final.odb'),'spef_sha256':sha(odbdir/'6_final.spef'),'FF_scope':'independent realFF library + actual routedSPEF + unchanged propagated signoffSDC; not TT-min'},'raw_routed_clock_ps':{k:{**clock[k]['all'],'spread_ps':round(clock[k]['all']['max']-clock[k]['all']['min'],2)} for k in ('tt','ff','ss')},'outline_um':[150.336,151.2],'orientation':'R0 only','pin_gate':pin,'views':{'checked_against_routed_TT_FF':True,'strict_child_lint':'PASS capM5 strict-pockets','LEF_postprocess':'standard own-net PORT stub and own M5 pocket closure, no routed ODB change','warnings':lint.get('warns',lint.get('warnings',[])),'hashes':{f.name:sha(f) for f in view.iterdir() if f.is_file()}},'open':['Actual96leaf absolute station/root delivery and compensated relativephase','Actual parent cut/PG/IR/EM and hierarchical access; HC48um harness does not qualify these new actual homes','Whole-token compiler/globalprogramme binding and production throughput'],'publication':'New literal near/middle singleleaf prototype only; historical HC and failed baseline preserved'}
 d['evidence_sha256']={f.name:sha(f) for f in e.iterdir() if f.is_file()}
 (b/'receipt.json').write_text(json.dumps(d,indent=2)+'\n')
 print(p,d['raw_routed_clock_ps'])
