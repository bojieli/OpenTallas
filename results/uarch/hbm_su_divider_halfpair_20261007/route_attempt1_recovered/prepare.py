from pathlib import Path
import hashlib,json,shutil,subprocess
r=Path('/srv/opentallas-scratch2/scratch/codex/su64-sta-recovery-2f22d245c');job=Path('/srv/opentallas-scratch2/scratch/claude/closure-loop/hbm_su_full64_64cda61ab');old=job/'routes/hbm_su_full64_64cda61ab.prev_1791400184';base=next((old/'work/orfs/results/asap7').glob('*/base'));dst=r/'orfs/results/asap7'/base.parent.name/'base';dst.mkdir(parents=True,exist_ok=False)
inputs=[]
def copy(s,d):
 d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(s,d);inputs.append({'source':str(s),'private':str(d),'sha256':hashlib.sha256(s.read_bytes()).hexdigest(),'bytes':s.stat().st_size});assert hashlib.sha256(d.read_bytes()).hexdigest()==inputs[-1]['sha256']
for name in ['6_final.odb','6_final.spef','6_final.sdc']:copy(base/name,dst/name)
post=['physical/hbm_su_c12/signoff_833_io150.sdc','physical/hbm_su_div64/full_generated_clocks_candidate.sdc','physical/hbm_su_div64/propagate_signoff.sdc']
for name in post:copy(job/'src'/name,r/'src'/name)
for name in ['args','physical.json','corner.log']:copy(old/name,r/('original_'+name))
metrics=next((old/'work/orfs/logs/asap7').glob('*/base/5_2_route.json'));copy(metrics,r/'original_drc_metrics.json')
image=subprocess.check_output(['docker','image','inspect','openroad/orfs:asap7lock','--format','{{.Id}}'],text=True).strip()
rec={'source_pin':'64cda61abe6779567e8601286ea0ee0245da7746','helper_pin':'2f22d245c','helper_sha256':hashlib.sha256((r/'src/tools/w18/corner_sta.py').read_bytes()).hexdigest(),'image_id':image,'post_sdc_order':post,'inputs':inputs,'scope':'Fresh standalone SS/FF of completed original route; automatic second route untouched'}
(r/'inputs.json').write_text(json.dumps(rec,indent=2)+'\n')
