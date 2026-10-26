import copy
import importlib.util
from pathlib import Path

loader = importlib.util.spec_from_file_location('flow_watch_tests', Path(__file__).with_name('flow_watch.py'))
watch = importlib.util.module_from_spec(loader)
loader.loader.exec_module(watch)


def test_reference_admission_and_other_die_metadata_do_not_change_vehicle():
    before = {'watch':['tools/flow_canary/*'], 'canaries':[
        {'die':'s81_head','item':'head','gen':'generate-head','mem_gb':24,'golden':None},
        {'die':'qwen_kvsys','item':'kv','gen':'generate-kv','mem_gb':40}]}
    after = copy.deepcopy(before)
    after['canaries'][1]['mem_gb'] = 52
    after['canaries'][1]['gen'] = 'generate-kv-fixed'
    assert not watch.spec_flow_changed(before, after, 's81_head')
    assert watch.spec_flow_changed(before, after, 'qwen_kvsys')
    after['canaries'][0]['gen'] = 'generate-head-fixed'
    assert watch.spec_flow_changed(before, after, 's81_head')
    assert watch.spec_flow_changed(before, after, 'unknown')


def test_watch_list_edits_are_not_a_flow_change():
    # AUTOPILOT-FIX 10-25 23:30: the lists only name the flow files, which every caller diffs itself
    spec = {'watch':['tools/*'],'canaries':[{'die':'s81_head','item':'head','gen':'gen'}]}
    after=copy.deepcopy(spec)
    after['watch'].append('physical/*')
    after['watch_exclude']=['*.md']
    assert not watch.spec_flow_changed(spec, after, 's81_head')
    after['die_plans']={'s81_head':['s81_head']}
    assert watch.spec_flow_changed(spec, after, 's81_head')


def test_live_watch_covers_flow_code_only():
    import json
    spec=json.loads(Path(__file__).with_name('canaries.json').read_text())
    flow=['tools/ref_tile/ref_tile.py','tools/ref_tile/cross_clock_paths.tcl','tools/die_plan/gen_phys.py',
          'tools/die_plan/hold_gate.tcl','physical/common_flow/clock_spine.tcl','tools/flow_canary/canaries.json',
          'physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py']
    assert watch.flow_paths(flow, spec, 'qwen_kvsys_core') == sorted(flow)
    other=['tools/flow_canary/trigger.py','tools/ref_tile/README.md','tools/ref_tile/tests/x.tcl',
           'tools/ref_tile/examples/x.py','tools/ref_tile/specs_qfwd/x.json','tools/ref_tile/m5-reroute-compare.timer',
           'physical/die_plan/qwen_kvsys/cores/harden/results/e1.json','physical/die_plan/qwen_kvsys/cores/harden/x.log',
           'physical/die_plan/qwen_kvsys/cores/harden/review/x.png','tools/autopilot/autopilot.py','docs/a.md']
    assert watch.flow_paths(other, spec, 'qwen_kvsys_core') == []
    # another die's plan tree never counts for a frozen QC / S81-HEAD row
    assert watch.flow_paths(['physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py'], spec, 'qwen_compute') == []
    assert watch.flow_paths(['physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py'], spec, 's81_head') == []


def test_test_changes_do_not_hold_rows_but_production_changes_do():
    spec={'watch':['physical/common_flow/*'], 'watch_exclude':['*/test_*.py','*/tests/*']}
    assert watch.flow_paths(['physical/common_flow/test_shallow_clock_cl.py'],spec,'s81_head') == []
    assert watch.flow_paths(['physical/common_flow/shallow_clock.py'],spec,'s81_head') == ['physical/common_flow/shallow_clock.py']


def test_new_unknown_implementation_fields_fail_closed():
    before={'watch':['tools/*'],'canaries':[{'die':'s81_head','item':'head','gen':'gen'}]}
    after=copy.deepcopy(before)
    after['canaries'][0]['future_floorplan_mode']='changed'
    assert watch.spec_flow_changed(before, after, 's81_head')
    after=copy.deepcopy(before)
    after['future_shared_config']={'changed':True}
    assert watch.spec_flow_changed(before, after, 's81_head')
