"""Whole plain-FT class ABI, boundary pins, and fail-closed checks."""
import copy
import json
import os
from pathlib import Path
import shutil
import sys

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind
import gen_rtl
import schema
import spare_ft
import straps


def vehicle():
    p = json.loads((HERE / 'examples/bind_tiny/die_plan_lanes.json').read_text())
    p['partition_types']['tf']['superset'] = True
    p['partition_types']['tf']['ft_slots'][0].update(in_window_um=[5,10], out_window_um=[5,10], layers=['M6'])
    p['partitions'].append(dict(name='F_unused', type='tf', spare_ends=['y']))
    return p


def test_requires_explicit_unlanded_whole_exact_sized_ft():
    p = vehicle()
    assert list(spare_ft.connections(spare_ft.declared(p)['F_unused'])) == [('y_i', "9'd0"), ('y_o', '')]
    for name, edit in [
        ('half', lambda q: q['partitions'][-1].update(spare_ends=['y_i'])),
        ('unknown', lambda q: q['partitions'][-1].update(spare_ends=['non_ft'])),
        ('bound', lambda q: q['partitions'][-2].update(spare_ends=['y'])),
        ('width', lambda q: q['ports'][0].update(width=7)),
        ('epoch', lambda q: q['ports'][0].update(epoch=False)),
        ('landing', lambda q: q['partition_types']['tf'].update(clock={'landing_contract': {'bands': {'y_i': {}}}})),
        ('forwarded clock', lambda q: q['partition_types']['tf'].update(clock={'edge_clocks': [{'port':'fclk_out_y_o'}]})),
    ]:
        q = copy.deepcopy(p)
        edit(q)
        with pytest.raises(ValueError):
            spare_ft.declared(q)


def test_gen_top_emits_full_epoch_and_strict_instance_pads(tmp_path):
    raw = json.loads((HERE / 'examples/tiny_plan.json').read_text())
    t = raw['partition_types']['mid']
    t['superset'] = True
    fl = dict(t['ft_slots'][0], name='extra', width=7, in_window_um=[5,10], out_window_um=[5,10], layers=['M6'])
    t['ft_slots'].append(fl)
    for part in raw['partitions']:
        if part['type'] == 'mid':
            part['spare_ends'] = ['extra']
    P = schema.Plan(raw)
    top = gen_rtl.die_top(P, gen_rtl.bus_epochs(P))
    f = tmp_path / 'top.sv'
    sp = spare_ft.declared(raw)
    masters = {pn: P.ptype(pn)["module"] for pn in sp}
    ties = spare_ft.write_pads(sp, f, top, gen_rtl.sv_id, masters)
    assert ties == {(p, 'extra_i'): "8'd0" for p in sp}
    for p, row in json.loads(Path(str(f) + '.pads.json').read_text())['instances'].items():
        assert row['ports'] == {'extra_i': [[0,7]], 'extra_o': [[0,7]]}
    for mutant in [top.replace("8'd0", "7'd0", 1), top.replace('.extra_o()', '.extra_o(clk)', 1),
                   top.replace(".extra_i(8'd0)", ".extra_i(clk)", 1)]:
        with pytest.raises(ValueError):
            spare_ft.write_pads(sp, f, mutant, gen_rtl.sv_id, masters)
    manifest = gen_rtl.parent_id_manifest(P)
    assert straps.audit_top_ties(top, manifest, spare_ft_ties=ties)['verdict'] == 'PASS'
    illegal = top.replace(".extra_o()", ".extra_o(8'd0)", 1)
    assert straps.audit_top_ties(illegal, manifest, spare_ft_ties=ties)['verdict'] == 'FAIL'


