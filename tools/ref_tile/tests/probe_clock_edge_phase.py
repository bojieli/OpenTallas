#!/usr/bin/env python3
"""Actual preserved WFC CTS replay; run with ot-run, never a closure receipt.

Arguments: retained gate directory, new output directory, candidate helper,
optional positive/rise_source_only/no_phase_subtraction mutant. Every physical
input is retained. Only generated clock-selector procedures are overlaid.
The post-CTS ODB and raw scene/edge tags are saved before any measurement.
"""
import pathlib,shutil,subprocess,sys
fixture=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); helper=pathlib.Path(sys.argv[3])
mode=sys.argv[4] if len(sys.argv)>4 else 'positive'
if mode not in {'positive','rise_source_only','no_phase_subtraction'}: raise ValueError(mode)
out.mkdir(exist_ok=False)
work=out/'orfs';shutil.copytree(fixture/'routes/gate/work/orfs',work,symlinks=True)
text=helper.read_text();proc=text[text.index('proc ot_ce_clock_wire'):text.index('# Match ck_insertion.py')]
if mode=='rise_source_only':
    proc=proc.replace('foreach transition {rise fall} marker {^ v}', 'foreach transition {rise} marker {^}')
    proc=proc.replace('$edge ni {^ v}', '$edge ne "^"')
if mode=='no_phase_subtraction':
    proc=proc.replace('{$arrival - $phase}', '{$arrival}')
proc=proc.replace('  return [lindex $values 0]', '''
  set result [lindex $values 0]
  if {[string match {*lock*} [get_full_name $pin]] && ($result <= 0 || $result >= 100)} {
    error "EDGE_PHASE_ASSERT: actual small-leaf negedge insertion contains source waveform phase: $result"
  }
  return $result''')
# Preserve actual in-memory CTS database before any measurement or IO re-reference.
proc=proc.replace('  set scene [get_property', '''  if {![info exists ::edge_saved]} {write_db /work/clockedge_post_cts.odb; set ::edge_saved 1}
  puts "EDGE_WAVEFORM [get_full_name $clock] [$clock waveform]"
  set scene [get_property''',1)
proc=proc.replace('        set arrival [sta::time_sta_ui [$path arrival]]','''        set arrival [sta::time_sta_ui [$path arrival]]
        puts "EDGE_TAG [get_full_name $pin] $tag arrival=$arrival"''')
sdc=next((fixture/'src/physical/ref_tile').glob('dsfd_vm_wfc_fault_bridge_native_1016_r1/clock_entry.sdc'))
s=sdc.read_text();a=s.index('proc ot_ce_clock_wire'); b=s.index('# Match ck_insertion.py',a);s=s[:a]+proc+s[b:]
(out/'clock_entry.sdc').write_text(s)
sdc2=sdc.with_name('signoff.sdc'); s2=sdc2.read_text(); a2=s2.index('proc ot_ce_clock_wire');b2=s2.index('# Match ck_insertion.py',a2);(out/'signoff.sdc').write_text(s2[:a2]+proc+s2[b2:])
cmd=['docker','run','--rm','-e','LEC_CHECK=0','-v',f'{fixture}/src:/src:ro','-v',f'{work}:/work','-v',f'{out}/clock_entry.sdc:/src/physical/ref_tile/dsfd_vm_wfc_fault_bridge_native_1016_r1/clock_entry.sdc:ro','-v',f'{out}/signoff.sdc:/src/physical/ref_tile/dsfd_vm_wfc_fault_bridge_native_1016_r1/signoff.sdc:ro','-w','/OpenROAD-flow-scripts/flow','openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base cts']
with (out/'flow.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
print('REPLAY_RC',r.returncode, 'MODE',mode)
print('\n'.join(x for x in (out/'flow.log').read_text().splitlines() if 'EDGE_' in x or 'Error:' in x or 'CTS_MEASURE' in x))
sys.exit(r.returncode)
