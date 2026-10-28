import json
from pathlib import Path
import gen_phys as G
import landing_contract as L
import schema as S
import sdc_lint as SD

HERE=Path(__file__).parent

def fixture():
    raw=json.loads((HERE/'examples/tiny_plan.json').read_text())
    tn=next(iter(raw['partition_types']));t=raw['partition_types'][tn]
    t.setdefault('clock',{})['landing_contract']={'pins':[
        dict(name='fclk_out_data',dir='out',kind='clock',source_clock_port='clk'),
        dict(name='cland_up_fault',dir='out',kind='ctl'),
        dict(name='cland_up_ready',dir='out',kind='ctl'),
        dict(name='cland_fstart_in_data',dir='in',kind='ctl')]}
    t['count_straps']=[dict(name='strap_ca_k_data',width=6)]
    return S.Plan(raw),tn

def test_explicit_output_collection_covers_control_excludes_forward_clock():
    p,tn=fixture();text=G.sdc(p,tn,G.type_pins(p,tn))
    assert 'remove_from_collection' not in text
    collection=text.splitlines()[0]
    assert collection.startswith('set cland_data_outputs [get_ports {')
    assert 'cland_up_fault' in collection and 'cland_up_ready' in collection
    assert 'fclk_out_data' not in collection
    assert 'create_generated_clock -name fclk_out_data' in text

def test_lint_context_times_landing_controls_and_knows_count_straps():
    p,tn=fixture();ctx=SD.kit_context(p,tn)
    assert {'cland_up_fault','cland_up_ready'} <= set(ctx['outputs'])
    assert 'cland_fstart_in_data' in ctx['inputs']
    assert 'strap_ca_k_data' in ctx['straps']
    assert 'fclk_out_data' not in ctx['outputs']
    assert ctx['forwarded_clock_outputs']==['fclk_out_data']


def test_head_phy_nonclock_pad_outputs_kept_clock_pads_not_data():
    p,tn=fixture()
    p.types[tn]['pads']=[dict(name='pma_tx',dir='out',width=544),dict(name='pma_rx',dir='in',width=544),
                        dict(name='pma_tck',dir='out',clock=True),dict(name='pma_rck',dir='in',clock=True)]
    selectors=L.data_output_selectors(p,tn)
    assert 'pma_tx[*]' in selectors and 'pma_tck' not in selectors
    ctx=SD.kit_context(p,tn)
    assert 'pma_tx' in ctx['outputs'] and 'pma_rx' in ctx['inputs']
    assert 'pma_tck' not in ctx['outputs'] and 'pma_rck' not in ctx['inputs']
