"""rd1 hub response calendar shift (default off): helper, loop wrap, DONE/other bits unmoved, off = identical."""
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('vm_calendar', TOOLS / 'hbm_vm_static_calendar.py')
VM = importlib.util.module_from_spec(spec); spec.loader.exec_module(VM)
RESP = VM.RESPONSE_FIELDS


def layout():
    widths = dict(client_seq=10, response_enable=5, response_seq=10, bank_enable=8, bank_client=24,
                  hub_ring_enable=2, hub_ring_client=6, rslot_v=8, wslot_v=8, rslot=24, wslot=24,
                  ring_tx_enable=2, ring_tx_source=6, replay_enable=1, replay_source=1,
                  lg_local_read=24, lg_local_write=24)
    fields, lo = [], 0
    for name in VM.FIELDS:
        fields.append(dict(name=name, lo=lo, bits=widths[name])); lo += widths[name]
    return dict(quadrant='SW', params=dict(RG=5, WG=2, NC=2, RB=3, WB=3, CW=3), fields=fields)


def rows():
    return [dict(client_seq=1, bank_enable=0x0f),
            dict(response_enable=0b10000, response_seq=0b11 << 8, bank_enable=0x03, rslot_v=1),
            dict(wslot_v=2),
            dict(response_enable=0b10000, response_seq=1 << 8, replay_enable=1)]


def strip(r):
    return {k: v for k, v in r.items() if k not in RESP}


def test_n0_is_a_noop_copy():
    r = rows()
    out = VM.shift_response(r, 0)
    assert out == r and out is not r and out[0] is not r[0]


def test_moves_only_response_fields_and_wraps_with_one_pad_row():
    r = rows()
    out = VM.shift_response(copy.deepcopy(r), 1)
    assert len(out) == len(r) + 1                                  # last row carried a response -> one pad row
    for i, row in enumerate(r):
        assert strip(out[i]) == strip(row)                         # every other field stays in its own row
    assert out[0].get('response_enable') is None
    assert (out[2]['response_enable'], out[2]['response_seq']) == (0b10000, 0b11 << 8)
    assert (out[4]['response_enable'], out[4]['response_seq']) == (0b10000, 1 << 8)
    assert strip(out[4]) == {}                                     # pad row carries nothing else


def test_no_pad_row_when_last_row_has_no_response():
    r = rows()[:3]
    out = VM.shift_response(r, 1)
    assert len(out) == 3 and out[2]['response_enable'] == 0b10000


def test_zero_valued_response_is_not_a_response():
    r = [dict(response_enable=0, response_seq=0, bank_enable=1)]
    assert len(VM.shift_response(r, 1)) == 1


def test_negative_rejected():
    with pytest.raises(ValueError):
        VM.shift_response(rows(), -1)


def test_packed_words_shift_equals_dict_shift():
    spec = layout()
    r = rows()
    dict_packed = [VM.pack(spec, x) for x in VM.shift_response(copy.deepcopy(r), 1)]
    int_packed = VM.shift_response([VM.pack(spec, x) for x in r], 1, spec=spec)
    assert dict_packed == int_packed


def test_compile_off_and_zero_identical_on_shift_adds_pad_and_keeps_other_bits():
    spec = layout()
    s = dict(base=3, loops=2, cycles=rows())
    base = VM.compile_schedule(spec, s)
    zero = VM.compile_schedule(spec, dict(s, resp_shift=0))
    assert json.dumps(base) == json.dumps(zero)
    assert 'resp_shift' not in base
    on = VM.compile_schedule(spec, dict(s, resp_shift=1))
    assert on['resp_shift']['pad_rows'] == 1
    assert on['output_edges'] == 5 * 2 and base['output_edges'] == 4 * 2      # output edge count follows the pad row
    assert on['start']['limit'] == base['start']['limit'] + 1
    mask = 0
    for f in spec['fields']:
        if f['name'] in RESP:
            mask |= ((1 << f['bits']) - 1) << f['lo']
    for a, b in zip(base['configuration_writes'], on['configuration_writes']):
        assert (int(a['data'], 16) & ~mask) == (int(b['data'], 16) & ~mask)   # DONE/ordinal/other bits unmoved
    assert int(on['configuration_writes'][-1]['data'], 16) & ~mask == 0xc7a1 << 240 | (3 + 4) << 224


def test_negative_schedule_shift_rejected():
    with pytest.raises(ValueError):
        VM.compile_schedule(layout(), dict(cycles=rows(), resp_shift=-1))


def test_idx_calendar_a_event_only_moves_responses():
    sys.path.insert(0, str(TOOLS))
    import hbm_layer_vehicle.idx_images as II
    ev = [('R', 3, 1), ('H', 5, 1), ('P', 7, 1), ('A', 9, 0), ('A', 10, 1)]
    words = II.calendar_words(ev, 0)
    out = VM.shift_response(words, 1)
    assert len(out) == len(words) + 1
    for i, w in enumerate(words):
        assert strip(out[i]) == strip(w)
    assert out[10]['response_enable'] == words[9]['response_enable']
    assert out[11]['response_enable'] == words[10]['response_enable']
