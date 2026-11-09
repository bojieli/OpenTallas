"""Packet builder: read-only verdicts, names moved types, never stamps."""
import copy
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import reset_scope_packet as P
from test_native_reset_scope import fixture


def files(tmp_path):
    return {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}


def test_selected_pass_other_type_moved(tmp_path, monkeypatch):
    raw, plan, ab, out = fixture(tmp_path)
    cur = copy.deepcopy(raw); cur['partition_types']['other']['clock']['taps'][0]['x'] = 99
    cp = tmp_path / 'current.json'; cp.write_text(json.dumps(cur))
    monkeypatch.delenv('OT_NATIVE_RESET_SCOPE', raising=False)
    before = files(tmp_path)
    res = P.evaluate(cp, out, ab, ['selected'])
    assert files(tmp_path) == before
    row = res['rows'][0]
    assert (row['default'], row['selected'], row['verdict']) == (False, True, 'SELECTED_PASS')
    assert row['item_env'] == {'OT_NATIVE_RESET_SCOPE': 'selected'}
    assert [m['type'] for m in res['moved_reset_types']] == ['other']
    assert all(res['receipt_reproduced'].values())
    assert 'OT_NATIVE_RESET_SCOPE' not in os.environ


def test_own_type_moved_needs_rebind(tmp_path, monkeypatch):
    raw, plan, ab, out = fixture(tmp_path)
    cur = copy.deepcopy(raw); cur['partition_types']['selected']['reset']['depth'] = 9
    cp = tmp_path / 'current.json'; cp.write_text(json.dumps(cur))
    res = P.evaluate(cp, out, ab, ['selected', 'nope'])
    assert res['rows'][0]['verdict'] == 'REBIND_NEEDED' and 'item_env' not in res['rows'][0]
    assert res['rows'][0]['own_reset_moved']
    assert res['rows'][1]['verdict'] == 'NOT_A_TYPE'
    assert P.main([str(cp), str(out), '--asbuilt', str(ab), '--items', 'selected']) == 3


def test_fresh_bind_is_already_fresh(tmp_path):
    raw, plan, ab, out = fixture(tmp_path)
    res = P.evaluate(plan, out, ab, ['selected'])
    assert res['rows'][0]['verdict'] == 'ALREADY_FRESH' and res['moved_reset_types'] == []
