import argparse
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import dsrom_bf_geometry_alloc as A
import dsrom_s81_fulldie as F


@pytest.fixture(autouse=True)
def restore_default_geometry():
    yield
    F.apply_options(F.die_options(argparse.ArgumentParser()).parse_args([]))


@pytest.mark.parametrize('pairs', [1792, 2048, 2304])
@pytest.mark.parametrize('dedicated', [False, True])
def test_compiler_bf_identity_matches_floorplan(pairs, dedicated):
    args = F.die_options(argparse.ArgumentParser()).parse_args(
        ['--gen', 'r8', '--die', 'layer1', '--pairs', str(pairs), '--bf-per-region', '4'])
    F.apply_options(args)
    pool = A.FlavourPool('bf', pairs, 4, dedicated)
    assert pool.bf == F.bf_sites() == {i * pairs // 512 for i in range(512)}
    for r in range(128):
        assert len(pool.byreg[(r, 'bf16')]) == 4
        if dedicated:
            assert not (set(pool.byreg[(r, 'q')]) & pool.bf)
        else:
            assert set(pool.byreg[(r, 'bf16')]) <= set(pool.byreg[(r, 'q')])


def test_q_only_stage_does_not_reserve_bf_sites():
    pool = A.FlavourPool('q', 1792, 4)
    assert not pool.bf
    assert sum(len(pool.byreg[(r, 'q')]) for r in range(128)) == 1792
