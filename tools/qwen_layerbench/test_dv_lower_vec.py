#!/usr/bin/env python3
"""QLB-C4b/3a 10-18 unit tests of tools/qwen_layerbench/dv_lower_vec.py (python3 -m pytest -q, repository root)."""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dv_lower as D      # noqa: E402
import dv_lower_vec as V  # noqa: E402

np = pytest.importorskip('numpy')
AGES = V.ROOT / V.AGES_VEC
need_ages = pytest.mark.skipif(not AGES.exists(), reason='vec_ages.json not measured')


def test_programme_ops_found():
    isa = V.isa_vec()
    assert isa['post_scale_pcs'] == [14, 22] and isa['residual_pcs'] == [15, 23]
    assert isa['head_k'] == 7 and isa['rope_pcs'] == [7, 8, 9, 10]


def test_roles_and_maps():
    own = D.ownership()
    roles = V.qkv_roles(own)
    assert [roles[s]['role'] for s in (0, 2, 4, 6, 8, 10)] == ['q'] * 4 + ['k', 'v']
    V.gu_check(own)
    vm = V.vm_map_vec(own)
    spans = sorted((r['base'], r['base'] + r['size']) for r in vm.values())
    assert all(a[1] <= b[0] for a, b in zip(spans, spans[1:])) and all(r['base'] % 16 == 0 for r in vm.values())


@need_ages
@pytest.mark.parametrize('mode', ['resid', 'qk', 'silu'])
def test_lowering_collision_free(mode):
    lw = V.lower_vec(mode, consts=dict(q_norm=np.ones(128, np.float32), k_norm=np.ones(128, np.float32), pos=7))
    assert not lw['collisions']
    edges = [c['edge'] for c in lw['commands']]
    assert len(edges) == len(set(edges))
    for c in lw['commands']:
        assert D.decode_cmd(int(c['cmd'], 16))['go'] == 1


@need_ages
def test_xslot_mutant_collides():
    assert V.lower_vec('resid', 'xslot')['collisions']
