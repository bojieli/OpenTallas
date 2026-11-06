"""A proved hard landing is accepted only at its exact parent interface."""
import copy
import json
import pytest
import face_guard as F
import hard_landing as H

NET = '''module top(clk, fclk_in_a, other, a, start);
input clk; input fclk_in_a; input other; input [1:0] a; input start;
signed_ring u_child (.clk(clk), .fclk(fclk_in_a), .d(a), .t_rst_n(start));
endmodule'''


def specs(tmp_path):
    row = dict(form='hard_child', D=4, instance='u_child', master='signed_ring',
               port='d', width=2, clock_pin='fclk', clock_port='fclk_in_a', evidence=str(tmp_path))
    return dict(a=row, start=dict(row, port='t_rst_n', width=1))


def proof(_):
    return (dict(master='signed_ring', D=4, width=2),
            dict(land_mux_bits=2, ring_start=dict(t_rst_n=dict(ring_clock=['fclk'], writer_flops=5))))


def test_exact_parent_child_and_writer_clock(tmp_path, monkeypatch):
    monkeypatch.setattr(H, 'prove', proof)
    r = F.guard(NET, land=specs(tmp_path), clocks=['fclk_in_a', 'other'])
    assert r['verdict'] == 'PASS' and r['hard_landing_bits'] == 3
    assert r['hard_landings']['start']['port'] == 't_rst_n'


@pytest.mark.parametrize('mutation', ['master', 'instance', 'port', 'clock', 'bits', 'extra_load', 'depth', 'width'])
def test_mismatched_actual_parent_rejected(tmp_path, monkeypatch, mutation):
    monkeypatch.setattr(H, 'prove', proof)
    net, land = NET, specs(tmp_path)
    if mutation == 'master': net = net.replace('signed_ring u_child', 'wrong_master u_child')
    if mutation == 'instance': net = net.replace('u_child', 'wrong_child')
    if mutation == 'port': net = net.replace('.d(a)', '.wrong(a)')
    if mutation == 'clock': net = net.replace('.fclk(fclk_in_a)', '.fclk(other)')
    if mutation == 'bits': net = net.replace('.d(a)', '.d({a[0],a[1]})')
    if mutation == 'extra_load': net = net.replace('endmodule', 'DFFHQNx1_ASAP7_75t_R extra (.CLK(clk), .D(a[0]), .QN()); endmodule')
    if mutation == 'depth': land['a']['D'] = 5
    if mutation == 'width': land['a']['width'] = 3
    r = F.guard(net, land=land, clocks=['fclk_in_a', 'other'])
    assert r['verdict'] == 'FAIL' and r['fail_counts'].get('land_slot'), r


def test_missing_real_evidence_never_accepts_macro(tmp_path):
    r = F.guard(NET, land=specs(tmp_path), clocks=['fclk_in_a', 'other'])
    assert r['verdict'] == 'FAIL'
    assert 'evidence rejected' in str(r['fails'])


def test_no_selected_hard_landing_keeps_metadata_unchanged(tmp_path):
    land = dict(schema='land_slots/3', buses=dict(a=dict(D=4, form='hold_mux')))
    assert H.emit({}, land, tmp_path, tmp_path) == land


def test_external_evidence_path_rejected(tmp_path):
    land = specs(tmp_path)
    p = tmp_path / 'land_slots.json'; p.write_text(json.dumps(dict(buses=land)))
    with pytest.raises(ValueError, match='inside the kit'): F.kit_land(p)
