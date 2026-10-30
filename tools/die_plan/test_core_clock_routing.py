import pytest
import core_clock_routing as CCR
import core_infra as CI
import core_infra_search as SEARCH
from test_core_infra import sample


def candidate():
    sl = sample()
    sl['core_tree'] = dict(clock_port='clk', nodes=[
        dict(name='root', master='BUFx16f_ASAP7_75t_R', xy_um=[430,430], parent='port:clk'),
        dict(name='leaf', master='BUFx8_ASAP7_75t_R', xy_um=[200,200], parent='root')],
        leaves=[dict(node='leaf', sinks=['u0/CLK'])])
    sl['pg_obstructions_um'] = {layer: [] for layer in ('M3','M4','M5')}
    sl['clock_ndr'] = dict(name='actual_2w2s', layers=['M3','M4','M5'], width_multiplier=2, spacing_multiplier=2)
    sl['effective_clock_routing'] = dict(mode='directional_envelope', layers=['M3','M4','M5'],
        layer_rc={layer:dict(resistance_kohm_per_um=r, capacitance_ff_per_um=c,
                            width_multiplier=2, spacing_multiplier=2)
                  for layer,r,c in [('M3',.3,.2),('M4',.1,.1),('M5',.2,.4)]},
        rc_source='synthetic prebuild test coupon', measured_timing_used=False, clearance_um=.072)
    return sl


def test_explicit_layer_rc_envelope_is_used_by_actual_model_and_emitter():
    sl=candidate(); model=CCR.profile(sl)
    assert model['vertical_rc'] == [.3,.4]  # worst R and C may be on different layers
    assert model['horizontal_rc'] == [.1,.1]
    plan=CI.compile_slice(sl)
    assert CI._ndr_line(plan) == 'ot_ci_clock_ndr {actual_2w2s} 2 2 {M3 M4 M5}'
    points={'u0/CLK':[210,210]}; caps={'u0/CLK':1.}
    actual=SEARCH.Model(sl, {'TT':{}}, points,caps,.001,.001)
    assert actual.routing_model == dict(nonleaf=model,leaf=model)
    assert actual.wire_cap[0] > actual.wire[0]*.001
    with pytest.raises(ValueError,match='competing'):
        SEARCH.Model(sl, {'TT':{}},points,caps,.001,.001,routing_model={})


@pytest.mark.parametrize('mutation,fragment',[
    (lambda s:s['effective_clock_routing'].update(layers=['M2','M4','M5']), 'M3/M4/M5'),
    (lambda s:s['clock_ndr'].update(layers=['M4','M5']), 'matching'),
    (lambda s:s['pg_obstructions_um'].pop('M3'), 'PG obstacles'),
    (lambda s:s['effective_clock_routing']['layer_rc'].pop('M3'), 'per-layer'),
    (lambda s:s['effective_clock_routing']['layer_rc']['M3'].update(resistance_kohm_per_um=float('nan')), 'invalid'),
    (lambda s:s['effective_clock_routing']['layer_rc']['M3'].update(width_multiplier=1), 'actual 2w2s'),
    (lambda s:s['effective_clock_routing'].update(measured_timing_used=True), 'measured'),
    (lambda s:s['effective_clock_routing'].update(rc_source=''), 'source'),
    (lambda s:s['effective_clock_routing'].update(clearance_um=-1), 'invalid'),
])
def test_incomplete_or_unpriced_optin_refused(mutation,fragment):
    sl=candidate(); mutation(sl)
    with pytest.raises(CI.InfraError,match=fragment):CI.compile_slice(sl)


def test_default_legacy_ndr_tcl_unchanged():
    sl=candidate(); sl.pop('effective_clock_routing');sl['clock_ndr']['layers']=['M4','M5']
    assert CI._ndr_line(CI.compile_slice(sl)) == 'ot_ci_clock_ndr {actual_2w2s} 2 2'
    assert CCR.profile(sl) is None


def test_unreachable_declared_pg_envelope_is_refused():
    sl=candidate(); sl['pg_obstructions_um']['M3']=[[0,0,864,864]]
    with pytest.raises(CI.InfraError,match='PG envelope'):
        CI.compile_slice(sl)


def test_tcl_explicit_layers_cover_m3_and_refuse_stale_rule():
    import pathlib
    import subprocess
    source=pathlib.Path(CI.__file__).with_name('core_infra.tcl')
    script=r'''
source SOURCE
set ::ot_ci_b block; set ::ot_ci_u 1000; set ::ot_ci_tree_out {};set ::stale 0
namespace eval ord {proc get_db_tech {} {return tech}}
proc block {method args} {return ndr}
proc tech {method layer} {return $layer}
proc M3 {method} {return 18}
proc M4 {method} {return 24}
proc M5 {method} {return 24}
proc ndr {method layer} {return rule_$layer}
proc rule_M3 {method} {if {$::stale} {return 18}; return 36}
proc rule_M4 {method} {return 48}
proc rule_M5 {method} {return 48}
ot_ci_clock_ndr actual 2 2 {M3 M4 M5}
set ::stale 1
if {![catch {ot_ci_clock_ndr actual 2 2 {M3 M4 M5}} msg] || $msg ne "OT_CORE_INFRA_CLOCK_NDR_RULE_MISMATCH actual/M3"} {error "stale M3 default accepted: $msg"}
if {![catch {ot_ci_clock_ndr actual 2 2 {M2 M4 M5}} msg]} {error "unsupported layer accepted"}
'''.replace('SOURCE','{'+str(source)+'}')
    result=subprocess.run(['tclsh'],input='if {[catch {\n'+script+'\n} msg]} {puts stderr $msg; exit 1}\n',text=True,capture_output=True)
    assert result.returncode == 0,result.stderr


def test_emission_needs_matching_actual_model_results():
    import copy
    sl=candidate()
    with pytest.raises(CI.InfraError,match='qualification'):
        CI.emit_tcl(sl)
    sl['core_tree']['model_qualification']=dict(model='effective_directional_envelope',
        source='synthetic model control', measured_timing_used=False,
        effective_clock_routing=copy.deepcopy(sl['effective_clock_routing']),
        corners={corner:dict(leaf_min=10.,leaf_max=11.,leaf_window=1.,slew_max=40.) for corner in ('TT','FF')})
    assert 'ot_ci_clock_ndr {actual_2w2s} 2 2 {M3 M4 M5}' in CI.emit_tcl(sl)
    sl['effective_clock_routing']['layer_rc']['M3']['capacitance_ff_per_um']*=2
    with pytest.raises(CI.InfraError,match='qualification'):
        CI.emit_tcl(sl)
