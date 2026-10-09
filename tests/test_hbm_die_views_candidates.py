"""Candidate attention halves must not inherit their absent parent's view."""
import importlib.util
import json
from pathlib import Path
import sys


def test_view_index_binds_only_instantiated_candidate_masters(tmp_path):
    tools = Path(__file__).resolve().parents[1] / 'tools'
    sys.path.insert(0, str(tools))
    spec = importlib.util.spec_from_file_location('candidate_views', tools / 'hbm_die_views.py')
    views = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(views)
    index = tmp_path / 'index.json'
    index.write_text(json.dumps({'masters': {
        'hfd_attn_tile': {'status': 'closed', 'dir': 'parent', 'lef': 'parent.lef'},
        'hfd_attn_half_lo': {'status': 'interim-not-closed', 'dir': 'half', 'lef': 'lo.lef'},
        'hfd_attn_half_hi': {'status': 'missing'},
    }}))
    assert set(views.real_views(index)) == {'hfd_attn_tile', 'hfd_attn_half_lo'}
    bound = views.real_views(index, {'hfd_attn_half_lo', 'hfd_attn_half_hi'})
    assert set(bound) == {'hfd_attn_half_lo'}
    assert bound['hfd_attn_half_lo'] == views.ROOT / 'half/lo.lef'
