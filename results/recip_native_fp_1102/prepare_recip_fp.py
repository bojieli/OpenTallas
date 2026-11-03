from pathlib import Path
import shutil,json,hashlib,re,tarfile
r=Path('/srv/opentallas-scratch2/claude/codex-q6-resume-prep-0230');o=Path('/srv/opentallas-scratch2/claude/codex-recip-native-fp-0640');assert not o.exists();o.mkdir();k=o/'kit';shutil.copytree(r/'candidate/recip',k);b='run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base';dst=k/b;dst.mkdir(parents=True)
for p in (r/'source/recip'/b).glob('1_*'):shutil.copy2(p,dst/p.name)
logs=k/'run/logs/asap7/hc_ot_qkh_recip_leaf__216x216/base';logs.mkdir(parents=True)
for n in ('1_2_yosys.log','1_synth.log'):shutil.copy2(r/'source/recip/run/logs/asap7/hc_ot_qkh_recip_leaf__216x216/base'/n,logs/n)
ad=json.loads((r/'ADMISSION_BUNDLE.json').read_text());shutil.copytree(ad['dir'],o/'admission_tools')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected={str(p.relative_to(k)):sha(p) for p in k.rglob('*') if p.is_file() and not str(p.relative_to(k)).startswith(('geom/','run/logs/'))}
# The three authentic stage outputs are already independently joined to native216.
record=json.loads((r/'recip_resume_record.json').read_text()) if (r/'recip_resume_record.json').exists() else None
three={n:sha(dst/n) for n in ('1_2_yosys.v','1_synth.odb','1_synth.sdc')}
assert three=={'1_2_yosys.v':'ebaffaeff0de02cd19b36ce216f644f43a319171467760e258f9042fd86815c6','1_synth.odb':'7870f090f523e48c889cbc7701ff159973f1d3337eb09ed4817decf2f1c431db','1_synth.sdc':'19e5582c1234efaff179dcec5736577b188062dad321f71fbcc21d4b5616354f'}
def cfg(p):return dict(re.findall(r'^(?:override )?export (\w+)\s*=\s*(.*?)\s*$',p.read_text(),re.M))
a,z=cfg(k/'config.mk'),cfg(k/'config_native216.mk');keys=[n for n in a if n.startswith(('SYNTH','VERILOG')) or n in ('SDC_FILE','ADDER_MAP_FILE','DONT_USE_SC','DONT_USE_CELLS','REMOVE_ABC_BUFFERS','PRE_SYNTH_TCL','POST_SYNTH_TCL')];assert all(a[n]==z.get(n) for n in keys),[(n,a[n],z.get(n)) for n in keys if a[n]!=z.get(n)]
fp={'classification':'MANUAL_PHYSICAL_CONTINUATION','KW_RESUME':'FULL/SYNTH unchanged; no cache PASS/fingerprint override','original_source':str(r/'source/recip'),'corrected_prepared_source':str(r/'candidate/recip'),'authentic_synth':three,'synth_config_fields_equal':{n:a[n] for n in keys},'readonly_unknown_inputs_preserved':['core_preflight.py','config_native216.mk'],'outline':[216,138.24],'same_RTL_SDC_defines':True,'normal_native_target':'do-floorplan = do-2_1_floorplan do-2_2_floorplan_macro do-2_3_floorplan_tapcell do-2_4_floorplan_pdn do-2_floorplan do-2_floorplan.sdc','allowed_outputs':'run/{results,logs,reports}/asap7/hc_ot_qkh_recip_leaf__216x216/base/2_* only','no_SYNTH_PLACE_CTS_route_STA':True,'resources':{'mem_GB':4,'threads':1,'disk_GB':2},'measured_old_2_1_floorplan_peak_KB':519900,'measured_old_2_1_floorplan_elapsed_s':56.65,'synth_output_hashes_unchanged_required_after_job':True,'expected':expected}
(o/'EXPECTED.json').write_text(json.dumps(fp,indent=2)+'\n')
with tarfile.open(o/'finite_export.tar.gz','w:gz') as t:
 for n in ('kit','admission_tools','EXPECTED.json'):t.add(o/n,arcname=n)
print(o,'export_MB', (o/'finite_export.tar.gz').stat().st_size/1e6)
