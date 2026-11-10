"""S81 RCK2-1109: opt-in second entries of an input pad clock (pad_clock.check_entries / entries_tcl, the
delta_rck2_1109 trunk geometry).  Absent entries keep every existing pad-clock output unchanged."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pad_clock as PC  # noqa: E402
import schema  # noqa: E402
from test_pad_clock import plan  # noqa: E402

ENTRY = dict(name='pma_rck_e1', xy_um=[300.0, 40.0], stations_um=[[10.016, 30.0], [210.0, 30.0]],
             cell='BUFx24_ASAP7_75t_R', region_um=[[0.0, 0.0, 400.0, 60.0]],
             sink_pins=[dict(module='native_mem', pin='clk')], evidence='unit test trunk')


def eplan(**over):
    p = plan()
    e = copy.deepcopy(ENTRY)
    e.update(over)
    p.types['mid']['clock']['pad_clock']['pins'][0]['entries'] = [e]
    return p


def test_absent_entries_emit_nothing():
    p = plan()
    assert PC.entries(p, 'mid') == [] and PC.entries_tcl(p, 'mid') == ''


def test_declared_entry_validates_and_emits_hook_data():
    p = eplan()
    w, h = p.types['mid']['outline_um']
    assert w > 400 and h > 60, 'fixture outline must hold the test trunk'
    (port, e), = PC.entries(p, 'mid')
    assert port == 'pma_rck' and e['name'] == 'pma_rck_e1'
    tcl = PC.entries_tcl(p, 'mid')
    assert tcl.count('set ::pce_entries {') == 1 and 'source /work/pad_clock_entry.tcl' in tcl
    assert ('{pma_rck pma_rck_e1 BUFx24_ASAP7_75t_R {{10.0160 30.0000} {210.0000 30.0000}} {300.0000 40.0000} '
            '{{0.0000 0.0000 400.0000 60.0000}} {{native_mem clk}}}') in tcl
    # the sidecar carries the entries (kit_contract / face_guard read name/dir/layer/xy only)
    assert PC.pins(p, 'mid')[0]['entries'][0]['cell'] == 'BUFx24_ASAP7_75t_R'


@pytest.mark.parametrize('fault', ['long-hop', 'outside', 'undeclared-sink', 'bad-region', 'port-name', 'output-pin',
                                   'extra-key', 'no-evidence', 'dup-name'])
def test_bad_entry_fails_closed(fault):
    p = eplan()
    pins = p.types['mid']['clock']['pad_clock']['pins']
    e = pins[0]['entries'][0]
    if fault == 'long-hop': e['xy_um'] = [700.0, 40.0]                      # 210 -> 700: 500 um > 405
    if fault == 'outside': e['xy_um'] = [-1.0, 40.0]
    if fault == 'undeclared-sink': e['sink_pins'] = [dict(module='other', pin='clk')]
    if fault == 'bad-region': e['region_um'] = [[10.0, 0.0, 5.0, 60.0]]
    if fault == 'port-name': e['name'] = 'pma_tck'
    if fault == 'output-pin': pins[1]['entries'] = [copy.deepcopy(e)]
    if fault == 'extra-key': e['note'] = 'x'
    if fault == 'no-evidence': e['evidence'] = ' '
    if fault == 'dup-name': pins[0]['entries'].append(dict(copy.deepcopy(e), sink_pins=[]))
    with pytest.raises(ValueError):
        PC.entries(p, 'mid')


def test_schema_accepts_entries():
    ent = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"][
        "properties"]["pad_clock"]["properties"]["pins"]["items"]["properties"]["entries"]
    assert set(ent["items"]["required"]) == PC.ENTRY_KEYS
    static = json.loads(HERE.joinpath('die_plan.schema.json').read_text())
    assert 'entries' in json.dumps(static["properties"]["partition_types"]["additionalProperties"]["properties"]
                                   ["clock"]["properties"]["pad_clock"])


def test_hook_moves_by_region_and_identity_without_dont_touch():
    body = HERE.joinpath('pad_clock_entry.tcl').read_text()
    assert 'pce_in $px $py $regions' in body and 'dict exists $want $key' in body
    # t14 probe 11-09: dont_touch trunk cells/nets break TritonCTS (ODB-0370) and -repair_clock_nets (RSZ-3006)
    assert 'setDoNotTouch' not in body
    assert 'moved no sink' in body and 'not on the pad net' in body


def _delta():
    path = HERE.parents[1] / 'physical' / 'die_plan' / 's81' / 'delta_rck2_1109.py'
    spec = importlib.util.spec_from_file_location('delta_rck2_1109', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_delta_trunk_points_are_even_and_within_reach():
    D = _delta()
    s0, corner, end = [257.952, 935.16], [257.952, 328.82], [1225.044, 328.82]
    pts = D.l_points(s0, corner, end, 4)
    assert pts[-1] == end and len(pts) == 4
    chain = [s0] + pts
    hops = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(chain, chain[1:])]
    assert max(hops) - min(hops) < 0.01 and max(hops) <= D.HOP_UM < PC.ENTRY_HOP_UM
    assert D.CELL == 'BUFx24_ASAP7_75t_R' and D.ENTRY == 'io_pma_rck_e1'
