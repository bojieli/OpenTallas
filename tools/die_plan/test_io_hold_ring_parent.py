"""DH56-IOHP: ring_hold kits carry the parent obligation's plan digest, and an ideal die spine is accepted only for
source-synchronous ring inputs captured on the SENDER's forwarded clock in the same parent."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import io_hold_parent as parent
from test_io_hold import _plan
from test_io_hold_core_parent import core_sta


def ring_sta(fwd=True):
    sta = core_sta()
    sta['spine'] = 'ideal'
    for c in sta['corners'].values():
        if fwd:
            c['seams']['pfa->pfb/fclk_in_x_i'] = copy.deepcopy(c['seams']['pfa->pfb/z_i'])
    return sta


def test_ideal_spine_ring_inputs_on_sender_fclk_pass():
    r = parent.check(_plan(), ring_sta(), core_receiver='pfb', core_type='cfg7', core_ports=['x_i', 'z_i'],
                     ring_clocks={'x_i': 'fclk_in_x_i', 'z_i': 'fclk_in_x_i'})
    assert r['verdict'] == 'PASS', r['ports']
    assert all('ideal spine exact' in q['clock_basis'] for q in r['ports'])


def test_ideal_spine_never_passes_without_ring_forwarded_seam():
    for ring, fwd in (({'x_i': 'fclk_in_x_i'}, True),           # z_i is not a ring input
                      ({'x_i': 'fclk_in_x_i', 'z_i': 'fclk_in_x_i'}, False),   # fclk not driven by the sender
                      ({}, True)):
        r = parent.check(_plan(), ring_sta(fwd), core_receiver='pfb', core_type='cfg7', core_ports=['x_i', 'z_i'],
                         ring_clocks=ring)
        assert r['verdict'] == 'INCOMPLETE', (ring, fwd)
        assert any('clock-tree or routed clock' in q.get('why', '') for q in r['ports'])


def test_receiver_partition_module_binds_type():
    sta = core_sta()
    sta['instances']['pfb'] = 'ot_cfg7_mod'
    sta['view_evidence']['ot_cfg7_mod'] = sta['view_evidence']['cfg7']
    r = parent.check(_plan(), sta, core_receiver='pfb', core_type='cfg7', core_ports=['x_i', 'z_i'],
                     core_module='ot_cfg7_mod')
    assert r['verdict'] == 'PASS'
    r = parent.check(_plan(), sta, core_receiver='pfb', core_type='cfg7', core_ports=['x_i', 'z_i'],
                     core_module='other')
    assert r['verdict'] != 'PASS'


def test_kit_ring_clocks_reads_ring_tags(tmp_path):
    (tmp_path / 'constraint.sdc').write_text('# OT_FWD_RING_MIN 80.0000\n'
                                             '# OT_FWD_RING_INPUTS fclk_in_rx_i rx_i[*] cland_dn_ready_rx_i\n'
                                             'set_input_delay -min 80 -clock fclk_in_rx_i [get_ports {rx_i[*]}]\n')
    assert parent.kit_ring_clocks(tmp_path) == {'rx_i': 'fclk_in_rx_i', 'cland_dn_ready_rx_i': 'fclk_in_rx_i'}


def test_ring_hold_kit_budget_records_plan_digest():
    import schema
    import gen_phys
    import sdc_lint
    from test_ring_input_sdc import _ring_kit
    P0, tn, _b, _w = _ring_kit()
    assert not gen_phys.ring_hold_obligation(P0, tn)          # no clock.ring_hold: no obligation (byte-identical)
    raw = copy.deepcopy(P0.raw)
    raw['clock']['ring_hold'] = dict(sender_ps=80.0)
    P = schema.Plan(raw)
    assert gen_phys.ring_hold_obligation(P, tn)
    assert sdc_lint._io_hold_ctx(P, tn).get('hold_in_min_ports_ps')  # the obligation signoff.py applies


def test_io_hold_kit_bind_refuses_mismatch(tmp_path):
    import json
    import io_hold_kit_bind as B
    import schema
    import sdc_lint
    import landing_contract as LC
    from test_ring_input_sdc import _ring_kit
    P0, tn, _b, _w = _ring_kit()
    raw = copy.deepcopy(P0.raw)
    raw['clock']['ring_hold'] = dict(sender_ps=80.0)
    P = schema.Plan(raw)
    (tmp_path / 'plan.json').write_text(json.dumps(raw))
    kd = tmp_path / 'kit'
    kd.mkdir()
    (kd / 'budget.json').write_text(json.dumps(dict(die=P.name, type=tn)))
    (kd / 'sdc_lint.json').write_text(json.dumps(sdc_lint._io_hold_ctx(P, tn)))
    (kd / 'constraint.sdc').write_text('x\n' + LC.ring_input_sdc(P, tn))
    assert B.main([str(tmp_path / 'plan.json'), str(kd), '--write']) == 0
    bud = json.loads((kd / 'budget.json').read_text())
    assert bud['io_hold']['mode'] == 'ring_hold' and len(bud['io_hold']['plan_sha256']) == 64
    assert B.main([str(tmp_path / 'plan.json'), str(kd)]) == 1          # already bound
    (kd / 'budget.json').write_text(json.dumps(dict(die=P.name, type=tn)))
    (kd / 'sdc_lint.json').write_text(json.dumps(dict(hold_in_min_ports_ps={'other': 1.0})))
    assert B.main([str(tmp_path / 'plan.json'), str(kd)]) == 1          # obligation differs
