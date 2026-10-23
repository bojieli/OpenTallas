from pathlib import Path
import importlib.util,json,hashlib
old=Path('/srv/opentallas-scratch/claude/codex-qw-classgeom0125');s=Path('/srv/opentallas-scratch/claude/codex-qw-classgeom0150');s.mkdir()
(s/'src').symlink_to(old/'src',target_is_directory=True)
helper=Path('/srv/opentallas-scratch/claude/classgeom_receiver_plan.py')
spec=importlib.util.spec_from_file_location('channel',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p=m.expand_channel(json.loads((old/'receiver_plan.json').read_text()),'dvs_E3',129.6,32983.176,24288.824,west=129.6)
p['receiver_channel_plan'].update(western_service_clearance_consumed_um=259.2,core_feed_bump_xy_um=[17150.4,12096.],core_feed_bump_moved=True,core_feed_bump_delta_um=[-259.2,0.])
for n in ['gen.sh','run.sh','run_candidate.sh','land_plan_bi_chain.json','reset_release_prior_g4try3.json']:
 t=(old/n).read_text().replace(str(old),str(s))
 if n=='gen.sh':t=t.replace('CORE_FEED_XY=17280.0,12096.0','CORE_FEED_XY=17150.4,12096.0')
 (s/n).write_text(t)
(s/'receiver_plan.json').write_text(json.dumps(p,indent=1)+'\n')
d=json.loads((old/'source.json').read_text());d['predecessor']=str(old);d['predecessor_terminal']='FAIL E2 class rly_dv_ch_E2_ar_ard_0 blocked dvs_E3; E1 class obstruction cleared';d['geometry_recipe_commit']='60b972a5f';d['geometry_plan']=p['receiver_channel_plan'];d['sha256']={f:hashlib.sha256((s/f).read_bytes()).hexdigest() for f in d['sha256']};(s/'source.json').write_text(json.dumps(d,indent=2)+'\n')
