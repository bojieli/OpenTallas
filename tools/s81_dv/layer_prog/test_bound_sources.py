"""Synthetic controls of the adopted Codex BoundSources adapter (a475386d8f): exact LSB-first projection, landing date,
and fail-closed cases (strict-bind errors, type splits, missing producer, gapped / stale trace). Not token evidence."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bound_sources import BoundSources  # noqa: E402


def make(tmp, report=None, bits=None):
    (tmp / 'rtl').mkdir(parents=True, exist_ok=True)
    (tmp / 'rtl/s81_bound_top.sv').write_text('module s81_bound_top; endmodule\n')
    (tmp / 'bind_report.json').write_text(json.dumps(report or dict(n_errors=0, errors=[], type_splits={})))
    sb = bits or [['leaf', 'u_a', 'x', 1], ['leaf', 'u_a', 'x', 0], ['leaf', 'u_b', 'y', 0]]
    (tmp / 'bind_latency.json').write_text(json.dumps(dict(buses=[dict(
        lane='l0', src='pa', dst='pb', bus_out='o0', bus_in='i0', width=len(sb), source_bits=sb,
        source_bit_order='lsb_first', bound_stages=5)])))
    return BoundSources(tmp)


def test_project_exact_bits_and_landing(tmp_path):
    b = make(tmp_path)
    r = b.project('l0', {'u_a.x': 0b10, 'u_b.y': 1}, 7)
    assert r['word'] == 0b101 and r['landed_cycle'] == 12 and r['sink_port'] == 'i0'


def test_missing_producer_rejected(tmp_path):
    b = make(tmp_path)
    with pytest.raises(ValueError, match='missing actual producer'):
        b.project('l0', {'u_a.x': 3}, 0)


@pytest.mark.parametrize('report', [dict(n_errors=2, errors=['x']), dict(n_errors=0, errors=[], type_splits={'t': 1})])
def test_non_strict_bind_rejected(tmp_path, report):
    with pytest.raises(ValueError):
        make(tmp_path, report=report)


def test_trace_requires_current_top_and_consecutive_edges(tmp_path):
    b = make(tmp_path)
    top = hashlib.sha256((tmp_path / 'rtl/s81_bound_top.sv').read_bytes()).hexdigest()
    v = {'u_a.x': 1, 'u_b.y': 0}
    ok = b.project_trace('l0', dict(bound_top_sha256=top, samples=[dict(cycle=3, values=v), dict(cycle=4, values=v)]))
    assert [s['landed_cycle'] for s in ok['samples']] == [8, 9]
    with pytest.raises(ValueError, match='consecutive'):
        b.project_trace('l0', dict(bound_top_sha256=top, samples=[dict(cycle=3, values=v), dict(cycle=5, values=v)]))
    with pytest.raises(ValueError, match='not from this current bound top'):
        b.project_trace('l0', dict(bound_top_sha256='0' * 64, samples=[dict(cycle=3, values=v)]))
