from pathlib import Path
import shutil,subprocess,json,hashlib
B=Path('/srv/opentallas-scratch/claude/mu-die-qw');old=B/'dv2f21g5r10bfp_diag1340';original=B/'dv2f21g5r10bfp';new=B/'dv2f21g5r10bfp_diag_profile1536'
assert not new.exists();new.mkdir()
# Source tree is immutable shared bytes; no source writes in this physical path.
subprocess.run(['cp','-al',str(old/'src'),str(new/'src')],check=True)
subprocess.run(['cp','-a','--reflink=auto',str(original/'out'),str(new/'out')],check=True)
for rel in ['out.log','pre_bind','reset_projection_diag1340','reset_sync_audit.txt','hier_check.line','diagnostic_compiler_failure.json','diagnostic_open_classification.json','reset_release_prior_g4try3.json','saved_case_diagnostic.py','freeze_saved_case_diagnostic.py']:
 p=old/rel;q=new/rel
 if p.is_dir():shutil.copytree(p,q)
 else:shutil.copy2(p,q)
(new/'original_gen_contract').mkdir()
for name in ['run.sh','gen.sh','run_candidate.sh','SHA256SUMS']:shutil.copy2(original/name,new/'original_gen_contract'/name)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(new/'original_gen_contract/run.sh')=='4d7c31b3ed2aed3f8945577ee9728ce7f5beb9fc5f088b3eca9ee08ebe48a0bc'
profiles={m:{'directory':p,'requires_lclk':m=='ot_qfd_ucie_x64_phy'}for m,p in [('ot_qfd_serdes_112g_x12_phy_s597','physical/qwen_missing_phy/nface_tall_1017/ot_qfd_serdes_112g_x12_phy_s597'),('ot_qfd_ucie_x64_phy','physical/qwen_missing_phy/nface_tall_1017/ot_qfd_ucie_x64_phy'),('ot_qkvd_ucie_x64_phy','physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy')]}
select=json.loads((new/'src/results/arch/qwen_split_compute_1014/bind_view_select.json').read_text());select.setdefault('views',{}).update({m:r['directory']for m,r in profiles.items()});(new/'physical_view_select.json').write_text(json.dumps(select,indent=2)+'\n')
shutil.copy2(Path(__file__).with_name('physical_profile_guard.py'),new/'physical_profile_guard.py')
files=['original_gen_contract/'+x for x in ['run.sh','gen.sh','run_candidate.sh','SHA256SUMS']]+['physical_view_select.json','physical_profile_guard.py']
for row in profiles.values():files.extend(str(p.relative_to(new))for p in (new/'src'/row['directory']).iterdir()if p.is_file())
c=dict(schema='opentallas.qwen.saved_case_phy_profile.v1',expected_environment={'OT_SPLIT_PHY_TALL':'1','OT_SPLIT_PHY_NFACE':'1','OT_SPLIT_UCIE_PHY_CLK':'1'},profiles=profiles,sha256={f:sha(new/f)for f in files},source_claim='Restores actual original TALL/NFACE source profile; analog/PG/nativeR/package qualification not inferred',previous_failure='dv2f21g5r10bfp_diag1340 unit3097292 exit11 packaging omission retained')
(new/'physical_profile_contract.json').write_text(json.dumps(c,indent=2)+'\n')
s=(old/'run_r10_physical_diagnostic.sh').read_text().replace('dv2f21g5r10bfp_diag1340','dv2f21g5r10bfp_diag_profile1536').replace('export OT_BIND_VIEW_SELECT=results/arch/qwen_split_compute_1014/bind_view_select.json','export OT_BIND_VIEW_SELECT="$S/physical_view_select.json"\nexport OT_SPLIT_PHY_TALL=1 OT_SPLIT_PHY_NFACE=1 OT_SPLIT_UCIE_PHY_CLK=1\npython3 "$S/physical_profile_guard.py" "$S" > "$S/physical_profile_guard.json"')
(new/'run_r10_physical_diagnostic.sh').write_text(s)
# Reuse captured GEN/source/reach/reset/hierarchy proofs, never rerun GEN/P2R.
subprocess.run(['python3',str(new/'freeze_saved_case_diagnostic.py'),str(new)],check=True)
p=new/'saved_case_diagnostic_manifest.json';d=json.loads(p.read_text())
for rel in files+['physical_profile_contract.json','run_r10_physical_diagnostic.sh']:
 d['sha256'][rel]=sha(new/rel)
d['physical_environment_guard']={'contract':'physical_profile_contract.json','guard':'physical_profile_guard.py','original_run_sha256':sha(new/'original_gen_contract/run.sh')};p.write_text(json.dumps(d,indent=2)+'\n')
print('PREPARED',new,'manifest',sha(p),'inputs',len(d['sha256']))
