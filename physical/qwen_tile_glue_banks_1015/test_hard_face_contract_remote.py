from pathlib import Path
import subprocess,json,time
R=Path('/srv/opentallas-scratch/claude/ref_gate/qfd_tile_nk_banked_v1-20261015-035551'); C=R/'routes/gate/work/orfs'; out=Path('/tmp/qce-face-contract-results');out.mkdir(exist_ok=True)
mutations={
 'legacy_failure': '',
 'ordinary_std_ff_positive': 'set b [ord::get_db_block];set bt [$b findBTerm {n_y[0]}];foreach i [$b getInsts] {if {[string match DFF* [[$i getMaster] getName]]} {set q [$i findITerm QN];if {$q ne \"NULL\" && [$q getNet] ne \"NULL\"} {$bt disconnect;$bt connect [$q getNet];break}}}',
 'verified_hard_faces': '',
 'missing_endpoint': 'set b [ord::get_db_block]; set i [$b findInst face_n_a]; set t [$i findITerm {d[0]}]; $t disconnect',
 'extra_residual_sink': 'set b [ord::get_db_block]; set n [[$b findBTerm {n_a[0]}] getNet]; foreach i [$b getInsts] {if {[string match DFF* [[$i getMaster] getName]]} {set t [$i findITerm D]; if {$t ne "NULL"} {$t disconnect; $t connect $n; break}}}',
 'wrong_bit': 'set b [ord::get_db_block]; set i [$b findInst face_n_a]; set t [$i findITerm {d[0]}]; $t disconnect; $t connect [[$b findBTerm {n_a[1]}] getNet]',
 'extra_boundary_port':'set b [ord::get_db_block]; odb::dbBTerm_create [[$b findBTerm {n_a[0]}] getNet] injected_unregistered',
 'changed_source_binding':'',
 'changed_view_binding':'',
 'changed_view_bytes':'',
 'own_clock_comb_sink':'set b [ord::get_db_block]; set n [[$b findBTerm ck] getNet]; foreach i [$b getInsts] {if {[string match BUF* [[$i getMaster] getName]]} {set t [$i findITerm A]; $t disconnect; $t connect $n; break}}'
}
results=[]
for name,mutation in mutations.items():
 binding='/src/physical/qwen_tile_glue_banks_1015/hard_face_binding.tcl'
 if name in ('changed_source_binding','changed_view_binding'):
  binding='/test/hard_face_binding_bad.tcl';s=Path('/tmp/hard_face_binding.tcl').read_text();import re;matches=list(re.finditer(r' [0-9a-f]{64}',s));m=matches[0 if name=='changed_source_binding' else 3];s=s[:m.start()]+' '+'0'*64+s[m.end():];Path('/tmp/hard_face_binding_bad.tcl').write_text(s)
 script=out/(name+'.tcl')
 script.write_text('read_db /work/results/asap7/opentallas_qfd_tile_nk_banked_v1_asap7_ref_gate/base/3_2_place_iop.odb\n'+mutation+'\nset ::env(RESULTS_DIR) /out\n'+('' if name in ('legacy_failure','ordinary_std_ff_positive') else 'set ::env(OT_OFLOP_HARD_FACE_AUDIT) '+binding+'\n')+'source /test/io_flop_at_pins.tcl\nset hist [dict create]; foreach i [[ord::get_db_block] getInsts] {if {[string match DFF* [[$i getMaster] getName]]} {set t [$i findITerm CLK];set n [$t getNet];if {$n eq \"NULL\"} {dict incr hist DISCONNECTED} else {dict incr hist [$n getName]}}}; puts \"ACTUAL_DFF_CLOCK_NET_CENSUS $hist\"\nputs CONTRACT_TEST_PASS\nexit\n')
 cmd=['docker','run','--rm','-v',str(R/'src')+':/src:ro','-v',str(C)+':/work:ro','-v',str(out)+':/out','-v','/tmp:/test:ro']
 cmd+=['-v','/tmp/qce-face-audit-mount:/src/physical/qwen_tile_glue_banks_1015:ro']
 if name=='changed_view_bytes':
  import shutil
  altered=out/'altered_view';shutil.copytree(R/'src/physical/ref_tile/qwen_glue_v514/views/qwen_glue_v514',altered,dirs_exist_ok=True)
  with (altered/'qwen_glue_v514.lef').open('a') as f:f.write('\n# negative test changed actual LEF bytes\n')
  cmd+=['-v',str(altered)+':/src/physical/ref_tile/qwen_glue_v514/views/qwen_glue_v514:ro']
 cmd+=['openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit','/out/'+name+'.tcl']
 p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(out/(name+'.log')).write_text(p.stdout)
 wanted=name in ('verified_hard_faces','ordinary_std_ff_positive'); actual='CONTRACT_TEST_PASS' in p.stdout
 relevant=[x for x in p.stdout.splitlines()if 'OT_HARD_FACE' in x or 'OT_IOFLOP:' in x or 'Error:' in x]
 specific={'missing_endpoint':'wrong/missing/extra endpoint at n_a[0]','extra_residual_sink':'own residual/comb endpoint at n_a[0]','wrong_bit':'wrong/missing/extra endpoint at n_a[0]','extra_boundary_port':'unclassified boundary port injected_unregistered','changed_source_binding':'changed bound file rtl/','changed_view_binding':'changed bound file physical/','changed_view_bytes':'changed bound file physical/','own_clock_comb_sink':'own residual clock has non-FF endpoint ck/'}
 passed=(name not in specific or specific[name] in p.stdout) and actual==wanted and (wanted or (('OT_HARD_FACE:' if name!='legacy_failure' else 'OT_IOFLOP: no pin flop found') in p.stdout))
 results.append(dict(case=name,exit=p.returncode,expected_pass=wanted,actual_pass=actual,test_pass=passed,evidence=relevant[-3:]))
 print(json.dumps(results[-1]),flush=True)
(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
raise SystemExit(0 if all(x['test_pass'] for x in results) else 1)
