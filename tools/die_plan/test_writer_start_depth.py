"""W1 forwarded-writer START (DIE-HEAD-38): W relays before the sender FSTART face flop, receiver K' = K + W - R."""
import copy
import pytest
import count_align_bind as CAB
import landing_place as LP
import schema as S
from clock_landings import Landings, LandingError
from test_clock_landings import ca_vehicle, A_BODY, B_BODY
from test_count_straps import strap_vehicle, TOP
from test_reader_start_depth import enable as enable_reader

WS = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]


def enable(p, n=1, raw='rst_n_t0'):
    p['partition_types']['A'].setdefault('clock', {})['landing_writer_start'] = dict(
        depth=n, branches={'x': {'stages': [dict(xy_um=[2. + i, 1.], raw_reset=raw) for i in range(n)]}})


def test_default_absent_is_unchanged():
    p, t = strap_vehicle()
    base = Landings(p, t)
    a0, b0 = base.type_rtl('A', A_BODY), base.type_rtl('B', B_BODY)
    assert '.d(cland_start_d), .q(cland_fstart_out_x));' in a0 and 'writer_start' not in a0 + b0
    assert CAB.writer_start_depth(p, 'A') == 0 and CAB.writer_start_depth(p, 'A', 'x') == 0
    assert LP._writer_start_groups(p['partition_types']['A']) == []
    st = CAB.strap_ties(t['count_aligned'], p)
    assert st['instances']['b']['values']['strap_ca_k_y'] == 62 and st['instances']['c']['values']['strap_ca_k_y'] == 63
    assert all('writer_start_depth' not in r for r in base.rows)


@pytest.mark.parametrize('w', [1, 2])
def test_writer_chain_and_receiver_K_plus_W(w):
    p, t = strap_vehicle(k_b=-2, k_c=-1)
    enable(p, w)
    st = CAB.strap_ties(t['count_aligned'], p)
    assert st['instances']['b']['values']['strap_ca_k_y'] == (-2 + w) % 64
    assert st['instances']['c']['values']['strap_ca_k_y'] == (-1 + w) % 64
    c = Landings(p, t)
    a = c.type_rtl('A', A_BODY)
    assert 'u_cland_writer_start_x_0 (.clk(clk), .rst_raw_n(rst_n_t0), .d(cland_start_d), .q(cland_writer_start_x_0));' in a
    assert f'.d(cland_writer_start_x_{w-1}), .q(cland_fstart_out_x));' in a
    assert '(* keep = "true" *) ot_dp_landing_relay u_cland_writer_start_x_0' in a
    assert {r['dst'] if 'dst' in r else r.get('port'): r['ring_k'] for r in c.rows}  # rows carry ring_k
    assert sorted(r['ring_k'] for r in c.rows) == sorted([-2 + w, -1 + w])
    assert all(r['writer_start_depth'] == w and r['steady_data_cycles_added'] == 0 for r in c.rows)
    ws = c.reset_placements['A']['x']['writer_start']
    assert ws['K_adjustment_at_receiver'] == w and ws['boot_extra_cycles'] == w and len(ws['stages']) == w
    c.type_rtl('B', B_BODY)
    top = c.top_rtl(TOP)
    assert ".strap_ca_k_y(6'b%s)" % format((-2 + w) % 64, '06b') in top


def test_writer_and_reader_compose_K_plus_W_minus_R():
    p, t = strap_vehicle(k_b=-2, k_c=3)
    enable(p, 1); enable_reader(p)
    st = CAB.strap_ties(t['count_aligned'], p)
    assert st['instances']['b']['values']['strap_ca_k_y'] == (-2 + 1 - 2) % 64
    assert st['instances']['c']['values']['strap_ca_k_y'] == (3 + 1 - 2) % 64
    c = Landings(p, t)
    assert sorted(r['ring_k'] for r in c.rows) == [-3, 2]
    assert all(r['boot_extra_cycles'] == 3 for r in c.rows)


def test_firm_groups():
    p, _ = strap_vehicle(); enable(p, 2)
    g = LP._writer_start_groups(p['partition_types']['A'])
    assert [r[0] for r in g] == ['u_cland_writer_start_x_0', 'u_cland_writer_start_x_1']
    assert g[0][1] == pytest.approx([-.16, -1.16, 4.16, 3.16]) and g[0][2] == 'writer-start:x'


def test_schema():
    js = pytest.importorskip('jsonschema')
    sch = WS['landing_writer_start']
    js.validate(dict(depth=1, branches={'x': {'stages': [dict(xy_um=[1, 2], raw_reset='rst_rl_3')]}}), sch)
    for bad in (dict(depth=0, branches={'x': {'stages': [dict(xy_um=[1, 2], raw_reset='r')]}}),
                dict(depth=1, branches={}),
                dict(depth=1, branches={'x': {'stages': [dict(xy_um=[1], raw_reset='r')]}}),
                dict(depth=1, branches={'x': {'stages': [dict(xy_um=[1, 2], raw_reset='1bad')]}}),
                dict(depth=1, origin_rect_um=[0, 0, 1, 1], branches={'x': {'stages': [dict(xy_um=[1, 2], raw_reset='r')]}})):
        with pytest.raises(js.ValidationError):
            js.validate(bad, sch)


PORT_BODY = A_BODY.replace(" output wire [4:0] x\n", " output wire [4:0] x,\n output wire rst_o_0\n").replace(
    " assign x = 0;", " assign x = 0;\n assign rst_o_0 = rst_n_t0;")


@pytest.mark.parametrize('edit,body,reason', [
    (lambda c: c['branches']['x']['stages'].pop(), A_BODY, 'exactly 1 physical stages'),
    (lambda c: c['branches']['x']['stages'][0].update(raw_reset='invented'), A_BODY, 'registered wavefront driver'),
    (lambda c: c['branches']['x']['stages'][0].update(xy_um=[float('nan'), 1]), A_BODY, 'finite xy_um'),
    (lambda c: c['branches'].update(nope=c['branches']['x']), A_BODY, 'output rings'),
    (lambda c: c.update(depth=True), A_BODY, 'integer'),
    (lambda c: None, PORT_BODY, 'drives an output port'),
])
def test_unsafe_contract_fails_closed(edit, body, reason):
    p, t = strap_vehicle(); enable(p)
    edit(p['partition_types']['A']['clock']['landing_writer_start'])
    with pytest.raises((LandingError, CAB.BindError), match=reason):
        Landings(p, t).type_rtl('A', body)


def test_parameter_form_fails_closed():
    p, t = ca_vehicle(); enable(p)
    with pytest.raises(LandingError, match='strap-form'):
        Landings(p, t).type_rtl('A', A_BODY)
