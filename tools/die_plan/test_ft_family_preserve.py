"""Opt-in physical-stage family exclusion; no instance dont_touch or synthesis edit."""
import json,subprocess
from pathlib import Path
import pytest
from ft_full_stage import install,install_family_preservation

def test_boolean_and_complete_packet_required(tmp_path):
 for value in (True,1,'yes'):
  with pytest.raises(ValueError):install({'ft_full_stage_preserve_ff_families':value},tmp_path/'plan.json',tmp_path)

def test_whole_mixed_family_preserved_before_both_native_stage_exclusions(tmp_path):
 doc={'slots':{'ft0':{'targets':[{'master':m} for m in ('DFFHQNx1_ASAP7_75t_R','DFFHQNx2_ASAP7_75t_R','DFFASRHQNx1_ASAP7_75t_R')]}}}
 (tmp_path/'config.mk').write_text('export DONT_USE_CELLS = OLD*\nexport PRE_RESIZE_TCL = /work/existing_resize.tcl\n')
 (tmp_path/'face_flops.tcl').write_text('lappend ::events face_place\n')
 install_family_preservation(doc,tmp_path)
 hook=(tmp_path/'ft_family_preserve.tcl').read_text()
 assert 'DFFHQNx*_ASAP7_75t_R' in hook and 'DFFASRHQNx*_ASAP7_75t_R' in hook
 assert 'DFFHQNx1_ASAP7_75t_R' not in hook
 assert 'dont_touch' not in hook and 'set_dont_use' not in hook
 assert 'export DONT_USE_CELLS = OLD*\n' in (tmp_path/'config.mk').read_text()
 assert (tmp_path/'ft_family_pre_resize.tcl').read_text().startswith('source "/work/existing_resize.tcl"\n')
 # Each native physical stage is a FRESH Tcl process. Its PRE hook changes
 # process-local env before ORFS calls set_dont_use, preserving existing flags.
 for stage in ('global_place','resize'):
  script='''set ::events {};set ::env(DONT_USE_CELLS) OLD*
proc set_dont_use {patterns} {set ::disabled $patterns;lappend ::events exclusions}
proc repair_design {} {
 foreach existing {DFFHQNx1_ASAP7_75t_R DFFHQNx2_ASAP7_75t_R} {
  if {![string match [lindex $::disabled 2] $existing]} {error "mixed family resize choice retained"}
 }
 if {[lsearch -glob $::disabled BUF*]>=0} {error "D-pin repair buffer family blocked"}
 lappend ::events data_pin_repair_allowed
}
source HOOK
set_dont_use $::env(DONT_USE_CELLS)
repair_design
if {$::events ne {exclusions data_pin_repair_allowed}} {error "PRE-hook/native ordering changed"}
'''.replace('HOOK','{'+str(tmp_path/'ft_family_preserve.tcl')+'}')
  p=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
  assert p.returncode==0 and not p.stderr,p.stdout+p.stderr

def test_nonsequential_family_rejected(tmp_path):
 with pytest.raises(ValueError):install_family_preservation({'slots':{'f':{'targets':[{'master':'BUFx8_ASAP7_75t_R'}]}}},tmp_path)
