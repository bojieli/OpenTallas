import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_hold_capture_loaded_map import merge_scoped,worst_slack,loaded_cone


def test_conflicting_template_names_preserve_both_library_definitions(tmp_path):
    a=tmp_path/'a.lib';b=tmp_path/'b.lib'
    a.write_text('library (a) { lu_table_template (delay) { variable_1 : input_net_transition; } cell (a) { timing () { cell_rise (delay) { values ("17"); } } } }')
    b.write_text('library (b) { lu_table_template (delay) { variable_1 : related_pin_transition; } cell (b) { timing () { rise_constraint (delay) { values ("23"); } } } }')
    merged,cells,names=merge_scoped([a,b])
    assert 'input_net_transition' in merged and 'related_pin_transition' in merged
    assert 'cell_rise (source0_delay)' in cells['a'] and 'rise_constraint (source1_delay)' in cells['b']
    assert '"17"' in cells['a'] and '"23"' in cells['b'] and len(names)==2


def test_all_groups_parser_keeps_worst_path_and_rejects_diagnostics():
    report='time 1ps\n802.37 slack (MET)\n-922.47 slack (VIOLATED)\n'
    assert worst_slack(report)==-922.47
    with pytest.raises(ValueError):worst_slack('Warning: missing endpoint\n'+report)
    with pytest.raises(ValueError):worst_slack(report.replace('time 1ps','time 1ns'))


def test_full_loaded_cone_retains_actual_macro_loop_and_existing_endpoint():
    cone,macros=loaded_cone()
    assert macros in cone and 'for (p = 0; p < 2;' in macros and 'b < CODE_BANKS' in macros
    assert 'ROM_HOLD_DIRECT_CAPTURE=1' in cone and 'CODE_BANKS=5' in cone
    assert 'always @(posedge clk) consumer_q <= wrom_q;' in cone
    assert 'input wire [2*CODE_BANKS*266-1:0] rom_rd' not in cone


def test_consumer_endpoint_resolution_follows_only_actual_qn_inverters():
    from qwen_rom_hold_capture_loaded_map import consumer_endpoints
    net={'netnames':{'consumer_q':{'bits':list(range(512))}},'cells':{}}
    for i in range(512):
        net['cells'][f'inv{i}']={'type':'INVx1_ASAP7_75t_R','connections':{'A':[1024+i],'Y':[i]}}
        net['cells'][f'ff{i}']={'type':'DFFHQNx1_ASAP7_75t_R','connections':{'QN':[1024+i]}}
    assert set(consumer_endpoints(net))=={f'ff{i}/D' for i in range(512)}
    del net['cells']['ff0']
    with pytest.raises(ValueError):consumer_endpoints(net)
