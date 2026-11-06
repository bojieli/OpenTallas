"""Legacy input capture is explicit hardware and exactly one extra data cycle."""
from copy import deepcopy
import pytest
import clock_landings as CL
from test_clock_landings import vehicle


def configured():
    p, t = vehicle()
    p['partition_types']['B']['clock'] = {'landing_input_freg': ['y']}
    t['ports'][0]['added_cycles'] = 4
    return p, t


def body():
    return """module b_mod (
 input wire clk,
 input wire [4:0] y
);
 wire rst_n, rst_n_t0, rr_parent, run;
 ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));
 wire [4:0] y_q;
 assign y_q = y;
endmodule
"""


def test_explicit_capture_emits_hardware_and_prices_once():
    p, t = configured()
    c = CL.Landings(p, t)
    text = c.type_rtl('B', body())
    assert 'ot_dp_clk_landing #(.W(5), .FREG(1)) u_cland_y' in text
    assert c.manifest()['lane_added_cycles'] == {'L': 4}
    assert c.manifest()['ports'][0]['input_capture_cycles'] == 1
    req = CL.requirements(p, t)
    assert req['lane_added_cycles'] == {'L': 4}
    assert req['added_live_data_storage_flops'] == 30
    assert req['cohorts']['B'][0]['added_live_data_storage_flops'] == 30


def test_default_remains_three_cycles_and_no_capture_parameter():
    p, t = vehicle(); c = CL.Landings(p, t)
    assert '.FREG(' not in c.type_rtl('B', body())
    assert c.manifest()['lane_added_cycles'] == {'L': 3}
    assert c.manifest()['added_cycles_per_crossing'] == 3
    assert CL.requirements(p, t)['added_live_data_storage_flops'] == 25


def test_stale_sidecar_or_unpriced_parameter_fails():
    p, t = configured(); t['ports'][0]['added_cycles'] = 3
    with pytest.raises(CL.LandingError, match='must be 4'): CL.Landings(p, t)
    p, t = vehicle(); t['ports'][0]['ring_params'] = {'FREG': 1}
    with pytest.raises(CL.LandingError, match='explicit plan selection'): CL.Landings(p, t)


@pytest.mark.parametrize('bad', [True, ['y', 'y'], [1], ['y[0]']])
def test_bad_capture_selection_rejected(bad):
    p, t = configured();p['partition_types']['B']['clock']['landing_input_freg'] = bad
    with pytest.raises(CL.LandingError): CL.Landings(p, t)


def test_native_network_and_bound_manifest_agree_without_doublecount():
    p, t = configured()
    p['lanes'] = [dict(id='L', ports=['P'])]
    p['clock'] = {'landing_network': {'data_cycles_per_crossing': 3, 'edges': [
      dict(id='cland_clk__P',kind='clock',src=dict(part='a',bus='fclk_out_x'),
           dst=dict(part='b',bus='fclk_in_y'))]}}
    assert CL.network_lane_cycles(p) == {'L': 4}
    assert CL.Landings(p, t).manifest()['lane_added_cycles'] == {'L': 4}
    p['partition_types']['B']['clock']['landing_input_freg'] = []
    assert CL.network_lane_cycles(p) == {'L': 3}


def test_count_aligned_form_cannot_silently_take_legacy_capture():
    p, t = configured()
    t['count_aligned'] = {'ports': {}}
    with pytest.raises(CL.LandingError, match='legacy ring'): CL.Landings(p, t)

def test_capture_configuration_passes_real_plan_schema():
    import schema as S
    clock_schema = S.SCHEMA['properties']['partition_types']['additionalProperties']['properties']['clock']
    errors = []
    S._check({'landing_input_freg': ['y']}, clock_schema, '$.clock', errors)
    assert not errors
    S._check({'landing_input_freg': ['bad bus']}, clock_schema, '$.clock', errors)
    assert any('landing_input_freg' in e for e in errors)
