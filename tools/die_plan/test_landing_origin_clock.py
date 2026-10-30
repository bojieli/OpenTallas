"""An explicit existing primary tap may clock only the dedicated START origin."""
import copy
import json
from pathlib import Path

import pytest

from clock_landings import Landings, LandingError, START_PIN_IN
from test_start_pins_compose import start_vehicle
from test_clock_landings import B_BODY


TINY = json.loads(Path(__file__).with_name('examples').joinpath('tiny_plan.json').read_text())
ROLE = ('child', START_PIN_IN, False, 0)
HEAD = 'module mid_mod (\n input wire clk,\n input wire clk_t7,\n output wire value'
BODY = 'ot_dp_rgate raw (.clk(clk), .d(rst_parent), .run(run), .q(rst_n_t0));'


def emitter(chosen='clk_t7'):
    raw = copy.deepcopy(TINY)
    if chosen is not None:
        raw['partition_types']['mid'].setdefault('clock', {})['landing_origin_clock_port'] = chosen
    obj = Landings.__new__(Landings)
    obj.plan, obj.types, obj.ca, obj.strap = raw, raw['partition_types'], True, None
    obj.reset_placements = {};obj.tstart=None
    return obj


def emit(obj, head=HEAD, role=ROLE):
    return '\n'.join(obj._origin_rtl('mid', dict(role=role), {}, BODY, [], head=head))


def test_existing_primary_tap_changes_only_origin_and_records_source():
    old = emit(emitter(None))
    obj = emitter(); actual = emit(obj)
    assert old.replace('.clk(clk), .rst_raw_n(cland_origin_reset), .p_start(',
                       '.clk(clk_t7), .rst_raw_n(cland_origin_reset), .p_start(') == actual
    assert 'u_cland_origin_rst (.clk(clk), .d(rst_parent)' in actual
    assert obj.reset_placements['mid']['count_origin']['clock_port'] == 'clk_t7'
    assert emit(emitter('clk')) == old


@pytest.mark.parametrize('chosen', ['clk_t999', 'pma_rck', 'fclk_in_data', 'value', True, 'clk_t7[0]'])
def test_spelling_cannot_invent_a_primary_clock(chosen):
    with pytest.raises(LandingError): emit(emitter(chosen))


@pytest.mark.parametrize('mutation', ['missing', 'output', 'vector', 'alias', 'data_role', 'secondary', 'forwarded', 'pad'])
def test_actual_interface_and_roles_must_match(mutation):
    obj = emitter(); head = HEAD; ck = obj.types['mid']['clock']
    if mutation == 'missing': head = head.replace(' input wire clk_t7,\n', '')
    if mutation == 'output': head = head.replace('input wire clk_t7', 'output wire clk_t7')
    if mutation == 'vector': head = head.replace('input wire clk_t7', 'input wire [0:0] clk_t7')
    if mutation == 'alias': head += ',\n input wire \\clk_t7[0] '
    if mutation == 'data_role': obj.types['mid']['buses'].append(dict(name='clk_t7', dir='in', width=1))
    if mutation == 'secondary': ck['edge_clocks'] = [dict(port='clk_t7', xy=[1, 1], period_mult=1)]
    if mutation == 'forwarded': ck['landing_contract'] = dict(pins=[dict(name='clk_t7', kind='clock', dir='in')])
    if mutation == 'pad': obj.types['mid']['pads'] = [dict(name='clk_t7', dir='in', width=1, clock=True)]
    with pytest.raises(LandingError): emit(obj, head)


@pytest.mark.parametrize('role,strap', [(('root',64),None), (('relay','other',1),None),
                                      (('child','ordinary_bus',False,0),None), (ROLE,True)])
def test_hook_is_only_for_dedicated_parameter_start_child(role,strap):
    obj=emitter();obj.strap=strap
    with pytest.raises(LandingError,match='dedicated parameter START child'): emit(obj, role=role)


def test_type_emission_passes_actual_existing_header_and_preserves_default():
    p, table = start_vehicle(strap=False)
    table['count_aligned']['ports']['Q']['K'] = -2
    table['count_aligned']['regions']['r2'].update(edge_fall=False,pad=0)
    for key in ('die','budgets','clock'):
        p[key] = copy.deepcopy(TINY[key])
    p.setdefault('lanes',[])
    old = Landings(p,table).type_rtl('B',B_BODY)
    p['partition_types']['B'].setdefault('clock',{})['landing_origin_clock_port']='clk'
    obj=Landings(p,table)
    assert obj.type_rtl('B',B_BODY)==old
    assert obj.reset_placements['B']['count_origin']['clock_port']=='clk'


def group_emitter():
    obj=emitter('primary_group_port');t=obj.types['mid'];ck=t['clock']
    t['hard_cores']=[dict(inst='u_core',module='core',origin_um=[10,10],outline_um=[8.64,8.64])]
    ck.update(core_taps='early',taps=[dict(name='u_core.clk',kind='core',xy=[20,20],insertion_ps=100)],
              core_groups=[dict(name='group',port='primary_group_port',xy=[20,20],members=[dict(inst='u_core',pin='clk',tap='u_core.clk')],
                                insertion_ps=100,insertion_ff_ps=81,basis='parent_budget',source='test primary input')])
    return obj


def test_nonprefix_primary_core_group_port_uses_role_not_spelling():
    assert '.clk(primary_group_port)' in emit(group_emitter(),HEAD.replace('clk_t7','primary_group_port'))


def test_native_recovered_root_cannot_be_relabelled_as_primary_core_group(tmp_path):
    obj=group_emitter();t=obj.types['mid'];sha='a'*64
    census=dict(top_module=t['module'],source_odb_sha256=sha,
        clock_root_ports=[dict(port='clk',net='clk',dir='INPUT'),dict(port='pma_rck[0]',net='pma_net',dir='INPUT')],
        ff_count=2,ff_clock_net_counts=dict(clk=1,pma_net=1),
        ff_clock_pins=[dict(inst='p0',pin='CLK',net='clk'),dict(inst='p1',pin='CLK',net='pma_net')],
        macro_clock_pins=[dict(inst='u_core',master='core',pin='clk',net='pma_net')])
    path=tmp_path/'census.json';path.write_text(json.dumps(census))
    t['clock']['native_domains']=dict(schema='opentallas.native_clock_domains.v1',core_root='clk',
        census_file=str(path),source_odb_sha256=sha,
        macro_pins=[dict(inst='u_core',module='core',pin='clk',root='pma_rck')])
    with pytest.raises(LandingError,match='actual primary native root'):
        emit(obj,HEAD.replace('clk_t7','primary_group_port'))
