"""DIE-HEAD-5 TILEIO 10-28: opt-in plan id_straps[].sites_um -> exact strap pins in io.tcl / plan pins / port_bind."""
import json
from pathlib import Path
import pytest
import gen_phys as G
import port_bind_gate as PB
import schema as S

HERE = Path(__file__).parent


def plan(sites=True):
    raw = json.loads((HERE / 'examples/tiny_plan.json').read_text())
    tn = next(iter(raw['partition_types']))
    sp = dict(name='strap_id', width=3)
    if sites:
        sp.update(layer='M7', sites_um=[[10.0 + 2.176 * i, 4.32] for i in range(3)])
    raw['partition_types'][tn]['id_straps'] = [sp]
    return S.Plan(raw), tn


def test_sites_placed_recorded_and_bound():
    P, tn = plan()
    sps = G.strap_pin_sites(P, tn)
    assert [s[0] for s in sps] == ['strap_id[0]', 'strap_id[1]', 'strap_id[2]']
    pins = G.type_pins(P, tn)
    io = G.io_tcl(P, tn, pins)
    for n, ln, x, y in sps:
        assert f"place_pin -pin_name {{{n}}} -layer {ln} -location {{{x:.4f} {y:.4f}}}" in io
    recs = {r['name'] for r in G.plan_pin_records(P, tn, pins)}
    assert {s[0] for s in sps} <= recs
    # port_bind: the strap bits are plan pins (extra 0) and the declared strap is an input
    plan_pins = [dict(bus=b, bit=i) for b, i, *_ in pins] + [dict(bus='strap_id', bit=i) for i in range(3)]
    ports = sorted({b for b, *_ in pins})
    nl = "module top(%s);\n" % ", ".join(ports + ['strap_id'])
    nl += "".join(f"  input [{max(i for bb, i, *_ in pins if bb == b)}:0] {b};\n" for b in ports)
    nl += "  input [2:0] strap_id;\nendmodule\n"
    r = PB.check(nl, 'top', plan_pins, ['strap_id'])
    assert r['extra'] == 0 and r['missing'] == 0 and r['bad_straps'] == []
    r0 = PB.check(nl, 'top', plan_pins[:-3], ['strap_id'])
    assert r0['extra'] == 3                       # without the sites the trial FAIL (extra 18 on hd_tile) returns


def test_opt_in_and_width_mismatch():
    P, tn = plan(sites=False)
    assert G.strap_pin_sites(P, tn) == []
    P, tn = plan()
    P.types[tn]['id_straps'][0]['sites_um'].pop()
    with pytest.raises(ValueError):
        G.strap_pin_sites(P, tn)
