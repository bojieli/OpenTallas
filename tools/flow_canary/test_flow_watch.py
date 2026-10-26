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


def test_watch_rules_remain_part_of_flow_contract():
    spec = {'watch':['tools/*'],'canaries':[{'die':'s81_head','item':'head','gen':'gen'}]}
    after=copy.deepcopy(spec)
    after['watch'].append('physical/*')
    assert watch.spec_flow_changed(spec, after, 's81_head')


def test_test_changes_do_not_hold_rows_but_production_changes_do():
    spec={'watch':['physical/common_flow/*'], 'watch_exclude':['*/test_*.py','*/tests/*']}
    assert watch.flow_paths(['physical/common_flow/test_shallow_clock_cl.py'],spec,'s81_head') == []
    assert watch.flow_paths(['physical/common_flow/shallow_clock.py'],spec,'s81_head') == ['physical/common_flow/shallow_clock.py']
