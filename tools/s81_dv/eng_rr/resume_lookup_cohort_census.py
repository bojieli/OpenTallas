#!/usr/bin/env python3
"""Resume only the census of immutable completed r1 netlist; preserve original failure."""
import pathlib,json,shutil,subprocess,hashlib
r=pathlib.Path.cwd();old=r/'native_r1';out=r/'census_r2';out.mkdir(exist_ok=False);src=out/'src';shutil.copytree(old/'src',src)
g='/srv/opentallas-scratch/claude/git-mirror/OpenTallas.git';ref='9725ff954'
p=src/'tools/textbook_lint.py';p.write_bytes(subprocess.check_output(['git','--git-dir='+g,'show',ref+':tools/textbook_lint.py']))
manifest=json.loads((old/'native/source_manifest.json').read_text());base=json.loads((src/'tools/s81_dv/eng_rr/native_template/reference_native.json').read_text());top=manifest['top']
net=old/'native/results/asap7/opentallas_lookup_cohorts_native/base/1_2_yosys.v';assert net.exists()
manifest['resume']={'synthesis_rerun':False,'prior_failure':'native_r1/native/census.log ModuleNotFoundError textbook_lint; preserved','mapped_netlist_sha256':hashlib.sha256(net.read_bytes()).hexdigest(),'additional_tool_ref':ref,'additional_tool_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'SOURCE_DIRECT_DIAGNOSTIC, existingphysicalreset2wrapper notpresent'}
(out/'source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
cmd=['docker','run','--rm','-v',str(src)+':/src:ro','-v',str(old/'native')+':/native_old:ro','-v',str(out)+':/work','openroad/orfs:latest','python3','/src/tools/ref_tile/native_census.py','--netlist','/native_old/results/asap7/opentallas_lookup_cohorts_native/base/1_2_yosys.v','--top',top,'--out','/work/native_census.json']
for lib in base['liberty']:
 if not lib['path'].startswith('/src/'):cmd+=['--liberty',lib['path']]
m='physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2'
for c in ['tt','ff']:cmd+=['--liberty','/src/'+m+'_'+c+'.lib']
with(out/'census.log').open('w')as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
j=json.loads((out/'native_census.json').read_text());print('SOURCE_DIRECT_NATIVE',j['status'],j['max_dynamic_loads'],len(j['violations']),len(j['role_errors']),flush=True)
raise SystemExit(rc)
