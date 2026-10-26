from pathlib import Path
import shutil,json,hashlib
old=Path('/srv/opentallas-scratch/claude/codex-qw-classgeom0105');s=Path('/srv/opentallas-scratch/claude/codex-qw-classgeom0125');s.mkdir()
(s/'src').symlink_to(old/'src',target_is_directory=True)
for n in ['gen.sh','run.sh','run_candidate.sh','receiver_plan.json','land_plan_bi_chain.json','reset_release_prior_g4try3.json']:
 t=(old/n).read_text().replace(str(old),str(s))
 if n=='gen.sh':t=t.replace('CORE_FEED_XY=17409.6,12096.0','CORE_FEED_XY=17280.0,12096.0')
 if n=='run.sh':t=t.replace('O=../out; L=../out.log;', 'O=$S/out; L=$S/out.log;')
 (s/n).write_text(t)
p=json.loads((s/'receiver_plan.json').read_text());p['receiver_channel_plan']['core_feed_bump_xy_um']=[17280.,12096.];p['receiver_channel_plan']['core_feed_bump_moved']=True;p['receiver_channel_plan']['core_feed_bump_delta_um']=[-129.6,0.];(s/'receiver_plan.json').write_text(json.dumps(p,indent=1)+'\n')
d=json.loads((old/'source.json').read_text());d['predecessor']=str(old);d['predecessor_terminal']='FAIL actual corefeed bump overlaps shifted dvs_E0';d['immutable_source_reuse']=str(old/'src');d['output_paths']='absolute fresh directory; immutable source reused without mutation';d['geometry_plan']=p['receiver_channel_plan'];d['sha256']={f:hashlib.sha256((s/f).read_bytes()).hexdigest() for f in d['sha256']};(s/'source.json').write_text(json.dumps(d,indent=2)+'\n')