@pytest.mark.skipif(not os.environ.get('OT_BIND_YOSYS') and not shutil.which('docker'), reason='needs Yosys')
@pytest.mark.parametrize("spare_name", ["F_unused", "A_spare_first"])
def test_native_strict_bound_live_and_spare_share_module(tmp_path, spare_name):
    raw = vehicle()
    raw["partitions"][-1]["name"] = spare_name
    # Use the same original as-built sources, including the occupied lane into/out of F.
    raw['asbuilt']['base'] = str(HERE / 'examples/bind_tiny')
    f = tmp_path / 'plan.json'
    f.write_text(json.dumps(raw))
    out = tmp_path / 'out'
    for cmd in ('elab', 'bind', 'verify'):
        opts = ['--strict'] if cmd == 'bind' else []
        assert bind.main([cmd, str(f), '--out', str(out), *opts]) == 0
    read = lambda name: json.loads((out / name).read_text())
    assert read('bind_report.json')['type_splits'] == []
    assert read('verify_report.json')['verdict'] == 'PASS'
    top = (out / 'rtl/bind_tiny_lanes_bound_top.sv').read_text()
    assert top.count('bt_tf ') == 2 and top.count(".y_i(9'd0)") == 1
    assert top.count('.y_o()') == 1
    assert [r for r in read('bind_tie_audit.json')['rows'] if r[0] == spare_name] == [[spare_name,'y_i',"9'd0"]]
    assert [r['bits'] for r in read('bind_declared_ties.json') if r.get('instance') == spare_name] == [list(range(9))]
    assert read('rtl/bind_tiny_lanes_bound_top.sv.pads.json')['instances'][spare_name]['ports'] == {
        'y_i': [[0,8]], 'y_o': [[0,8]]}
    body = (out / 'rtl/bt_tf.sv').read_text()
    assert body.count('ot_dp_st #(.W(8))') == 1 and '.ea(y_i[8])' in body


@pytest.mark.skipif(not os.environ.get('OT_BIND_YOSYS') and not shutil.which('docker'), reason='needs Yosys')
def test_kit_refuses_stale_or_incomplete_spare_ft_bind(tmp_path):
    raw = vehicle()
    raw['asbuilt']['base'] = str(HERE / 'examples/bind_tiny')
    path = tmp_path / 'plan.json'
    path.write_text(json.dumps(raw))
    out = tmp_path / 'bind'
    for cmd in ('elab', 'bind'):
        assert bind.main([cmd, str(path), '--out', str(out)]) == 0
    kit_args = ['kit-rtl', str(path), '--out', str(out), '--type', 'tf', '--kit', str(tmp_path / 'kit')]
    assert bind.main(kit_args) == 0
    details = json.loads((tmp_path / 'kit/kit_rtl.json').read_text())
    assert not details['spare_ft_passthrough'] and not details['spare_out_bits']
    receipt = out / 'bind_declared_ties.json'
    original = receipt.read_text()
    receipt.write_text('[]')
    assert bind.main(kit_args) != 0
    receipt.write_text(original)
    source = out / 'rtl/bt_tf.sv'
    body = source.read_text()
    source.write_text(body.replace('u_ft_y_o_0', 'u_old_y_0'))
    assert bind.main(kit_args) != 0
    source.write_text(body.replace('output wire [8:0] y_o', 'output wire [7:0] y_o'))
    assert bind.main(kit_args) != 0


def test_dormant_landed_slot_ring_pins_allowed_only_with_its_strap():
    """UNIFY-TOOLS-R3 DORMANT: a landed class slot keeps its ring pins on a spare copy when the type declares its
    dormant strap strap_ca_off_<slot>_i; without it the landing role still refuses"""
    p = vehicle()
    pins = [dict(name=n, dir=d, kind=k, layer="M5", xy_um=[1.0, 1.0]) for n, d, k in (
        ("fclk_in_y_i", "in", "clock"), ("cland_fstart_in_y_i", "in", "ctl"), ("fclk_out_y_o", "out", "clock"),
        ("cland_fstart_out_y_o", "out", "ctl"))]
    p['partition_types']['tf']['clock'] = {'landing_contract': {'pins': pins}}
    p['partition_types']['tf']['count_straps'] = [dict(name='strap_ca_k_y_i', width=6)]
    with pytest.raises(ValueError, match='landing or clock role'):
        spare_ft.declared(copy.deepcopy(p))
    p['partition_types']['tf']['count_straps'].append(dict(name='strap_ca_off_y_i', width=1))
    assert list(spare_ft.connections(spare_ft.declared(p)['F_unused'])) == [('y_i', "9'd0"), ('y_o', '')]
    # other landing roles (bands, local collector sources) still refuse
    q = copy.deepcopy(p)
    q['partition_types']['tf']['clock']['landing_contract']['bands'] = {'y_i': {}}
    with pytest.raises(ValueError):
        spare_ft.declared(q)
