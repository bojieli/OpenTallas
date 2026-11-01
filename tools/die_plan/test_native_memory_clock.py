"""Native SRAM references are separate from measured logic CTS means."""
import json
from types import SimpleNamespace
import pytest
import core_clock_contract as C


def model(tmp_path):
    name = 'ram'
    meta = dict(alignment_v2=dict(kind='sram', spec=dict(name=name,words=512,bits=128), verification=dict(pass_=True)))
    meta['alignment_v2']['verification'] = {'pass':True}
    (tmp_path/'ram.json').write_text(json.dumps(meta))
    tables = 'rise_constraint(t){values("1");} fall_constraint(t){values("2");}'
    text = '''cell(ram) { memory(){type:ram; address_width:9; word_width:128;}
      pin(clk){direction:input; clock:true;}
      pin(d){direction:input; timing(){related_pin:"clk";timing_type:setup_rising;TABLES}
        timing(){related_pin:"clk";timing_type:hold_rising;TABLES}}
      pin(q){direction:output;timing(){related_pin:"clk";timing_type:rising_edge;
        cell_rise(t){values("10");}cell_fall(t){values("11");}}}}'''.replace('TABLES',tables)
    for corner in ('tt','ff'):(tmp_path/f'ram_{corner}.lib').write_text(text)
    core = dict(inst='u_ram',module=name,lib=str(tmp_path/'ram_tt.lib'))
    return core, SimpleNamespace(types={'parent':dict(hard_cores=[core])})


def test_native_is_reference_not_zero_mean(tmp_path):
    core, plan = model(tmp_path)
    refs = C.native_clock_models(plan,'parent')
    assert refs[0]['clock_pins'] == ['clk']
    assert refs[0]['corners']['ff']['arc_census'] == dict(setup=1,hold=1,clk_to_q=1)
    assert 'mean_ps' not in json.dumps(refs)
    assert C.latency_table(plan,'parent') == []


@pytest.mark.parametrize('edit', ['cell','memory','clock','hold','output','name','corner'])
def test_native_model_fails_closed(tmp_path, edit):
    core, plan = model(tmp_path)
    lib = tmp_path/'ram_ff.lib'
    if edit == 'name':
        meta=json.loads((tmp_path/'ram.json').read_text());meta['alignment_v2']['spec']['name']='other'
        (tmp_path/'ram.json').write_text(json.dumps(meta))
    elif edit == 'corner':lib.unlink()
    else:
        old,new={'cell':('cell(ram)','cell(wrong)'), 'memory':('type:ram','type:rom'),
                 'clock':('clock:true','clock:false'), 'hold':('hold_rising','max_clock_tree_path'),
                 'output':('cell_rise(t)','missing_rise(t)')}[edit]
        lib.write_text(lib.read_text().replace(old,new))
    with pytest.raises(C.ContractError):C.latency_table(plan,'parent')


def test_native_early_compensation_is_not_ignored(tmp_path):
    core,plan=model(tmp_path)
    plan.types['parent']['clock']=dict(taps=[dict(kind='core',name='u_ram.clk',early_ps=1)])
    with pytest.raises(C.ContractError,match='native SRAM early compensation'):C.latency_table(plan,'parent')


def test_logic_still_requires_actual_mean(tmp_path):
    core,plan=model(tmp_path)
    (tmp_path/'ram.json').unlink()
    with pytest.raises(C.ContractError):C.latency_table(plan,'parent')
